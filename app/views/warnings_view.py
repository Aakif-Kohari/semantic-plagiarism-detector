"""
Warnings & Live Incident Stream View Component.

Renders Tab 1 containing detected plagiarism warnings, live feed auto-refresh,
date range filters, and expand/collapse controls.
"""

from datetime import date, timedelta

import streamlit as st

from app.session_keys import SessionKeys
from src.i18n.translator import get_text

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

try:
    from src.utils.warning_list import render_warning_controls
except ImportError:
    render_warning_controls = None


def get_date_range_preset(preset: str) -> tuple[date, date]:
    """Calculate start and end dates based on preset string."""
    today = date.today()
    if preset == "Today":
        return today, today
    elif preset == "Last 7 Days":
        return today - timedelta(days=6), today
    elif preset == "Last 30 Days":
        return today - timedelta(days=29), today
    else:  # "All Time"
        return date(2020, 1, 1), today


def render_warnings_view(
    flags: list, threshold: float, ai_probabilities: dict, lang_code: str
):
    """Render Tab 1: Warnings & Live Incident Stream."""
    st.subheader(get_text("tab_warnings", lang=lang_code))

    auto_refresh_enabled = st.toggle(
        "Auto-refresh live feed (30s)",
        value=False,
        key=SessionKeys.INCIDENT_STREAM_AUTO_REFRESH,
        help=(
            "When enabled, the incident feed re-runs every 30 seconds "
            "to surface newly flagged submissions automatically."
        ),
    )

    if auto_refresh_enabled and st_autorefresh is not None:
        st_autorefresh(
            interval=30 * 1000,
            key="incident_stream_autorefresh",
        )

    st.session_state[SessionKeys.INCIDENT_STREAM_AUTO_REFRESH] = auto_refresh_enabled

    if auto_refresh_enabled:
        if st_autorefresh is None:
            st.warning(
                "Auto-refresh is enabled, but the `streamlit-autorefresh` "
                "package is not installed. Install it via `pip install streamlit-autorefresh`."
            )
        else:
            st.caption("🔴 Live — refreshing every 30 seconds.")
    else:
        st.caption("⚪ Live feed paused — toggle on to auto-refresh.")

    st.divider()

    if SessionKeys.WARNINGS_EXPAND_ALL not in st.session_state:
        st.session_state[SessionKeys.WARNINGS_EXPAND_ALL] = False

    st.markdown("### 📅 Incident Date Filter")
    date_preset = st.radio(
        "Select Date Range",
        options=["Today", "Last 7 Days", "Last 30 Days", "All Time"],
        horizontal=True,
        key="incident_date_preset",
        help="Quickly filter the incident table by common date ranges.",
    )

    start_date, end_date = get_date_range_preset(date_preset)
    st.caption(
        f"Filtering incidents from **{start_date.strftime('%Y-%m-%d')}** to "
        f"**{end_date.strftime('%Y-%m-%d')}**"
    )

    if not flags:
        st.info("No plagiarism incidents detected above configured threshold.")
    elif render_warning_controls is not None:
        render_warning_controls(
            flags, threshold=threshold, ai_probabilities=ai_probabilities
        )

        button_label = (
            "📂 Expand All"
            if not st.session_state[SessionKeys.WARNINGS_EXPAND_ALL]
            else "📁 Collapse All"
        )

        if st.button(button_label, key="toggle_warning_accordions"):
            st.session_state[SessionKeys.WARNINGS_EXPAND_ALL] = not st.session_state[
                SessionKeys.WARNINGS_EXPAND_ALL
            ]
            st.rerun()

        render_warning_controls(
            flags,
            threshold=threshold,
            ai_probabilities=ai_probabilities,
            expanded=st.session_state[SessionKeys.WARNINGS_EXPAND_ALL],
        )
