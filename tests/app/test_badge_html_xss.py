"""Regression tests for badge_html HTML escaping."""

from app.theme import badge_html


def test_badge_html_escapes_malicious_label():
    """Ensure malicious HTML in a custom badge label is rendered as text."""
    malicious_label = "<script>alert(1)</script>"

    html = badge_html("high", malicious_label)

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html
