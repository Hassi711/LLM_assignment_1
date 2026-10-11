"""Inspect the Urdu News Dataset CSV without loading the full file into memory.

Usage (Windows):
    python inspect_news_csv.py "data/raw/urdu-news-dataset-1M.csv"

This script only reads the header and a few rows; it does not modify the dataset.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def shorten(value: object, limit: int = 180) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    return text if len(text) <= limit else text[:limit] + "..."


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", help="Path to the extracted Urdu news CSV")
    parser.add_argument("--rows", type=int, default=3, help="Number of sample rows to display (default: 3)")
    args = parser.parse_args()

    path = Path(args.csv_path)
    if not path.is_file():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        print('Check the path and put quotes around it if it contains spaces.', file=sys.stderr)
        return 2

    size = path.stat().st_size
    print(f"File: {path.resolve()}")
    print(f"Size: {size:,} bytes ({size / 1_000_000:.2f} MB; {size / (1024**3):.2f} GiB)")
    print("Reading only the header and a few records; the full CSV is not loaded into memory.\n")

    # Some CSV cells can be long. Increase Python csv's default field limit safely.
    csv.field_size_limit(min(sys.maxsize, 100_000_000))

    try:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print("ERROR: No CSV header found. Check whether the file is really a CSV.", file=sys.stderr)
                return 3

            headers = reader.fieldnames
            print(f"Columns ({len(headers)}):")
            for i, header in enumerate(headers, start=1):
                print(f"  {i:>2}. {header!r}")

            for row_number in range(1, max(0, args.rows) + 1):
                row = next(reader, None)
                if row is None:
                    break
                print(f"\n--- SAMPLE ROW {row_number} ---")
                for header in headers:
                    value = row.get(header, "")
                    print(f"{header}: {shorten(value)}")
    except (OSError, csv.Error, UnicodeError) as exc:
        print(f"ERROR while reading CSV: {exc}", file=sys.stderr)
        return 4

    print("\nInspection complete. No files were changed.")
    print("Next: identify the article-text column before running any cleaning script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
