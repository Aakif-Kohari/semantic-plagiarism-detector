from unittest.mock import patch

from app.theme import badge_html, get_colors, inject_css


def test_get_colors_returns_valid_theme_colors():
    colors = get_colors()

    assert isinstance(colors, dict)
    assert colors
    assert "background" in colors
    assert "accent" in colors


def test_inject_css_generates_css_without_errors():
    with patch("app.theme.st.markdown") as mock_markdown:
        inject_css()

    mock_markdown.assert_called_once()

    css = mock_markdown.call_args.args[0]

    assert isinstance(css, str)
    assert len(css.strip()) > 0
    assert "<style>" in css


def test_badge_html_returns_valid_html():
    html = badge_html("high")

    assert isinstance(html, str)
    assert len(html.strip()) > 0
    assert "badge" in html