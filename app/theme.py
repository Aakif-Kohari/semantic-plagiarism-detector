from __future__ import annotations
"""
app/theme.py
------------
Theme management and CSS utility functions for the Semantic Plagiarism Detector.

Provides:
- Light and Dark theme color definitions
- CSS class name constants for consistent styling
- HTML generation helpers for UI components
- Dynamic theme injection for Streamlit
"""
# -*- coding: utf-8 -*-

from app.css_constants import (
    BADGE,
    EMPTY_STATE,
    EMPTY_ICON,
    EMPTY_TITLE,
    EMPTY_DESC,
    SIDEBAR_USER_BADGE,
    AVATAR,
    SIM_PILL,
)
"""
theme.py
--------
Centralized theme management and CSS injection for the Semantic Plagiarism Detector.

This module defines the color palettes for Light and Dark modes, provides 
utilities for sanitizing hex colors, and injects global CSS to ensure a 
cohesive, theme-aware user experience across all Streamlit components.

Recent Additions (Issue #572):
- Added comprehensive CSS rules targeting Streamlit's `.stFileUploader` 
  dropzone borders, background, and hover states to match the active theme tokens.
"""

import re
import secrets
import streamlit as st

# ── CSP Nonce Generation (Issue #644) ──────────────────────────────────────────
def generate_csp_nonce(length: int = 16) -> str:
    """Generate a cryptographically secure random hex nonce for use in CSP headers."""
    return secrets.token_hex(length)


def get_csp_nonce() -> str:
    """
    Retrieve or create a per-session CSP nonce stored in st.session_state.

    Generates a new nonce on the first call each session and returns the
    cached value on subsequent calls, ensuring a consistent nonce is used
    across all inline <style> and <script> blocks rendered in one page load.
    """
    try:
        if isinstance(st.session_state, dict):
            # Dict-like mock used in unit tests
            if not st.session_state.get("csp_nonce"):
                st.session_state["csp_nonce"] = generate_csp_nonce()
            return st.session_state["csp_nonce"]
        if "csp_nonce" not in st.session_state or not st.session_state.csp_nonce:
            st.session_state.csp_nonce = generate_csp_nonce()
        return st.session_state.csp_nonce
    except Exception:
        return generate_csp_nonce()


# ── Matplotlib Theme Helper ────────────────────────────────────────────────────
def apply_matplotlib_theme(theme_colors: dict | None = None) -> None:
    """Apply the active theme colours to Matplotlib's global rcParams."""
    try:
        import matplotlib as mpl
        colors = theme_colors if theme_colors is not None else get_colors()
        mpl.rcParams["figure.facecolor"] = colors.get("background", "#FFFFFF")
        mpl.rcParams["axes.facecolor"] = colors.get("surface", "#F8FAFC")
        mpl.rcParams["axes.edgecolor"] = colors.get("border", "#E2E8F0")
        mpl.rcParams["axes.labelcolor"] = colors.get("ink", "#0F172A")
        mpl.rcParams["xtick.color"] = colors.get("ink", "#0F172A")
        mpl.rcParams["ytick.color"] = colors.get("ink", "#0F172A")
        mpl.rcParams["text.color"] = colors.get("ink", "#0F172A")
    except Exception:
        pass


# ── Validation Patterns ────────────────────────────────────────────────────────
HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")


def sanitize_hex_color(color_val: str, fallback: str = "#000000") -> str:
    """
    Validates and sanitizes a hex color string against ^#(?:[0-9a-fA-F]{3}){1,2}$.
    Returns fallback if invalid.
    """
    if isinstance(color_val, str) and HEX_COLOR_PATTERN.match(color_val.strip()):
        return color_val.strip()
    return fallback


def sanitize_theme_colors(colors: dict) -> dict:
    """Sanitize all color values in a theme dictionary to ensure CSS safety."""
    sanitized = {}
    fallback_map = {
        "background": "#FFFFFF",
        "surface": "#F8FAFC",
        "card": "#FFFFFF",
        "ink": "#0F172A",
        "muted": "#64748B",
        "accent": "#0D9488",
        "border": "#E2E8F0",
        "input": "#FFFFFF",
        "neutral_soft": "#F1F5F9",
        "danger": "#FF4B4B",
        "danger_soft": "#FEE2E2",
        "warning": "#FFA500",
        "warning_soft": "#FEF3C7",
        "success": "#21C55D",
        "success_soft": "#DCFCE7",
    }
    for k, v in colors.items():
        fallback = fallback_map.get(k, "#000000")
        sanitized[k] = sanitize_hex_color(str(v), fallback=fallback)
    return sanitized


# ── CSS Class Constants ────────────────────────────────────────────────────────
try:
    from app.css_constants import (
        CLASS_AVATAR, CLASS_BADGE, CLASS_EMPTY_DESC, CLASS_EMPTY_ICON,
        CLASS_EMPTY_STATE, CLASS_EMPTY_TITLE, CLASS_PIPELINE_ACTIVE,
        CLASS_PIPELINE_ARROW, CLASS_PIPELINE_DONE, CLASS_PIPELINE_ETA,
        CLASS_PIPELINE_STEP, CLASS_PIPELINE_STEPS, CLASS_SIDEBAR_USER_BADGE,
        CLASS_SIM_PILL, CLASS_WELCOME_BANNER
    )
except ImportError:
    # Fallbacks for isolated testing
    CLASS_AVATAR = "avatar-circle"
    CLASS_BADGE = "severity-badge"
    CLASS_EMPTY_DESC = "empty-desc"
    CLASS_EMPTY_ICON = "empty-icon"
    CLASS_EMPTY_STATE = "empty-state"
    CLASS_EMPTY_TITLE = "empty-title"
    CLASS_PIPELINE_ACTIVE = "pipeline-active"
    CLASS_PIPELINE_ARROW = "pipeline-arrow"
    CLASS_PIPELINE_DONE = "pipeline-done"
    CLASS_PIPELINE_ETA = "pipeline-eta"
    CLASS_PIPELINE_STEP = "pipeline-step"
    CLASS_PIPELINE_STEPS = "pipeline-steps"
    CLASS_SIDEBAR_USER_BADGE = "sidebar-user-badge"
    CLASS_SIM_PILL = "sim-pill"
    CLASS_WELCOME_BANNER = "welcome-banner"


# ── Theme Definitions ──────────────────────────────────────────────────────────
THEMES = {
    "Light": {
        "background": "#FFFFFF",
        "surface": "#F8FAFC",
        "card": "#FFFFFF",
        "ink": "#0F172A",
        "muted": "#64748B",
        "accent": "#0D9488",
        "border": "#E2E8F0",
        "input": "#FFFFFF",
        "danger": "#FF4B4B",
        "danger_soft": "#FEE2E2",
        "warning": "#FFA500",
        "warning_soft": "#FEF3C7",
        "success": "#21C55D",
        "success_soft": "#DCFCE7",
        "neutral_soft": "#F1F5F9",
    },
    "Dark": {
        "background": "#0E1117",
        "surface": "#161B22",
        "card": "#1F2937",
        "ink": "#F8FAFC",
        "muted": "#CBD5E1",
        "accent": "#2DD4BF",
        "border": "#374151",
        "input": "#111827",
        "danger": "#F87171",
        "danger_soft": "#450A0A",
        "warning": "#FBBF24",
        "warning_soft": "#422006",
        "success": "#4ADE80",
        "success_soft": "#052E16",
        "neutral_soft": "#1E293B",
    },
}

# Backward-compatible default palette used by existing tests and callers.
COLORS = THEMES["Light"]

# ── Colormap Mappings & Constants ──────────────────────────────────────────────
UI_COLORMAP_OPTIONS: list[str] = ["Viridis", "Plasma", "Coolwarm", "YlOrRd"]

MATPLOTLIB_CMAP_MAPPING: dict[str, str] = {
    "Viridis": "viridis",
    "Plasma": "plasma",
    "Coolwarm": "coolwarm",
    "YlOrRd": "YlOrRd",
    "Legacy Red/Green": "RdYlGn_r",
}

PLOTLY_CMAP_MAPPING: dict[str, str] = {
    "Viridis": "Viridis",
    "Plasma": "Plasma",
    "Coolwarm": "RdBu_r",
    "YlOrRd": "YlOrRd",
    "Legacy Red/Green": "RdYlGn_r",
}

DEFAULT_UI_COLORMAP: str = "Viridis"


def initialize_theme() -> None:
    """Initialize the active theme for the current session."""
    try:
        if "theme" not in st.session_state:
            query_theme = st.query_params.get("theme")
            if query_theme and query_theme.lower() == "dark":
                st.session_state.theme = "Dark"
            elif query_theme and query_theme.lower() == "light":
                st.session_state.theme = "Light"
            else:
                st.session_state.theme = "Light"
                
        if "theme_colors" not in st.session_state:
            st.session_state.theme_colors = THEMES[st.session_state.theme]
    except Exception:
        pass


def get_theme_name() -> str:
    """Return the active theme name."""
    initialize_theme()
    try:
        return st.session_state.theme
    except Exception:
        return "Light"


def set_theme(theme_name: str) -> None:
    """Set the active theme."""
    if theme_name in THEMES:
        try:
            st.session_state.theme = theme_name
            st.session_state.theme_colors = THEMES[theme_name]
            st.query_params["theme"] = theme_name.lower()
        except Exception:
            pass


def get_colors() -> dict:
    """Return the colors for the active theme."""
    initialize_theme()
    try:
        return st.session_state.theme_colors
    except Exception:
        return THEMES["Light"]


def inject_css() -> None:
    """
    Inject CSS for the currently selected Light or Dark theme.
    
    Includes comprehensive styling for file uploaders, empty states, 
    pipeline indicators, and severity badges to ensure a cohesive UI.
    """
    colors = sanitize_theme_colors(get_colors())

    # Issue #572: File Uploader Drag-Zone Customization
    file_uploader_css = f"""
    /* File Uploader Drag-Zone Customization */
    .stFileUploader [data-testid="stFileUploaderDropzone"] {{
        border: 2px dashed {colors['border']} !important;
        border-radius: 8px !important;
        background-color: {colors['surface']} !important;
        transition: all 0.2s ease-in-out !important;
        padding: 1.5rem !important;
    }}
    
    .stFileUploader [data-testid="stFileUploaderDropzone"]:hover {{
        border-color: {colors['accent']} !important;
        background-color: {colors['neutral_soft']} !important;
        cursor: pointer !important;
    }}
    
    .stFileUploader [data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderInstruction"] {{
        color: {colors['muted']} !important;
        font-weight: 500 !important;
    }}
    
    .stFileUploader [data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderBrowseFiles"] {{
        background-color: {colors['accent']} !important;
        color: #FFFFFF !important;
        border-radius: 4px !important;
        font-weight: 600 !important;
        transition: background-color 0.2s ease !important;
    }}
    
    .stFileUploader [data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderBrowseFiles"]:hover {{
        background-color: {colors['ink']} !important;
    }}
    """

    # Issue #1028: Active Sidebar Tab Accent Border Styling
    sidebar_active_tab_css = f"""
    /* Active Sidebar Navigation Tab Highlight (Issue #1028) */
    section[data-testid="stSidebar"] .stButton button[data-selected="true"],
    section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"][aria-selected="true"],
    section[data-testid="stSidebar"] button[aria-selected="true"],
    section[data-testid="stSidebar"] .stButton button.st-active,
    .stButton button[data-selected="true"] {{
        border-left: 4px solid #4f46e5 !important;
        background-color: {colors.get('neutral_soft', '#F1F5F9')} !important;
        color: {colors.get('accent', '#0D9488')} !important;
        font-weight: 700 !important;
        border-top-left-radius: 0 !important;
        border-bottom-left-radius: 0 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        transition: border-left-color 0.2s ease, background-color 0.2s ease, color 0.2s ease !important;
    }}

    section[data-testid="stSidebar"] .stButton button[data-selected="true"]:hover,
    .stButton button[data-selected="true"]:hover {{
        border-left: 4px solid #4f46e5 !important;
        background-color: {colors.get('surface', '#F8FAFC')} !important;
    }}

    section[data-testid="stSidebar"] .stButton button:hover {{
        border-left: 4px solid #4f46e5;
        transition: border-left 0.2s ease !important;
    }}
    """

    base_css = f"""
    /* Global Theme Overrides */
    .stApp {{
        background-color: {colors['background']} !important;
        color: {colors['ink']} !important;
    }}
    
    .block-container {{
        padding-top: 2rem !important;
    }}
    
    .stAlert {{
        border-radius: 8px !important;
    }}
    
    .stCard {{
        background-color: {colors['card']} !important;
        border: 1px solid {colors['border']} !important;
        border-radius: 8px !important;
    }}
    
    /* Empty State Styling */
    .{CLASS_EMPTY_STATE} {{
        text-align: center;
        padding: 2rem;
        background-color: {colors['surface']};
        border-radius: 8px;
        border: 1px dashed {colors['border']};
    }}
    
    .{CLASS_EMPTY_ICON} {{
        font-size: 3rem;
        margin-bottom: 1rem;
        color: {colors['muted']};
    }}
    
    .{CLASS_EMPTY_TITLE} {{
        font-size: 1.25rem;
        font-weight: 600;
        color: {colors['ink']};
        margin-bottom: 0.5rem;
    }}
    
    .{CLASS_EMPTY_DESC} {{
        color: {colors['muted']};
        font-size: 0.95rem;
    }}
    
    /* Pipeline Progress Styling */
    .{CLASS_PIPELINE_STEPS} {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: 1.5rem 0;
    }}
    
    .{CLASS_PIPELINE_STEP} {{
        color: {colors['muted']};
        font-weight: 500;
        font-size: 0.9rem;
    }}
    
    .{CLASS_PIPELINE_ACTIVE} {{
        color: {colors['accent']};
        font-weight: 700;
    }}
    
    .{CLASS_PIPELINE_DONE} {{
        color: {colors['success']};
    }}
    
    .{CLASS_PIPELINE_ARROW} {{
        color: {colors['border']};
        margin: 0 0.5rem;
    }}
    
    .{CLASS_PIPELINE_ETA} {{
        font-size: 0.8rem;
        color: {colors['muted']};
        margin-top: 0.5rem;
        font-style: italic;
    }}
    
    /* Sidebar User Badge */
    .{CLASS_SIDEBAR_USER_BADGE} {{
        display: flex;
        align-items: center;
        padding: 0.75rem;
        background-color: {colors['surface']};
        border-radius: 8px;
        border: 1px solid {colors['border']};
        margin-bottom: 1rem;
    }}
    
    .{CLASS_AVATAR} {{
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background-color: {colors['accent']};
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        margin-right: 0.75rem;
    }}
    
    /* Severity Badges */
    .{CLASS_BADGE} {{
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
    }}
    
    .{CLASS_SIM_PILL} {{
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
    }}
    
    .{CLASS_WELCOME_BANNER} {{
        background: linear-gradient(135deg, {colors['accent']} 0%, {colors['success']} 100%);
        color: #FFFFFF;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }}
    """

    css = base_css + file_uploader_css + sidebar_active_tab_css

    if st.session_state.get("privacy_mode", False):
        css += """
        /* Privacy Mode: Blur student name labels */
        [class*="st-key-student_"] {
            filter: blur(4px) !important;
            transition: filter 0.3s ease;
        }
        [class*="st-key-student_"]:hover {
            filter: none !important;
        }
        """

    # Issue #644: wrap CSS in a nonced <style> block
    nonce = get_csp_nonce()
    css_html = f'<style nonce="{nonce}">\n{css}\n</style>'

    # ── Search Hotkey: press "/" to focus the warning search bar ──────────
    hotkey_js = f"""
    <script nonce="{nonce}">
    (function() {{
        // Prevent duplicate listeners (Streamlit re-runs on rerender)
        if (window.__chalu_hotkey_installed) return;
        window.__chalu_hotkey_installed = true;

        document.addEventListener('keydown', function(e) {{
            // Only trigger on "/" key
            if (e.key !== '/') return;
            // Don't intercept if user is already typing in an input/textarea
            var active = document.activeElement;
            if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA')) {{
                return;
            }}
            // Don't intercept modifier combos (Cmd+/, Ctrl+/)
            if (e.metaKey || e.ctrlKey || e.altKey) return;

            e.preventDefault();

            // Find the warning search input by its Streamlit widget key
            // Streamlit renders st.text_input(key="warning_search") with a
            // data attribute or aria-label matching the label text.
            var searchInputs = document.querySelectorAll('input[type="text"]');
            for (var i = 0; i < searchInputs.length; i++) {{
                var input = searchInputs[i];
                // Match by the placeholder or aria-label containing "search"
                var label = (input.getAttribute('placeholder') || '') +
                            (input.getAttribute('aria-label') || '');
                if (label.toLowerCase().indexOf('search') !== -1) {{
                    input.focus();
                    input.select();
                    return;
                }}
            }}
            // Fallback: try the .stTextInput class
            var textInputs = document.querySelectorAll('.stTextInput input[type="text"]');
            if (textInputs.length > 0) {{
                textInputs[0].focus();
                textInputs[0].select();
            }}
        }});
    }})();
    </script>
    """

    st.markdown(css_html, unsafe_allow_html=True)
    st.markdown(hotkey_js, unsafe_allow_html=True)


# ── Severity Helpers ───────────────────────────────────────────────────────────
try:
    from src.core.config import DEFAULT_THRESHOLDS, normalize_severity_label, severity_key
except ImportError:
    # Fallbacks for testing
    class DefaultThresholds:
        plagiarism = 0.59
    DEFAULT_THRESHOLDS = DefaultThresholds()
    def normalize_severity_label(label: str) -> str: return label.lower()
    def severity_key(score: float) -> str:
        if score >= 0.90:
            return "high"
        if score >= 0.59:
            return "medium"
        return "low"


def severity_tier(score: float, threshold: float = DEFAULT_THRESHOLDS.plagiarism) -> str:
    """Return the severity tier based on score and threshold."""
    if score >= 0.90:
        return "high"
    elif score >= threshold:
        return "medium"
    else:
        return "low"


def tier_from_severity_label(label: str) -> str:
    """Map canonical or legacy severity labels to a lowercase tier."""
    try:
        return normalize_severity_label(label).lower()
    except ValueError:
        return "low"


def tier_color(tier: str) -> str:
    """Returns color hex associated with a tier."""
    colors = get_colors()
    if tier == "high":
        return colors["danger"]
    elif tier == "medium":
        return colors["warning"]
    elif tier == "low":
        return colors["success"]
    return colors["neutral_soft"]


def badge_html(tier: str, label: str = None) -> str:
    """Generates standard HTML badge chip for severity."""
    colors = get_colors()
    if tier == "high":
        text_color = colors["danger"]
        bg_color = colors["danger_soft"]
        default_label = "🔴 High"
    elif tier == "medium":
        text_color = colors["warning"]
        bg_color = colors["warning_soft"]
        default_label = "🟡 Medium"
    else:
        text_color = colors["success"]
        bg_color = colors["success_soft"]
        default_label = "🟢 Low"

    display_label = label if label is not None else default_label
    return f'<span class="{BADGE}" style="background-color: {bg_color}; color: {text_color}; border: 1px solid {text_color};">{display_label}</span>'
    return f'<span class="{CLASS_BADGE}" style="background-color: {bg_color}; color: {text_color}; border: 1px solid {text_color};">{display_label}</span>'
    return f'<span class="{CLASS_BADGE}" style="color: {text_color}; background-color: {bg_color};">{display_label}</span>'


def format_similarity_html(score: float, threshold: float = DEFAULT_THRESHOLDS.plagiarism) -> str:
    """Return a themed similarity pill using central severity boundaries."""
    colors = get_colors()
    tier = severity_key(score)

    if tier == "high":
        bg = colors["danger"]
        text = "#FFFFFF"
    elif tier == "medium":
        bg = colors["warning"]
        text = "#000000"
    else:
        bg = colors["success"]
        text = "#FFFFFF"

    return (
        f'<span class="{SIM_PILL}" style="background:{bg};">'
        f'<span class="{CLASS_SIM_PILL}" style="background:{bg};">'
        f"Similarity: {score * 100:.1f}%</span>"
    )
    return f'<span class="{CLASS_SIM_PILL}" style="background-color: {bg}; color: {text};">Similarity: {score * 100:.1f}%</span>'


def empty_state_html(icon: str, title: str, description: str) -> str:
    """Return styled empty-state HTML block."""
    return (
        f'<div class="{EMPTY_STATE}">'
        f'<div class="{EMPTY_ICON}">{icon}</div>'
        f'<div class="{EMPTY_TITLE}">{title}</div>'
        f'<div class="{EMPTY_DESC}">{description}</div>'
        f'<div class="{CLASS_EMPTY_STATE}">'
        f'<div class="{CLASS_EMPTY_ICON}">{icon}</div>'
        f'<div class="{CLASS_EMPTY_TITLE}">{title}</div>'
        f'<div class="{CLASS_EMPTY_DESC}">{description}</div>'
        f'</div>'
    )


def sidebar_user_badge_html(username: str, role: str) -> str:
    """Return the sidebar user badge with avatar circle."""
    initial = username[0].upper() if username else "?"
    return (
        f'<div class="{SIDEBAR_USER_BADGE}">'
        f'<div class="{AVATAR}">{initial}</div>'
        f'<div><strong>{username}</strong><br>'
        f'<div class="{CLASS_SIDEBAR_USER_BADGE}">'
        f'<div class="{CLASS_AVATAR}">{initial}</div>'
        f'<div>'
        f'<div style="font-weight: 600;">{username}</div>'
        f'<div style="font-size: 0.8rem; color: {get_colors()["muted"]};">{role.upper()}</div>'
        f'</div>'
        f'</div>'
    )


def pipeline_progress_html(steps: list[str], active_index: int = -1, estimated_seconds: int | None = None) -> str:
    """Return a horizontal pipeline progress indicator with optional ETA."""
    parts = []
    for i, step in enumerate(steps):
        if active_index < 0:
            cls = CLASS_PIPELINE_STEP
        elif i < active_index:
            cls = f"{CLASS_PIPELINE_STEP} {CLASS_PIPELINE_DONE}"
        elif i == active_index:
            cls = f"{CLASS_PIPELINE_STEP} {CLASS_PIPELINE_ACTIVE}"
        else:
            cls = CLASS_PIPELINE_STEP

        prefix = "✓ " if active_index >= 0 and i < active_index else ""
        parts.append(f'<span class="{cls}">{prefix}{step}</span>')

        if i < len(steps) - 1:
            parts.append(f'<span class="{CLASS_PIPELINE_ARROW}">→</span>')

    progress = f'<div class="{CLASS_PIPELINE_STEPS}">{"".join(parts)}</div>'

    if estimated_seconds is None:
        return progress

    try:
        from src.utils.processing_time import format_processing_duration
        duration = format_processing_duration(estimated_seconds)
    except ImportError:
        duration = f"{estimated_seconds}s"
        
    eta = f'<div class="{CLASS_PIPELINE_ETA}">Estimated processing time: about {duration}</div>'
    return f"{progress}{eta}"


def back_to_top_html(scroll_threshold: int = 250) -> str:
    """Return HTML and JavaScript for a floating back-to-top button.
    The button is hidden by default and fades in once the user scrolls past
    the configured threshold.  Clicking it smoothly scrolls the page to the top.

    Streamlit (>= 1.28) scrolls inside a container whose parent holds
    ``[data-testid="block-container"]``, not the window viewport.

    The IIFE guards against duplicate listener registration across Streamlit
    reruns.  The click handler uses event delegation and the scroll handler
    re-queries the button on each event so that Streamlit reruns (which
    recreate the DOM) do not break the feature.
    """
    nonce = get_csp_nonce()
    return f"""
    <button id="back-to-top-btn"            type="button"
            aria-label="Back to top"
title="Back to top">
        ⬆️ Top
    </button>
    <div id="back-to-top-status" class="sr-only" role="status" aria-live="polite"></div>    <script nonce="{nonce}">
    (function () {{
        if (window.__backToTopInitialized) return;
        window.__backToTopInitialized = true;

var SCROLL_THRESHOLD = {scroll_threshold};
        /* Streamlit >= 1.28 scrolls inside the parent of
           [data-testid="block-container"], not the window. */
        var scrollContainer =
            document.querySelector('[data-testid="block-container"]')
                ?.parentElement
            || document.querySelector('section.main > div')
            || window;

        /* Event delegation — works even after Streamlit recreates the
           button element on a rerun. */
        scrollContainer.addEventListener('click', function (e) {{
            if (e.target.closest('#back-to-top-btn')) {{
                scrollContainer.scrollTo({{ top: 0, behavior: 'smooth' }});
            }}
        }});

        /* Re-query the button every scroll tick so the .visible class
           is always applied to the live element, not a detached one. */
scrollContainer.addEventListener('scroll', function () {{
            var btn = document.getElementById('back-to-top-btn');
            var status = document.getElementById('back-to-top-status');
            if (!btn) return;
            var scrollTop = scrollContainer === window
                ? window.scrollY
                : scrollContainer.scrollTop;
            var shouldShow = scrollTop > SCROLL_THRESHOLD;
            var wasVisible = btn.classList.contains('visible');
            btn.classList.toggle('visible', shouldShow);
            if (status && shouldShow && !wasVisible) {{
                status.textContent = 'Back to top button available';
            }} else if (status && !shouldShow && wasVisible) {{
                status.textContent = '';
            }}
        }}, {{ passive: true }});    }})();
    </script>
    """


def version_check_widget_html(local_version: str, latest_tag: str, repo_url: str = "https://github.com/Ganesh-403/semantic-plagiarism-detector/releases/latest") -> str:
    """Return an HTML snippet that renders an update-available notification banner."""
    colors = get_colors()
    warning_color = colors["warning"]
    warning_soft = colors["warning_soft"]
    ink = colors["ink"]

    return f"""
<div id="spd-update-banner" style="
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    margin-top: 8px;
    background: {warning_soft};
    border: 1px solid {warning_color};
    border-radius: 8px;
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    color: {ink};
">
    <span style="font-size: 1.1rem;">🔔</span>
    <span>
        <strong>Update available:</strong>
        v{local_version} &rarr; <strong>{latest_tag}</strong>.
        &nbsp;
        <a href="{repo_url}" target="_blank" rel="noopener noreferrer"
           style="color: {warning_color}; font-weight: 600; text-decoration: underline;">
            View release &rarr;
        </a>
    </span>
</div>
"""


def active_tab_border_style(color: str = "#4f46e5", width: int = 4) -> str:
    """Return inline CSS string for an active navigation tab accent border (Issue #1028).

    Args:
        color: Hex or CSS color string for the accent border.
        width: Border width in pixels.

    Returns:
        CSS declaration string, e.g. "border-left: 4px solid #4f46e5;".
    """
    valid_color = sanitize_hex_color(color, fallback="#4f46e5")
    return f"border-left: {width}px solid {valid_color};"


def get_active_sidebar_tab_css(accent_border_color: str = "#4f46e5") -> str:
    """Generate standalone CSS snippet for active sidebar tab buttons.

    Args:
        accent_border_color: Primary border color for active state.

    Returns:
        CSS style block string.
    """
    colors = get_colors()
    border = sanitize_hex_color(accent_border_color, fallback="#4f46e5")
    bg = colors.get("neutral_soft", "#F1F5F9")
    accent = colors.get("accent", "#0D9488")
    return f"""
    section[data-testid="stSidebar"] .stButton button[data-selected="true"],
    section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"][aria-selected="true"],
    .stButton button[data-selected="true"] {{
        border-left: 4px solid {border} !important;
        background-color: {bg} !important;
        color: {accent} !important;
        font-weight: 700 !important;
    }}
    """


def get_sidebar_tab_style(
    is_selected: bool = False,
    accent_border_color: str = "#4f46e5",
) -> dict[str, str]:
    """Return a dictionary of inline CSS properties for sidebar tab rendering.

    Args:
        is_selected: Whether the tab is currently active/selected.
        accent_border_color: Border accent color for the active state.

    Returns:
        Dictionary of CSS property names to values.
    """
    colors = get_colors()
    border = sanitize_hex_color(accent_border_color, fallback="#4f46e5")
    if is_selected:
        return {
            "border-left": f"4px solid {border}",
            "background-color": colors.get("neutral_soft", "#F1F5F9"),
            "color": colors.get("accent", "#0D9488"),
            "font-weight": "700",
        }
    return {
        "border-left": "4px solid transparent",
        "background-color": "transparent",
        "color": colors.get("ink", "#0F172A"),
        "font-weight": "400",
    }


# Theme Accent Palettes for custom sidebar highlight customization
THEME_ACCENT_PALETTES: dict[str, dict[str, str]] = {
    "Indigo": {"primary": "#4f46e5", "hover": "#4338ca", "light": "#e0e7ff"},
    "Teal": {"primary": "#0d9488", "hover": "#0f766e", "light": "#ccfbf1"},
    "Emerald": {"primary": "#059669", "hover": "#047857", "light": "#d1fae5"},
    "Rose": {"primary": "#e11d48", "hover": "#be123c", "light": "#ffe4e6"},
    "Violet": {"primary": "#7c3aed", "hover": "#6d28d9", "light": "#ede9fe"},
    "Amber": {"primary": "#d97706", "hover": "#b45309", "light": "#fef3c7"},
}


def get_theme_accent_color(theme_name: str | None = None) -> str:
    """Retrieve the primary accent color for a specified theme or active theme.

    Args:
        theme_name: Optional theme name ('Light', 'Dark', or palette name).

    Returns:
        Hex color string for active accent.
    """
    if theme_name in THEME_ACCENT_PALETTES:
        return THEME_ACCENT_PALETTES[theme_name]["primary"]
    if theme_name in THEMES:
        return THEMES[theme_name].get("accent", "#4f46e5")
    colors = get_colors()
    return colors.get("accent", "#4f46e5")


def build_active_tab_custom_css(
    accent_hex: str = "#4f46e5",
    border_width: int = 4,
    bg_hover: str | None = None,
) -> str:
    """Build dynamic custom CSS for active sidebar tab navigation.

    Args:
        accent_hex: Hex code for the left border accent.
        border_width: Width of the active border in pixels.
        bg_hover: Optional background color on hover.

    Returns:
        CSS text block with rules targeting active tab selectors.
    """
    border_color = sanitize_hex_color(accent_hex, fallback="#4f46e5")
    hover_bg = sanitize_hex_color(bg_hover, fallback="#F1F5F9") if bg_hover else "#F1F5F9"
    return f"""
    /* Custom Active Sidebar Tab Highlight */
    section[data-testid="stSidebar"] .stButton button[data-selected="true"],
    section[data-testid="stSidebar"] [aria-selected="true"],
    .stButton button[data-selected="true"] {{
        border-left: {border_width}px solid {border_color} !important;
        background-color: {hover_bg} !important;
        font-weight: 700 !important;
        transition: border-left 0.2s ease, background-color 0.2s ease !important;
    }}
    section[data-testid="stSidebar"] .stButton button[data-selected="true"]:hover {{
        border-left-color: {border_color} !important;
    }}
    """


def generate_active_tab_theme_tokens(theme_name: str | None = None) -> dict[str, str]:
    """Generate design system tokens for sidebar tab navigation states.

    Args:
        theme_name: Active theme ('Light' or 'Dark').

    Returns:
        Dictionary mapping tab state token keys to CSS color/dimension values.
    """
    selected_theme = theme_name if theme_name in THEMES else get_theme_name()
    palette = THEMES.get(selected_theme, THEMES["Light"])
    return {
        "active_border_color": "#4f46e5",
        "active_border_width": "4px",
        "active_bg_color": palette.get("neutral_soft", "#F1F5F9"),
        "active_text_color": palette.get("accent", "#0D9488"),
        "active_font_weight": "700",
        "inactive_bg_color": "transparent",
        "inactive_text_color": palette.get("ink", "#0F172A"),
        "inactive_font_weight": "400",
        "hover_border_color": "#4f46e5",
        "hover_bg_color": palette.get("surface", "#F8FAFC"),
    }


def get_sidebar_navigation_config() -> dict[str, Any]:
    """Return central configuration parameters for sidebar active tab rendering.

    Returns:
        Dictionary containing active tab style settings.
    """
    colors = get_colors()
    return {
        "accent_border_color": "#4f46e5",
        "accent_border_width_px": 4,
        "active_background": colors.get("neutral_soft", "#F1F5F9"),
        "active_text_color": colors.get("accent", "#0D9488"),
        "transition_duration_ms": 200,
        "border_position": "left",
        "supported_selectors": [
            'section[data-testid="stSidebar"] .stButton button[data-selected="true"]',
            'section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"][aria-selected="true"]',
            'section[data-testid="stSidebar"] button[aria-selected="true"]',
            'section[data-testid="stSidebar"] .stButton button.st-active',
            '.stButton button[data-selected="true"]',
        ],
    }


def render_active_tab_badge_html(tab_name: str, is_active: bool = False) -> str:
    """Render an HTML badge snippet representing an active/inactive tab indicator.

    Args:
        tab_name: Name of the navigation tab.
        is_active: Whether the tab is currently selected.

    Returns:
        HTML string representation.
    """
    colors = get_colors()
    if is_active:
        style = (
            f"border-left: 4px solid #4f46e5; "
            f"background-color: {colors.get('neutral_soft', '#F1F5F9')}; "
            f"color: {colors.get('accent', '#0D9488')}; "
            f"font-weight: 700; padding: 6px 12px; border-radius: 0 4px 4px 0;"
        )
    else:
        style = (
            f"border-left: 4px solid transparent; "
            f"background-color: transparent; "
            f"color: {colors.get('muted', '#64748B')}; "
            f"font-weight: 400; padding: 6px 12px;"
        )
    return f'<div class="sidebar-tab-badge" style="{style}">{tab_name}</div>'


SIDEBAR_TAB_THEME_TEMPLATES: dict[str, dict[str, str]] = {
    "Default": {
        "border_width": "4px",
        "border_style": "solid",
        "border_color": "#4f46e5",
        "border_radius": "0 6px 6px 0",
        "shadow": "0 1px 3px rgba(0,0,0,0.05)",
    },
    "Modern": {
        "border_width": "4px",
        "border_style": "solid",
        "border_color": "#4f46e5",
        "border_radius": "0 8px 8px 0",
        "shadow": "0 2px 4px rgba(79,70,229,0.15)",
    },
    "Glassmorphism": {
        "border_width": "4px",
        "border_style": "solid",
        "border_color": "#4f46e5",
        "border_radius": "0 10px 10px 0",
        "shadow": "0 4px 12px rgba(0,0,0,0.1)",
    },
    "Minimal": {
        "border_width": "3px",
        "border_style": "solid",
        "border_color": "#4f46e5",
        "border_radius": "0",
        "shadow": "none",
    },
    "High Contrast": {
        "border_width": "5px",
        "border_style": "solid",
        "border_color": "#4f46e5",
        "border_radius": "0 4px 4px 0",
        "shadow": "0 0 0 2px #000000",
    },
}


def generate_sidebar_theme_stylesheet(
    template_name: str = "Modern",
    accent_color: str = "#4f46e5",
) -> str:
    """Generate complete CSS stylesheet rules for sidebar navigation tabs.

    Args:
        template_name: Name of sidebar tab theme template.
        accent_color: Primary border accent color.

    Returns:
        Formatted CSS stylesheet block string.
    """
    template = SIDEBAR_TAB_THEME_TEMPLATES.get(template_name, SIDEBAR_TAB_THEME_TEMPLATES["Default"])
    border = sanitize_hex_color(accent_color, fallback="#4f46e5")
    colors = get_colors()
    return f"""
    /* Sidebar Navigation Stylesheet ({template_name}) */
    section[data-testid="stSidebar"] .stButton button[data-selected="true"],
    section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"][aria-selected="true"],
    section[data-testid="stSidebar"] button[aria-selected="true"],
    .stButton button[data-selected="true"] {{
        border-left: {template['border_width']} {template['border_style']} {border} !important;
        border-radius: {template['border_radius']} !important;
        box-shadow: {template['shadow']} !important;
        background-color: {colors.get('neutral_soft', '#F1F5F9')} !important;
        color: {colors.get('accent', '#0D9488')} !important;
        font-weight: 700 !important;
    }}
    """


def get_active_tab_accessibility_attributes(is_active: bool = True) -> dict[str, str]:
    """Return WAI-ARIA accessibility attributes for tab navigation buttons.

    Args:
        is_active: Whether the tab button is currently active.

    Returns:
        Dictionary of HTML attribute key-value pairs.
    """
    if is_active:
        return {
            "aria-selected": "true",
            "data-selected": "true",
            "tabindex": "0",
            "role": "tab",
        }
    return {
        "aria-selected": "false",
        "data-selected": "false",
        "tabindex": "-1",
        "role": "tab",
    }


def render_sidebar_navigation_menu(
    tabs: list[tuple[str, str]],
    active_tab_id: str,
) -> str:
    """Render an HTML string representing a complete sidebar navigation menu with active indicator.

    Args:
        tabs: List of tuples (tab_id, tab_label).
        active_tab_id: ID of the currently selected tab.

    Returns:
        HTML string containing menu container and tab elements.
    """
    html_items = []
    for tab_id, label in tabs:
        is_active = (tab_id == active_tab_id)
        badge = render_active_tab_badge_html(label, is_active=is_active)
        html_items.append(f'<li data-tab-id="{tab_id}">{badge}</li>')

    return f'<ul class="sidebar-nav-menu" style="list-style: none; padding: 0; margin: 0;">{"".join(html_items)}</ul>'



