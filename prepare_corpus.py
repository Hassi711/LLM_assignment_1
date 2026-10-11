"""Clean source documents, deduplicate, split by document, and build a data card.

Input sources must first be registered in sources.csv. Large archives (.zip/.tar)
should be extracted into data/raw/ before running this script.
"""
from __future__ import annotations

import argparse
import bz2
import csv
import fnmatch
import gzip
import hashlib
import html
import json
import lzma
import math
import random
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterator, TextIO

from normalize import normalize

EOT = "<|endoftext|>"
EOT_OVERHEAD = len(("\n" + EOT + "\n").encode("utf-8"))
URDU_SCRIPT = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")

# These patterns target common navigation/boilerplate, not ordinary Urdu prose.
_BOILERPLATE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in [
        r"\bread more\b", r"\brelated articles?\b", r"\byou may also like\b",
        r"\bshare (this article|on facebook|on twitter|on whatsapp)\b",
        r"\bsubscribe (now|to our newsletter)\b", r"\badvertisement\b",
        r"\bclick here\b", r"\baccept (all )?cookies\b", r"\bprivacy policy\b",
        r"\bterms of (use|service)\b", r"\ball rights reserved\b",
        r"\bfollow us\b", r"\bview comments\b", r"\bpost a comment\b",
        r"مزید پڑھیں", r"متعلقہ خبریں", r"اشتہار", r"تبصرے ارسال کریں",
        r"ہمیں فالو کریں", r"شیئر کریں", r"رازداری کی پالیسی", r"تمام حقوق محفوظ ہیں",
    ]
]

TEXT_KEY_HINTS = ("text", "content", "article", "body", "story", "extract", "paragraph", "description", "urdu", "news", "fulltext", "full_text", "document")
TITLE_KEYS = {"title", "headline", "heading", "name"}
BAD_KEY_HINTS = ("url", "link", "date", "time", "author", "category", "label", "class", "id", "tag", "source", "license", "licence")


def logical_suffix(path: Path) -> str:
    name = path.name.lower()
    for suffix in (".gz", ".bz2", ".xz"):
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    return Path(name).suffix.lower()


def open_text(path: Path) -> TextIO:
    lower = path.name.lower()
    if lower.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8-sig", errors="replace", newline="")
    if lower.endswith(".bz2"):
        return bz2.open(path, "rt", encoding="utf-8-sig", errors="replace", newline="")
    if lower.endswith(".xz"):
        return lzma.open(path, "rt", encoding="utf-8-sig", errors="replace", newline="")
    return path.open("r", encoding="utf-8-sig", errors="replace", newline="")


def _key_norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _find_text_field(keys: list[str]) -> str | None:
    scored: list[tuple[int, str]] = []
    for original in keys:
        key = _key_norm(original)
        score = 0
        if key in {"text", "content", "articletext", "articlebody", "body", "urdu_text", "news_text", "fulltext", "full_text"}:
            score += 100
        for hint in TEXT_KEY_HINTS:
            if hint.replace("_", "") in key:
                score += 20
        for hint in BAD_KEY_HINTS:
            if hint.replace("_", "") in key:
                score -= 18
        if key in {"title", "headline", "heading", "name"}:
            score -= 25
        if score > 0:
            scored.append((score, original))
    return max(scored)[1] if scored else None


def record_text(record: object) -> str:
    if isinstance(record, str):
        return record
    if isinstance(record, list):
        chunks = [record_text(item) for item in record]
        return "\n".join(chunk for chunk in chunks if chunk)
    if not isinstance(record, dict):
        return ""
    keys = [str(k) for k, v in record.items() if isinstance(v, str) and v.strip()]
    text_key = _find_text_field(keys)
    parts: list[str] = []
    if text_key:
        parts.append(record[text_key])
        for key in keys:
            if _key_norm(key) in TITLE_KEYS and record[key] and record[key] != record[text_key]:
                parts.insert(0, record[key])
                break
    else:
        # Conservative fallback: choose the longest text field likely to contain prose.
        candidates = [(len(str(record[k])), str(k), str(record[k])) for k in keys
                      if not any(h in _key_norm(k) for h in BAD_KEY_HINTS)]
        if candidates:
            parts.append(max(candidates)[2])
    return "\n".join(parts)


def _has_blank_line(path: Path) -> bool:
    # Treat blank lines as paragraph separators only when text occurs after one;
    # a lone trailing newline/blank line must not turn sentence-per-line corpora
    # into one-document-per-line datasets.
    saw_content = False
    saw_blank_after_content = False
    with open_text(path) as f:
        for line in f:
            if not line.strip():
                if saw_content:
                    saw_blank_after_content = True
                continue
            if saw_blank_after_content:
                return True
            saw_content = True
    return False


def iter_txt_documents(path: Path, lines_per_document: int = 100) -> Iterator[str]:
    # If paragraph separators exist, preserve paragraphs as document-like units.
    # Sentence-per-line corpora without original document boundaries are grouped
    # into fixed-size blocks rather than randomly splitting individual lines.
    paragraph_mode = _has_blank_line(path)
    with open_text(path) as f:
        if paragraph_mode:
            buffer: list[str] = []
            for line in f:
                if not line.strip():
                    if buffer:
                        yield "".join(buffer)
                        buffer = []
                else:
                    buffer.append(line)
            if buffer:
                yield "".join(buffer)
        else:
            buffer = []
            for line in f:
                if line.strip():
                    buffer.append(line)
                if len(buffer) >= lines_per_document:
                    yield "".join(buffer)
                    buffer = []
            if buffer:
                yield "".join(buffer)


def iter_documents(path: Path) -> Iterator[str]:
    suffix = logical_suffix(path)
    if suffix in {".txt", ".text", ".md"}:
        yield from iter_txt_documents(path)
        return
    if suffix in {".jsonl", ".ndjson"}:
        with open_text(path) as f:
            for line_number, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    print(f"WARNING: skipping malformed JSON at {path}:{line_number}", file=sys.stderr)
                    continue
                body = record_text(record)
                if body.strip():
                    yield body
        return
    if suffix == ".csv" or suffix == ".tsv":
        delimiter = "\t" if suffix == ".tsv" else ","
        with open_text(path) as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            if not reader.fieldnames:
                return
            text_field = _find_text_field([str(x) for x in reader.fieldnames])
            if not text_field:
                raise ValueError(f"Could not identify a text column in {path}; columns={reader.fieldnames}")
            print(f"CSV {path.name}: text column selected as {text_field!r}")
            title_field = next((col for col in reader.fieldnames if _key_norm(col) in TITLE_KEYS), None)
            for row in reader:
                body = str(row.get(text_field) or "").strip()
                title = str(row.get(title_field) or "").strip() if title_field else ""
                if title and title != body:
                    body = title + "\n" + body
                if body.strip():
                    yield body
        return
    if suffix in {".html", ".htm", ".xml"}:
        try:
            from bs4 import BeautifulSoup
        except ImportError as exc:
            raise RuntimeError("Install beautifulsoup4 to process HTML/XML files.") from exc
        with open_text(path) as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        for node in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            node.decompose()
        body = soup.get_text("\n")
        if body.strip():
            yield body
        return
    # Do not silently interpret compressed archives or arbitrary binary files as text.
    raise ValueError(f"Unsupported file type: {path}. Extract archives first; supported: TXT, CSV, TSV, JSONL, HTML.")


def remove_known_boilerplate(text: str) -> tuple[str, int, int]:
    kept: list[str] = []
    removed = 0
    removed_bytes = 0
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line_clean = html.unescape(line).strip()
        if not line_clean:
            kept.append("")
            continue
        if any(pattern.search(line_clean) for pattern in _BOILERPLATE_PATTERNS):
            removed += 1
            removed_bytes += len(line.encode("utf-8", errors="replace"))
            continue
        kept.append(line_clean)
    return "\n".join(kept), removed, removed_bytes


def urdu_stats(text: str) -> tuple[int, int, float]:
    script_chars = len(URDU_SCRIPT.findall(text))
    letters_and_marks = sum(1 for ch in text if unicodedata.category(ch)[0] in {"L", "M"})
    ratio = script_chars / max(1, letters_and_marks)
    return script_chars, letters_and_marks, ratio


def load_sources(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"No source rows found in {csv_path}")
    required = {"file_pattern", "source_id", "source_name", "genre", "url", "license", "collection_date", "priority", "source_cap_mib", "notes"}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"sources.csv is missing columns: {sorted(missing)}")
    return sorted(rows, key=lambda r: int(r.get("priority") or 999))


def match_source(path: Path, sources: list[dict[str, str]]) -> dict[str, str] | None:
    matches = [s for s in sources if fnmatch.fnmatch(path.name.lower(), s["file_pattern"].strip().lower())]
    if not matches:
        return None
    return max(matches, key=lambda r: len(r["file_pattern"]))


def bytes_mib(value: int) -> str:
    return f"{value / (1024 * 1024):.2f} MiB"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--out-dir", default="data/processed")
    parser.add_argument("--sources", default="sources.csv")
    parser.add_argument("--target-mib", type=float, default=520.0,
                        help="Target aggregate output text size, including document markers; default 520 MiB.")
    parser.add_argument("--min-urdu-ratio", type=float, default=0.35,
                        help="Minimum Arabic-script characters / all Unicode letters and marks (default 0.35).")
    parser.add_argument("--min-urdu-chars", type=int, default=20)
    parser.add_argument("--seed", type=int, default=4172026)
    parser.add_argument("--work-dir", default="work")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.out_dir)
    work_dir = Path(args.work_dir)
    sources_path = Path(args.sources)
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw directory not found: {raw_dir}")
    if not sources_path.exists():
        raise FileNotFoundError(f"Sources manifest not found: {sources_path}. Copy sources.csv.template to sources.csv first.")
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    sources = load_sources(sources_path)
    source_stats: dict[str, dict[str, object]] = {}
    for s in sources:
        source_stats[s["source_id"]] = {
            "source_id": s["source_id"], "source_name": s["source_name"], "genre": s["genre"],
            "file_pattern": s["file_pattern"], "raw_file_bytes": 0, "raw_text_bytes_seen": 0,
            "input_documents_seen": 0, "known_boilerplate_lines_removed": 0,
            "known_boilerplate_bytes_removed": 0,
            "empty_documents_removed": 0, "empty_documents_removed_bytes": 0,
            "duplicate_documents_removed": 0, "duplicate_documents_removed_bytes": 0,
            "raw_unique_documents": 0, "repeated_boilerplate_lines_removed": 0,
            "repeated_boilerplate_bytes_removed": 0,
            "low_urdu_documents_removed": 0, "low_urdu_documents_removed_bytes": 0,
            "empty_after_line_filter_removed": 0, "empty_after_line_filter_removed_bytes": 0,
            "duplicate_after_cleaning_removed": 0, "duplicate_after_cleaning_removed_bytes": 0, "clean_documents_available": 0,
            "clean_bytes_available": 0, "selected_documents": 0, "selected_bytes": 0,
            "collection_date": s.get("collection_date", ""), "url": s.get("url", ""),
            "license": s.get("license", ""), "notes": s.get("notes", ""),
            "priority": int(s.get("priority") or 999), "source_cap_mib": float(s.get("source_cap_mib") or 250),
        }

    db_path = work_dir / "corpus_work.sqlite3"
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=FILE")
    conn.execute("""CREATE TABLE raw_docs (
        id INTEGER PRIMARY KEY,
        source_id TEXT NOT NULL, source_name TEXT NOT NULL, genre TEXT NOT NULL,
        text TEXT NOT NULL, norm_hash TEXT NOT NULL UNIQUE, raw_bytes INTEGER NOT NULL
    )""")
    conn.execute("CREATE TABLE line_freq (line TEXT PRIMARY KEY, doc_count INTEGER NOT NULL)")
    conn.execute("""CREATE TABLE clean_docs (
        id INTEGER PRIMARY KEY,
        source_id TEXT NOT NULL, source_name TEXT NOT NULL, genre TEXT NOT NULL,
        text TEXT NOT NULL, clean_hash TEXT NOT NULL UNIQUE, byte_len INTEGER NOT NULL
    )""")
    conn.execute("CREATE TABLE selected (doc_id INTEGER PRIMARY KEY, rank INTEGER NOT NULL, split TEXT NOT NULL)")
    conn.execute("CREATE INDEX idx_clean_source ON clean_docs(source_id, id)")

    # Enumerate only ordinary text-like files. Archive files must be extracted manually.
    allowed_suffixes = {".txt", ".text", ".md", ".jsonl", ".ndjson", ".csv", ".tsv", ".html", ".htm", ".xml", ".txt.gz", ".csv.gz", ".jsonl.gz", ".txt.bz2", ".txt.xz"}
    paths = []
    for path in raw_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.name.lower() in {"sources.csv", "urwiki_collection_manifest.json"}:
            continue
        low_name = path.name.lower()
        if not any(low_name.endswith(suffix) for suffix in allowed_suffixes):
            continue
        source = match_source(path, sources)
        if source:
            paths.append((int(source.get("priority") or 999), path, source))
    paths.sort(key=lambda item: (item[0], str(item[1]).lower()))

    if not paths:
        conn.close()
        raise RuntimeError("No raw files matched sources.csv. Put source files inside data/raw and check file_pattern entries.")

    cap_seen: defaultdict[str, int] = defaultdict(int)
    for _, path, src in paths:
        source_id = src["source_id"]
        stats = source_stats[source_id]
        stats["raw_file_bytes"] = int(stats["raw_file_bytes"]) + path.stat().st_size
        cap = int(float(src.get("source_cap_mib") or 250) * 1024 * 1024)
        print(f"\n[INGEST] {path} -> {src['source_name']} (raw file {bytes_mib(path.stat().st_size)}, source text cap {bytes_mib(cap)})")
        try:
            for raw_doc in iter_documents(path):
                if cap_seen[source_id] >= cap:
                    print(f"Reached configured source text cap for {src['source_name']}; moving to next source.")
                    break
                stats["input_documents_seen"] = int(stats["input_documents_seen"]) + 1
                raw_doc = raw_doc.replace("\x00", " ")
                doc_bytes = len(raw_doc.encode("utf-8", errors="replace"))
                cap_seen[source_id] += doc_bytes
                stats["raw_text_bytes_seen"] = int(stats["raw_text_bytes_seen"]) + doc_bytes
                preclean, known_removed, known_removed_bytes = remove_known_boilerplate(raw_doc)
                stats["known_boilerplate_lines_removed"] = int(stats["known_boilerplate_lines_removed"]) + known_removed
                stats["known_boilerplate_bytes_removed"] = int(stats["known_boilerplate_bytes_removed"]) + known_removed_bytes
                normalized_for_hash = normalize(preclean)
                if not normalized_for_hash:
                    stats["empty_documents_removed"] = int(stats["empty_documents_removed"]) + 1
                    stats["empty_documents_removed_bytes"] = int(stats["empty_documents_removed_bytes"]) + doc_bytes
                    continue
                digest = hashlib.sha256(normalized_for_hash.encode("utf-8")).hexdigest()
                cur = conn.execute(
                    "INSERT OR IGNORE INTO raw_docs(source_id,source_name,genre,text,norm_hash,raw_bytes) VALUES(?,?,?,?,?,?)",
                    (source_id, src["source_name"], src["genre"], preclean, digest, doc_bytes),
                )
                if cur.rowcount == 0:
                    stats["duplicate_documents_removed"] = int(stats["duplicate_documents_removed"]) + 1
                    stats["duplicate_documents_removed_bytes"] = int(stats["duplicate_documents_removed_bytes"]) + doc_bytes
                    continue
                stats["raw_unique_documents"] = int(stats["raw_unique_documents"]) + 1
                # Count each distinct normalized line at most once per document.
                line_set = {normalize(line) for line in preclean.splitlines() if len(normalize(line)) >= 25}
                for line in line_set:
                    conn.execute(
                        "INSERT INTO line_freq(line,doc_count) VALUES(?,1) ON CONFLICT(line) DO UPDATE SET doc_count=doc_count+1",
                        (line,),
                    )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            print(f"ERROR processing {path}: {exc}", file=sys.stderr)
            raise

    unique_raw_docs = conn.execute("SELECT COUNT(*) FROM raw_docs").fetchone()[0]
    repeat_threshold = max(25, math.ceil(unique_raw_docs * 0.0001))
    frequent_lines = {row[0] for row in conn.execute(
        "SELECT line FROM line_freq WHERE doc_count >= ? AND length(line) BETWEEN 25 AND 500",
        (repeat_threshold,),
    )}
    print(f"\n[LINE CLEANING] {unique_raw_docs:,} unique source documents; repeated-line threshold={repeat_threshold}; lines selected as boilerplate={len(frequent_lines):,}")

    raw_cursor = conn.execute("SELECT source_id,source_name,genre,text FROM raw_docs ORDER BY id")
    clean_hashes: set[str] = set()
    global_counts = {
        "unique_raw_documents": unique_raw_docs,
        "repeat_line_document_threshold": repeat_threshold,
        "repeated_boilerplate_lines_identified": len(frequent_lines),
        "repeated_boilerplate_lines_removed": 0,
        "repeated_boilerplate_bytes_removed": 0,
        "empty_after_line_filter_removed": 0,
        "empty_after_line_filter_removed_bytes": 0,
        "low_urdu_documents_removed": 0,
        "low_urdu_documents_removed_bytes": 0,
        "duplicate_after_cleaning_removed": 0,
        "duplicate_after_cleaning_removed_bytes": 0,
        "clean_documents_available": 0,
        "clean_bytes_available": 0,
    }
    for source_id, source_name, genre, raw_text in raw_cursor:
        lines_out = []
        removed = 0
        removed_bytes = 0
        for line in raw_text.splitlines():
            line_norm = normalize(line)
            if line_norm and line_norm in frequent_lines:
                removed += 1
                removed_bytes += len(line.encode("utf-8", errors="replace"))
                continue
            if line_norm:
                lines_out.append(line_norm)
        source_stats[source_id]["repeated_boilerplate_lines_removed"] = int(source_stats[source_id]["repeated_boilerplate_lines_removed"]) + removed
        source_stats[source_id]["repeated_boilerplate_bytes_removed"] = int(source_stats[source_id]["repeated_boilerplate_bytes_removed"]) + removed_bytes
        global_counts["repeated_boilerplate_lines_removed"] += removed
        global_counts["repeated_boilerplate_bytes_removed"] += removed_bytes
        cleaned = normalize(" ".join(lines_out))
        if not cleaned:
            removed_doc_bytes = len(raw_text.encode("utf-8", errors="replace"))
            source_stats[source_id]["empty_after_line_filter_removed"] = int(source_stats[source_id]["empty_after_line_filter_removed"]) + 1
            source_stats[source_id]["empty_after_line_filter_removed_bytes"] = int(source_stats[source_id]["empty_after_line_filter_removed_bytes"]) + removed_doc_bytes
            global_counts["empty_after_line_filter_removed"] += 1
            global_counts["empty_after_line_filter_removed_bytes"] += removed_doc_bytes
            continue
        urdu_chars, total_letters, ratio = urdu_stats(cleaned)
        if urdu_chars < args.min_urdu_chars or ratio < args.min_urdu_ratio:
            rejected_bytes = len(cleaned.encode("utf-8"))
            source_stats[source_id]["low_urdu_documents_removed"] = int(source_stats[source_id]["low_urdu_documents_removed"]) + 1
            source_stats[source_id]["low_urdu_documents_removed_bytes"] = int(source_stats[source_id]["low_urdu_documents_removed_bytes"]) + rejected_bytes
            global_counts["low_urdu_documents_removed"] += 1
            global_counts["low_urdu_documents_removed_bytes"] += rejected_bytes
            continue
        digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
        if digest in clean_hashes:
            duplicate_bytes = len(cleaned.encode("utf-8"))
            source_stats[source_id]["duplicate_after_cleaning_removed"] = int(source_stats[source_id]["duplicate_after_cleaning_removed"]) + 1
            source_stats[source_id]["duplicate_after_cleaning_removed_bytes"] = int(source_stats[source_id]["duplicate_after_cleaning_removed_bytes"]) + duplicate_bytes
            global_counts["duplicate_after_cleaning_removed"] += 1
            global_counts["duplicate_after_cleaning_removed_bytes"] += duplicate_bytes
            continue
        clean_hashes.add(digest)
        byte_len = len(cleaned.encode("utf-8"))
        conn.execute(
            "INSERT INTO clean_docs(source_id,source_name,genre,text,clean_hash,byte_len) VALUES(?,?,?,?,?,?)",
            (source_id, source_name, genre, cleaned, digest, byte_len),
        )
        source_stats[source_id]["clean_documents_available"] = int(source_stats[source_id]["clean_documents_available"]) + 1
        source_stats[source_id]["clean_bytes_available"] = int(source_stats[source_id]["clean_bytes_available"]) + byte_len
        global_counts["clean_documents_available"] += 1
        global_counts["clean_bytes_available"] += byte_len
    conn.commit()

    # Select from each source in priority order, enforcing per-source caps so no
    # single corpus silently dominates. A source cap applies to kept clean text.
    target_bytes = int(args.target_mib * 1024 * 1024)
    selected_ids: list[int] = []
    total_selected_bytes = 0
    for src in sources:
        source_id = src["source_id"]
        cap_bytes = int(float(src.get("source_cap_mib") or 250) * 1024 * 1024)
        this_source_bytes = 0
        cursor = conn.execute("SELECT id,byte_len FROM clean_docs WHERE source_id=? ORDER BY id", (source_id,))
        for doc_id, body_bytes in cursor:
            entry_bytes = int(body_bytes) + EOT_OVERHEAD
            if this_source_bytes + entry_bytes > cap_bytes:
                continue
            if total_selected_bytes + entry_bytes > target_bytes:
                # A long document may not fit the remaining gap; inspect later
                # (possibly shorter) documents before moving to the next source.
                continue
            selected_ids.append(int(doc_id))
            this_source_bytes += entry_bytes
            total_selected_bytes += entry_bytes
            source_stats[source_id]["selected_documents"] = int(source_stats[source_id]["selected_documents"]) + 1
            source_stats[source_id]["selected_bytes"] = int(source_stats[source_id]["selected_bytes"]) + entry_bytes
            if total_selected_bytes >= target_bytes:
                break
        if total_selected_bytes >= target_bytes:
            break

    if not selected_ids:
        conn.close()
        raise RuntimeError("No documents survived cleaning. Check the text columns and --min-urdu-ratio.")

    rng = random.Random(args.seed)
    rng.shuffle(selected_ids)
    n_docs = len(selected_ids)
    n_train = int(n_docs * 0.98)
    n_val = int(n_docs * 0.01)
    assignments = []
    for rank, doc_id in enumerate(selected_ids):
        if rank < n_train:
            split = "train"
        elif rank < n_train + n_val:
            split = "val"
        else:
            split = "test"
        assignments.append((doc_id, rank, split))
    conn.executemany("INSERT INTO selected(doc_id,rank,split) VALUES(?,?,?)", assignments)
    conn.commit()

    # Write UTF-8 text files, exactly one end-of-document marker per document.
    outputs = {name: out_dir / f"{name}.txt" for name in ("train", "val", "test")}
    split_counts = {name: {"documents": 0, "bytes": 0, "words": 0} for name in outputs}
    output_unique_words: set[str] = set()
    output_source_bytes: defaultdict[str, int] = defaultdict(int)
    output_source_docs: defaultdict[str, int] = defaultdict(int)
    for split, output_path in outputs.items():
        with output_path.open("w", encoding="utf-8", newline="\n") as f:
            cursor = conn.execute(
                "SELECT c.source_id,c.text FROM selected s JOIN clean_docs c ON c.id=s.doc_id WHERE s.split=? ORDER BY s.rank",
                (split,),
            )
            for source_id, text_value in cursor:
                serialized = text_value + "\n" + EOT + "\n"
                encoded = serialized.encode("utf-8")
                f.write(serialized)
                split_counts[split]["documents"] += 1
                split_counts[split]["bytes"] += len(encoded)
                split_counts[split]["words"] += len(text_value.split())
                output_source_bytes[source_id] += len(encoded)
                output_source_docs[source_id] += 1
                # Exact count of distinct whitespace-delimited normalized terms.
                output_unique_words.update(text_value.split())

    total_output_bytes = sum(item["bytes"] for item in split_counts.values())
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest": str(sources_path),
        "target_mib": args.target_mib,
        "target_bytes": target_bytes,
        "actual_output_bytes": total_output_bytes,
        "actual_output_mib": total_output_bytes / (1024 * 1024),
        "target_met": total_output_bytes >= target_bytes,
        "minimum_500_mib_met": total_output_bytes >= 500 * 1024 * 1024,
        "seed": args.seed,
        "split_rule": "shuffle whole documents with fixed seed; 98% train, 1% validation, remaining documents test (rounding assigned to test)",
        "normalization": {
            "urdu_yeh": "U+064A and U+0649 mapped to U+06CC",
            "urdu_kaf": "U+0643 mapped to U+06A9",
            "heh": "U+0647 mapped to U+06C1; U+06C1 and U+06BE kept distinct",
            "zwnj": "removed (U+200C), as allowed by assignment; justify this trade-off in report",
            "digits": "Arabic-Indic, Eastern Arabic-Indic and ASCII digits mapped to ASCII 0-9",
            "unicode": "NFC; whitespace collapsed to a single space within each document",
        },
        "heuristics": {
            "minimum_urdu_script_characters": args.min_urdu_chars,
            "minimum_script_ratio": args.min_urdu_ratio,
            "script_ratio_definition": "Arabic-script characters in U+0600–U+08FF divided by all Unicode letters and combining marks",
            "repeated_line_threshold": repeat_threshold,
            "line_grouping": "TXT files with no blank paragraph separators are grouped into blocks of 100 non-empty lines because original document boundaries may be unavailable",
        },
        "global_cleaning_counts": global_counts,
        "split_counts": split_counts,
        "totals": {
            "documents": sum(x["documents"] for x in split_counts.values()),
            "words_whitespace_delimited": sum(x["words"] for x in split_counts.values()),
            "unique_whitespace_delimited_terms": len(output_unique_words),
        },
        "sources": [],
    }
    for src in sources:
        st = source_stats[src["source_id"]]
        st["selected_documents"] = output_source_docs[src["source_id"]]
        st["selected_bytes"] = output_source_bytes[src["source_id"]]
        report["sources"].append(st)

    report_path = out_dir / "cleaning_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_data_card(out_dir / "DATA_CARD.md", report, sources)
    conn.close()

    print("\n=== CORPUS BUILD SUMMARY ===")
    print(f"Documents: {report['totals']['documents']:,}")
    print(f"Words (space-separated): {report['totals']['words_whitespace_delimited']:,}")
    print(f"Unique space-separated terms: {report['totals']['unique_whitespace_delimited_terms']:,}")
    print(f"Output: {bytes_mib(total_output_bytes)} ({total_output_bytes:,} bytes)")
    for split, values in split_counts.items():
        print(f"{split}.txt: {values['documents']:,} documents, {bytes_mib(values['bytes'])}, {values['words']:,} words")
    print(f"Report: {report_path}")
    print(f"Data card: {out_dir / 'DATA_CARD.md'}")
    if total_output_bytes < target_bytes:
        print("\nWARNING: Target was not met. Add a suitable source, raise source_cap_mib in sources.csv, and rerun.")
    elif total_output_bytes < 500 * 1024 * 1024:
        print("\nWARNING: The 500 MiB minimum was not met; increase --target-mib and available source caps.")
    else:
        print("\nThe corpus meets the 500 MiB aggregate output-size threshold. Review source licences and cleaning logs before submission.")


def write_data_card(path: Path, report: dict, sources: list[dict[str, str]]) -> None:
    lines = [
        "# DATA_CARD — Urdu BPE Corpus", "",
        f"Generated: {report['created_at_utc']}", "",
        "## Sources", "",
        "| Source | Genre | URL | Licence / terms recorded | Collection date | Raw file size | Selected cleaned contribution | Notes |",
        "|---|---|---|---|---|---:|---:|---|",
    ]
    for s in sources:
        stat = next((x for x in report["sources"] if x["source_id"] == s["source_id"]), {})
        raw_size = int(stat.get("raw_file_bytes", 0))
        cleaned = int(stat.get("selected_bytes", 0))
        fields = [s.get("source_name", ""), s.get("genre", ""), s.get("url", ""), s.get("license", ""),
                  s.get("collection_date", "FILL IN collection/download date"), bytes_mib(raw_size), bytes_mib(cleaned), s.get("notes", "")]
        fields = [str(v).replace("|", "\\|").replace("\n", " ") for v in fields]
        lines.append("| " + " | ".join(fields) + " |")
    split = report["split_counts"]
    totals = report["totals"]
    lines += [
        "", "## Corpus totals", "",
        f"- Aggregate UTF-8 output size, including `<|endoftext|>` separators: {report['actual_output_bytes']:,} bytes ({report['actual_output_mib']:.2f} MiB).",
        f"- Documents: {totals['documents']:,}.",
        f"- Words: {totals['words_whitespace_delimited']:,} whitespace-separated terms.",
        f"- Unique words: {totals['unique_whitespace_delimited_terms']:,} unique whitespace-separated terms (punctuation may remain attached).",
        f"- Size target met: {report['target_met']}; 500 MiB minimum met: {report['minimum_500_mib_met']}.",
        "", "## Splits", "",
        "| File | Documents | Bytes | MiB | Space-separated terms |", "|---|---:|---:|---:|---:|",
    ]
    for name, values in split.items():
        lines.append(f"| {name}.txt | {values['documents']:,} | {values['bytes']:,} | {values['bytes'] / (1024*1024):.2f} | {values['words']:,} |")
    c = report["global_cleaning_counts"]
    lines += [
        "", "## Cleaning steps and removals", "",
        f"- Input documents seen: {sum(int(x['input_documents_seen']) for x in report['sources']):,}.",
        f"- Empty documents removed: {sum(int(x['empty_documents_removed']) for x in report['sources']):,} documents / {bytes_mib(sum(int(x['empty_documents_removed_bytes']) for x in report['sources']))} raw text.",
        f"- Exact duplicate documents removed during ingestion: {sum(int(x['duplicate_documents_removed']) for x in report['sources']):,} documents / {bytes_mib(sum(int(x['duplicate_documents_removed_bytes']) for x in report['sources']))} text.",
        f"- Known boilerplate lines removed: {sum(int(x['known_boilerplate_lines_removed']) for x in report['sources']):,} lines / {bytes_mib(sum(int(x['known_boilerplate_bytes_removed']) for x in report['sources']))} text.",
        f"- Repeated boilerplate lines identified: {c['repeated_boilerplate_lines_identified']:,}; occurrences removed: {c['repeated_boilerplate_lines_removed']:,} lines / {bytes_mib(c['repeated_boilerplate_bytes_removed'])} text.",
        f"- Documents removed after repeated-line filtering because empty: {c['empty_after_line_filter_removed']:,} documents / {bytes_mib(c['empty_after_line_filter_removed_bytes'])} text.",
        f"- Documents rejected by Urdu-script heuristic: {c['low_urdu_documents_removed']:,} documents / {bytes_mib(c['low_urdu_documents_removed_bytes'])} text.",
        f"- Additional duplicates removed after normalization: {c['duplicate_after_cleaning_removed']:,} documents / {bytes_mib(c['duplicate_after_cleaning_removed_bytes'])} text.",
        "- Unicode NFC applied; Arabic yeh/alef maksura, Arabic kaf, heh variants, tatweel, invisible characters, digits and whitespace handled according to `normalize.py`.",
        f"- Urdu filter: at least {report['heuristics']['minimum_urdu_script_characters']} Arabic-script characters and script ratio ≥ {report['heuristics']['minimum_script_ratio']:.2f}.",
        f"- Document splitting: {report['split_rule']}.",
        "", "## Known gaps and biases", "",
        "- The exact source mix and genre balance are shown above; published news corpora may overrepresent news topics and contemporary vocabulary.",
        "- Urdu-script ratio is a heuristic, not a linguistic language identifier. Arabic, Persian, and some mixed-script content can be misclassified.",
        "- Removing ZWNJ may change orthographic distinctions; this choice follows the assignment's suggested policy and must be discussed in the report.",
        "- Sources that provide only sentence-per-line text have no preserved original document boundaries; the pipeline groups 100 non-empty lines into pseudo-documents and records this limitation.",
        "- Copyright and redistribution conditions differ by source. Keep data inside the course as instructed and do not redistribute restricted raw text.",
        "", "## Reproducibility", "",
        f"- Random seed: `{report['seed']}`.",
        "- Detailed source-level counts and cleaning measurements: `cleaning_report.json`.",
        "- Check that every collection date and licence field is complete before submission.", "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
