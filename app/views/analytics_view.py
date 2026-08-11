"""
Analytics Dashboard View Component.

Renders Tab 7 analytics dashboard and pipeline timing breakdowns.
"""

import streamlit as st
from app.theme import get_chart_colors

try:
    from src.visualization.analytics import plot_processing_time_breakdown
except ImportError:
    plot_processing_time_breakdown = None


def render_analytics_view():
    """Render Tab 7: Analytics Dashboard."""
    st.subheader("📊 Analytics Dashboard")
    st.markdown("### ⏱️ Pipeline Processing Time Breakdown")
    stage_timings = st.session_state.get("last_stage_timings") or st.session_state.get("stage_timings")
    if plot_processing_time_breakdown:
        active_theme_colors = get_chart_colors() if callable(get_chart_colors) else None
        fig_time = plot_processing_time_breakdown(
            stage_timings=stage_timings,
            theme_colors=active_theme_colors,
        )
        st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.info("Analytics metrics summary loaded.")
