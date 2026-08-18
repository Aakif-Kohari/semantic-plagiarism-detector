"""
src/utils/diff_highlighter.py
-----------------------------
Utilities for highlighting overlapping text segments between two documents.

Provides HTML rendering functions that visually emphasize matching phrases,
words, or character sequences to help instructors quickly identify plagiarized
content in side-by-side comparison views.
"""

from __future__ import annotations

import re
import html
from typing import Tuple


def highlight_overlap(
    text_a: str, 
    text_b: str, 
    min_match_length: int = 4
) -> Tuple[str, str]:
    """Highlight overlapping sequences between two text strings.
    
    Identifies common word sequences of at least `min_match_length` words
    and wraps them in HTML <mark> tags with a distinct background color.
    This helps instructors visually identify plagiarized phrases while
    ignoring common stop words and short coincidental matches.
    
    Args:
        text_a: The first document's text chunk.
        text_b: The second document's text chunk.
        min_match_length: Minimum number of consecutive words required to
                         constitute a "match". Defaults to 4 to avoid
                         highlighting common phrases like "in the" or "and the".
                         
    Returns:
        A tuple of two HTML strings (highlighted_a, highlighted_b) with
        matching sequences wrapped in <mark> tags. Returns escaped HTML
        to prevent XSS vulnerabilities.
        
    Examples:
        >>> a, b = highlight_overlap("the quick brown fox", "a quick brown dog")
        >>> "<mark>" in a
        True
    """
    if not text_a or not text_b:
        return html.escape(text_a or ""), html.escape(text_b or "")
    
    # Escape HTML entities first to prevent XSS
    safe_a = html.escape(text_a)
    safe_b = html.escape(text_b)
    
    # Tokenize into words for sequence matching
    words_a = re.findall(r'\b\w+\b', text_a.lower())
    words_b = re.findall(r'\b\w+\b', text_b.lower())
    
    if not words_a or not words_b:
        return safe_a, safe_b
    
    # Find longest common subsequence of words
    matches = []
    for i in range(len(words_a)):
        for j in range(len(words_b)):
            k = 0
            while (i + k < len(words_a) and 
                   j + k < len(words_b) and 
                   words_a[i + k] == words_b[j + k]):
                k += 1
            
            if k >= min_match_length:
                # Store match as (start_idx_a, end_idx_a, start_idx_b, end_idx_b)
                matches.append((i, i + k, j, j + k))
    
    if not matches:
        return safe_a, safe_b
    
    # Apply highlighting to the original text
    # We need to map word indices back to character positions
    def highlight_text(text: str, word_matches: list[tuple[int, int]]) -> str:
        """Apply <mark> tags to matching word sequences."""
        if not word_matches:
            return html.escape(text)
        
        # Find character positions for each word
        word_positions = []
        for match in re.finditer(r'\b\w+\b', text):
            word_positions.append((match.start(), match.end()))
        
        # Build highlighted string
        result = []
        last_end = 0
        
        for start_word, end_word in sorted(word_matches):
            if start_word >= len(word_positions):
                continue
                
            char_start = word_positions[start_word][0]
            char_end = word_positions[min(end_word - 1, len(word_positions) - 1)][1]
            
            # Add non-matching text
            result.append(html.escape(text[last_end:char_start]))
            # Add highlighted matching text
            result.append(f'<mark style="background-color: #fef08a; padding: 2px 4px; border-radius: 3px;">')
            result.append(html.escape(text[char_start:char_end]))
            result.append('</mark>')
            
            last_end = char_end
        
        # Add remaining text
        result.append(html.escape(text[last_end:]))
        return "".join(result)
    
    # Extract unique match ranges for each text
    ranges_a = sorted(list(set((m[0], m[1]) for m in matches)))
    ranges_b = sorted(list(set((m[2], m[3]) for m in matches)))
    
    # Merge overlapping ranges to prevent nested <mark> tags
    def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
        if not ranges:
            return []
        merged = [ranges[0]]
        for start, end in ranges[1:]:
            if start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return merged
    
    ranges_a = merge_ranges(ranges_a)
    ranges_b = merge_ranges(ranges_b)
    
    # Issue #2003: Fixed indentation - return statement now properly aligned at column 8
    return (
        highlight_text(text_a, ranges_a),
        highlight_text(text_b, ranges_b)
    )


def _escape_text(text: str) -> str:
    """Escape HTML and Markdown syntax characters."""
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for m_char in ["*", "_", "~", "`", "#", "[", "]", "(", ")", "|", "{", "}"]:
        escaped = escaped.replace(m_char, f"\\{m_char}")
    return escaped


def _sanitize_color(color: str, fallback: str = "rgba(250, 204, 21, 0.3)") -> str:
    """Sanitize CSS color value to prevent HTML/CSS/JS injection."""
    if not isinstance(color, str):
        return fallback
    color_trimmed = color.strip()
    if any(c in color_trimmed for c in ("'", '"', ";", "<", ">")):
        return fallback
    if re.match(
        r"^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*[\d\.]+%?)?\s*\)$",
        color_trimmed,
    ):
        return color_trimmed
    if any(c in color_trimmed for c in ("(", ")")):
        return fallback
    if re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$|^[a-zA-Z]+$", color_trimmed):
        return color_trimmed
    return fallback


def _build_html(
    tokens: list[str],
    highlight_mask: list[bool],
    theme_colors: dict[str, str] | None = None,
) -> str:
    """Build the final HTML string by grouping highlighted tokens inside <mark> tags."""
    parts = []
    in_highlight = False

    for token, should_highlight in zip(tokens, highlight_mask):
        escaped_token = _escape_text(token)

        if should_highlight:
            if not in_highlight:
                raw_bg = (
                    theme_colors.get("warning_soft", "rgba(250, 204, 21, 0.3)")
                    if theme_colors
                    else "rgba(250, 204, 21, 0.3)"
                )
                highlight_bg = _sanitize_color(raw_bg)

                parts.append(
                    f"<mark style='background-color: {highlight_bg}; "
                    "color: inherit; padding: 1px 3px; border-radius: 3px;'>"
                )
                in_highlight = True

            parts.append(escaped_token)
        else:
            if in_highlight:
                parts.append("</mark>")
                in_highlight = False
            parts.append(escaped_token)

    if in_highlight:
        parts.append("</mark>")

    return "".join(parts)
