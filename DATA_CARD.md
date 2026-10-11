# DATA_CARD — Urdu BPE Corpus

Generated: 2026-10-11T15:53:36.920393+00:00

## Sources

| Source | Genre | URL | Licence / terms recorded | Collection date | Raw file size | Selected cleaned contribution | Notes |
|---|---|---|---|---|---:|---:|---|
| Urdu Wikipedia | encyclopedia | https://ur.wikipedia.org/ | Wikipedia text generally CC BY-SA / GFDL; preserve attribution and verify current applicable terms | 2026-10-11 | 56.91 MiB | 55.09 MiB | Collected by own script through official MediaWiki API; see data/raw/urwiki_collection_manifest.json |
| UFAL UrMonoCorp | mixed | https://ufal.mff.cuni.cz/node/998 | CC BY-NC-SA 3.0; Non-commercial research use per UFAL page and LINDAT repository | 2026-10-11 | 213.46 MiB | 299.79 MiB | Extract the plain-text corpus or read gzip directly; LINDAT handle 11858/00-097C-0000-0023-65A9-5 |
| Urdu News Dataset 1M | news | https://data.mendeley.com/datasets/834vsxnb99/4 | Mendeley listing says CC BY 4.0; dataset notes say source sites allowed non-commercial research with source credit; verify and follow the stricter applicable terms | 2026-10-11 | 1996.92 MiB | 165.11 MiB | Use only for course/research as permitted; do not redistribute raw news text unless rights allow it |

## Corpus totals

- Aggregate UTF-8 output size, including `<|endoftext|>` separators: 545,259,515 bytes (520.00 MiB).
- Documents: 114,857.
- Words: 68,979,057 whitespace-separated terms.
- Unique words: 934,745 unique whitespace-separated terms (punctuation may remain attached).
- Size target met: False; 500 MiB minimum met: True.

## Splits

| File | Documents | Bytes | MiB | Space-separated terms |
|---|---:|---:|---:|---:|
| train.txt | 112,559 | 534,399,365 | 509.64 | 67,597,701 |
| val.txt | 1,148 | 5,246,881 | 5.00 | 668,160 |
| test.txt | 1,150 | 5,613,269 | 5.35 | 713,196 |

## Cleaning steps and removals

- Input documents seen: 152,917.
- Empty documents removed: 139 documents / 0.36 MiB raw text.
- Exact duplicate documents removed during ingestion: 27 documents / 0.06 MiB text.
- Known boilerplate lines removed: 16,637 lines / 51.90 MiB text.
- Repeated boilerplate lines identified: 10; occurrences removed: 623 lines / 0.03 MiB text.
- Documents removed after repeated-line filtering because empty: 0 documents / 0.00 MiB text.
- Documents rejected by Urdu-script heuristic: 149 documents / 0.01 MiB text.
- Additional duplicates removed after normalization: 0 documents / 0.00 MiB text.
- Unicode NFC applied; Arabic yeh/alef maksura, Arabic kaf, heh variants, tatweel, invisible characters, digits and whitespace handled according to `normalize.py`.
- Urdu filter: at least 20 Arabic-script characters and script ratio ≥ 0.35.
- Document splitting: shuffle whole documents with fixed seed; 98% train, 1% validation, remaining documents test (rounding assigned to test).

## Known gaps and biases

- The exact source mix and genre balance are shown above; published news corpora may overrepresent news topics and contemporary vocabulary.
- Urdu-script ratio is a heuristic, not a linguistic language identifier. Arabic, Persian, and some mixed-script content can be misclassified.
- Removing ZWNJ may change orthographic distinctions; this choice follows the assignment's suggested policy and must be discussed in the report.
- Sources that provide only sentence-per-line text have no preserved original document boundaries; the pipeline groups 100 non-empty lines into pseudo-documents and records this limitation.
- Copyright and redistribution conditions differ by source. Keep data inside the course as instructed and do not redistribute restricted raw text.

## Reproducibility

- Random seed: `4172026`.
- Detailed source-level counts and cleaning measurements: `cleaning_report.json`.
- Check that every collection date and licence field is complete before submission.
