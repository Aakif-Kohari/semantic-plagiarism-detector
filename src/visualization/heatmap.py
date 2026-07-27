"""
heatmap.py
----------
Generates similarity heatmaps for Semantic Plagiarism Detector.

This module provides high-quality, customizable heatmap visualizations for 
document similarity matrices. It bridges the gap between backend scoring 
and frontend rendering, offering both static (Matplotlib/Seaborn) and 
interactive (Plotly) options. 

Recent additions (Issue #697):
- Streamlit UI components (`render_heatmap_ui`) to inject interactive controls.
- Dynamic colormap selection (Viridis, Plasma, Coolwarm, YlOrRd) accessible to end-users.
- Enhanced matrix validation and error handling for robust UI behavior.
- Support for both light and dark modes inherited from the application theme system.

Exports:
    - plot_similarity_heatmap: Matplotlib/Seaborn (high-res PNG download)
    - plot_similarity_heatmap_plotly: Plotly (interactive hover values)
    - plot_chunk_similarity_comparison: Matplotlib chunk-level heatmap
    - render_heatmap_ui: Streamlit component rendering the heatmap with interactive controls
"""

from contextlib import contextmanager
from typing import Generator, Optional
import logging

import matplotlib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
from matplotlib.figure import Figure
from matplotlib.ticker import PercentFormatter

# Enforce non-interactive backend for standard plot generation to prevent thread-safety 
# issues in web environments like Streamlit.
matplotlib.use("Agg")

try:
    from src.core.similarity import PLAGIARISM_THRESHOLD
except ImportError:
    # Fallback for standalone testing or isolated environments
    PLAGIARISM_THRESHOLD = 0.75

# ── Logger Configuration ───────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ── Colormap Mappings & Constants ──────────────────────────────────────────────
# Colormap options/mappings now live in app/theme.py (Issue #633).

try:
    from app.theme import (
        UI_COLORMAP_OPTIONS,
        MATPLOTLIB_CMAP_MAPPING,
        PLOTLY_CMAP_MAPPING,
        DEFAULT_UI_COLORMAP,
    )
except ImportError:
    # Fallback for standalone testing or isolated environments
    UI_COLORMAP_OPTIONS = ["Viridis", "Plasma", "Coolwarm", "YlOrRd"]
    MATPLOTLIB_CMAP_MAPPING = {"Viridis": "viridis"}
    PLOTLY_CMAP_MAPPING = {"Viridis": "Viridis"}
    DEFAULT_UI_COLORMAP = "Viridis"

# ── Data Validation Helpers ────────────────────────────────────────────────────

def validate_similarity_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validates and cleans the input similarity matrix before visualization.
    
    Ensures that:
    1. The matrix is square.
    2. Values are strictly bounded between 0.0 and 1.0.
    3. Null values are appropriately filled.
    
    Args:
        df (pd.DataFrame): The raw similarity matrix.
        
    Returns:
        pd.DataFrame: A cleaned, safe-to-plot DataFrame.
        
    Raises:
        ValueError: If the dataframe cannot be coerced into a valid square matrix.
    """
    # 1. Check if DataFrame is empty
    if df.empty:
        logger.warning("Empty DataFrame provided to heatmap generator.")
        return df

    # 2. Verify square dimensions
    rows, cols = df.shape
    if rows != cols:
        logger.error(f"Similarity matrix must be square. Received {rows}x{cols}.")
        raise ValueError("Similarity matrix is not square.")

    # 3. Create a safe copy to avoid mutating the original data
    clean_df = df.copy()

    # 4. Handle missing values (NaNs) by assuming 0 similarity for unknown pairs
    if clean_df.isnull().values.any():
        logger.info("NaN values detected in similarity matrix. Filling with 0.0.")
        clean_df.fillna(0.0, inplace=True)

    # 5. Bound constraints (Cosine similarity should be [-1, 1], but in this context 
    # we represent it as [0, 1]. We clamp values to prevent colormap overflow).
    clean_df = clean_df.clip(lower=0.0, upper=1.0)

    # 6. Ensure the diagonal is exactly 1.0 (self-similarity)
    np.fill_diagonal(clean_df.values, 1.0)

    return clean_df


def _get_theme_color(theme_colors: Optional[dict], key: str, fallback: str) -> str:
    """
    Safely retrieves a color from a theme dictionary with a fallback.
    
    Args:
        theme_colors (Optional[dict]): The theme dictionary injected from the app.
        key (str): The specific color key to lookup (e.g., 'background', 'ink').
        fallback (str): The hex code to use if the key or dictionary is missing.
        
    Returns:
        str: A valid hex color code.
    """
    if not theme_colors:
        return fallback
    return theme_colors.get(key, fallback)


# ── Static Visualization (Matplotlib/Seaborn) ──────────────────────────────────

@contextmanager
def matplotlib_figure(*args, **kwargs) -> Generator[tuple, None, None]:
    """Context manager that yields (fig, ax) and guarantees plt.close(fig)."""
    fig, ax = plt.subplots(*args, **kwargs)
    try:
        yield fig, ax
    finally:
        plt.close(fig)


def plot_similarity_heatmap(
    similarity_df: pd.DataFrame,
    title: str = "Semantic Similarity Matrix",
    threshold: float = PLAGIARISM_THRESHOLD,
    figsize: Optional[tuple] = None,
    annotate: bool = True,
    dpi: int = 150,
    theme_colors: Optional[dict] = None,
    colormap_name: str = DEFAULT_UI_COLORMAP,
) -> Figure:
    """
    High-resolution Matplotlib heatmap optimized for static PNG export.

    This function generates a highly detailed, publication-ready heatmap. It 
    highlights potentially plagiarized document pairs by analyzing the intersection
    of their similarity scores against the defined threshold.

    Args:
        similarity_df (pd.DataFrame): Square N×N DataFrame of cosine similarity scores.
        title (str): Plot title displayed at the top.
        threshold (float): Scores >= this threshold receive a distinctive red border.
        figsize (Optional[tuple]): (width, height) in inches; auto-calculated if None.
        annotate (bool): Whether to explicitly overlay numeric scores on the cells.
        dpi (int): Resolution for the figure export (default 150 -> high-res).
        theme_colors (Optional[dict]): Optional dictionary for dark/light mode injection.
        colormap_name (str): UI string for the desired colormap (e.g., "Viridis").

    Returns:
        Figure: A rendered Matplotlib Figure object.
    """
    # Map the UI friendly name to the specific Matplotlib colormap string
    cmap = MATPLOTLIB_CMAP_MAPPING.get(colormap_name, "viridis")
    
    # Process and validate the incoming data
    try:
        clean_df = validate_similarity_matrix(similarity_df)
    except ValueError as ve:
        logger.error(f"Validation failed: {ve}")
        clean_df = similarity_df  # Attempt to proceed anyway or return empty
        
    n = len(clean_df)

    # 1. Guard clause for empty datasets
    if n == 0:
        with matplotlib_figure() as (fig, ax):
            ax.set_title(title)
            return fig

    # 2. Dynamic aspect ratio and figure sizing based on document count
    if figsize is None:
        cell_size = max(1.2, 6 / n)
        width = max(6.0, n * cell_size + 2.0)
        height = max(5.0, n * cell_size + 1.5)
        figsize = (width, height)

    with matplotlib_figure(figsize=figsize, dpi=dpi) as (fig, ax):
        sns.heatmap(
            clean_df,
            ax=ax,
            annot=annotate,
            fmt=".2f" if annotate else "",
            cmap=cmap,
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

        data = clean_df.values

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


# ── Interactive Visualization (Plotly) ─────────────────────────────────────────

def plot_similarity_heatmap_plotly(
    similarity_df: pd.DataFrame,
    title: str = "Semantic Similarity Matrix",
    threshold: float = PLAGIARISM_THRESHOLD,
    theme_colors: Optional[dict] = None,
    colormap_name: str = DEFAULT_UI_COLORMAP,
):
    """
    Interactive Plotly heatmap featuring dynamic hover values and custom threshold bounds.

    This function utilizes plotly.graph_objects to create a rich, web-native 
    interactive chart. It includes custom hovering templates that clearly state 
    the documents being compared and overlays shapes for threshold violations.

    Args:
        similarity_df (pd.DataFrame): Square N×N DataFrame of cosine similarity scores.
        title (str): Chart title.
        threshold (float): Similarity score threshold for drawing red alert boxes.
        theme_colors (Optional[dict]): Theme dict for mapping dark/light modes.
        colormap_name (str): UI string representing the requested colormap.

    Returns:
        plotly.graph_objects.Figure: A Plotly figure ready for `st.plotly_chart()`.
    """
    import plotly.graph_objects as go

    # 1. Map the chosen UI string to Plotly's internal colorscale naming convention
    cmap = PLOTLY_CMAP_MAPPING.get(colormap_name, "Viridis")

    # 2. Guard for empty DataFrame (0 documents)
    if similarity_df.empty or len(similarity_df) == 0:
        fig = go.Figure()
        fig.update_layout(title=title)
        fig.add_annotation(text="No data available to plot.", showarrow=False, font=dict(size=14))
        return fig
        
    try:
        clean_df = validate_similarity_matrix(similarity_df)
    except ValueError as error:
        logger.error(error)
        return go.Figure()

    names = list(clean_df.columns)
    z_matrix = clean_df.values.tolist()
    n = len(names)

    # 3. Construct a highly readable, rich HTML hover text matrix
    # Plotly expects a 2D array of strings corresponding to the Z values.
    hover_text = [
        [
            f"<b>{names[i]}</b> vs <b>{names[j]}</b><br>"
            f"Similarity: {clean_df.values[i, j]:.2%}<br>"
            f"Status: {'Flagged' if (i != j and clean_df.values[i, j] >= threshold) else 'Normal'}"
            for j in range(n)
        ]
        for i in range(n)
    ]

    # 4. Initialize the Heatmap trace
    fig = go.Figure(
        data=go.Heatmap(
            z=z_matrix,
            x=names,
            y=names,
            text=hover_text,
            hovertemplate="%{text}<extra></extra>",
            colorscale=cmap,
            zmin=0.0,
            zmax=1.0,
            colorbar=dict(
                title="Cosine Similarity", 
                thickness=15,
                tickformat=".0%"
            ),
            xgap=2, # Creates a grid-like separation between cells
            ygap=2,
        )
    )

    # 5. Programmatically annotate each cell with its numeric score
    # We alter the text color based on the cell's background intensity to maintain contrast.
    annotations = []
    for i in range(n):
        for j in range(n):
            val = clean_df.values[i, j]
            # Simple heuristic for text color based on general colormap luminance 
            # In production with specific maps, this might need tuning.
            font_color = "black" if (0.3 < val < 0.8 and cmap not in ["Viridis", "Plasma"]) else "white"
            
            # For lighter maps like YlOrRd, darker text is generally better at lower values
            if cmap == "YlOrRd" and val < 0.6:
                font_color = "black"
                
            annotations.append(
                dict(
                    x=names[j],
                    y=names[i],
                    text=f"{val:.2f}",
                    showarrow=False,
                    font=dict(
                        size=max(9, 14 - n),
                        color=font_color,
                        family="Arial, sans-serif",
                    ),
                )
            )

    # 6. Overlay distinctive red bounding boxes for flagged document pairs
    shapes = []
    for i in range(n):
        for j in range(n):
            if i != j and clean_df.values[i, j] >= threshold:
                shapes.append(
                    dict(
                        type="rect",
                        x0=j - 0.5,
                        x1=j + 0.5,
                        y0=i - 0.5,
                        y1=i + 0.5,
                        line=dict(color="#d62728", width=3),
                        fillcolor="rgba(0,0,0,0)" # Transparent fill
                    )
                )

    # 7. Apply dynamic responsive dimensions and layout theme
    cell_px = max(80, 600 // n)
    bg_color = _get_theme_color(theme_colors, "background", "rgba(0,0,0,0)") # Default to transparent for native integration
    ink_color = _get_theme_color(theme_colors, "ink", "#0F172A")

    fig.update_layout(
    title=dict(
        text=title,
        font=dict(
            size=18,
            family="Arial, sans-serif",
            color=ink_color
        )
    ),

    height=max(500, n * cell_px + 150),

    autosize=True,

    xaxis=dict(
        side="bottom",
        tickangle=-30,
        title="Document ID",
        color=ink_color,
        fixedrange=False,   # Enable zoom on x-axis
    ),

    yaxis=dict(
        autorange="reversed",
        title="Document ID",
        color=ink_color,
        fixedrange=False,   # Enable zoom on y-axis
    ),

    annotations=annotations,

    shapes=shapes,

    margin=dict(
        l=140,
        r=60,
        t=70,
        b=140
    ),

    paper_bgcolor=bg_color,

    plot_bgcolor=bg_color,

    font=dict(
        color=ink_color
    ),

    hoverlabel=dict(
        bgcolor=_get_theme_color(
            theme_colors,
            "surface",
            "white"
        ),
        font_size=14,
        font_family="Arial"
    )
)

    return fig


# ── Granular Analysis (Chunk-Level Heatmap) ────────────────────────────────────

def plot_chunk_similarity_comparison(
    doc_a_name: str,
    doc_b_name: str,
    chunks_a: list,
    chunks_b: list,
    sim_matrix: np.ndarray,
    theme_colors: Optional[dict] = None,
    colormap_name: str = DEFAULT_UI_COLORMAP,
) -> Figure:
    """
    Renders a granular, chunk-level similarity heatmap between two specific documents.
    
    This function is critical for deep-dive analysis, allowing users to pinpoint 
    exactly which paragraphs or sentences within two documents triggered a 
    plagiarism alert.

    Args:
        doc_a_name (str): Identifier for the primary document.
        doc_b_name (str): Identifier for the comparative document.
        chunks_a (list): List of text chunks (strings) from Document A.
        chunks_b (list): List of text chunks (strings) from Document B.
        sim_matrix (np.ndarray): 2D numpy array of shape (len(chunks_a), len(chunks_b)).
        theme_colors (Optional[dict]): UI Theme dictionary.
        colormap_name (str): UI colormap selection.

    Returns:
        Figure: A rendered Matplotlib Figure for the chunk comparison.
    """
    cmap = MATPLOTLIB_CMAP_MAPPING.get(colormap_name, "viridis")
    
    # Ensure matrix bounds
    sim_matrix = np.clip(sim_matrix, 0.0, 1.0)
    na, nb = sim_matrix.shape

    # Helper function to truncate chunk text for axis labels
    def short_label(text, max_chars=40):
        # Clean newlines and extra spaces for cleaner labels
        clean_text = " ".join(str(text).split())
        return clean_text[:max_chars].strip() + "…" if len(clean_text) > max_chars else clean_text

    # Generate axis labels mapping to the text chunks
    row_labels = [f"A{i + 1}: {short_label(c)}" for i, c in enumerate(chunks_a)]
    col_labels = [f"B{j + 1}: {short_label(c)}" for j, c in enumerate(chunks_b)]

    with matplotlib_figure(figsize=(max(8, nb * 1.5), max(6, na * 0.8)), dpi=150) as (fig, ax):
        sns.heatmap(
            sim_matrix,
            ax=ax,
            annot=True,
            fmt=".2f",
            cmap=cmap,
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
def render_heatmap_ui(
    similarity_df,
    threshold=PLAGIARISM_THRESHOLD,
    theme_colors=None,
):
    """
    Streamlit UI wrapper for similarity heatmap controls.

    Provides:
    - Fit Matrix view
    - High Similarity Focus view
    - Reset View
    - Dynamic colormap selection
    """

    if similarity_df.empty:
        st.warning("No similarity data available.")
        return

    clean_df = validate_similarity_matrix(similarity_df)

    if clean_df.empty:
        st.warning("Validated similarity matrix is empty.")
        return

    # Heatmap view controls
    zoom_mode = st.radio(
        "Heatmap View",
        [
            "Fit Matrix",
            "High Similarity Focus",
            "Reset View",
        ],
        horizontal=True,
        key="heatmap_zoom_mode",
    )

    # Colormap selector
    default_index = (
        UI_COLORMAP_OPTIONS.index(DEFAULT_UI_COLORMAP)
        if DEFAULT_UI_COLORMAP in UI_COLORMAP_OPTIONS
        else 0
    )

    colormap_name = st.selectbox(
        "Color Map",
        UI_COLORMAP_OPTIONS,
        index=default_index,
        key="heatmap_colormap",
    )

    n = len(clean_df)

    # Create plot with selected colormap
    fig = plot_similarity_heatmap_plotly(
        clean_df,
        threshold=threshold,
        theme_colors=theme_colors,
        colormap_name=colormap_name,
    )

    # Apply zoom modes
    if zoom_mode == "Fit Matrix":

        fig.update_xaxes(
            range=[-0.5, n - 0.5]
        )

        fig.update_yaxes(
            range=[n - 0.5, -0.5]
        )

    elif zoom_mode == "High Similarity Focus":

        matrix = clean_df.values

        coords = np.where(
            matrix >= threshold
        )

        if len(coords[0]) > 0:

            min_x = max(min(coords[1]) - 1, -0.5)
            max_x = min(max(coords[1]) + 1, n - 0.5)

            min_y = max(min(coords[0]) - 1, -0.5)
            max_y = min(max(coords[0]) + 1, n - 0.5)

            fig.update_xaxes(
                range=[
                    min_x,
                    max_x,
                ]
            )

            fig.update_yaxes(
                range=[
                    max_y,
                    min_y,
                ]
            )

        else:
            st.info(
                "No document pairs found above the similarity threshold."
            )

    elif zoom_mode == "Reset View":

        fig.update_xaxes(
            autorange=True
        )

        fig.update_yaxes(
            autorange=True
        )

    st.plotly_chart(
        fig,
        use_container_width=True
    )