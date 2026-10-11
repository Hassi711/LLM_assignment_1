"""Encode corpus text into flat uint16 NumPy arrays."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterator

import numpy as np

from bpe import BPETokenizer


def iter_file_ids(tokenizer: BPETokenizer, path: Path) -> Iterator[int]:
    with path.open("r", encoding="utf-8", newline="") as source:
        for line in source:
            for piece in tokenizer.pretokenize(line):
                if piece == "<|endoftext|>":
                    yield 256
                else:
                    yield from tokenizer._encode_piece(piece)


def encode_file(tokenizer: BPETokenizer, source: str | Path, destination: str | Path) -> int:
    source_path = Path(source)
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    chunks: list[np.ndarray] = []
    current_chunk: list[int] = []
    chunk_size = 2_000_000
    total_count = 0

    with source_path.open("r", encoding="utf-8", newline="") as source_file:
        for line in source_file:
            for piece in tokenizer.pretokenize(line):
                if piece == "<|endoftext|>":
                    current_chunk.append(256)
                else:
                    current_chunk.extend(tokenizer._encode_piece(piece))
            if len(current_chunk) >= chunk_size:
                arr = np.array(current_chunk, dtype=np.uint16)
                chunks.append(arr)
                total_count += len(arr)
                current_chunk = []
    if current_chunk:
        arr = np.array(current_chunk, dtype=np.uint16)
        chunks.append(arr)
        total_count += len(arr)
        current_chunk = []

    if total_count == 0:
        with destination_path.open("wb") as output:
            np.save(output, np.empty(0, dtype=np.uint16))
        return 0

    output = np.lib.format.open_memmap(destination_path, mode="w+", dtype=np.uint16, shape=(total_count,))
    offset = 0
    for chunk in chunks:
        output[offset : offset + len(chunk)] = chunk
        offset += len(chunk)
    output.flush()
    del output
    return total_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", default="tokenizer.json")
    parser.add_argument("--train", default="data/processed/train.txt")
    parser.add_argument("--val", default="data/processed/val.txt")
    parser.add_argument("--out-dir", default="data/processed")
    args = parser.parse_args()

    tokenizer = BPETokenizer.load(args.tokenizer)
    out_dir = Path(args.out_dir)
    for split, source in (("train", args.train), ("val", args.val)):
        destination = out_dir / f"{split}.bin"
        count = encode_file(tokenizer, source, destination)
        print(f"{destination}: {count:,} uint16 IDs ({destination.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
