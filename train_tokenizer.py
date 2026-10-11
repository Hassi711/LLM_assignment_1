"""Train the Urdu byte-BPE model and record runtime/machine metadata."""
from __future__ import annotations

import argparse
import platform
import time
from pathlib import Path

from bpe import BPETokenizer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("train_file", nargs="?", default="data/processed/train.txt")
    parser.add_argument("--vocab-size", type=int, default=50_000)
    parser.add_argument("--out", default="tokenizer.json")
    args = parser.parse_args()

    start = time.perf_counter()
    tokenizer = BPETokenizer.train_file(args.train_file, args.vocab_size)
    elapsed = time.perf_counter() - start
    tokenizer.save(args.out)
    print(f"Vocabulary size: {tokenizer.vocab_size:,}")
    print(f"Merges: {len(tokenizer.merges):,}")
    print(f"Training wall time: {elapsed:.2f} seconds")
    print(f"Machine: {platform.platform()} ({platform.processor() or 'processor not reported'})")
    print(f"Tokenizer saved: {Path(args.out)}")


if __name__ == "__main__":
    main()
