"""
tests/visualization/test_calibration_curve.py
---------------------------------------------
Unit tests for the precision/recall calibration curve helper added for
the automated threshold calibration & backtest harness (Issue #2267).
"""

from __future__ import annotations

import plotly.graph_objects as go
import pytest

from src.core.calibration import evaluate_thresholds
from src.visualization.analytics import plot_precision_recall_curve


def _sample_sweep():
    return evaluate_thresholds(
        [0.2, 0.5, 0.6, 0.9],
        [0, 0, 1, 1],
        [0.1, 0.3, 0.5, 0.7, 0.9],
    )


def test_plot_precision_recall_curve_returns_figure():
    fig = plot_precision_recall_curve(_sample_sweep())

    assert isinstance(fig, go.Figure)
    trace_names = {trace.name for trace in fig.data}
    assert {"Precision", "Recall", "F1"} <= trace_names


def test_plot_precision_recall_curve_current_threshold_vline():
    fig = plot_precision_recall_curve(_sample_sweep(), current_threshold=0.59)

    assert tuple(fig.layout.xaxis.range) == (0.0, 1.0)
    assert tuple(fig.layout.yaxis.range) == (0.0, 1.0)
    # A vline is stored as a shape annotation in the layout.
    shapes = fig.layout.shapes
    assert len(shapes) == 1
    assert shapes[0].type == "line"
    assert shapes[0].x0 == 0.59


def test_plot_precision_recall_curve_empty():
    fig = plot_precision_recall_curve([])

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_plot_precision_recall_curve_theme_colors():
    theme = {
        "background": "#1e293b",
        "surface": "#0f172a",
        "ink": "#f8fafc",
        "muted": "#94a3b8",
        "border": "#334155",
    }
    fig = plot_precision_recall_curve(_sample_sweep(), theme_colors=theme)

    assert fig.layout.paper_bgcolor == theme["background"]
    assert fig.layout.plot_bgcolor == theme["surface"]
    assert fig.layout.font.color == theme["ink"]
