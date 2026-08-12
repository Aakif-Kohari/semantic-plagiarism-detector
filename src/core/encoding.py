"""
src/core/encoding.py
--------------------
Utilities for detecting, normalizing, and repairing text encoding issues
commonly encountered when extracting text from PDFs, DOCX files, and
legacy web scrapes.

Real-world documents often suffer from "mojibake" — character garbling
caused by interpreting text in the wrong encoding (e.g., reading UTF-8
bytes as Windows-1252 or Latin-1). This module provides lookup tables
and helper functions to reverse these transformations.

Recent Additions (Issue #2052):
- Expanded the mojibake replacement dictionary from 3 patterns to 20+
  patterns covering common Windows-1252 → UTF-8 garbling scenarios.
- Added detailed docstrings explaining the origin of each pattern.
- Added detect_mojibake() heuristic to identify potentially garbled text.
"""

import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)

# ── Mojibake Replacement Dictionary ───────────────────────────────────────────
# This dictionary maps common mojibake sequences (resulting from UTF-8 text
# being incorrectly decoded as Windows-1252/Latin-1) back to their correct
# UTF-8 characters.
#
# Origin of patterns:
# When a UTF-8 encoded character (which may use 2-4 bytes) is read by a
# system expecting single-byte Windows-1252, each byte is mapped to a
# distinct character. For example, the UTF-8 bytes for 'ñ' (0xC3 0xB1)
# are interpreted as 'Ã' (0xC3) and '±' (0xB1) in Windows-1252, resulting
# in the garbled string "Ã±".
#
# Handled Patterns (Issue #2052):
# - Accented vowels and consonants (Ã± → ñ, Ã³ → ó, Ã­ → í, etc.)
# - Smart quotes and apostrophes (â€œ → “, â€ → ”, â€™ → ’)
# - Dashes and ellipses (â€” → —, â€“ → –, â€¦ → …)
# - Common symbols and ligatures (ÃŸ → ß, Ã¦ → æ, Ã¸ → ø)
# - Stray control characters (Â → empty string)

MOJIBAKE_REPLACEMENTS: Dict[str, str] = {
    # --- Original 3 patterns ---
    "Ã©": "é",  # e with acute
    "Ã¡": "á",  # a with acute
    "Ã¼": "ü",  # u with diaeresis
    
    # --- Expanded Windows-1252 → UTF-8 patterns (Issue #2052) ---
    
    # Spanish / Portuguese accents
    "Ã±": "ñ",  # n with tilde
    "Ã³": "ó",  # o with acute
    "Ã­": "í",  # i with acute
    "Ãº": "ú",  # u with acute
    "Ã§": "ç",  # c with cedilla
    
    # French / German accents
    "Ã¨": "è",  # e with grave
    "Ãª": "ê",  # e with circumflex
    "Ã®": "î",  # i with circumflex
    "Ã´": "ô",  # o with circumflex
    "Ã»": "û",  # u with circumflex
    "ÃŸ": "ß",  # German sharp s (Eszett)
    
    # Nordic characters
    "Ã¦": "æ",  # ae ligature
    "Ã¸": "ø",  # o with stroke
    "Ã¥": "å",  # a with ring above
    
    # Smart quotes (Microsoft Word auto-formatting)
    "â€œ": "“",  # Left double quotation mark
    "â€": "”",   # Right double quotation mark
    "â€˜": "‘",  # Left single quotation mark
    "â€™": "’",  # Right single quotation mark (apostrophe)
    
    # Punctuation and symbols
    "â€”": "—",  # Em dash
    "â€“": "–",  # En dash
    "â€¦": "…",  # Horizontal ellipsis
    "Â": "",     # Stray non-breaking space prefix (often appears before symbols)
    "Ã": "Ã",   # Capital A with tilde (sometimes garbled, kept as-is if standalone)
}

# Compile a regex pattern for efficient bulk replacement.
# We sort the keys by length (longest first) to ensure multi-byte sequences
# like "â€œ" are matched before shorter sequences like "â".
_SORTED_MOJIBAKE_KEYS = sorted(MOJIBAKE_REPLACEMENTS.keys(), key=len, reverse=True)
_MOJIBAKE_PATTERN = re.compile(
    "|".join(re.escape(key) for key in _SORTED_MOJIBAKE_KEYS)
)


def normalize_encoding(text: str) -> str:
    """Repair common mojibake patterns in extracted text.
    
    Applies a pre-compiled regex substitution to replace garbled character
    sequences (resulting from UTF-8/Windows-1252 encoding mismatches) with
    their correct Unicode equivalents.
    
    This function is idempotent — applying it multiple times to the same
    text will not alter already-corrected characters.
    
    Args:
        text: The raw extracted text potentially containing mojibake.
        
    Returns:
        The cleaned text with mojibake patterns replaced. Returns an empty
        string if the input is None or not a string.
        
    Examples:
        >>> normalize_encoding("The cafÃ© was beautifÃ»l.")
        'The café was beautifûl.'
        
        >>> normalize_encoding("He said, â€œHello!â€")
        'He said, “Hello!”'
        
    Handled Patterns:
        See the module-level `MOJIBAKE_REPLACEMENTS` dictionary for the
        complete list of 20+ supported garbling patterns.
    """
    if not text or not isinstance(text, str):
        return ""
        
    # Use the compiled regex for O(N) replacement performance
    return _MOJIBAKE_PATTERN.sub(
        lambda match: MOJIBAKE_REPLACEMENTS[match.group(0)],
        text
    )


def detect_mojibake(text: str, threshold: float = 0.05) -> bool:
    """Heuristically detect if a text string contains significant mojibake.
    
    Calculates the ratio of known mojibake sequences to the total text length.
    If the ratio exceeds the threshold, the text is likely garbled and should
    be passed through `normalize_encoding()`.
    
    Args:
        text: The text to inspect.
        threshold: Minimum ratio of mojibake characters to trigger a positive
                   detection. Defaults to 0.05 (5%).
                   
    Returns:
        True if the text appears to contain mojibake, False otherwise.
    """
    if not text or not isinstance(text, str):
        return False
        
    # Count occurrences of known mojibake patterns
    matches = _MOJIBAKE_PATTERN.findall(text)
    if not matches:
        return False
        
    # Calculate total characters consumed by mojibake patterns
    mojibake_chars = sum(len(m) for m in matches)
    ratio = mojibake_chars / len(text)
    
    return ratio >= threshold
