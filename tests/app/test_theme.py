"""Tests for app/theme.py theming and styling utilities."""

import pytest
from app.theme import (
    THEMES,
    COLORS,
    severity_tier,
    tier_from_severity_label,
    tier_color,
    badge_html,
    format_similarity_html,
    empty_state_html,
    sidebar_user_badge_html,
    pipeline_progress_html,
)


def test_themes_have_expected_keys():
    """Verify both Light and Dark themes have all expected color keys."""
    required_keys = [
        "background",
        "surface",
        "card",
        "ink",
        "muted",
        "accent",
        "border",
        "input",
        "danger",
        "danger_soft",
        "warning",
        "warning_soft",
        "success",
        "success_soft",
        "neutral_soft",
    ]
    for theme_name, theme in THEMES.items():
        assert theme_name in ["Light", "Dark"]
        for key in required_keys:
            assert key in theme, f"Theme {theme_name} missing key: {key}"


def test_default_colors():
    """Verify default COLORS matches Light theme."""
    assert COLORS == THEMES["Light"]


def test_severity_tier_high():
    """Test high severity tier detection."""
    assert severity_tier(0.95, 0.59) == "high"
    assert severity_tier(0.90, 0.59) == "high"
    assert severity_tier(1.0, 0.59) == "high"


def test_severity_tier_medium():
    """Test medium severity tier detection."""
    assert severity_tier(0.85, 0.59) == "medium"
    assert severity_tier(0.75, 0.59) == "medium"
    assert severity_tier(0.59, 0.59) == "medium"


def test_severity_tier_low():
    """Test low severity tier detection."""
    assert severity_tier(0.50, 0.59) == "low"
    assert severity_tier(0.00, 0.59) == "low"
    assert severity_tier(0.58, 0.59) == "low"


def test_severity_tier_with_higher_threshold():
    """Test severity with different threshold."""
    assert severity_tier(0.76, 0.75) == "medium"
    assert severity_tier(0.75, 0.75) == "medium"
    assert severity_tier(0.74, 0.75) == "low"
    assert severity_tier(0.50, 0.75) == "low"


def test_tier_from_severity_label():
    """Test mapping severity labels to tier keys."""
    assert tier_from_severity_label("🔴 High") == "high"
    assert tier_from_severity_label("🟡 Medium") == "medium"
    assert tier_from_severity_label("HIGH") == "high"
    assert tier_from_severity_label("Warning") == "medium"
    assert tier_from_severity_label("Low") == "low"
    assert tier_from_severity_label("unknown") == "low"
    assert tier_from_severity_label("low") == "low"


def test_tier_color():
    """Test color mapping for severity tiers."""
    assert tier_color("high") == COLORS["danger"]
    assert tier_color("medium") == COLORS["warning"]
    assert tier_color("low") == COLORS["success"]
    assert tier_color("unknown") == COLORS["neutral_soft"]


def test_badge_html_default():
    """Test badge HTML generation with default label."""
    html = badge_html("high")
    assert "class=\"badge\"" in html
    assert f"background-color: {COLORS['danger_soft']}" in html
    assert f"color: {COLORS['danger']}" in html
    assert "border: 1px solid" in html
    assert COLORS["danger"] in html
    assert "🔴 High" in html

    html_med = badge_html("medium")
    assert f"background-color: {COLORS['warning_soft']}" in html_med
    assert f"color: {COLORS['warning']}" in html_med

    html_low = badge_html("low")
    assert f"background-color: {COLORS['success_soft']}" in html_low
    assert f"color: {COLORS['success']}" in html_low
    assert "🟢 Low" in html_low


def test_badge_html_custom_label():
    """Test badge HTML with custom label."""
    custom_label = "Custom Label"
    html = badge_html("high", custom_label)
    assert custom_label in html
    assert "🔴 High" not in html


def test_format_similarity_html():
    """Test similarity pill HTML generation."""
    high_html = format_similarity_html(0.95)
    assert 'class="sim-pill"' in high_html
    assert f"background:{COLORS['danger']};" in high_html
    assert "Similarity: 95.0%" in high_html

    med_html = format_similarity_html(0.80)
    assert f"background:{COLORS['warning']};" in med_html
    assert "Similarity: 80.0%" in med_html

    low_html = format_similarity_html(0.50)
    assert f"background:{COLORS['success']};" in low_html
    assert "Similarity: 50.0%" in low_html


def test_format_similarity_html_custom_threshold():
    """Test similarity pill with custom threshold."""
    html = format_similarity_html(0.70, threshold=0.75)
    assert f"background:{COLORS['success']};" in html


def test_empty_state_html():
    """Test empty state HTML generation."""
    html = empty_state_html("📁", "No Files", "Please upload files to continue.")
    assert 'class="empty-state"' in html
    assert 'class="empty-icon"' in html
    assert "📁" in html
    assert 'class="empty-title"' in html
    assert "No Files" in html
    assert 'class="empty-desc"' in html
    assert "Please upload files to continue." in html


def test_sidebar_user_badge_html():
    """Test sidebar user badge HTML generation."""
    html = sidebar_user_badge_html("testuser", "admin")
    assert 'class="sidebar-user-badge"' in html
    assert 'class="avatar"' in html
    assert "T" in html
    assert "<strong>testuser</strong>" in html
    assert "ADMIN" in html


def test_sidebar_user_badge_html_empty_username():
    """Test sidebar user badge with empty username."""
    html = sidebar_user_badge_html("", "user")
    assert "?" in html


def test_pipeline_progress_html_all_pending():
    """Test pipeline progress with all steps pending."""
    steps = ["Extract", "Chunk", "Embed"]
    html = pipeline_progress_html(steps)
    assert 'class="pipeline-steps"' in html
    assert 'class="pipeline-step"' in html
    assert "Extract" in html
    assert "Chunk" in html
    assert "Embed" in html
    assert "→" in html


def test_pipeline_progress_html_with_done_steps():
    """Test pipeline progress with completed steps."""
    steps = ["Extract", "Chunk", "Embed", "Flag"]
    html = pipeline_progress_html(steps, active_index=1)
    assert 'class="pipeline-step done"' in html
    assert 'class="pipeline-step active"' in html
    assert "✓ Extract" in html
    assert "Chunk" in html
    assert "→" in html


def test_pipeline_progress_html_with_active_and_done():
    """Test pipeline progress with active and completed steps."""
    steps = ["Extract", "Chunk", "Embed"]
    html = pipeline_progress_html(steps, active_index=1)
    assert 'class="pipeline-step active"' in html
    assert "✓ Extract" in html
    assert "Chunk" in html
