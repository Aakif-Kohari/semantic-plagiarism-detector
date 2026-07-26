import pandas as pd
import pytest
from src.visualization.heatmap import plot_similarity_heatmap, plot_similarity_heatmap_plotly

@pytest.fixture
def empty_df():
    """Return an empty DataFrame with no rows and columns."""
    return pd.DataFrame()

@pytest.fixture
def single_doc_df():
    """Return a 1x1 similarity matrix for a single document."""
    return pd.DataFrame([[1.0]], columns=["doc1"], index=["doc1"])

def test_plot_similarity_heatmap_empty(empty_df):
    """Heatmap should handle empty DataFrame without raising errors."""
    fig = plot_similarity_heatmap(empty_df)
    assert fig is not None
    # The figure should have at least one Axes object
    assert hasattr(fig, "axes")

def test_plot_similarity_heatmap_single(single_doc_df):
    """Heatmap should correctly render a 1x1 similarity matrix."""
    fig = plot_similarity_heatmap(single_doc_df)
    assert fig is not None
    ax = fig.axes[0]
    # A heatmap creates at least one collection (QuadMesh)
    assert any(hasattr(col, "get_array") for col in ax.collections)

def test_plot_similarity_heatmap_plotly_empty(empty_df):
    """Plotly heatmap should handle empty DataFrame gracefully."""
    fig = plot_similarity_heatmap_plotly(empty_df)
    assert fig is not None
    # Plotly Figure should have the title set
    assert fig.layout.title.text == "Semantic Similarity Matrix"

def test_plot_similarity_heatmap_plotly_single(single_doc_df):
    """Plotly heatmap should correctly render a 1x1 similarity matrix."""
    fig = plot_similarity_heatmap_plotly(single_doc_df)
    assert fig is not None
    # Verify that heatmap data exists
    assert len(fig.data) == 1
    # Check that the values are as expected (handle tuple or list)
    heatmap = fig.data[0]
    # Convert to list of lists for comparison
    z_values = [list(row) for row in heatmap.z]
    assert z_values == [[1.0]]
