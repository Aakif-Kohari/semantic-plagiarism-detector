"""
tests/visualization/test_analytics.py
-------------------------------------
Unit tests for plot_similarity_boxplot.
"""

import plotly.graph_objects as go

from src.visualization.analytics import plot_similarity_boxplot


def test_plot_similarity_boxplot_returns_figure():
    """Test that the function returns a Plotly Figure."""
    incidents = [{"assignment_title": "Essay", "similarity_score": 0.8}]
    fig = plot_similarity_boxplot(incidents)
    assert isinstance(fig, go.Figure)


def test_plot_similarity_boxplot_groups_by_assignment_title():
    """Test that one box trace is created per assignment title."""
    incidents = [
        {"assignment_title": "Essay 1", "similarity_score": 0.8},
        {"assignment_title": "Essay 1", "similarity_score": 0.6},
        {"assignment_title": "Essay 2", "similarity_score": 0.3},
    ]
    fig = plot_similarity_boxplot(incidents)

    assert len(fig.data) == 2

    trace_by_name = {trace.name: list(trace.y) for trace in fig.data}
    assert trace_by_name["Essay 1"] == [0.8, 0.6]
    assert trace_by_name["Essay 2"] == [0.3]


def test_plot_similarity_boxplot_empty_incidents():
    """Test that an empty incident list returns an empty chart with a message."""
    fig = plot_similarity_boxplot([])

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0
    assert len(fig.layout.annotations) == 1


def test_plot_similarity_boxplot_skips_missing_scores():
    """Test that incidents without a similarity score are skipped."""
    incidents = [
        {"assignment_title": "Essay 1", "similarity_score": 0.7},
        {"assignment_title": "Essay 1"},
        {"assignment_title": "Essay 1", "similarity_score": None},
        {"assignment_title": "Essay 1", "similarity_score": "not-a-number"},
    ]
    fig = plot_similarity_boxplot(incidents)

    assert len(fig.data) == 1
    assert list(fig.data[0].y) == [0.7]


def test_plot_similarity_boxplot_fallback_keys():
    """Test that 'title' and 'similarity' fallback keys are honoured."""
    incidents = [
        {"title": "Essay 1", "similarity": 0.9},
        {"title": "Essay 1", "similarity_score": 0.5},
    ]
    fig = plot_similarity_boxplot(incidents)

    assert len(fig.data) == 1
    assert list(fig.data[0].y) == [0.9, 0.5]
