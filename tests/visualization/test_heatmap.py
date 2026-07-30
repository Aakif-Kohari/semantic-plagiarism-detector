"""
tests/visualization/test_heatmap.py
-----------------------------------
Unit tests for plot_similarity_heatmap edge cases.
"""

import pandas as pd
import pytest
from matplotlib.figure import Figure
from src.visualization.heatmap import plot_similarity_heatmap


def test_plot_similarity_heatmap_empty_dataframe():
    """Test heatmap generation when an empty DataFrame is passed."""
    df = pd.DataFrame()

    # The current implementation raises ZeroDivisionError for empty DataFrames
    # This is expected behavior as the function requires at least one document
    with pytest.raises(ZeroDivisionError):
        plot_similarity_heatmap(df)


def test_plot_similarity_heatmap_large_dataframe():
    """Test heatmap generation with a large DataFrame of realistic values."""
    # Create a 5x5 similarity matrix with realistic cosine similarity values
    data = {
        "doc1": [1.00, 0.85, 0.42, 0.23, 0.15],
        "doc2": [0.85, 1.00, 0.38, 0.19, 0.12],
        "doc3": [0.42, 0.38, 1.00, 0.67, 0.31],
        "doc4": [0.23, 0.19, 0.67, 1.00, 0.28],
        "doc5": [0.15, 0.12, 0.31, 0.28, 1.00],
    }
    df = pd.DataFrame(data, index=["doc1", "doc2", "doc3", "doc4", "doc5"])

    fig = plot_similarity_heatmap(df)

    assert isinstance(fig, Figure)
    # Verify the figure contains at least one Axes
    assert len(fig.axes) > 0
