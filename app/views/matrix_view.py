"""
Similarity Matrix View Component.

Renders Tab 3 displaying document similarity matrix dataframe.
"""

import streamlit as st


def render_matrix_view(active_sim_df):
    """Render Tab 3: Similarity Matrix."""
    st.subheader("📋 Similarity Matrix")
    if active_sim_df is not None:
        st.dataframe(active_sim_df.style.format("{:.4f}"), use_container_width=True)
    else:
        st.info("No document similarity matrix available yet.")
