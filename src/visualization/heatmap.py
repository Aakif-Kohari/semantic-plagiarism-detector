"""
heatmap.py
----------
Generates similarity heatmaps.
- plot_similarity_heatmap        → Matplotlib/Seaborn (high-res PNG download)
- plot_similarity_heatmap_plotly → Plotly (interactive hover values)
- plot_chunk_similarity_comparison → Matplotlib chunk-level heatmap
"""

from typing import Optional

import matplotlib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure
from matplotlib.ticker import PercentFormatter

matplotlib.use("Agg")

from src.core.similarity import PLAGIARISM_THRESHOLD

# ── Colour palette ─────────────────────────────────────────────────────────────
# RdYlGn_r: Red (high similarity / risk) → Yellow → Green (low similarity)
_CMAP = "RdYlGn_r"


def plot_similarity_heatmap(
    similarity_df: pd.DataFrame,
    title: str = "Semantic Similarity Matrix",
    threshold: float = PLAGIARISM_THRESHOLD,
    figsize: Optional[tuple] = None,
    annotate: bool = True,
    dpi: int = 150,
    theme_colors: Optional[dict] = None,
) -> Figure:
    """
    High-resolution Matplotlib heatmap for PNG download.

    Args:
        similarity_df: Square N×N DataFrame of cosine similarity scores.
        title:         Plot title.
        threshold:     Scores >= this get a red border.
        figsize:       (width, height) in inches; auto-sized if None.
        annotate:      Annotate cells with numeric scores.
        dpi:           Resolution for savefig (default 150 → high-res PNG).

    Returns:
        Matplotlib Figure (use fig.savefig(..., dpi=dpi) for high-res export).
    """
    n = len(similarity_df)

    # Guard for empty DataFrame (0 documents)
    if n == 0:
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.set_title(title)
        return fig

    if figsize is None:
        cell_size = max(1.2, 6 / n)
        figsize = (max(6, n * cell_size + 2), max(5, n * cell_size + 1.5))

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    sns.heatmap(
        similarity_df,
        ax=ax,
        annot=annotate,
        fmt=".2f" if annotate else "",
        cmap=_CMAP,
        vmin=0.0,
        vmax=1.0,
        linewidths=0.6,
        linecolor="#cccccc",
        square=True,
        cbar_kws={"label": "Cosine Similarity", "shrink": 0.8, "pad": 0.02},
        annot_kws={"size": max(7, 14 - n), "weight": "bold"},
    )

    colorbar = ax.collections[0].colorbar
    colorbar.ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))

    if theme_colors:
        fig.patch.set_facecolor(theme_colors.get("background", "#FFFFFF"))
        ax.set_facecolor(theme_colors.get("surface", "#F8FAFC"))
        ax.tick_params(colors=theme_colors.get("ink", "#0F172A"))
        ax.xaxis.label.set_color(theme_colors.get("ink", "#0F172A"))
        ax.yaxis.label.set_color(theme_colors.get("ink", "#0F172A"))
        title_color = theme_colors.get("ink", "#0F172A")
    else:
        title_color = "black"

    data = similarity_df.values

    # Diagonal border (self-similarity)
    for i in range(n):
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (i, i),
                1,
                1,
                boxstyle="square,pad=0",
                linewidth=2,
                edgecolor="#555555",
                facecolor="none",
                zorder=3,
            )
        )

    # Red border on flagged pairs
    for i in range(n):
        for j in range(n):
            if i != j and data[i, j] >= threshold:
                ax.add_patch(
                    mpatches.FancyBboxPatch(
                        (j, i),
                        1,
                        1,
                        boxstyle="square,pad=0",
                        linewidth=2.5,
                        edgecolor="#d62728",
                        facecolor="none",
                        zorder=4,
                    )
                )

    ax.set_title(title, fontsize=15, fontweight="bold", pad=16, color=title_color)
    ax.set_xlabel("Documents", fontsize=11, labelpad=10)
    ax.set_ylabel("Documents", fontsize=11, labelpad=10)
    ax.set_xticklabels(
        ax.get_xticklabels(), rotation=30, ha="right", fontsize=max(8, 11 - n // 3)
    )
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=max(8, 11 - n // 3))

    red_patch = mpatches.Patch(
        edgecolor="#d62728",
        facecolor="none",
        linewidth=2,
        label=f"Potential Plagiarism (≥ {threshold:.0%})",
    )
    ax.legend(
        handles=[red_patch],
        loc="upper left",
        bbox_to_anchor=(0.0, -0.18),
        frameon=True,
        fontsize=9,
    )
    if theme_colors:
        legend = ax.get_legend()
        if legend:
            for text in legend.get_texts():
                text.set_color(theme_colors.get("ink", "#0F172A"))
            legend.get_frame().set_facecolor(theme_colors.get("background", "#FFFFFF"))
            legend.get_frame().set_edgecolor(theme_colors.get("border", "#E2E8F0"))

    fig.tight_layout()
    return fig


def plot_similarity_heatmap_plotly(
    similarity_df: pd.DataFrame,
    title: str = "Semantic Similarity Matrix",
    threshold: float = PLAGIARISM_THRESHOLD,
    theme_colors: Optional[dict] = None,
):
    """
    Interactive Plotly heatmap with hover values and flagged-pair annotations.

    Returns a plotly.graph_objects.Figure for st.plotly_chart().
    """
    # Guard for empty DataFrame (0 documents)
    if similarity_df.empty or len(similarity_df) == 0:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.update_layout(title=title)
        return fig

    import plotly.graph_objects as go

    names = list(similarity_df.columns)
    z = similarity_df.values.tolist()
    n = len(names)

    # Custom hover text: show both doc names + score
    hover = [
        [
            f"<b>{names[i]}</b> vs <b>{names[j]}</b><br>Similarity: {similarity_df.values[i, j]:.4f}"
            for j in range(n)
        ]
        for i in range(n)
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=names,
            y=names,
            text=hover,
            hovertemplate="%{text}<extra></extra>",
            colorscale="RdYlGn_r",
            zmin=0.0,
            zmax=1.0,
            colorbar=dict(title="Cosine Similarity", thickness=15),
            xgap=1,
            ygap=1,
        )
    )

    # Annotate each cell with its score
    annotations = []
    for i in range(n):
        for j in range(n):
            val = similarity_df.values[i, j]
            annotations.append(
                dict(
                    x=names[j],
                    y=names[i],
                    text=f"{val:.2f}",
                    showarrow=False,
                    font=dict(
                        size=max(9, 14 - n),
                        color="black" if 0.3 < val < 0.8 else "white",
                        family="Arial Black",
                    ),
                )
            )

    # Red rectangle shapes on flagged pairs
    shapes = []
    for i in range(n):
        for j in range(n):
            if i != j and similarity_df.values[i, j] >= threshold:
                shapes.append(
                    dict(
                        type="rect",
                        x0=j - 0.5,
                        x1=j + 0.5,
                        y0=i - 0.5,
                        y1=i + 0.5,
                        line=dict(color="#d62728", width=3),
                    )
                )

    cell_px = max(80, 600 // n)

    bg_color = theme_colors.get("background", "#FFFFFF") if theme_colors else "#FFFFFF"
    ink_color = theme_colors.get("ink", "#0F172A") if theme_colors else "#0F172A"

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, family="Arial Black")),
        height=max(500, n * cell_px + 150),
        autosize=True,
        xaxis=dict(side="bottom", tickangle=-30),
        yaxis=dict(autorange="reversed"),
        annotations=annotations,
        shapes=shapes,
        margin=dict(l=140, r=60, t=70, b=140),
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        font=dict(color=ink_color),
    )

    return fig


def plot_chunk_similarity_comparison(
    doc_a_name: str,
    doc_b_name: str,
    chunks_a: list,
    chunks_b: list,
    sim_matrix: np.ndarray,
    theme_colors: Optional[dict] = None,
) -> Figure:
    """Chunk-level similarity heatmap between two documents."""
    na, nb = sim_matrix.shape

    def short_label(text, max_chars=40):
        return text[:max_chars].strip() + "…" if len(text) > max_chars else text

    row_labels = [f"A{i + 1}: {short_label(c)}" for i, c in enumerate(chunks_a)]
    col_labels = [f"B{j + 1}: {short_label(c)}" for j, c in enumerate(chunks_b)]

    fig, ax = plt.subplots(figsize=(max(8, nb * 1.5), max(6, na * 0.8)), dpi=150)

    sns.heatmap(
        sim_matrix,
        ax=ax,
        annot=True,
        fmt=".2f",
        cmap=_CMAP,
        vmin=0.0,
        vmax=1.0,
        linewidths=0.5,
        linecolor="#cccccc",
        xticklabels=col_labels,
        yticklabels=row_labels,
        annot_kws={"size": 8},
        cbar_kws={"label": "Cosine Similarity", "shrink": 0.7},
    )

    ax.set_title(
        f"Chunk-Level Similarity: {doc_a_name}  vs  {doc_b_name}",
        fontsize=13,
        fontweight="bold",
        pad=14,
    )
    ax.set_xlabel(f"Chunks from {doc_b_name}", fontsize=10)
    ax.set_ylabel(f"Chunks from {doc_a_name}", fontsize=10)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha="right", fontsize=7)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=7)

    if theme_colors:
        fig.patch.set_facecolor(theme_colors.get("background", "#FFFFFF"))
        ax.set_facecolor(theme_colors.get("surface", "#F8FAFC"))
        ax.tick_params(colors=theme_colors.get("ink", "#0F172A"))
        ax.xaxis.label.set_color(theme_colors.get("ink", "#0F172A"))
        ax.yaxis.label.set_color(theme_colors.get("ink", "#0F172A"))
        ax.title.set_color(theme_colors.get("ink", "#0F172A"))

    fig.tight_layout()
    return fig