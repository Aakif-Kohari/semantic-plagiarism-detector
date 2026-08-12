"""Encoding fallback for document parsing."""

from __future__ import annotations

from typing import Any


def normalize_encoding(text: Any) -> str:
    """Replace common mojibake with the intended characters."""
    if not isinstance(text, str):
        return ""

    replacements = {
        "\ufffd": "",  # replacement character
        "Ã©": "é",
        "Ã¡": "á",
        "Ã¼": "ü",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text
