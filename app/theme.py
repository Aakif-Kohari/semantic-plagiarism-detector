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

from app.css_constants import (
    HERO_KICKER,
    BADGE,
    META_CHIP,
    META_CHIP_CODE,
    EMPTY_STATE,
    EMPTY_ICON,
    EMPTY_TITLE,
    EMPTY_DESC,
    SIDEBAR_USER_BADGE,
    AVATAR,
    PIPELINE_STEPS,
    PIPELINE_STEP,
    PIPELINE_STEP_ACTIVE,
    PIPELINE_STEP_DONE,
    PIPELINE_ARROW,
    MONO_TEXT,
    SIM_PILL,
    LOGIN_CONTAINER,
    LOGIN_HEADER,
    LOGIN_ICON,
    LOGIN_TITLE,
    LOGIN_SUBTITLE,
    LOGIN_ACCENT_BAR,
    APP_FOOTER,
    LEGEND_CONTAINER,
    LEGEND_ITEM,
    LEGEND_COLOR,
    ST_TEXT_INPUT,
    ST_TEXT_AREA,
    ST_NUMBER_INPUT,
    ST_BUTTON,
    ST_DOWNLOAD_BUTTON,
    ST_FORM_SUBMIT_BUTTON,
    ST_EXPANDER,
    ST_FORM,
    ST_DATAFRAME,
    ST_TABLE,
    ST_FILE_UPLOADER_DROPZONE,
    ST_CAPTION_CONTAINER,
    ST_CAPTION,
    ST_TABS,
    ST_TABS_BUTTON,
    ST_TABS_BUTTON_ACTIVE,
    WARNING_CARD_HIGH,
    WARNING_CARD_MEDIUM,
    WARNING_CARD_LOW,
)
import streamlit as st

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


def initialize_theme() -> None:
    """Initialize the active theme for the current session."""
    if "theme" not in st.session_state:
        st.session_state.theme = "Light"


def get_theme_name() -> str:
    """Return the active theme name."""
    initialize_theme()
    return st.session_state.theme


def set_theme(theme_name: str) -> None:
    """Set the active theme."""
    if theme_name in THEMES:
        st.session_state.theme = theme_name


def get_colors() -> dict:
    """Return the colors for the active theme."""
    return THEMES[get_theme_name()]


def inject_css() -> None:
    """Inject CSS for the currently selected Light or Dark theme."""
    colors = get_colors()

    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;0,6..72,700;1,6..72,400&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

        :root {{
            --background: {colors["background"]};
            --surface: {colors["surface"]};
            --card: {colors["card"]};
            --ink: {colors["ink"]};
            --muted: {colors["muted"]};
            --accent: {colors["accent"]};
            --border: {colors["border"]};
            --input: {colors["input"]};
            --neutral-soft: {colors["neutral_soft"]};
            --danger: {colors["danger"]};
            --danger-soft: {colors["danger_soft"]};
            --warning: {colors["warning"]};
            --warning-soft: {colors["warning_soft"]};
            --success: {colors["success"]};
            --success-soft: {colors["success_soft"]};
        }}

        html,
        body,
        [class*="css"] {{
            font-family: 'Inter', sans-serif !important;
        }}

        .stApp {{
            background-color: var(--background) !important;
            color: var(--ink) !important;
        }}

        [data-testid="stHeader"] {{
            background-color: var(--background) !important;
        }}

        [data-testid="stToolbar"] {{
            color: var(--ink) !important;
        }}

        h1,
        h2,
        h3,
        h4,
        h5,
        h6 {{
            font-family: 'Newsreader', Georgia, serif !important;
            color: var(--ink) !important;
            font-weight: 700 !important;
        }}

        p,
        label,
        span,
        li,
        [data-testid="stMarkdownContainer"],
        [data-testid="stWidgetLabel"] {{
            color: var(--ink);
        }}

        [data-testid="stCaptionContainer"],
        .stCaption {{
            color: var(--muted) !important;
        }}

        .hero-kicker {{
            font-family: 'Inter', sans-serif;
            font-size: 0.8rem;
            font-weight: 700;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-bottom: 0.25rem;
        }}

        /* ── Sidebar ────────────────────────────────────────────────── */

        [data-testid="stSidebar"] {{
            background-color: var(--surface) !important;
            border-right: 1px solid var(--border) !important;
        }}

        [data-testid="stSidebar"] * {{
            color: var(--ink);
        }}

        .sidebar-brand-title {{
            font-family: 'Newsreader', serif;
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--ink);
            text-align: center;
            line-height: 1.2;
            margin-top: 0.25rem;
            margin-bottom: 0;
        }}

        .sidebar-brand-kicker {{
            font-family: 'Inter', sans-serif;
            font-size: 0.7rem;
            font-weight: 700;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            text-align: center;
            margin-bottom: 1.25rem;
        }}

        .sidebar-section-label {{
            font-family: 'Inter', sans-serif;
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 2px;
        }}

        .sidebar-user-badge {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            border-radius: 8px;
            background-color: var(--neutral-soft);
            border: 1px solid var(--border);
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--ink);
            margin-bottom: 0.75rem;
        }}

        .sidebar-user-badge .avatar {{
            width: 28px;
            height: 28px;
            border-radius: 50%;
            background-color: var(--accent);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 700;
            flex-shrink: 0;
        }}

        /* ── Metric cards ───────────────────────────────────────────── */

        div[data-testid="stMetric"] {{
            background-color: var(--card) !important;
            border: 1px solid var(--border) !important;
            border-top: 4px solid var(--accent) !important;
            border-radius: 8px !important;
            padding: 14px 16px !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12) !important;
        }}

        div[data-testid="stMetricLabel"] > div {{
            font-family: 'Inter', sans-serif !important;
            font-size: 0.75rem !important;
            font-weight: 700 !important;
            color: var(--muted) !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
        }}

        div[data-testid="stMetricValue"] > div {{
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 1.6rem !important;
            font-weight: 700 !important;
            color: var(--ink) !important;
        }}

        div[data-testid="stMetricDelta"] > div {{
            font-family: 'Inter', sans-serif !important;
            font-size: 0.8rem !important;
            font-weight: 600 !important;
        }}

        /* ── Badge ──────────────────────────────────────────────────── */

        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 700;
            font-family: 'IBM Plex Mono', monospace;
            text-align: center;
        }}

        .meta-chip {{
            background-color: var(--neutral-soft);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--ink);
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}

        .meta-chip code {{
            font-family: 'IBM Plex Mono', monospace !important;
            background: none !important;
            padding: 0 !important;
            color: var(--accent) !important;
            font-weight: 700 !important;
        }}

        /* ── Login container ────────────────────────────────────────── */

        .login-container {{
            background-color: var(--card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            padding: 2.5rem !important;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.18) !important;
            max-width: 480px;
            margin: 2rem auto;
            animation: loginSlideIn 0.4s ease-out;
        }}

        .login-container .login-header {{
            text-align: center;
            margin-bottom: 1.5rem;
        }}

        .login-container .login-icon {{
            font-size: 3rem;
            line-height: 1;
            margin-bottom: 0.5rem;
        }}

        .login-container .login-title {{
            font-family: 'Newsreader', serif;
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 0.25rem;
        }}

        .login-container .login-subtitle {{
            font-size: 0.85rem;
            color: var(--muted);
        }}

        .login-accent-bar {{
            height: 4px;
            background: linear-gradient(90deg, var(--accent), transparent);
            border-radius: 2px;
            margin-bottom: 1.5rem;
        }}

        @keyframes loginSlideIn {{
            from {{
                opacity: 0;
                transform: translateY(12px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        /* ── Warning card accent borders ────────────────────────────── */

        .warning-card-high {{
            border-left: 4px solid var(--danger) !important;
        }}

        .warning-card-medium {{
            border-left: 4px solid var(--warning) !important;
        }}

        .warning-card-low {{
            border-left: 4px solid var(--success) !important;
        }}

        /* ── Similarity score pill ──────────────────────────────────── */

        .sim-pill {{
            display: inline-block;
            padding: 3px 12px;
            border-radius: 10px;
            font-size: 0.85rem;
            font-weight: 700;
            font-family: 'IBM Plex Mono', monospace;
            color: white;
        }}

        /* ── Mono text ──────────────────────────────────────────────── */

        .mono-text {{
            font-family: 'IBM Plex Mono', monospace !important;
        }}

        /* ── Legend ─────────────────────────────────────────────────── */

        .legend-container {{
            display: flex;
            gap: 16px;
            align-items: center;
            margin-bottom: 1rem;
            font-size: 0.8rem;
            font-weight: 500;
            color: var(--muted);
        }}

        .legend-item {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}

        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 3px;
            display: inline-block;
        }}

        /* ── Form inputs ────────────────────────────────────────────── */

        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        [data-baseweb="select"] > div {{
            background-color: var(--input) !important;
            color: var(--ink) !important;
            border-color: var(--border) !important;
        }}

        [data-baseweb="popover"],
        [data-baseweb="menu"],
        [role="listbox"] {{
            background-color: var(--card) !important;
            color: var(--ink) !important;
        }}

        .stButton button,
        .stDownloadButton button,
        .stFormSubmitButton button {{
            border-color: var(--border) !important;
        }}

        [data-testid="stExpander"],
        [data-testid="stForm"] {{
            background-color: var(--card) !important;
            border-color: var(--border) !important;
        }}

        [data-testid="stDataFrame"],
        [data-testid="stTable"] {{
            border-color: var(--border) !important;
        }}

        [data-testid="stFileUploaderDropzone"] {{
            background-color: var(--surface) !important;
            border-color: var(--border) !important;
        }}

        /* ── Tabs ───────────────────────────────────────────────────── */

        [data-testid="stTabs"] button {{
            color: var(--muted) !important;
        }}

        [data-testid="stTabs"] button[aria-selected="true"] {{
            color: var(--accent) !important;
            border-bottom-color: var(--accent) !important;
        }}

        hr {{
            border-color: var(--border) !important;
        }}

        /* ── Enhanced footer ────────────────────────────────────────── */

        .app-footer {{
            text-align: center;
            padding: 1rem 0 0.5rem;
            font-size: 0.78rem;
            color: var(--muted);
        }}

        .app-footer a {{
            color: var(--accent);
            text-decoration: none;
        }}

        .app-footer a:hover {{
            text-decoration: underline;
        }}

        /* ── Empty state ────────────────────────────────────────────── */

        .empty-state {{
            text-align: center;
            padding: 2.5rem 1rem;
            color: var(--muted);
        }}

        .empty-state .empty-icon {{
            font-size: 3rem;
            line-height: 1;
            margin-bottom: 0.75rem;
        }}

        .empty-state .empty-title {{
            font-family: 'Newsreader', serif;
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--ink);
            margin-bottom: 0.25rem;
        }}

        .empty-state .empty-desc {{
            font-size: 0.85rem;
            max-width: 400px;
            margin: 0 auto;
        }}

        /* ── Pipeline progress ──────────────────────────────────────── */

        .pipeline-steps {{
            display: flex;
            gap: 4px;
            align-items: center;
            justify-content: center;
            margin: 1rem 0;
            flex-wrap: wrap;
        }}

        .pipeline-step {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 600;
            background-color: var(--neutral-soft);
            color: var(--muted);
            border: 1px solid var(--border);
        }}

        .pipeline-step.active {{
            background-color: var(--accent);
            color: white;
            border-color: var(--accent);
            animation: pipelinePulse 1.2s ease-in-out infinite;
        }}

        .pipeline-step.done {{
            background-color: var(--success-soft);
            color: var(--success);
            border-color: var(--success);
        }}

        .pipeline-arrow {{
            color: var(--muted);
            font-size: 0.7rem;
        }}

        @keyframes pipelinePulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
        }}

        /* ── Responsive: mobile / tablet ────────────────────────────── */

        @media (max-width: 768px) {{
            .login-container {{
                padding: 1.5rem !important;
                margin: 1rem auto;
            }}

            .sidebar-brand-title {{
                font-size: 1.25rem;
            }}

            div[data-testid="stMetricValue"] > div {{
                font-size: 1.3rem !important;
            }}
        }}
    </style>
    """

    st.markdown(css, unsafe_allow_html=True)


# ── Severity helpers ──────────────────────────────────────────────────────────


def severity_tier(score: float, threshold: float) -> str:
    """
    Categorizes the score into a severity tier matching the backend.

    High: >= 0.90
    Medium: >= threshold
    Low: < threshold
    """
    if score >= 0.90:
        return "high"
    elif score >= threshold:
        return "medium"
    else:
        return "low"


def tier_from_severity_label(label: str) -> str:
    """Maps existing label string to tier key."""
    clean = label.lower()
    if "high" in clean:
        return "high"
    elif "medium" in clean or "warn" in clean:
        return "medium"
    else:
        return "low"


def tier_color(tier: str) -> str:
    """Returns color hex associated with a tier."""
    if tier == "high":
        return get_colors()["danger"]
    elif tier == "medium":
        return get_colors()["warning"]
    elif tier == "low":
        return get_colors()["success"]
    return get_colors()["neutral_soft"]


def badge_html(tier: str, label: str = None) -> str:
    """Generates standard HTML badge chip for severity."""
    if tier == "high":
        text_color = get_colors()["danger"]
        bg_color = get_colors()["danger_soft"]
        default_label = "🔴 High"
    elif tier == "medium":
        text_color = get_colors()["warning"]
        bg_color = get_colors()["warning_soft"]
        default_label = "🟡 Medium"
    else:
        text_color = get_colors()["success"]
        bg_color = get_colors()["success_soft"]
        default_label = "🟢 Low"

    display_label = label if label is not None else default_label
    return f'<span class="{BADGE}" style="background-color: {bg_color}; color: {text_color}; border: 1px solid {text_color};">{display_label}</span>'


# ── UI helpers ────────────────────────────────────────────────────────────────


def format_similarity_html(score: float, threshold: float = 0.59) -> str:
    """Return a themed similarity pill for use with st.markdown(unsafe_allow_html=True)."""
    colors = get_colors()
    if score >= 0.90:
        bg = colors["danger"]
    elif score >= threshold:
        bg = colors["warning"]
    else:
        bg = colors["success"]
    return (
        f'<span class="{SIM_PILL}" style="background:{bg};">'
        f"Similarity: {score * 100:.1f}%</span>"
    )


def empty_state_html(icon: str, title: str, description: str) -> str:
    """Return styled empty-state HTML block."""
    return (
        f'<div class="{EMPTY_STATE}">'
        f'<div class="{EMPTY_ICON}">{icon}</div>'
        f'<div class="{EMPTY_TITLE}">{title}</div>'
        f'<div class="{EMPTY_DESC}">{description}</div>'
        f"</div>"
    )


def sidebar_user_badge_html(username: str, role: str) -> str:
    """Return the sidebar user badge with avatar circle."""
    initial = username[0].upper() if username else "?"
    return (
        f'<div class="{SIDEBAR_USER_BADGE}">'
        f'<div class="{AVATAR}">{initial}</div>'
        f'<div><strong>{username}</strong><br>'
        f'<span style="font-size:0.7rem;color:var(--muted);">{role.upper()}</span></div>'
        f"</div>"
    )


def pipeline_progress_html(steps: list[str], active_index: int = -1) -> str:
    """Return a horizontal pipeline progress indicator.

    Args:
        steps: List of step labels (e.g. ["Extract", "Chunk", "Embed", ...]).
        active_index: 0-based index of the currently running step.
            Steps before *active_index* are marked done; steps after are
            pending.  Pass -1 (default) to mark all steps as pending.
    """
    parts = []
    for i, step in enumerate(steps):
        if active_index < 0:
            cls = PIPELINE_STEP
        elif i < active_index:
            cls = PIPELINE_STEP_DONE
        elif i == active_index:
            cls = PIPELINE_STEP_ACTIVE
        else:
            cls = PIPELINE_STEP

        prefix = "✓ " if (active_index >= 0 and i < active_index) else ""
        parts.append(f'<span class="{cls}">{prefix}{step}</span>')
        if i < len(steps) - 1:
            parts.append(f'<span class="{PIPELINE_ARROW}">→</span>')

    return f'<div class="{PIPELINE_STEPS}">{"".join(parts)}</div>'
