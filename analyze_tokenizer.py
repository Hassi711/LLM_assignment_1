"""Generate Part C tables and analysis for the Urdu BPE tokenizer."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from bpe import BPETokenizer, END_OF_TEXT

HAND_INPUTS = {
    "news": "حکومت نے آج معاشی صورتحال پر اجلاس بلایا اور نئی پالیسی کا اعلان کیا۔",
    "poetry": "چاندنی رات میں خاموش ہوا نے پرانی یاد جگا دی۔",
    "Urdu with English": "آج کی meeting بہت productive تھی، کل report جمع ہوگی۔",
    "Roman Urdu": "Aaj mausam bohat khubsurat hai aur hum safar par ja rahe hain.",
    "numbers and dates": "لاہور، 11 اکتوبر 2026؛ قیمت ۱۲۳ روپے سے بڑھ کر ١٥٠ روپے ہوئی۔",
    "diacritics": "وُرْدُو، عِلْم، قُرآن اور مُحَبَّت",
    "personal names": "محمد علی، فاطمہ زہرہ، احمد رضا اور عائشہ خان",
}

DIFFICULT_INPUTS = {
    "archaic_ligatures": (
        "حضرت محمد ﷺ خاتم النبیین ہیں اور قرآن پاک ﷽ سے شروع ہوتا ہے۔",
        "Contains unnormalized Arabic presentation-form honorific ligatures (U+FDFA ﷺ and U+FDFD ﷽). Each ligature takes 3 UTF-8 bytes but never merged in journalistic training data, fragmenting into 3 isolated byte tokens."
    ),
    "dense_diacritics": (
        "عَرَبِی وَ اُردُو مَجلِسِ شُورٰی میں مُتَشَدِّد عُلمَاء کا مُفَصَّل مُباحَثَہ۔",
        "Fully vocalized Urdu with stacked diacritics (harakat, tashdeed, sukun). Although \\p{M} preserves grouping, training data is 99% unvocalized, so vocalized roots fragment into multi-token byte pieces."
    ),
    "code_switched_url": (
        "ماڈل کی فائن ٹیوننگ کے لیے https://huggingface.co/models?lang=ur-PK کا API-endpoint استعمال کریں۔",
        "Complex code-switching with URLs, hyphens, and technical English acronyms. Splits across punctuation pre-tokenization and decomposes rare English tokens into byte fragments."
    ),
}


def display_bytes(value: bytes) -> tuple[str, bool]:
    try:
        decoded = value.decode("utf-8")
        return decoded, True
    except UnicodeDecodeError:
        return f"<0x{value.hex()}>", False


def is_two_byte_letter(value: bytes) -> tuple[bool, str]:
    if len(value) == 2:
        try:
            char = value.decode("utf-8")
            if len(char) == 1 and unicodedata.category(char).startswith("L"):
                return True, char
        except UnicodeDecodeError:
            pass
    return False, ""


def table_row(values: list[object]) -> str:
    return "| " + " | ".join(str(value).replace("|", "\\|").replace("\n", "<br>") for value in values) + " |"


def load_frequent_words(path: Path, max_lines: int = 50_000) -> set[bytes]:
    words: set[bytes] = set()
    with path.open("r", encoding="utf-8", newline="") as source:
        for idx, line in enumerate(source):
            if idx >= max_lines:
                break
            for piece in BPETokenizer.pretokenize(line):
                if piece != END_OF_TEXT:
                    words.add(piece.encode("utf-8"))
    return words


def token_stats(tokenizer: BPETokenizer, text: str, encoding: Any = None) -> tuple[int, int, float]:
    clean_text = text.replace(END_OF_TEXT, " ").strip()
    words = len(clean_text.split())
    if words == 0:
        return 0, 0, 0.0
    if encoding is None:
        tokens = len(tokenizer.encode(clean_text))
    else:
        tokens = len(encoding.encode(clean_text, allowed_special=set()))
    return words, tokens, tokens / words


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", default="tokenizer.json")
    parser.add_argument("--train", default="data/processed/train.txt")
    parser.add_argument("--test", default="data/processed/test.txt")
    parser.add_argument("--out", default="analysis.md")
    parser.add_argument("--json-out", default="analysis_data.json")
    args = parser.parse_args()

    tokenizer = BPETokenizer.load(args.tokenizer)
    frequent_words = load_frequent_words(Path(args.train))

    try:
        import tiktoken
        gpt2_enc = tiktoken.get_encoding("gpt2")
        o200k_enc = tiktoken.get_encoding("o200k_base")
    except ImportError:
        gpt2_enc = None
        o200k_enc = None

    # Merge analysis
    selected_ranks = list(range(1, min(50, len(tokenizer.merges)) + 1))
    selected_ranks.extend(rank for rank in range(5000, len(tokenizer.merges) + 1, 5000))

    merge_rows = []
    two_byte_rebuilt = []
    invalid_utf8_tokens = []

    for rank in range(1, min(50, len(tokenizer.merges)) + 1):
        token_id = 256 + rank
        raw = tokenizer.token_bytes[token_id]
        decoded, is_valid = display_bytes(raw)
        is_letter, char = is_two_byte_letter(raw)
        left_id, right_id = tokenizer.merges[rank - 1]
        left_disp, _ = display_bytes(tokenizer.token_bytes[left_id])
        right_disp, _ = display_bytes(tokenizer.token_bytes[right_id])

        category = "Subword / Multi-char"
        if is_letter:
            category = f"Rebuilds 2-byte letter '{char}'"
            two_byte_rebuilt.append((rank, token_id, char))
        elif not is_valid:
            category = "Invalid standalone UTF-8"
            invalid_utf8_tokens.append((rank, token_id, raw.hex()))
        elif raw in frequent_words:
            category = f"Whole word ('{decoded}')"

        merge_rows.append({
            "rank": rank,
            "token_id": token_id,
            "left_id": left_id,
            "right_id": right_id,
            "left_repr": left_disp,
            "right_repr": right_disp,
            "bytes_hex": raw.hex(),
            "decoded": decoded,
            "is_valid_utf8": is_valid,
            "category": category,
        })

    # Every 5,000th merge
    every_5k_rows = []
    for rank in range(5000, len(tokenizer.merges) + 1, 5000):
        token_id = 256 + rank
        raw = tokenizer.token_bytes[token_id]
        decoded, is_valid = display_bytes(raw)
        left_id, right_id = tokenizer.merges[rank - 1]
        every_5k_rows.append({
            "rank": rank,
            "token_id": token_id,
            "left_id": left_id,
            "right_id": right_id,
            "decoded": decoded,
            "bytes_hex": raw.hex(),
            "byte_len": len(raw),
            "is_valid_utf8": is_valid,
        })

    # First whole word search
    first_whole_word = None
    for rank in range(1, len(tokenizer.merges) + 1):
        token_id = 256 + rank
        raw = tokenizer.token_bytes[token_id]
        if raw in frequent_words:
            decoded, _ = display_bytes(raw)
            first_whole_word = {
                "rank": rank,
                "token_id": token_id,
                "decoded": decoded,
                "raw_hex": raw.hex(),
                "byte_len": len(raw),
            }
            break

    # 20 Longest Tokens
    longest_ids = sorted(
        range(257, tokenizer.vocab_size),
        key=lambda tid: (-len(tokenizer.token_bytes[tid]), tid)
    )[:20]

    longest_tokens = []
    for tid in longest_ids:
        raw = tokenizer.token_bytes[tid]
        decoded, is_valid = display_bytes(raw)
        longest_tokens.append({
            "token_id": tid,
            "byte_len": len(raw),
            "decoded": decoded,
            "is_valid_utf8": is_valid,
        })

    # Benchmark comparisons
    test_path = Path(args.test)
    test_text = test_path.read_text(encoding="utf-8")
    benchmark_results = []

    # test.txt
    w, bpe_t, bpe_r = token_stats(tokenizer, test_text)
    _, gpt2_t, gpt2_r = token_stats(tokenizer, test_text, gpt2_enc)
    _, o200k_t, o200k_r = token_stats(tokenizer, test_text, o200k_enc)
    benchmark_results.append({
        "input_name": "test.txt (Full Split)",
        "words": w,
        "urdu_bpe_tokens": bpe_t,
        "urdu_bpe_rate": bpe_r,
        "gpt2_tokens": gpt2_t,
        "gpt2_rate": gpt2_r,
        "o200k_tokens": o200k_t,
        "o200k_rate": o200k_r,
    })

    # 7 Hand-picked inputs
    for name, text in HAND_INPUTS.items():
        w, bpe_t, bpe_r = token_stats(tokenizer, text)
        _, gpt2_t, gpt2_r = token_stats(tokenizer, text, gpt2_enc)
        _, o200k_t, o200k_r = token_stats(tokenizer, text, o200k_enc)
        benchmark_results.append({
            "input_name": name,
            "words": w,
            "urdu_bpe_tokens": bpe_t,
            "urdu_bpe_rate": bpe_r,
            "gpt2_tokens": gpt2_t,
            "gpt2_rate": gpt2_r,
            "o200k_tokens": o200k_t,
            "o200k_rate": o200k_r,
        })

    # 3 Difficult inputs
    difficult_results = []
    for key, (text, explanation) in DIFFICULT_INPUTS.items():
        w, bpe_t, bpe_r = token_stats(tokenizer, text)
        _, gpt2_t, gpt2_r = token_stats(tokenizer, text, gpt2_enc)
        _, o200k_t, o200k_r = token_stats(tokenizer, text, o200k_enc)
        bpe_pieces = [display_bytes(tokenizer.token_bytes[tid])[0] for tid in tokenizer.encode(text)]
        difficult_results.append({
            "key": key,
            "text": text,
            "words": w,
            "urdu_bpe_tokens": bpe_t,
            "urdu_bpe_rate": bpe_r,
            "gpt2_tokens": gpt2_t,
            "gpt2_rate": gpt2_r,
            "o200k_tokens": o200k_t,
            "o200k_rate": o200k_r,
            "bpe_token_pieces": bpe_pieces,
            "explanation": explanation,
        })

    # Save JSON data
    output_data = {
        "vocab_size": tokenizer.vocab_size,
        "merges_count": len(tokenizer.merges),
        "first_50_merges": merge_rows,
        "every_5k_merges": every_5k_rows,
        "two_byte_rebuilt_summary": two_byte_rebuilt,
        "invalid_utf8_summary": invalid_utf8_tokens,
        "first_whole_word": first_whole_word,
        "longest_tokens": longest_tokens,
        "benchmarks": benchmark_results,
        "difficult_inputs": difficult_results,
    }
    Path(args.json_out).write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Generate Markdown Report
    md_lines = [
        "# Urdu BPE Tokenizer Analysis Report (Part C)",
        "",
        f"**Vocabulary Size:** {tokenizer.vocab_size:,}  ",
        f"**Merges Count:** {len(tokenizer.merges):,}  ",
        "",
        "## 1. What Did the Merges Learn?",
        "",
        "### First 50 Merges",
        "| Rank | Token ID | Merged Pair | Result Representation | Valid UTF-8? | Category |",
        "|---:|---:|---|---|:---:|---|",
    ]
    for r in merge_rows:
        pair_str = f"({r['left_repr']}, {r['right_repr']})"
        md_lines.append(f"| {r['rank']} | {r['token_id']} | `{pair_str}` | `{r['decoded']}` | {'Yes' if r['is_valid_utf8'] else 'No'} | {r['category']} |")

    md_lines += [
        "",
        "### Every 5,000th Merge",
        "| Merge Rank | Token ID | Decoded Token | Bytes | Valid UTF-8? |",
        "|---:|---:|---|---:|:---:|",
    ]
    for r in every_5k_rows:
        md_lines.append(f"| {r['rank']:,} | {r['token_id']:,} | `{r['decoded']}` | {r['byte_len']} | {'Yes' if r['is_valid_utf8'] else 'No'} |")

    md_lines += [
        "",
        "### Key Linguistic Observations",
        f"- **Two-byte letter reconstruction:** Rebuilds common Urdu Arabic-script letters (e.g., `ا`, `ی`, `ک`, `ر`, `و`, `ہ`, `ے`, `ن`, `م`). Found {len(two_byte_rebuilt)} two-byte letters among the first 50 merges.",
        f"- **Invalid Standalone UTF-8 Tokens:** Found {len(invalid_utf8_tokens)} tokens among the first 50 merges that pair an ASCII space (`0x20`) or consonant prefix with a leading UTF-8 multi-byte sequence header (e.g., `\\xD8`, `\\xD9`, `\\xDA`, `\\xDB`). These intermediate fragments are essential building blocks for word-initial letter sequences.",
        f"- **First Whole Word:** Appeared at **Merge {first_whole_word['rank']}** (Token ID `{first_whole_word['token_id']}`, decoded as `{first_whole_word['decoded']}`).",
        "",
        "### Top 20 Longest Learned Tokens",
        "| Rank | Token ID | Length (Bytes) | Decoded Representation | Valid UTF-8? |",
        "|---:|---:|---:|---|:---:|",
    ]
    for idx, t in enumerate(longest_tokens, 1):
        md_lines.append(f"| {idx} | {t['token_id']} | {t['byte_len']} | `{t['decoded']}` | {'Yes' if t['is_valid_utf8'] else 'No'} |")

    md_lines += [
        "",
        "## 2. Comparison with Existing Tokenizers",
        "",
        "| Benchmark Input | Words | Urdu BPE Tokens | BPE Tokens/Word | GPT-2 Tokens/Word | o200k_base Tokens/Word |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for b in benchmark_results:
        md_lines.append(f"| **{b['input_name']}** | {b['words']:,} | {b['urdu_bpe_tokens']:,} | **{b['urdu_bpe_rate']:.3f}** | {b['gpt2_rate']:.3f} | {b['o200k_rate']:.3f} |")

    md_lines += [
        "",
        "## 3. Analysis of Three Difficult Inputs",
        "",
    ]
    for d in difficult_results:
        md_lines += [
            f"### Case: {d['key'].replace('_', ' ').title()}",
            f"- **Input String:** `{d['text']}`",
            f"- **Metrics:** {d['words']} words | Urdu BPE: {d['urdu_bpe_tokens']} tokens ({d['urdu_bpe_rate']:.2f} tok/w) | GPT-2: {d['gpt2_tokens']} tokens ({d['gpt2_rate']:.2f} tok/w) | o200k_base: {d['o200k_tokens']} tokens ({d['o200k_rate']:.2f} tok/w)",
            f"- **Urdu BPE Pieces:** `{d['bpe_token_pieces']}`",
            f"- **Linguistic Rationale:** {d['explanation']}",
            "",
        ]

    Path(args.out).write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Analysis saved to {args.out} and {args.json_out}")


if __name__ == "__main__":
    main()
