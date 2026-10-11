"""Course-project Urdu text normalization, written without an Urdu NLP library.

Normalization is deliberately separate from BPE tokenization.  Do not normalize
text inside BPETokenizer.encode(); keep this function in the corpus pipeline.
"""
from __future__ import annotations

import re
import unicodedata

# Convert common Arabic-script spellings to the Urdu code points specified by
# the assignment. The do-chashmi heh U+06BE is intentionally left unchanged.
_CHAR_MAP: dict[int, str | None] = {
    ord("\u064A"): "\u06CC",  # Arabic yeh -> Urdu yeh
    ord("\u0649"): "\u06CC",  # alef maksura -> Urdu yeh
    ord("\u0643"): "\u06A9",  # Arabic kaf -> Urdu kaf
    ord("\u0647"): "\u06C1",  # Arabic heh -> gol heh
    ord("\u0640"): None,       # tatweel
    ord("\u200C"): None,       # ZWNJ: removed, as allowed by assignment
    ord("\u200D"): None,       # ZWJ
    ord("\uFEFF"): None,       # BOM / zero-width no-break space
    ord("\u200E"): None,       # LRM
    ord("\u200F"): None,       # RLM
    ord("\u061C"): None,       # Arabic letter mark
    ord("\u202A"): None,       # bidi embedding/control characters
    ord("\u202B"): None,
    ord("\u202C"): None,
    ord("\u202D"): None,
    ord("\u202E"): None,
    ord("\u2066"): None,
    ord("\u2067"): None,
    ord("\u2068"): None,
    ord("\u2069"): None,
    ord("\u00A0"): " ",       # no-break space
    ord("\u202F"): " ",       # narrow no-break space
    ord("\u2000"): " ",
    ord("\u2001"): " ",
    ord("\u2002"): " ",
    ord("\u2003"): " ",
    ord("\u2004"): " ",
    ord("\u2005"): " ",
    ord("\u2006"): " ",
    ord("\u2007"): " ",
    ord("\u2008"): " ",
    ord("\u2009"): " ",
    ord("\u200A"): " ",
}

# Chosen convention: convert Arabic-Indic, Eastern Arabic-Indic (Urdu), and
# ASCII digits to ASCII 0-9. This makes equivalent numerals consistent.
for _start in (0x0660, 0x06F0):
    for _digit in range(10):
        _CHAR_MAP[_start + _digit] = str(_digit)

_TRANSLATION = str.maketrans(_CHAR_MAP)
_MULTI_SPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Normalize one document to a single-space-separated UTF-8-safe string."""
    if not isinstance(text, str):
        raise TypeError(f"normalize() expected str, received {type(text).__name__}")
    # NFC combines canonically equivalent Unicode sequences without applying
    # broad compatibility transformations that may alter text unnecessarily.
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_TRANSLATION)
    text = _MULTI_SPACE.sub(" ", text).strip()
    return text
