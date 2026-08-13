from __future__ import annotations

"""
analytics.py
-----------
Plotly visualizations for plagiarism analytics dashboard.
Supports dynamic light and dark mode theme switching (#1619).
"""

from collections.abc import Callable
from typing import Any, TypeVar

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

FigureT = TypeVar("FigureT")


def apply_plotly_theme(
    fig: go.Figure,
    theme_colors: dict[str, str] | None = None,
    show_grid: bool = True,
) -> go.Figure:
    """Apply matching light/dark theme colors (paper_bgcolor, plot_bgcolor, font_color) to a Plotly figure."""
    if not theme_colors or not isinstance(theme_colors, dict):
        return fig

    paper_bg = theme_colors.get("background", "white")
    plot_bg = theme_colors.get("surface", "white")
    font_color = theme_colors.get("ink", "#0f172a")
    grid_color = theme_colors.get("border", "#e2e8f0")

    fig.update_layout(
        paper_bgcolor=paper_bg,
        plot_bgcolor=plot_bg,
        font=dict(color=font_color),
    )
    if show_grid:
        fig.update_xaxes(gridcolor=grid_color)
        fig.update_yaxes(gridcolor=grid_color)

    return fig


def _create_boxplot_trace(name: str, scores: list[float], **kwargs: Any) -> go.Box:
    """Create a standardized Plotly Box trace with uniform styling."""
    return go.Box(
        y=scores,
        name=name,
        boxpoints="outliers",
        marker_color="#636efa",
        line_color="#4a4dba",
        hovertemplate="<b>%{name}</b><br>Similarity Score: %{y:.2f}<extra></extra>",
        **kwargs,
    )


def plot_similarity_boxplot_by_group(
    scores_dict: dict[str, list[float]],
    show_grid: bool = True,
    theme_colors: dict[str, str] | None = None,
) -> go.Figure:
    """Create a box plot of similarity score quartiles, grouped by assignment.

    Renders one box (25th/50th/75th percentile, whiskers, and outliers) per
    key in ``scores_dict`` so distributions can be compared across groups.

    Args:
        scores_dict: Mapping of assignment/group name to its list of
            similarity scores (0.0-1.0).
        show_grid: Whether to show chart gridlines.
        theme_colors: Optional theme palette for light/dark backgrounds.

    Returns:
        Plotly Figure object with one box trace per group.
    """
if not scores_dict:
        return _empty_chart(
            title="Similarity Score Quartile Distribution",
            message="No similarity scores available to plot",
            theme_colors=theme_colors,
            show_grid=show_grid,
            xaxis_title="Assignment",
            yaxis_title="Similarity Score",
        )
    fig = go.Figure()
    for group_name, scores in scores_dict.items():
        fig.add_trace(_create_boxplot_trace(name=str(group_name), scores=scores))

    fig.update_layout(
        title="Similarity Score Quartile Distribution",
        xaxis_title="Assignment",
        yaxis_title="Similarity Score",
        height=400,
        showlegend=False,
        autosize=True,
    )

    fig.update_xaxes(showgrid=show_grid)
    fig.update_yaxes(showgrid=show_grid, range=[0.0, 1.0])

    _apply_theme_colors(fig, theme_colors)

    return fig


def _apply_theme_colors(
    fig: go.Figure,
    theme_colors: dict[str, str] | None,
    theme_override: str | None = None,
) -> None:
    """Apply light/dark theme colors to a Plotly figure layout.

    Matches the ``theme_colors`` palette produced by ``app.theme.get_colors()``
    so charts render on dark backgrounds in Dark mode. When ``theme_colors``
    is ``None`` the default Plotly template is left untouched.

    Args:
        fig: Plotly figure to style.
        theme_colors: Optional dict with ``background``, ``surface``, ``ink``,
            ``muted`` and ``border`` color keys.
        theme_override: Optional explicit override ("light" or "dark") that
            forces the ``plotly_white``/``plotly_dark`` template, bypassing
            automatic theme detection.
    """
    if theme_override == "light":
        fig.update_layout(template="plotly_white")
    elif theme_override == "dark":
        fig.update_layout(template="plotly_dark")

    if not theme_colors:
        return


def calculate_severity_ratios(incidents: list[dict[str, Any]]) -> dict[str, float]:
    """Calculate the percentage breakdown of High, Medium, and Low severity incidents.

    Severity is derived from each incident's similarity score:
        High:   score >= 0.80 (80%)
        Medium: 0.50 <= score < 0.80 (50-79%)
        Low:    score < 0.50

    Incidents without a usable numeric score are ignored. Percentages are
    calculated against the count of incidents that had a usable score.

    Args:
        incidents: List of dicts, each expected to contain a
            'similarity_score' key (falls back to 'similarity').

    Returns:
        Dict with 'High', 'Medium', and 'Low' keys mapping to their
        percentage share (0.0-100.0), rounded to 2 decimal places.
        Returns all zeros if no usable scores are found.
    """
    counts = {"High": 0, "Medium": 0, "Low": 0}
    total = 0

    for incident in incidents:
        score = incident.get("similarity_score")
        if score is None:
            score = incident.get("similarity")
        try:
            score = float(score)
        except (TypeError, ValueError):
            continue

        total += 1
        if score >= 0.80:
            counts["High"] += 1
        elif score >= 0.50:
            counts["Medium"] += 1
        else:
            counts["Low"] += 1

    if total == 0:
        return {"High": 0.0, "Medium": 0.0, "Low": 0.0}

    return {label: round((count / total) * 100, 2) for label, count in counts.items()}


def _annotation_color(theme_colors: dict[str, str] | None) -> str:
    """Pick a readable annotation color for the given theme.

    Falls back to a neutral slate gray that is legible on both the default
    light Plotly background and the dark dashboard surface.
    """
    if theme_colors and isinstance(theme_colors, dict):
        return theme_colors.get("ink", "#64748b")
    return "#64748b"


def _empty_chart(
    title: str,
    message: str,
    theme_colors: dict[str, str] | None = None,
    show_grid: bool = True,
    height: int = 400,
    xaxis_title: str | None = None,
    yaxis_title: str | None = None,
) -> go.Figure:
    """Build a themed placeholder figure for an empty-state chart.

    Centralizes the boilerplate every chart function needs when there is
    no data to plot: an empty figure with a centered message annotation,
    the standard title/height layout, and consistent theme/gridline styling.

    Args:
        title: Chart title to display.
        message: Empty-state message shown as a centered annotation.
        theme_colors: Optional theme palette for light/dark backgrounds.
        show_grid: Whether to show chart gridlines.
        height: Plot height in pixels.
        xaxis_title: Optional x-axis label (omitted if not provided).
        yaxis_title: Optional y-axis label (omitted if not provided).

    Returns:
        A themed Plotly Figure with no data traces and an explanatory
        annotation.
    """
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, color=_annotation_color(theme_colors)),
    )

    layout_kwargs: dict[str, Any] = {"title": title, "height": height, "autosize": True}
    if xaxis_title is not None:
        layout_kwargs["xaxis_title"] = xaxis_title
    if yaxis_title is not None:
        layout_kwargs["yaxis_title"] = yaxis_title
    fig.update_layout(**layout_kwargs)

    fig.update_xaxes(showgrid=show_grid)
    fig.update_yaxes(showgrid=show_grid)

    return apply_plotly_theme(fig, theme_colors, show_grid=show_grid)

def build_visualization_lazily(
    enabled: bool,
    factory: Callable[[], FigureT],
) -> FigureT | None:
    """Build a visualization only after the user explicitly enables it.

    Streamlit evaluates the bodies of all tabs during a script rerun. Merely
    placing a chart inside a tab therefore does not defer expensive figure
    construction. This helper keeps the figure factory uncalled until the UI
    control for that visualization is enabled.

    Args:
        enabled: Whether the user requested the visualization.
        factory: Zero-argument callable that creates the figure.

    Returns:
        The created figure when enabled, otherwise ``None``.
    """
    if not enabled:
        return None

    return factory()


def get_top_similar_pairs(
    similarity_df: pd.DataFrame,
    top_n: int = 5,
) -> list[tuple[str, str, float]]:
    """Return the top-N highest similarity document pairs.

    Extracts only the upper triangle of the similarity matrix to avoid
    duplicate pairs and excludes self-similarity.

    Args:
        similarity_df: Square DataFrame containing pairwise similarity scores.
        top_n: Number of highest similarity pairs to return.

    Returns:
        List of tuples in the form: (document_a, document_b, similarity_score)
        sorted by similarity score in descending order.
    """
    if similarity_df.empty or similarity_df.shape[0] < 2:
        return []

    pairs: list[tuple[str, str, float]] = []
    doc_names = list(similarity_df.index)

    for i in range(len(doc_names)):
        for j in range(i + 1, len(doc_names)):
            score = float(similarity_df.iloc[i, j])
            pairs.append((doc_names[i], doc_names[j], score))

    pairs.sort(key=lambda pair: pair[2], reverse=True)
    return pairs[:top_n]


def plot_high_severity_trends(
    trend_data: list[dict[str, Any]],
    show_grid: bool = True,
    theme_colors: dict[str, str] | None = None,
    theme_override: str | None = None,
) -> go.Figure:
    """Create an interactive line chart showing High severity plagiarism incidents over time."""
if not trend_data:
        return _empty_chart(
            title="High Severity Plagiarism Trends (Last 30 Days)",
            message="No High severity incidents recorded in the specified period",
            theme_colors=theme_colors,
            show_grid=show_grid,
            xaxis_title="Date",
            yaxis_title="Number of High Severity Incidents",
        )
    df = pd.DataFrame(trend_data)
    df["date"] = pd.to_datetime(df["date"])
    df["cumulative"] = df["count"].cumsum()

    fig = px.line(
        df,
        x="date",
        y="count",
        title="High Severity Plagiarism Trends (Last 30 Days)",
        labels={"date": "Date", "count": "Number of High Severity Incidents"},
        markers=True,
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["cumulative"],
            mode="lines+markers",
            name="Cumulative Incidents",
            yaxis="y2",
        )
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Number of High Severity Incidents",
        yaxis2=dict(
            title="Cumulative Incidents",
            overlaying="y",
            side="right",
        ),
        hovermode="x unified",
        height=400,
        showlegend=True,
        autosize=True,
    )
    fig.update_xaxes(showgrid=show_grid)
    fig.update_yaxes(showgrid=show_grid)

    fig.update_traces(
        line=dict(color="#ff4b4b", width=3), marker=dict(size=8, color="#ff4b4b")
    )
    return apply_plotly_theme(fig, theme_colors, show_grid=show_grid)


def plot_most_plagiarized_documents(
    doc_data: list[dict[str, Any]],
    show_grid: bool = True,
    theme_colors: dict[str, str] | None = None,
    theme_override: str | None = None,
) -> go.Figure:
    """Create a bar chart showing the most frequently plagiarized documents."""
if not doc_data:
        return _empty_chart(
            title="Most Frequently Plagiarized Documents",
            message="No plagiarism incidents recorded",
            theme_colors=theme_colors,
            show_grid=show_grid,
            xaxis_title="Document Name",
            yaxis_title="Number of Incidents",
        )
    df = pd.DataFrame(doc_data)
    df["display_name"] = df["document_name"].apply(
        lambda x: x[:30] + "..." if len(x) > 30 else x
    )

    fig = px.bar(
        df,
        x="display_name",
        y="incident_count",
        title="Most Frequently Plagiarized Documents",
        labels={
            "display_name": "Document Name",
            "incident_count": "Number of Incidents",
        },
        orientation="v",
    )

    fig.update_layout(
        xaxis_title="Document Name",
        yaxis_title="Number of Incidents",
        height=400,
        showlegend=False,
        autosize=True,
    )
    fig.update_xaxes(showgrid=show_grid)
    fig.update_yaxes(showgrid=show_grid)

    fig.update_traces(
        marker_color="#ffa500",
        marker_line_color="#cc8400",
        marker_line_width=1.5,
    )

    full_names = df["document_name"].tolist()
    fig.update_traces(
        customdata=full_names,
        hovertemplate="<b>%{customdata}</b><br>Incidents: %{y}<extra></extra>",
    )
    return apply_plotly_theme(fig, theme_colors, show_grid=show_grid)


def plot_similarity_distribution(
    sim_matrix: pd.DataFrame,
    title: str = "Distribution of Similarity Scores",
    show_grid: bool = True,
    theme_colors: dict[str, str] | None = None,
) -> go.Figure:
    """Create a histogram showing the distribution of all pairwise similarity scores."""
if sim_matrix.empty or sim_matrix.shape[0] < 2:
        return _empty_chart(
            title=title,
            message="Not enough documents to compute a similarity distribution",
            theme_colors=theme_colors,
            show_grid=show_grid,
            xaxis_title="Similarity Score",
            yaxis_title="Number of Document Pairs",
        )
    mask = np.triu(np.ones(sim_matrix.shape, dtype=bool), k=1)
    scores = sim_matrix.where(mask).stack().values

    fig = px.histogram(
        scores,
        nbins=30,
        title=title,
        labels={
            "value": "Similarity Score",
            "count": "Number of Document Pairs",
        },
        range_x=[0.0, 1.0],
    )

    fig.update_layout(
        xaxis_title="Similarity Score",
        yaxis_title="Number of Document Pairs",
        bargap=0.05,
        height=400,
        showlegend=False,
        autosize=True,
    )
    fig.update_xaxes(showgrid=show_grid)
    fig.update_yaxes(showgrid=show_grid)

    fig.update_traces(
        marker_color="#636efa",
        marker_line_color="#4a4dba",
        marker_line_width=1,
        hovertemplate="Score: %{x:.2f}<br>Pairs: %{y}<extra></extra>",
    )
    return apply_plotly_theme(fig, theme_colors, show_grid=show_grid)


def plot_document_sizes(
    word_counts: dict[str, int],
    show_grid: bool = True,
    theme_colors: dict[str, str] | None = None,
) -> go.Figure:
    """Create a bar chart visualizing document word counts."""
if not word_counts:
        return _empty_chart(
            title="Document Word Counts",
            message="No documents currently in the database",
            theme_colors=theme_colors,
            show_grid=show_grid,
        )
    doc_names = list(word_counts.keys())
    counts = list(word_counts.values())

    display_names = [
        name[:30] + "..." if len(name) > 30 else name for name in doc_names
    ]

    fig = px.bar(
        x=display_names,
        y=counts,
        title="Document Word Counts",
        labels={"x": "Document Name", "y": "Word Count"},
    )

    fig.update_layout(
        xaxis_title="Document Name",
        yaxis_title="Word Count",
        height=400,
        showlegend=False,
        autosize=True,
    )
    fig.update_xaxes(showgrid=show_grid)
    fig.update_yaxes(showgrid=show_grid)

    fig.update_traces(
        marker_color="#00cc96",
        customdata=doc_names,
        hovertemplate="<b>%{customdata}</b><br>Words: %{y}<extra></extra>",
    )
    return apply_plotly_theme(fig, theme_colors, show_grid=show_grid)


def plot_similarity_boxplot(
    incidents: list[dict[str, Any]],
    show_grid: bool = True,
    theme_colors: dict[str, str] | None = None,
) -> go.Figure:
    """Create a box plot showing similarity score distributions per assignment."""
    rows: list[dict[str, Any]] = []
    for incident in incidents:
        title = incident.get("assignment_title") or incident.get("title")
        score = incident.get("similarity_score")
        if score is None:
            score = incident.get("similarity")
        if title is None or score is None:
            continue
        try:
            score = float(score)
        except (TypeError, ValueError):
            continue
        rows.append({"assignment_title": str(title), "similarity_score": score})

if not rows:
        return _empty_chart(
            title="Similarity Score Distribution by Assignment",
            message="No similarity scores recorded for the selected incidents",
            theme_colors=theme_colors,
            show_grid=show_grid,
            xaxis_title="Assignment Title",
            yaxis_title="Similarity Score",
        )
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(row["assignment_title"], []).append(row["similarity_score"])

    fig = go.Figure()
    for title, scores in grouped.items():
        fig.add_trace(_create_boxplot_trace(name=title, scores=scores))

    fig.update_layout(
        title="Similarity Score Distribution by Assignment",
        xaxis_title="Assignment Title",
        yaxis_title="Similarity Score",
        height=400,
        showlegend=False,
        autosize=True,
    )
    fig.update_xaxes(showgrid=show_grid)
    fig.update_yaxes(showgrid=show_grid, range=[0.0, 1.0])
    return apply_plotly_theme(fig, theme_colors, show_grid=show_grid)


def plot_severity_donut_chart(
    incidents: list[dict[str, Any]],
    theme_colors: dict[str, str] | None = None,
) -> go.Figure:
    """Create a donut chart showing the distribution of plagiarism incident severities."""
if not incidents:
        return _empty_chart(
            title="Plagiarism Incident Severity Distribution",
            message="No plagiarism incidents recorded",
            theme_colors=theme_colors,
            show_grid=False,
        )
    df = pd.DataFrame(incidents)
    if "severity" not in df.columns:
        df["severity"] = "Unknown"

    counts = df["severity"].value_counts().reset_index()
    counts.columns = ["severity", "count"]

    color_map = {
        "High": "#ef4444",
        "Medium": "#f59e0b",
        "Low": "#10b981",
    }
    colors = [color_map.get(sev, "#cccccc") for sev in counts["severity"]]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=counts["severity"],
                values=counts["count"],
                hole=0.4,
                marker=dict(colors=colors),
                textinfo="label+percent",
                hovertemplate="<b>Severity: %{label}</b><br>Incidents: %{value}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title="Plagiarism Incident Severity Distribution",
        height=400,
        showlegend=True,
        autosize=True,
    )
    return apply_plotly_theme(fig, theme_colors, show_grid=False)


def plot_similarity_histogram(
    scores: list[float],
    n_bins: int = 20,
    colorscale: str = "Viridis",
    theme_colors: dict[str, str] | None = None,
) -> go.Figure:
    """Create an interactive histogram of pairwise similarity scores with gradient coloring.

    Args:
        scores: List of similarity scores to plot.
        n_bins: Number of histogram bins.
        colorscale: Plotly colorscale for the bar gradient. Accessible options
            include "Viridis" (default), "Cividis", "Plasma", "Inferno", and
            "Turbo". "Cividis" is designed for colorblind accessibility.
        theme_colors: Optional theme color overrides.

    Returns:
        A Plotly figure with the similarity score histogram.
    """
if not scores:
        return _empty_chart(
            title="Similarity Score Distribution",
            message="No similarity scores available to plot",
            theme_colors=theme_colors,
            show_grid=False,
        )
    counts, bin_edges = np.histogram(scores, bins=n_bins, range=(0.0, 1.0))
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    fig = go.Figure(
        data=go.Bar(
            x=bin_centers,
            y=counts,
            marker=dict(
                color=counts,
                colorscale=colorscale,
                colorbar=dict(title="Pair Count"),
                line=dict(color="#4a4dba", width=1),
            ),
            hovertemplate="Score: %{x:.2f}<br>Pairs: %{y}<extra></extra>",
        )
    )

    fig.update_layout(
        title="Similarity Score Distribution",
        xaxis_title="Similarity Score",
        yaxis_title="Number of Document Pairs",
        bargap=0.05,
        height=400,
        showlegend=False,
        autosize=True,
    )
    return apply_plotly_theme(fig, theme_colors, show_grid=True)


def plot_similarity_percentiles(
    similarity_scores: list[float],
    show_grid: bool = True,
    theme_colors: dict[str, str] | None = None,
) -> go.Figure:
    """Create a horizontal bar chart of the similarity score percentile breakdown."""
    scores: list[float] = []
    for value in similarity_scores:
        try:
            scores.append(float(value))
        except (TypeError, ValueError):
            continue

if not scores:
        return _empty_chart(
            title="Similarity Score Percentile Breakdown",
            message="No similarity scores available to compute percentiles",
            theme_colors=theme_colors,
            show_grid=show_grid,
            xaxis_title="Similarity Score",
            yaxis_title="Percentile",
        )
    percentile_values = np.percentile(scores, [25, 50, 75, 90])
    percentile_labels = ["25th", "50th (Median)", "75th", "90th"]

    fig = px.bar(
        x=percentile_values,
        y=percentile_labels,
        orientation="h",
        title="Similarity Score Percentile Breakdown",
        labels={
            "x": "Similarity Score",
            "y": "Percentile",
        },
        range_x=[0.0, 1.0],
    )

    fig.update_layout(
        xaxis_title="Similarity Score",
        yaxis_title="Percentile",
        height=400,
        showlegend=False,
        autosize=True,
    )
    fig.update_xaxes(showgrid=show_grid)
    fig.update_yaxes(showgrid=show_grid)

    fig.update_traces(
        marker_color="#636efa",
        marker_line_color="#4a4dba",
        marker_line_width=1,
        hovertemplate="<b>%{y}</b><br>Similarity Score: %{x:.2f}<extra></extra>",
    )
    return apply_plotly_theme(fig, theme_colors, show_grid=show_grid)


def plot_hierarchical_dendrogram(
    similarity_matrix: pd.DataFrame,
    title: str = "Hierarchical Clustering Dendrogram",
    height: int = 500,
    theme_colors: dict[str, str] | None = None,
    show_grid: bool = True,
) -> go.Figure:
    """Create an interactive hierarchical clustering dendrogram.

    Builds the dendrogram from a square pairwise similarity DataFrame
    using Ward's linkage method on the distance matrix
    (``distance = 1 - similarity``). The resulting tree is rendered as an
    interactive Plotly figure with hover tooltips showing the documents
    joined at each merge.

    Ward's linkage minimizes within-cluster variance, producing compact
    clusters that correspond well to intuitively similar document groups.
    Using ``1 - similarity`` as the distance ensures that highly similar
    documents merge near the bottom of the tree and dissimilar documents
    merge near the top — exactly the grouping an instructor wants when
    scanning for clusters of suspiciously similar submissions.

    Args:
        similarity_matrix: Square DataFrame whose ``.index`` and
            ``.columns`` are identical document names and whose values
            are pairwise similarity scores in ``[0.0, 1.0]``. The matrix
            must be symmetric. Diagonal entries are ignored.
        title: Title displayed above the dendrogram.
        height: Plot height in pixels.
        theme_colors: Optional theme dict for light/dark mode alignment
            (see :func:`apply_plotly_theme`). When ``None``, Plotly
            defaults are used.
        show_grid: Whether to show the y-axis gridlines (merge-distance
            reference lines).

    Returns:
        A :class:`plotly.graph_objects.Figure` containing the dendrogram
        as a single ``Scatter`` trace in ``lines`` mode. The figure is
        ready to be rendered by ``st.plotly_chart`` or returned from an
        API endpoint. If the input is empty or has fewer than two
        documents, an empty figure with an explanatory annotation is
        returned instead of raising.
    """
    fig = go.Figure()

    # ── Validate input ───────────────────────────────────────────────
if similarity_matrix is None or similarity_matrix.empty:
        return _empty_chart(
            title=title,
            message="No similarity data available to build a dendrogram",
            theme_colors=theme_colors,
            show_grid=show_grid,
            height=height,
            xaxis_title="Document",
            yaxis_title="Merge Distance (1 − similarity)",
        )

    if similarity_matrix.shape[0] < 2:
        return _empty_chart(
            title=title,
            message="At least two documents are required to build a dendrogram",
            theme_colors=theme_colors,
            show_grid=show_grid,
            height=height,
            xaxis_title="Document",
            yaxis_title="Merge Distance (1 − similarity)",
        )
    # ── Build linkage matrix via Ward's method ──────────────────────
    # Lazy import keeps cold-start fast for users who never render this
    # chart, and keeps scipy out of the import graph of lighter modules
    # that re-export the analytics package.
    from scipy.cluster.hierarchy import linkage
    from scipy.spatial.distance import squareform

    doc_names = list(similarity_matrix.index)

    # Clamp similarities into [0, 1] defensively: some embedding pipelines
    # produce tiny negative cosines that should be treated as 0 similarity
    # (maximum distance) rather than as invalid input.
    sim_values = np.clip(similarity_matrix.to_numpy(dtype=float), 0.0, 1.0)

    # Distance = 1 − similarity.  Ward's method expects a condensed
    # distance vector (upper triangle, row-major).  ``squareform`` with
    # ``checks=False`` accepts a symmetric full matrix and returns the
    # condensed vector linkage() consumes.
    distance_matrix = 1.0 - sim_values
    # Zero out the diagonal to guarantee a valid condensed form even if
    # floating-point drift produced 1e-16 self-distances.
    np.fill_diagonal(distance_matrix, 0.0)

    condensed = squareform(distance_matrix, checks=False)
    linkage_matrix = linkage(condensed, method="ward")

    # ── Convert linkage matrix → dendrogram coordinates ──────────────
    # Each merge produces two child segments + one horizontal segment.
    # We plot them as a single Scatter trace in lines mode so the
    # tooltip can hover any segment and reveal which documents merged.
    xs: list[float] = []
    ys: list[float] = []
    hover_texts: list[str] = []

    n_leaves = len(doc_names)
    # Leaf x-position → index in doc_names.  Internal nodes are placed
    # at the midpoint of their two children.
    cluster_x: dict[int, float] = {
        leaf_idx: float(leaf_idx) for leaf_idx in range(n_leaves)
    }

    def _cluster_members(cluster_id: int) -> list[int]:
        """Return the leaf indices that belong to a cluster node iteratively."""
        members = []
        stack = [cluster_id]
        while stack:
            curr_id = stack.pop()
            if curr_id < n_leaves:
                members.append(int(curr_id))
            else:
                row = linkage_matrix[curr_id - n_leaves]
                stack.append(int(row[0]))
                stack.append(int(row[1]))
        return members

    for step, row in enumerate(linkage_matrix, start=1):
        left_id = int(row[0])
        right_id = int(row[1])
        merge_distance = float(row[2])
        new_id = n_leaves + step - 1

        left_x = cluster_x[left_id]
        right_x = cluster_x[right_id]

        # The merge-distance y-coordinate of each child is its own cluster
        # height.  Leaves have height 0.
        left_y = (
            float(linkage_matrix[left_id - n_leaves][2]) if left_id >= n_leaves else 0.0
        )
        right_y = (
            float(linkage_matrix[right_id - n_leaves][2])
            if right_id >= n_leaves
            else 0.0
        )

        # Two vertical drops + one horizontal bridge.  We interleave
        # ``None`` separators so Plotly draws disjoint line segments in a
        # single Scatter trace.
        # Left child: vertical from (left_x, left_y) → (left_x, merge_distance)
        xs.extend([left_x, left_x, right_x, right_x, None])
        ys.extend([left_y, merge_distance, merge_distance, right_y, None])

        # Build a descriptive hover tooltip for every point on this merge.
        left_members = _cluster_members(left_id)
        right_members = _cluster_members(right_id)
        left_names = ", ".join(doc_names[i] for i in left_members)
        right_names = ", ".join(doc_names[i] for i in right_members)
        tooltip = (
            f"<b>Merge #{step}</b><br>"
            f"Distance: {merge_distance:.3f} "
            f"(similarity: {1.0 - merge_distance:.3f})<br>"
            f"Cluster A ({len(left_members)}): {left_names}<br>"
            f"Cluster B ({len(right_members)}): {right_names}"
        )
        # The horizontal bridge is the meaningful segment for the
        # tooltip; the vertical drops reuse the same text so any hover
        # position is informative.
        hover_texts.extend([tooltip, tooltip, tooltip, tooltip, ""])

        cluster_x[new_id] = (left_x + right_x) / 2.0

    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines",
            line=dict(color="#636efa", width=2),
            hovertext=hover_texts,
            hoverinfo="text",
            showlegend=False,
        )
    )

    # ── Axis layout ─────────────────────────────────────────────────
    # Leaf x-tick labels show each document name; y-axis inverts so the
    # tree grows downward from highest distance (top) to leaves (bottom),
    # matching the canonical dendrogram orientation.
    fig.update_xaxes(
        tickmode="array",
        tickvals=list(range(n_leaves)),
        ticktext=doc_names,
        tickangle=-45,
    )
    fig.update_yaxes(
        title="Merge Distance (1 − similarity)",
        autorange="reversed",
        range=[1.0, 0.0],
    )

    fig.update_layout(
        title=title,
        xaxis_title="Document",
        height=height,
        autosize=True,
        showlegend=False,
        hovermode="closest",
        margin=dict(b=120, l=60, r=40, t=60),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=show_grid)

    return apply_plotly_theme(fig, theme_colors, show_grid=show_grid)


def plot_monthly_incident_trends(
    incidents: list[dict[str, Any]],
    show_grid: bool = True,
    theme_colors: dict[str, str] | None = None,
    months_to_show: int = 12,
) -> go.Figure:
    """Create a vertical bar chart showing monthly plagiarism incident trends.
    
    Aggregates incident counts by month (YYYY-MM format) to help instructors
    and administrators track semester-over-semester plagiarism patterns.
    This visualization is particularly useful for identifying seasonal spikes
    (e.g., during midterms or finals) and evaluating the effectiveness of
    academic integrity interventions over time.
    
    The chart displays the most recent ``months_to_show`` months, sorted
    chronologically from oldest to newest (left to right). Months with zero
    incidents are included in the timeline to maintain temporal continuity.
    
    Args:
        incidents: List of incident dictionaries. Each dict should contain a
                   ``date_flagged`` or ``timestamp`` key with an ISO 8601
                   datetime string or parseable date format.
        show_grid: Whether to display horizontal gridlines for easier
                   value estimation. Defaults to True.
        theme_colors: Optional theme palette dictionary for Light/Dark mode
                      synchronization. When None, Plotly defaults are used.
        months_to_show: Number of recent months to display on the x-axis.
                        Defaults to 12 (one full year). Must be >= 1.
                        
    Returns:
        A Plotly Figure object containing the monthly trend bar chart.
        If no valid incidents are provided, returns an empty-state chart
        with an explanatory annotation.
        
    Data Requirements:
        Each incident dictionary should ideally contain:
        - ``date_flagged`` or ``timestamp``: ISO 8601 datetime string
        - ``similarity_score``: Optional, used for severity coloring
        
    Examples:
        >>> incidents = [
        ...     {"date_flagged": "2024-01-15T10:00:00", "similarity_score": 0.85},
        ...     {"date_flagged": "2024-01-20T14:30:00", "similarity_score": 0.92},
        ...     {"date_flagged": "2024-02-05T09:15:00", "similarity_score": 0.75},
        ... ]
        >>> fig = plot_monthly_incident_trends(incidents, months_to_show=6)
        >>> # Returns a bar chart with Jan 2024 (2 incidents) and Feb 2024 (1 incident)
        
    Notes:
        - Months are formatted as "YYYY-MM" (e.g., "2024-01") for clarity
        - The y-axis always starts at 0 to prevent misleading visualizations
        - Bars are colored using the primary theme color with hover tooltips
          showing the exact month and incident count
    """
    # ── Validate and parse input data ─────────────────────────────────────────
    if not incidents or not isinstance(incidents, list):
        return _empty_chart(
            title="Monthly Plagiarism Incident Trends",
            message="No plagiarism incidents recorded to display trends",
            theme_colors=theme_colors,
            show_grid=show_grid,
            xaxis_title="Month (YYYY-MM)",
            yaxis_title="Number of Incidents",
        )

    # Parse dates and aggregate by month
    monthly_counts: dict[str, int] = {}
    valid_dates_found = False
    
    for incident in incidents:
        # Try multiple common date keys
        date_str = (
            incident.get("date_flagged") 
            or incident.get("timestamp") 
            or incident.get("created_at")
        )
        
        if not date_str:
            continue
            
        try:
            # Parse ISO 8601 or common datetime formats
            if isinstance(date_str, str):
                # Handle ISO format with timezone
                if "T" in date_str:
                    dt = pd.to_datetime(date_str, utc=True)
                else:
                    dt = pd.to_datetime(date_str)
            else:
                # Assume it's already a datetime-like object
                dt = pd.to_datetime(date_str)
                
            # Extract YYYY-MM format
            month_key = dt.strftime("%Y-%m")
            monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
            valid_dates_found = True
            
        except (ValueError, TypeError, pd.errors.ParserError) as exc:
            # Skip incidents with unparseable dates
            continue

    if not valid_dates_found or not monthly_counts:
        return _empty_chart(
            title="Monthly Plagiarism Incident Trends",
            message="No incidents with valid dates found in the dataset",
            theme_colors=theme_colors,
            show_grid=show_grid,
            xaxis_title="Month (YYYY-MM)",
            yaxis_title="Number of Incidents",
        )

    # ── Build complete timeline (fill missing months with 0) ──────────────────
    # Sort months chronologically
    sorted_months = sorted(monthly_counts.keys())
    
    # Determine the date range to display
    if len(sorted_months) > months_to_show:
        # Show only the most recent N months
        display_months = sorted_months[-months_to_show:]
    else:
        display_months = sorted_months
        
    # Fill in any missing months within the display range to maintain continuity
    # This prevents gaps in the timeline that could mislead viewers
    start_date = pd.to_datetime(display_months[0] + "-01")
    end_date = pd.to_datetime(display_months[-1] + "-01")
    
    # Generate complete month range
    complete_range = pd.date_range(start=start_date, end=end_date, freq="MS")
    
    # Build final data structure
    chart_data = []
    for dt in complete_range:
        month_key = dt.strftime("%Y-%m")
        count = monthly_counts.get(month_key, 0)
        chart_data.append({
            "month": month_key,
            "incident_count": count,
            "display_label": dt.strftime("%b %Y"),  # "Jan 2024" format for readability
        })

    # ── Create Plotly bar chart ───────────────────────────────────────────────
    df = pd.DataFrame(chart_data)
    
    # Determine bar color based on theme
    bar_color = "#636efa"  # Default Plotly blue
    if theme_colors and isinstance(theme_colors, dict):
        # Use primary color if available, otherwise fallback
        bar_color = theme_colors.get("primary", "#636efa")
    
    fig = px.bar(
        df,
        x="display_label",
        y="incident_count",
        title="Monthly Plagiarism Incident Trends",
        labels={
            "display_label": "Month",
            "incident_count": "Number of Incidents",
        },
        orientation="v",
    )

    # ── Customize layout and styling ─────────────────────────────────────────
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Number of Incidents",
        height=450,
        showlegend=False,
        autosize=True,
        bargap=0.2,  # Space between bars
        yaxis=dict(
            rangemode="tozero",  # Always start y-axis at 0
            dtick=1,  # Integer ticks only (can't have 1.5 incidents)
        ),
    )
    
    fig.update_xaxes(
        showgrid=show_grid,
        tickangle=-45,  # Angle labels for better readability
    )
    fig.update_yaxes(showgrid=show_grid)

    # Style the bars
    fig.update_traces(
        marker_color=bar_color,
        marker_line_color="#4a4dba",
        marker_line_width=1.5,
        customdata=df["month"],  # Store YYYY-MM for tooltip
        hovertemplate=(
            "<b>%{customdata}</b><br>"
            "Incidents: %{y}<br>"
            "<extra></extra>"
        ),
    )

    # Add value labels on top of bars for quick reading
    fig.update_traces(
        text=df["incident_count"],
        textposition="outside",
        textfont=dict(size=11),
    )

    # Apply theme colors for Light/Dark mode support
    return apply_plotly_theme(fig, theme_colors, show_grid=show_grid)
