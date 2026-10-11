"""Small unit tests for the project normalizer; run with: python -m unittest."""
import unittest
from normalize import normalize


class NormalizeTests(unittest.TestCase):
    def test_yeh_and_alef_maksura(self):
        self.assertEqual(normalize("ي ى"), "ی ی")

    def test_kaf_and_heh(self):
        self.assertEqual(normalize("ك ه ھ ہ"), "ک ہ ھ ہ")

    def test_invisibles_and_tatweel(self):
        self.assertEqual(normalize("اـب\u200cج\u200dد"), "ابجد")

    def test_digit_convention(self):
        self.assertEqual(normalize("۱۲۳ ١٢٣ 123"), "123 123 123")

    def test_whitespace(self):
        self.assertEqual(normalize("  اردو\n\tمتن  "), "اردو متن")

    def test_empty_string(self):
        self.assertEqual(normalize(""), "")


if __name__ == "__main__":
    unittest.main()
