"""
Utilities for rendering and formatting FAISS search results.

This module provides helper functions for retrieving,
formatting, and displaying vector search results.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd
import streamlit as st


RESULT_COLUMNS: list[str] = [
    "Rank",
    "Target Document",
    "Chunk",
    "Similarity Score",
    "Matching Text",
    "Stats",
]


def _record_value(record: Any, name: str, default: Any = None) -> Any:
    """
    Read a field from dataclass-like or mapping-like records.

    Args:
        record: The record to read the field from (mapping or object).
        name: The name of the field to read.
        default: The default value to return if the field is not found.

    Returns:
        The value of the field, or the default value.
    """
    if isinstance(record, dict):
        return record.get(name, default)
    return getattr(record, name, default)


def faiss_results_dataframe(
    results: Iterable[tuple[Any, float]],
    min_similarity: float | None = None,
    max_similarity: float | None = None,
) -> pd.DataFrame:
    """
    Convert FAISS records into a sortable display DataFrame.

    Args:
        results: An iterable of tuples containing a record and a raw similarity score.
        min_similarity: Minimum similarity score to include.
        max_similarity: Maximum similarity score to include.

    Returns:
        A pandas DataFrame containing the formatted search results.
    """
    rows: list[dict[str, Any]] = []

    for record, raw_score in results:
        score: float = float(raw_score)

        if min_similarity is not None and score < min_similarity:
            continue
        if max_similarity is not None and score > max_similarity:
            continue

        document: str = str(_record_value(record, "doc_name", "Unknown document"))
        chunk_index: int = int(_record_value(record, "chunk_index", 0))
        chunk_text: str = str(_record_value(record, "chunk_text", ""))

        from src.utils.text_stats import format_text_stats

        rows.append(
            {
                "Target Document": document,
                "Chunk": chunk_index + 1,
                "Similarity Score": score,
                "Matching Text": chunk_text,
                "Stats": format_text_stats(chunk_text),
            }
        )

    if not rows:
        return pd.DataFrame(columns=RESULT_COLUMNS)

    dataframe: pd.DataFrame = pd.DataFrame(rows)
    dataframe = dataframe.sort_values(
        by=["Similarity Score", "Target Document", "Chunk"],
        ascending=[False, True, True],
        kind="stable",
    ).reset_index(drop=True)

    dataframe.insert(0, "Rank", range(1, len(dataframe) + 1))

    return dataframe[RESULT_COLUMNS]


@st.dialog("🔍 Chunk Diff Inspector", width="large")
def inspect_diff_dialog(query_text: str, matched_text: str, doc_name: str, score: float):
    """Render a side-by-side highlighted diff of query vs matched chunk inside a modal."""
    st.markdown(f"### Match Similarity: **{score:.1%}**")

    from src.utils.diff_highlighter import highlight_overlap
    highlighted_query, highlighted_match = highlight_overlap(query_text, matched_text)

    col_q, col_m = st.columns(2)
    with col_q:
        st.markdown("### 📝 Query Text")
        st.markdown(
            f"<div style='border: 1px solid #cccccc; padding: 12px; border-radius: 6px; min-height: 150px; white-space: pre-wrap;'>{highlighted_query}</div>",
            unsafe_allow_html=True
        )
    with col_m:
        st.markdown(f"### 📄 Matched Chunk ({doc_name})")
        st.markdown(
            f"<div style='border: 1px solid #cccccc; padding: 12px; border-radius: 6px; min-height: 150px; white-space: pre-wrap;'>{highlighted_match}</div>",
            unsafe_allow_html=True
        )


def render_faiss_results_ui(
    results: Iterable[tuple[Any, float]],
    query_text: str,
) -> None:
    """
    Render FAISS search results with a clean interface and an interactive 
    'Inspect Diff' modal dialog for side-by-side comparison.
    """



    if not results:
        st.info("No significant matches found above threshold.")
        return

    for i, (record, raw_score) in enumerate(results):
        score = float(raw_score)
        doc_name = str(_record_value(record, "doc_name", "Unknown document"))
        chunk_index = int(_record_value(record, "chunk_index", 0))
        chunk_text = str(_record_value(record, "chunk_text", ""))

        st.markdown(
            f"<div style='border: 1px solid #e2e8f0; padding: 12px; border-radius: 8px; margin-bottom: 12px;'>"
            f"<strong>📄 {doc_name}</strong> (Chunk #{chunk_index + 1}) · "
            f"<span style='color: #3b82f6; font-weight: bold;'>Similarity: {score:.1%}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        st.caption(chunk_text[:300] + ("..." if len(chunk_text) > 300 else ""))

        if st.button("🔍 Inspect Diff", key=f"diff_btn_{i}_{doc_name}_{chunk_index}"):
            inspect_diff_dialog(query_text, chunk_text, doc_name, score)

        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

