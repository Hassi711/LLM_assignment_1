# Urdu Byte-Pair Encoding (BPE) Tokenizer from Scratch
**Course:** CS 417: Large Language Models (Spring 2026)  
**Institution:** National University of Sciences & Technology (NUST SEECS)  
**Assignment 1:** Build an Urdu BPE Tokenizer from Scratch (CLO 3)  
**Vocabulary Target:** Exactly 50,000 tokens (IDs 0–49,999; 49,743 merges)  

---

## 1. Executive Summary & Verification Highlights

This project implements a complete, native **byte-level BPE tokenizer** for Urdu in plain Python without any tokenizer libraries (`tokenizers`, `tiktoken`, `sentencepiece`, `minbpe` were strictly avoided for implementation).

- **Corpus (Part A):** Curated **545.26 MB** (520.00 MiB) of cleaned, deduplicated UTF-8 Urdu text across 3 diverse sources (Encyclopedia, Journalism, Mixed Literature). Exactly **55.11 MiB** was independently collected via automated discovery and extraction using the Urdu Wikipedia MediaWiki API (proven by `data/raw/urwiki_collection_manifest.json`).
- **Tokenizer (Part B):** Trained on `data/processed/train.txt` (509.64 MiB, 67,597,701 words) in **352.25 seconds** (~5.8 minutes) using a 3-tier optimization (weighted distinct pre-token counts, inverted pair-to-word index, and lazy heap). Produces exactly 49,743 merges, reaching a vocabulary size of 50,000.
- **Lossless Guarantee:** Verified `decode(encode(text)) == text` across all edge cases including Urdu diacritics, Roman Urdu, emojis, English code-mixing, and empty strings.
- **Compression Efficiency (Part C):** Achieves **1.084 tokens/word** on `test.txt`, providing a **5.16× compression advantage** over OpenAI GPT-2 (5.594 tok/w) and beating OpenAI `o200k_base` (1.521 tok/w).
- **Deliverables:** Includes `DATA_CARD.md`, `tokenizer.json`, `report.pdf` (exactly 4 pages), encoded binary arrays `train.bin` (72.1M IDs) and `val.bin` (700K IDs), and submission archive `assignment1_submission.zip`.

---

## 2. Directory Structure

```text
urdu_bpe_corpus_starter/
├── normalize.py                     # Custom Urdu Unicode normalization function
├── bpe.py                           # Byte-level BPE tokenizer (BPETokenizer)
├── train_tokenizer.py               # Tokenizer training CLI script
├── encode_corpus.py                 # Fast chunked memmap corpus encoder to uint16
├── collect_ur_wikipedia.py          # Multi-threaded Urdu Wikipedia API scraper
├── prepare_corpus.py                # Cleaning, normalization, deduplication & splitting pipeline
├── inspect_news_csv.py              # Low-memory streaming inspector for raw CSV
├── analyze_tokenizer.py             # Part C empirical evaluation & benchmark tables
├── build_report.py                  # Generates the 4-page academic report.pdf via ReportLab
├── test_bpe.py                      # Unit tests for BPE mechanics and lossless decoding
├── test_normalize.py                # Unit tests for Unicode normalization mappings
├── DATA_CARD.md                     # Comprehensive corpus data card & provenance
├── README.md                        # Reproduction commands & technical documentation
├── tokenizer.json                   # Trained BPE tokenizer model (50,000 vocab, 49,743 merges)
├── report.pdf                       # Official 4-page analysis report
├── requirements.txt                 # Project dependencies
├── sources.csv                      # Registered corpus sources and metadata
├── data/
│   ├── raw/                         # Raw downloaded and collected datasets
│   │   ├── urwiki_api.jsonl         # 55.1 MiB self-collected Wikipedia articles
│   │   ├── urwiki_collection_manifest.json # Proof & evidence of independent API collection
│   │   ├── ufal-urmonocorp.txt.gz   # UFAL Monolingual Corpus (mixed genre)
│   │   └── urdu-news-dataset-1M.csv # 1M Urdu News dataset (journalism genre)
│   └── processed/                   # Final cleaned corpus splits (≥500 MB)
│       ├── train.txt                # 509.64 MiB (98% split, 67,597,701 words)
│       ├── val.txt                  # 5.00 MiB (1% split, 668,160 words)
│       ├── test.txt                 # 5.35 MiB (1% split, 713,196 words)
│       ├── train.bin                # 72,127,369 uint16 token IDs (144.25 MB)
│       ├── val.bin                  # 700,321 uint16 token IDs (1.40 MB)
│       └── cleaning_report.json     # Detailed stats of cleaning stages and removals
└── work/                            # Generated plots and scratch files
    ├── benchmark_comparison.png     # Benchmark tokens/word bar chart
    └── vocab_growth.png             # Vocabulary growth curve
```

---

## 3. Environment Setup

Install the required dependencies using PowerShell:

```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

*Note: For Part C comparisons only, `tiktoken` is installed to measure GPT-2 and `o200k_base` benchmarks. Neither `tiktoken` nor any tokenizer library is imported or used inside the tokenizer implementation (`bpe.py`).*

---

## 4. End-to-End Reproduction Workflow

### Step 1: Run Unit Tests
Verify that normalization rules, special token reservation, tie-breaking, and fast/reference algorithm parity hold:

```powershell
python -m unittest discover -p "test_*.py" -v
```

### Step 2: Corpus Collection & Preparation (Part A)
1. Collect Wikipedia articles via the MediaWiki Parsoid API (generates manifest evidence):
```powershell
python collect_ur_wikipedia.py --target-mib 80 --delay 0.05 --threads 4
```
2. Ingest all 3 sources, apply `normalize()`, deduplicate, filter, and partition into 98/1/1 splits:
```powershell
python prepare_corpus.py --raw-dir data/raw --out-dir data/processed --sources sources.csv --target-mib 520 --min-urdu-ratio 0.35 --min-urdu-chars 20 --seed 4172026
```

### Step 3: Train the BPE Tokenizer (Part B)
Train the byte-level BPE tokenizer on `train.txt` to exactly 50,000 vocabulary size:

```powershell
python train_tokenizer.py data/processed/train.txt --vocab-size 50000 --out tokenizer.json
```
*Output: `Vocabulary size: 50,000`, `Merges: 49,743`, `Training wall time: ~352s`.*

### Step 4: Encode the Corpus to Binary Arrays
Encode `train.txt` and `val.txt` into flat `uint16` NumPy binary files:

```powershell
python encode_corpus.py --tokenizer tokenizer.json --train data/processed/train.txt --val data/processed/val.txt --out-dir data/processed
```
*Output: `train.bin` (72,127,369 IDs, 144,254,866 bytes) and `val.bin` (700,321 IDs, 1,400,770 bytes).*

### Step 5: Run Empirical Analysis & Benchmark Evaluation (Part C)
Generate analysis markdown, structured data, and plots comparing against GPT-2 and `o200k_base`:

```powershell
python analyze_tokenizer.py --tokenizer tokenizer.json --train data/processed/train.txt --test data/processed/test.txt --out analysis.md --json-out analysis_data.json
```

### Step 6: Compile the 4-Page PDF Report
Compile the official academic PDF report using ReportLab:

```powershell
python build_report.py
```
*Output: `report.pdf` (exactly 4 pages).*

---

## 5. Tokenizer Architecture & Specifications

1. **Base Vocabulary:** 256 byte values (IDs 0–255). Every Unicode string is initially interpreted as UTF-8 bytes, ensuring an unknown token (`<unk>`) is impossible.
2. **Special Token:** Reserved ID 256 for `<|endoftext|>`. It is never split, never takes part in pair counting, and never undergoes merges.
3. **Merges:** IDs 257 to 49,999 (exactly 49,743 merges) learned in chronological order.
4. **Pre-tokenization Pattern:**
   ```python
   PRETOKEN_PATTERN = r"<\|endoftext\|>| ?[\p{L}\p{M}\p{N}\u200c]+| ?[^\s\p{L}\p{M}\p{N}\u200c]+|\s+"
   ```
   - Preserves combining marks (`\p{M}`) and ZWNJ (`\u200C`) attached to Urdu letter stems.
   - Attaches leading ASCII space (`0x20`) to the subsequent token (GPT-2 style).
5. **Deterministic Tie-Breaking:** When two byte pairs possess identical frequencies, the pair with the lexicographically greater byte tuple `(tokens[pair[0]], tokens[pair[1]])` is selected, guaranteeing reproducible merges across platforms.
6. **Lossless Round-Trip Guarantee:** `decode(encode(text)) == text` is strictly preserved for all Unicode characters.

---

## 6. Empirical Benchmark Summary (Part C)

| Benchmark Split / Input | Words | Custom Urdu BPE Tokens | Custom BPE (tok/w) | GPT-2 (tok/w) | o200k_base (tok/w) | Custom vs GPT-2 Adv. |
|---|---:|---:|---:|---:|---:|---:|
| **test.txt (Full Split)** | 713,196 | 772,919 | **1.084** | 5.594 | 1.521 | **+5.16×** |
| **News** | 14 | 15 | **1.071** | 5.786 | 1.500 | **+5.40×** |
| **Poetry** | 10 | 12 | **1.200** | 5.600 | 1.600 | **+4.67×** |
| **Urdu with English** | 10 | 16 | **1.600** | 4.300 | 1.300 | **+2.69×** |
| **Roman Urdu** | 12 | 31 | **2.583** | 2.083 | 1.667 | 0.81× |
| **Numbers and Dates** | 13 | 26 | **2.000** | 6.000 | 2.077 | **+3.00×** |
| **Diacritics** | 5 | 14 | **2.800** | 8.400 | 4.400 | **+3.00×** |
| **Personal Names** | 9 | 11 | **1.222** | 6.000 | 1.889 | **+4.91×** |

### Key Findings:
- On native Urdu text (`test.txt`), the custom BPE tokenizer encodes text at **1.084 tokens/word**, eliminating the 5.16× "token tax" imposed by GPT-2 (5.594 tok/w) and exceeding multilingual state-of-the-art `o200k_base` (1.521 tok/w).
- In a 2,048-token context window, our tokenizer fits **~1,890 full Urdu words**, compared to only **~366 words** with GPT-2's tokenizer.
