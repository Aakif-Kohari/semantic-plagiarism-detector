import pandas as pd
import pytest
from src.visualization.heatmap import (
    plot_similarity_heatmap,
    plot_similarity_heatmap_plotly,
)

@pytest.fixture
def empty_df():
    """Return an empty DataFrame with no rows and columns."""
    return pd.DataFrame()

@pytest.fixture
def single_doc_df():
    """Return a 1x1 similarity matrix for a single document."""
    return pd.DataFrame([[1.0]], columns=["doc1"], index=["doc1"])

def test_plot_similarity_heatmap_empty(empty_df):
    """Heatmap should handle an empty DataFrame gracefully."""
    fig = plot_similarity_heatmap(empty_df, title="Empty Heatmap")
    # Figure should be created and contain a single Axes
    assert hasattr(fig, "axes")
    assert len(fig.axes) == 1
    ax = fig.axes[0]
    # Title should be set to the provided title
    assert ax.get_title() == "Empty Heatmap"
    # No patches should be added for an empty matrix
    assert not ax.patches

def test_plot_similarity_heatmap_single(single_doc_df):
    """Heatmap should correctly render a 1x1 similarity matrix."""
    fig = plot_similarity_heatmap(single_doc_df, title="Single Document Heatmap")
    assert hasattr(fig, "axes")
    # Figure should have at least two axes: main plot and colorbar
    assert len(fig.axes) >= 2
    # Identify main axis (the one with our title)
    main_ax = next(ax for ax in fig.axes if ax.get_title() == "Single Document Heatmap")
    # Title should match
    assert main_ax.get_title() == "Single Document Heatmap"
    # A diagonal patch (border) should be present on main axis
    assert any(main_ax.patches), "Diagonal patch missing for single document heatmap"

def test_plot_similarity_heatmap_plotly_empty(empty_df):
    """Plotly heatmap should handle an empty DataFrame without errors."""
    fig = plot_similarity_heatmap_plotly(empty_df, title="Empty Plotly Heatmap")
    assert hasattr(fig, "layout")
    # Verify title is set correctly
    assert fig.layout.title.text == "Empty Plotly Heatmap"
    # No data traces should be present for empty input
    assert len(fig.data) == 0

def test_plot_similarity_heatmap_plotly_single(single_doc_df):
    """Plotly heatmap should correctly render a 1x1 similarity matrix."""
    fig = plot_similarity_heatmap_plotly(single_doc_df, title="Single Plotly Heatmap")
    assert hasattr(fig, "layout")
    assert fig.layout.title.text == "Single Plotly Heatmap"
    # Expect a single heatmap trace
    assert any(trace.type == "heatmap" for trace in fig.data)
    # Verify the data values match the input matrix
    heatmap = next(trace for trace in fig.data if trace.type == "heatmap")
    z_values = [list(row) for row in heatmap.z]
    assert z_values == [[1.0]]
