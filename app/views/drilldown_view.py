"""
Pair Drill-Down View Component.

Renders Tab 5 containing Cosine vs Lexical score comparisons and pairwise
document snippet inspection.
"""

import itertools

import pandas as pd
import streamlit as st

from src.core.lexical_similarity import jaccard_similarity
from src.utils.diff_highlighter import highlight_overlap

try:
    from src.utils.warning_list import render_copy_button
except ImportError:
    render_copy_button = None

SEMANTIC_HIGH_THRESHOLD = 0.80
LEXICAL_LOW_THRESHOLD = 0.30


def render_cosine_vs_lexical_comparison_table(
    sim_df,
    raw_texts,
    *,
    semantic_threshold: float = SEMANTIC_HIGH_THRESHOLD,
    lexical_threshold: float = LEXICAL_LOW_THRESHOLD,
):
    """Render Cosine vs Lexical comparison table."""
    if sim_df is None or raw_texts is None or len(raw_texts) < 2:
        st.info(
            "Upload at least two documents to view the Cosine vs Lexical "
            "Similarity comparison table."
        )
        return None

    doc_names = list(sim_df.columns) if sim_df is not None else list(raw_texts.keys())
    rows = []
    for da, db in itertools.combinations(doc_names, 2):
        try:
            cosine_score = float(sim_df.loc[da, db])
        except Exception:
            cosine_score = 0.0

        text_a = raw_texts.get(da, "") or ""
        text_b = raw_texts.get(db, "") or ""
        try:
            jaccard_score = float(jaccard_similarity(text_a, text_b))
        except Exception:
            jaccard_score = 0.0

        is_semantic_only = (
            cosine_score >= semantic_threshold and jaccard_score <= lexical_threshold
        )
        rows.append(
            {
                "Document A": da,
                "Document B": db,
                "Cosine (Semantic)": cosine_score,
                "Jaccard (Lexical)": jaccard_score,
                "Semantic Only": is_semantic_only,
            }
        )

    comp_df = pd.DataFrame(rows)
    if not comp_df.empty:
        st.dataframe(comp_df, use_container_width=True)

    return comp_df


def render_drilldown_view(active_sim_df, raw_texts: dict, flags: list, doc_names: list):
    """Render Tab 5: Pair Drill-Down."""
    st.subheader("🔬 Pair Drill-Down")

    render_cosine_vs_lexical_comparison_table(
        active_sim_df,
        raw_texts,
        semantic_threshold=SEMANTIC_HIGH_THRESHOLD,
        lexical_threshold=LEXICAL_LOW_THRESHOLD,
    )

    st.markdown("---")

    if active_sim_df is not None and len(doc_names) >= 2:
        c1, c2 = st.columns(2)
        with c1:
            da = st.selectbox("Document A", doc_names, key="da")
        with c2:
            db = st.selectbox("Document B", [d for d in doc_names if d != da], key="db")
        sim_val = float(active_sim_df.loc[da, db])
        st.write(f"Overall Similarity: `{sim_val:.1%}`")

        pair_flags = [
            f
            for f in flags
            if (f["doc_a"] == da and f["doc_b"] == db)
            or (f["doc_a"] == db and f["doc_b"] == da)
        ]

        if pair_flags:
            st.markdown("### 📝 Flagged Snippets")
            for rank, flag in enumerate(pair_flags, 1):
                ca = str(flag.get("snippet_a", ""))
                cb = str(flag.get("snippet_b", ""))

                if flag["doc_a"] == db:
                    ca, cb = cb, ca

                highlighted_ca, highlighted_cb = highlight_overlap(ca, cb)

                with st.expander(
                    f"Incident #{rank} - Similarity: {flag.get('similarity', 0.0):.1%}",
                    expanded=(rank == 1),
                ):
                    c_a, c_b = st.columns(2)
                    with c_a:
                        st.markdown(f"**{da}**")
                        st.markdown(highlighted_ca, unsafe_allow_html=True)
                        if render_copy_button:
                            render_copy_button(
                                text_to_copy=ca,
                                button_id=f"copy_ca_{rank}",
                                copy_label="📋 Copy Snippet",
                            )
                    with c_b:
                        st.markdown(f"**{db}**")
                        st.markdown(highlighted_cb, unsafe_allow_html=True)
                        if render_copy_button:
                            render_copy_button(
                                text_to_copy=cb,
                                button_id=f"copy_cb_{rank}",
                                copy_label="📋 Copy Snippet",
                            )
