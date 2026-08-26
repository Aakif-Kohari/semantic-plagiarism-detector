"""
Streamlit Dashboard Component for FAISS Vector Embedding Search Telemetry
"""

import streamlit as st
from typing import Dict, Any, List


class FAISSVectorDashboardComponent:
    """
    Renders enterprise Streamlit UI widgets for FAISS dense vector search,
    L2 distance distribution, and nearest neighbor matches.
    """

    @staticmethod
    def render_vector_index_metrics(vector_count: int, dimension: int) -> None:
        """Renders vector index state metrics card."""
        st.subheader("⚡ FAISS Dense Vector Index Status")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Vectors Indexed", vector_count)
        with col2:
            st.metric("Embedding Dimension", f"{dimension}D")
        with col3:
            st.metric("Index Search Metric", "L2 Euclidean")

    @staticmethod
    def render_nearest_neighbor_results(results: list[dict[str, Any]]) -> None:
        """Renders top-k nearest neighbor match candidates."""
        st.subheader("🎯 Nearest Neighbor Semantic Matches")
        if not results:
            st.info("No nearest neighbor document matches found.")
            return

        for idx, res in enumerate(results):
            st.write(
                f"**Match #{idx + 1} - Document:** `{res.get('matchedDocId')}` | "
                f"**L2 Distance:** {res.get('l2Distance')} | "
                f"**Similarity Score:** {res.get('semanticSimilarityScore') * 100}%"
            )


# ==============================================================================
# STREAMLIT UI COMPONENT SPECIFICATIONS — FAISS VECTOR VISUALIZATION
# ------------------------------------------------------------------------------
# Section 1: Visual Design Guidelines
# - High-density metrics cards for vector search telemetry.
# - Clean interactive list layout for nearest neighbor search results.
# ==============================================================================
