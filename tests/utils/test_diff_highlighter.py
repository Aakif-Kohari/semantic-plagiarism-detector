"""Regression tests for diff highlighter overlap edge cases."""

import html

from src.utils.diff_highlighter import highlight_overlap


def test_no_overlap():
    """Completely different texts should not produce highlight tags."""
    result_a, result_b = highlight_overlap(
        "alpha beta gamma delta",
        "one two three four",
    )

    assert "<mark" not in result_a
    assert "</mark>" not in result_a
    assert "<mark" not in result_b
    assert "</mark>" not in result_b


def test_full_overlap():
    """Identical text should be fully wrapped in a highlight tag."""
    text = "alpha beta gamma delta"
    result_a, result_b = highlight_overlap(text, text)

    assert "<mark" in result_a
    assert "</mark>" in result_a
    assert "<mark" in result_b
    assert "</mark>" in result_b
    assert text in result_a
    assert text in result_b


def test_one_empty_input():
    """An empty input should return escaped text without highlight tags."""
    text = "<script>alert('x')</script>"
    result_a, result_b = highlight_overlap(text, "")

    assert result_a == html.escape(text)
    assert result_b == ""
    assert "<mark" not in result_a
    assert "<mark" not in result_b
