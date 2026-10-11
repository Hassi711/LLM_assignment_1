"""Byte-level BPE tokenizer for Urdu, implemented without tokenizer libraries."""
from __future__ import annotations

import heapq
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import regex

END_OF_TEXT = "<|endoftext|>"
PRETOKEN_PATTERN = (
    rf"{re.escape(END_OF_TEXT)}|"
    r" ?[\p{L}\p{M}\p{N}\u200c]+|"
    r" ?[^\s\p{L}\p{M}\p{N}\u200c]+|"
    r"\s+"
)
_PRETOKEN_RE = regex.compile(PRETOKEN_PATTERN)


class _ReversePair:
    def __init__(self, value: tuple[bytes, bytes]) -> None:
        self.value = value

    def __lt__(self, other: "_ReversePair") -> bool:
        return self.value > other.value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _ReversePair) and self.value == other.value


class BPETokenizer:
    """A lossless UTF-8 byte BPE tokenizer with reserved end-of-text ID 256."""

    def __init__(self, merges: Sequence[tuple[int, int]] = ()) -> None:
        self.merges = list(merges)
        self.token_bytes: list[bytes] = [bytes((value,)) for value in range(256)]
        self.token_bytes.append(END_OF_TEXT.encode("utf-8"))
        for left, right in self.merges:
            if left >= len(self.token_bytes) or right >= len(self.token_bytes):
                raise ValueError("Merge refers to a token that has not been defined yet")
            self.token_bytes.append(self.token_bytes[left] + self.token_bytes[right])
        self.merge_ranks = {pair: rank for rank, pair in enumerate(self.merges)}
        self._encode_cache: dict[str, tuple[int, ...]] = {}

    @property
    def vocab_size(self) -> int:
        return len(self.token_bytes)

    @staticmethod
    def pretokenize(text: str) -> Iterator[str]:
        """Yield pieces; Urdu combining marks and ZWNJ stay with their word."""
        yield from (match.group(0) for match in _PRETOKEN_RE.finditer(text))

    @staticmethod
    def _count_word_frequencies(chunks: Iterable[str]) -> Counter[bytes]:
        frequencies: Counter[bytes] = Counter()
        for chunk in chunks:
            for piece in _PRETOKEN_RE.finditer(chunk):
                value = piece.group(0)
                if value != END_OF_TEXT:
                    frequencies[value.encode("utf-8")] += 1
        return frequencies

    @classmethod
    def train_reference(cls, text: str, vocab_size: int = 50_000) -> "BPETokenizer":
        """Slow baseline: recount all adjacent pairs for every merge."""
        if not 257 <= vocab_size <= 65_536:
            raise ValueError("vocab_size must be between 257 and 65536")
        words = [list(value) for value in cls._count_word_frequencies((text,)).elements()]
        tokens = [bytes((value,)) for value in range(256)] + [END_OF_TEXT.encode("utf-8")]
        merges: list[tuple[int, int]] = []
        for _ in range(vocab_size - 257):
            counts: Counter[tuple[int, int]] = Counter()
            for word in words:
                counts.update(zip(word, word[1:]))
            if not counts:
                raise ValueError(f"Corpus exhausted at vocabulary size {len(tokens) + 1}")
            pair = max(counts, key=lambda item: (counts[item], tokens[item[0]], tokens[item[1]], item))
            new_id = len(tokens)
            merged = tokens[pair[0]] + tokens[pair[1]]
            words = [cls._merge_word(word, pair, new_id) for word in words]
            merges.append(pair)
            tokens.append(merged)
        return cls(merges)

    @classmethod
    def train_fast(cls, chunks: Iterable[str], vocab_size: int = 50_000) -> "BPETokenizer":
        """Train with distinct-word weights and incremental pair/word indexes."""
        if not 257 <= vocab_size <= 65_536:
            raise ValueError("vocab_size must be between 257 and 65536")
        frequencies = cls._count_word_frequencies(chunks)
        if not frequencies:
            raise ValueError("Training corpus contains no pre-tokens")
        words = [list(value) for value in frequencies]
        weights = [frequencies[value] for value in frequencies]
        tokens = [bytes((value,)) for value in range(256)] + [END_OF_TEXT.encode("utf-8")]
        pair_counts: Counter[tuple[int, int]] = Counter()
        pair_words: defaultdict[tuple[int, int], set[int]] = defaultdict(set)
        pair_heap: list[tuple[int, _ReversePair, int, int, tuple[int, int]]] = []

        def push_pair(pair: tuple[int, int]) -> None:
            count = pair_counts.get(pair, 0)
            if count:
                heapq.heappush(
                    pair_heap,
                    (-count, _ReversePair((tokens[pair[0]], tokens[pair[1]])), -pair[0], -pair[1], pair),
                )

        def word_pairs(word: Sequence[int]) -> Counter[tuple[int, int]]:
            return Counter(zip(word, word[1:]))

        for word_index, word in enumerate(words):
            for pair, occurrences in word_pairs(word).items():
                pair_counts[pair] += occurrences * weights[word_index]
                pair_words[pair].add(word_index)
        for pair in pair_counts:
            push_pair(pair)

        merges: list[tuple[int, int]] = []
        target_merges = vocab_size - 257
        start_merge_time = time.time()
        for _ in range(target_merges):
            while pair_heap and -pair_heap[0][0] != pair_counts.get(pair_heap[0][4], 0):
                heapq.heappop(pair_heap)
            if not pair_heap:
                raise ValueError(f"Corpus exhausted at vocabulary size {len(tokens) + 1}")
            pair = heapq.heappop(pair_heap)[4]
            tokens.append(tokens[pair[0]] + tokens[pair[1]])
            affected = tuple(pair_words.pop(pair, ()))
            new_id = len(tokens) - 1
            changed_pairs: set[tuple[int, int]] = set()
            for word_index in affected:
                word = words[word_index]
                old_pairs = word_pairs(word)
                for old_pair, occurrences in old_pairs.items():
                    pair_counts[old_pair] -= occurrences * weights[word_index]
                    if pair_counts[old_pair] <= 0:
                        del pair_counts[old_pair]
                    members = pair_words.get(old_pair)
                    if members is not None:
                        members.discard(word_index)
                        if not members:
                            pair_words.pop(old_pair, None)
                    changed_pairs.add(old_pair)
                merged_word = cls._merge_word(word, pair, new_id)
                words[word_index] = merged_word
                for new_pair, occurrences in word_pairs(merged_word).items():
                    pair_counts[new_pair] += occurrences * weights[word_index]
                    pair_words[new_pair].add(word_index)
                    changed_pairs.add(new_pair)
            for changed_pair in changed_pairs:
                push_pair(changed_pair)
            merges.append(pair)
            if len(merges) % 2500 == 0 or len(merges) == target_merges:
                elapsed = time.time() - start_merge_time
                rate = len(merges) / max(0.001, elapsed)
                print(f"Learned {len(merges):,} / {target_merges:,} merges (vocab {len(tokens):,}) | {rate:.1f} merges/s | elapsed {elapsed:.1f}s", flush=True)
            if len(pair_heap) > max(10_000, 4 * len(pair_counts)):
                pair_heap = []
                for active_pair in pair_counts:
                    push_pair(active_pair)
        return cls(merges)

    @classmethod
    def train_file(cls, path: str | Path, vocab_size: int = 50_000) -> "BPETokenizer":
        """Train from a UTF-8 corpus without loading the full file as one string."""
        def lines() -> Iterator[str]:
            with Path(path).open("r", encoding="utf-8", newline="") as source:
                yield from source
        return cls.train_fast(lines(), vocab_size)

    @staticmethod
    def _merge_word(word: Sequence[int], pair: tuple[int, int], new_id: int) -> list[int]:
        result: list[int] = []
        index = 0
        while index < len(word):
            if index + 1 < len(word) and (word[index], word[index + 1]) == pair:
                result.append(new_id)
                index += 2
            else:
                result.append(word[index])
                index += 1
        return result

    def _encode_piece(self, piece: str) -> tuple[int, ...]:
        cached = self._encode_cache.get(piece)
        if cached is not None:
            return cached
        ids = list(piece.encode("utf-8"))
        while len(ids) > 1:
            candidate = min(
                ((self.merge_ranks[(ids[i], ids[i + 1])], i, ids[i], ids[i + 1])
                 for i in range(len(ids) - 1)
                 if (ids[i], ids[i + 1]) in self.merge_ranks),
                default=None,
            )
            if candidate is None:
                break
            _, _, left, right = candidate
            ids = self._merge_word(ids, (left, right), 257 + self.merge_ranks[(left, right)])
        result = tuple(ids)
        self._encode_cache[piece] = result
        return result

    def encode(self, text: str) -> list[int]:
        ids: list[int] = []
        for piece in self.pretokenize(text):
            if piece == END_OF_TEXT:
                ids.append(256)
            else:
                ids.extend(self._encode_piece(piece))
        return ids

    def decode(self, ids: Iterable[int]) -> str:
        data = bytearray()
        for token_id in ids:
            if not 0 <= int(token_id) < self.vocab_size:
                raise ValueError(f"Token ID out of range: {token_id}")
            if int(token_id) == 256:
                data.extend(self.token_bytes[256])
            else:
                data.extend(self.token_bytes[int(token_id)])
        return data.decode("utf-8", errors="strict")

    def save(self, path: str | Path) -> None:
        payload = {
            "format": "urdu-byte-bpe-v1",
            "special_token": END_OF_TEXT,
            "special_token_id": 256,
            "vocab_size": self.vocab_size,
            "pretoken_pattern": PRETOKEN_PATTERN,
            "merges": self.merges,
        }
        Path(path).write_text(json.dumps(payload, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "BPETokenizer":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("format") != "urdu-byte-bpe-v1" or payload.get("special_token_id") != 256:
            raise ValueError("Unsupported tokenizer file")
        tokenizer = cls([tuple(pair) for pair in payload["merges"]])
        if tokenizer.vocab_size != payload.get("vocab_size"):
            raise ValueError("Tokenizer vocabulary size does not match its merge list")
        return tokenizer
