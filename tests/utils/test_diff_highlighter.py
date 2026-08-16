"""Unit tests for the diff highlighting utility."""

from src.utils.diff_highlighter import highlight_overlap


def test_highlight_overlap_exact_match():
    """Verify that exact matching sub-segments are highlighted in yellow."""
    text_a = "This is a very long sequence of words that is matching exactly here."
    text_b = "This is another sequence of words that is matching exactly here."

    html_a, html_b = highlight_overlap(text_a, text_b, min_match_len=15)

    # The matching part "sequence of words that is matching exactly here." is 47 characters.
    # It should be wrapped in the styled <mark> tag.
    mark_style = (
        "style='background-color: rgba(250, 204, 21, 0.3); "
        "color: inherit; padding: 1px 3px; border-radius: 3px;'"
    )
    assert f"<mark {mark_style}>" in html_a
    assert f"<mark {mark_style}>" in html_b
    assert "matching exactly here." in html_a
    assert "matching exactly here." in html_b


def test_highlight_overlap_no_match():
    """Verify that strings with no overlap are returned fully escaped but unhighlighted."""
    text_a = "Abc def ghi"
    text_b = "Xyz opq rst"

    html_a, html_b = highlight_overlap(text_a, text_b, min_match_len=5)

    assert "<mark" not in html_a
    assert "<mark" not in html_b
    assert html_a == "Abc def ghi"
    assert html_b == "Xyz opq rst"


def test_highlight_overlap_below_threshold():
    """Verify that matches below the minimum character length threshold are ignored."""
    text_a = "Match here"
    text_b = "Match also"

    # Match "Match" is 5 characters, which is below min_match_len of 10.
    html_a, html_b = highlight_overlap(text_a, text_b, min_match_len=10)

    assert "<mark" not in html_a
    assert "<mark" not in html_b


def test_highlight_overlap_html_escaping():
    """Verify that HTML special characters are escaped to prevent XSS."""
    text_a = "Match <b>bold HTML</b> and check code & characters"
    text_b = "Match <b>bold HTML</b> and check other & symbols"

    html_a, _ = highlight_overlap(text_a, text_b, min_match_len=10)

    assert "<b>" not in html_a
    assert "&amp;" in html_a
    assert "&lt;b&gt;" in html_a


def test_highlight_overlap_markdown_escaping():
    """Verify that Markdown formatting characters are escaped to prevent rendering bugs."""
    text_a = "Match *bold markdown* and _italic_ and [link]()"
    text_b = "Match *bold markdown* and _italic_ and [other link]()"

    html_a, _ = highlight_overlap(text_a, text_b, min_match_len=10)

    # Markdown characters should be backslash-escaped
    assert "\\*" in html_a
    assert "\\_" in html_a
    assert "\\[" in html_a


def test_highlight_overlap_empty_inputs():
    """Verify that empty inputs are handled gracefully without crashing."""
    html_a, html_b = highlight_overlap("", "some text")
    assert html_a == ""
    assert html_b == "some text"


# ── Edge Case Tests (Issue #2246) ────────────────────────────────────────────

def test_highlight_overlap_both_empty():
    """Both empty strings should return two empty strings without crashing."""
    html_a, html_b = highlight_overlap("", "")
    assert html_a == ""
    assert html_b == ""


def test_highlight_overlap_identical_strings():
    """Identical strings should be fully highlighted."""
    text = "The quick brown fox jumps over the lazy dog"
    html_a, html_b = highlight_overlap(text, text, min_match_len=5)
    assert "<mark" in html_a
    assert "<mark" in html_b


def test_highlight_overlap_custom_theme_colors():
    """Custom theme_colors dict should override the default highlight color."""
    text_a = "shared content between two documents here"
    text_b = "shared content in another document here"
    custom_color = "rgba(0, 255, 0, 0.4)"
    html_a, html_b = highlight_overlap(
        text_a, text_b, min_match_len=5,
        theme_colors={"warning_soft": custom_color}
    )
    assert custom_color in html_a
    assert custom_color in html_b


def test_highlight_overlap_custom_theme_colors_missing_key():
    """Missing warning_soft key in theme_colors falls back to default color."""
    text_a = "shared content between two documents here"
    text_b = "shared content in another document here"
    html_a, _ = highlight_overlap(
        text_a, text_b, min_match_len=5,
        theme_colors={"other_key": "blue"}
    )
    assert "rgba(250, 204, 21, 0.3)" in html_a


def test_highlight_overlap_whitespace_only():
    """Whitespace-only inputs should not produce mark tags."""
    html_a, html_b = highlight_overlap("   ", "   ", min_match_len=5)
    assert "<mark" not in html_a
    assert "<mark" not in html_b


def test_highlight_overlap_single_word_above_threshold():
    """A single long matching word above min_match_len should be highlighted."""
    text_a = "supercalifragilistic is a word"
    text_b = "supercalifragilistic appears here"
    html_a, html_b = highlight_overlap(text_a, text_b, min_match_len=10)
    assert "<mark" in html_a
    assert "<mark" in html_b


def test_highlight_overlap_numeric_strings():
    """Numeric-only strings with no alphanumeric overlap produce no highlights."""
    html_a, html_b = highlight_overlap("123 456", "789 012", min_match_len=5)
    assert "<mark" not in html_a
    assert "<mark" not in html_b


def test_highlight_overlap_unicode_text():
    """Unicode and emoji characters are handled without crashing."""
    text_a = "Héllo wörld café résumé shared phrase"
    text_b = "Bonjour shared phrase monde café"
    html_a, html_b = highlight_overlap(text_a, text_b, min_match_len=5)
    assert isinstance(html_a, str)
    assert isinstance(html_b, str)


def test_highlight_overlap_min_match_len_zero():
    """min_match_len=0 should highlight all non-empty matching tokens."""
    text_a = "hello world"
    text_b = "hello there"
    html_a, html_b = highlight_overlap(text_a, text_b, min_match_len=0)
    assert "<mark" in html_a
    assert "<mark" in html_b


def test_highlight_overlap_returns_tuple_of_two_strings():
    """Return type is always a tuple of exactly two strings."""
    result = highlight_overlap("foo bar baz", "foo qux baz", min_match_len=3)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(isinstance(r, str) for r in result)


def test_highlight_overlap_malicious_theme_colors():
    """Verify malicious theme color values are sanitized/rejected to prevent injection."""
    text_a = "shared content between two documents here"
    text_b = "shared content in another document here"
    malicious_color = "'); alert(1); //"
    html_a, html_b = highlight_overlap(
        text_a,
        text_b,
        min_match_len=5,
        theme_colors={"warning_soft": malicious_color},
    )
    assert malicious_color not in html_a
    assert "alert(1)" not in html_a
    assert "rgba(250, 204, 21, 0.3)" in html_a

