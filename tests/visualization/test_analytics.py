import pytest
import plotly.graph_objects as go
from src.visualization.analytics import plot_severity_donut_chart

def test_plot_severity_donut_chart_returns_figure():
    incidents = [{"severity": "High"}, {"severity": "Medium"}]
    fig = plot_severity_donut_chart(incidents)
    assert isinstance(fig, go.Figure)

def test_plot_severity_donut_chart_counts_correct():
    incidents = [
        {"severity": "High"},
        {"severity": "High"},
        {"severity": "Medium"},
        {"severity": "Low"},
        {"severity": "Low"},
        {"severity": "Low"}
    ]
    fig = plot_severity_donut_chart(incidents)
    
    # Extract the pie trace
    pie_trace = fig.data[0]
    labels = list(pie_trace.labels)
    values = list(pie_trace.values)
    
    assert "High" in labels
    assert values[labels.index("High")] == 2
    
    assert "Medium" in labels
    assert values[labels.index("Medium")] == 1
    
    assert "Low" in labels
    assert values[labels.index("Low")] == 3

def test_plot_severity_donut_chart_donut_hole():
    incidents = [{"severity": "High"}]
    fig = plot_severity_donut_chart(incidents)
    pie_trace = fig.data[0]
    assert pie_trace.hole == 0.4

def test_plot_severity_donut_chart_colors():
    incidents = [
        {"severity": "High"},
        {"severity": "Medium"},
        {"severity": "Low"}
    ]
    fig = plot_severity_donut_chart(incidents)
    pie_trace = fig.data[0]
    labels = list(pie_trace.labels)
    colors = pie_trace.marker.colors
    
    expected_colors = {
        "High": "#ef4444",
        "Medium": "#f59e0b",
        "Low": "#10b981"
    }
    
    for i, label in enumerate(labels):
        assert colors[i] == expected_colors[label]

def test_plot_severity_donut_chart_empty_input():
    # Empty input shouldn't crash
    fig = plot_severity_donut_chart([])
    assert isinstance(fig, go.Figure)
    # Check if there's an annotation for empty data
    assert len(fig.layout.annotations) == 1
    assert fig.layout.annotations[0].text == "No plagiarism incidents recorded"
