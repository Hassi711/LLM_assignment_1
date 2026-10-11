"""Tests for byte-level BPE training, serialization, and lossless Unicode handling."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from bpe import BPETokenizer
from encode_corpus import encode_file


class BPETokenizerTests(unittest.TestCase):
    def test_reference_and_fast_trainers_learn_same_merges(self):
        sample = "اردو وُردُا ZWNJ token\nکتاب 🙂 <|endoftext|>"
        self.assertEqual(
            BPETokenizer.train_reference(sample * 4, 280).merges,
            BPETokenizer.train_fast([sample * 4], 280).merges,
        )

    def test_lossless_round_trip_and_special_id(self):
        text = "کتاب وُردُا English 🙂\n<|endoftext|> ١٢٣"
        tokenizer = BPETokenizer.train_fast([text * 4], 280)
        encoded = tokenizer.encode(text)
        self.assertIn(256, encoded)
        self.assertEqual(tokenizer.decode(encoded), text)
        self.assertEqual(tokenizer.encode(""), [])

    def test_equal_frequency_uses_greater_byte_pair(self):
        tokenizer = BPETokenizer.train_fast(["ab ac"], 258)
        self.assertEqual(tokenizer.merges[0], (ord("a"), ord("c")))

    def test_saved_tokenizer_and_numpy_export(self):
        text = "اردو sample\n<|endoftext|>\n"
        tokenizer = BPETokenizer.train_fast([text * 4], 268)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model_path = root / "tokenizer.json"
            source_path = root / "corpus.txt"
            encoded_path = root / "corpus.bin"
            tokenizer.save(model_path)
            restored = BPETokenizer.load(model_path)
            with source_path.open("w", encoding="utf-8", newline="\n") as source:
                source.write(text)
            count = encode_file(restored, source_path, encoded_path)
            values = np.load(encoded_path)
            self.assertEqual(values.dtype, np.uint16)
            self.assertEqual(count, len(values))
            self.assertEqual(restored.decode(values.tolist()), text)

            empty_path = root / "empty.bin"
            empty_source = root / "empty.txt"
            empty_source.write_bytes(b"")
            self.assertEqual(encode_file(restored, empty_source, empty_path), 0)
            self.assertEqual(np.load(empty_path).dtype, np.uint16)


if __name__ == "__main__":
    unittest.main()
