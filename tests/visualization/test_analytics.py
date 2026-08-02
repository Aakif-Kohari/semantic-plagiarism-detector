"""
tests/visualization/test_analytics.py
-------------------------------------
Unit tests for plot_similarity_percentiles.
"""

import numpy as np
import plotly.graph_objects as go
import pytest

from src.visualization.analytics import plot_similarity_percentiles


def test_plot_similarity_percentiles_calculation():
    """Verify the 25th, 50th, 75th, and 90th percentiles are plotted correctly."""
    scores = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    fig = plot_similarity_percentiles(scores)

    expected = np.percentile(scores, [25, 50, 75, 90])
    assert list(fig.data[0].x) == pytest.approx(list(expected))
    assert list(fig.data[0].y) == ["25th", "50th (Median)", "75th", "90th"]


def test_plot_similarity_percentiles_returns_figure():
    """Test that the function returns a Plotly Figure."""
    fig = plot_similarity_percentiles([0.4, 0.6, 0.8])
    assert isinstance(fig, go.Figure)


def test_plot_similarity_percentiles_empty_scores():
    """Test that an empty score list returns an empty chart with a message."""
    fig = plot_similarity_percentiles([])

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0
    assert len(fig.layout.annotations) == 1


def test_plot_similarity_percentiles_skips_invalid_scores():
    """Test that non-numeric scores are ignored during percentile calculation."""
    scores = [0.2, "not-a-number", None, 0.8]
    fig = plot_similarity_percentiles(scores)

    expected = np.percentile([0.2, 0.8], [25, 50, 75, 90])
    assert list(fig.data[0].x) == pytest.approx(list(expected))
