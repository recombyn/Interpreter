from __future__ import annotations

import unicodedata


_FULLWIDTH = str.maketrans(
    {i: i - 0xFEE0 for i in range(0xFF01, 0xFF5F)}
)


def normalize_text(text: str) -> str:
    """NFC + fullwidth ASCII to halfwidth. Encoding only, not semantics."""
    folded = unicodedata.normalize("NFC", text).translate(_FULLWIDTH)
    return " ".join(folded.split()).strip()
