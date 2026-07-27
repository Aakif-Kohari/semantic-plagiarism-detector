"""
tests/visualization/test_network_graph.py
-------------------------------------------
Unit tests for plot_similarity_network edge cases.
"""

from unittest.mock import patch

import pandas as pd
import plotly.graph_objects as go

from src.visualization.network_graph import (
    build_network_data,
    plot_similarity_network,
    render_network_plotly,
)


def test_build_network_data_structure():
    """Verify build_network_data returns expected keys, NetworkX graph, and Plotly traces."""
    data = {
        "doc1": [1.0, 0.85, 0.20],
        "doc2": [0.85, 1.0, 0.10],
        "doc3": [0.20, 0.10, 1.0],
    }
    df = pd.DataFrame(data, index=["doc1", "doc2", "doc3"])

    net_data = build_network_data(df, threshold=0.75)

    assert "shapes" in net_data
    assert "edge_hover_trace" in net_data
    assert "node_trace" in net_data
    assert "graph" in net_data
    assert "pos" in net_data

    # Check graph nodes and edges
    assert len(net_data["graph"].nodes()) == 3
    assert len(net_data["graph"].edges()) == 1
    assert len(net_data["shapes"]) == 1


def test_build_network_data_with_theme_colors():
    """Verify build_network_data applies custom theme colors correctly."""
    data = {
        "doc1": [1.0, 0.95],
        "doc2": [0.95, 1.0],
    }
    df = pd.DataFrame(data, index=["doc1", "doc2"])
    custom_theme = {
        "danger": "#e53935",
        "warning": "#fb8c00",
        "success": "#43a047",
        "background": "#121212",
        "ink": "#ffffff",
    }

    net_data = build_network_data(df, threshold=0.75, theme_colors=custom_theme)

    # Similarity 0.95 >= 0.90 -> danger color
    assert net_data["shapes"][0]["line"]["color"] == "#e53935"
    assert net_data["node_trace"].textfont.color == "#ffffff"


def test_render_network_plotly_construction():
    """Verify render_network_plotly constructs a valid Plotly Figure from network data."""
    data = {
        "doc1": [1.0, 0.85],
        "doc2": [0.85, 1.0],
    }
    df = pd.DataFrame(data, index=["doc1", "doc2"])
    custom_theme = {
        "background": "#f0f0f0",
        "ink": "#111111",
    }

    net_data = build_network_data(df, threshold=0.75, theme_colors=custom_theme)
    fig = render_network_plotly(
        net_data, title="Custom Title", theme_colors=custom_theme
    )

    assert isinstance(fig, go.Figure)
    assert fig.layout.title.text == "Custom Title"
    assert fig.layout.paper_bgcolor == "#f0f0f0"
    assert fig.layout.plot_bgcolor == "#f0f0f0"
    assert len(fig.layout.shapes) == 1


def test_plot_similarity_network_returns_plotly_figure():

    # Setup simple square similarity matrix
    data = {
        "doc1": [1.0, 0.85, 0.20],
        "doc2": [0.85, 1.0, 0.10],
        "doc3": [0.20, 0.10, 1.0],
    }
    df = pd.DataFrame(data, index=["doc1", "doc2", "doc3"])

    fig = plot_similarity_network(df, threshold=0.75)

    assert isinstance(fig, go.Figure)
    # Check that there are traces in the graph
    assert len(fig.data) == 2  # edge_hover_trace, node_trace

    # Check that layout has shapes representing the edges
    # doc1 and doc2 are connected (0.85 >= 0.75), so 1 line shape should exist
    assert len(fig.layout.shapes) == 1
    assert fig.layout.shapes[0]["type"] == "line"


def test_plot_similarity_network_no_edges():
    # Setup matrix where no similarities exceed the threshold
    data = {
        "doc1": [1.0, 0.10, 0.20],
        "doc2": [0.10, 1.0, 0.15],
        "doc3": [0.20, 0.15, 1.0],
    }
    df = pd.DataFrame(data, index=["doc1", "doc2", "doc3"])

    fig = plot_similarity_network(df, threshold=0.75)

    assert isinstance(fig, go.Figure)
    # No shapes/lines should be added
    assert len(fig.layout.shapes) == 0


def test_plot_similarity_network_single_document():
    """Test graph generation when only one document is provided (1x1 matrix)."""
    data = {"doc1": [1.0]}
    df = pd.DataFrame(data, index=["doc1"])

    fig = plot_similarity_network(df, threshold=0.75)

    assert isinstance(fig, go.Figure)
    # No edges should be created for a single document
    assert len(fig.layout.shapes) == 0


def test_plot_similarity_network_empty_dataframe():
    """Test graph generation when an empty DataFrame is passed."""
    df = pd.DataFrame()

    fig = plot_similarity_network(df, threshold=0.75)

    assert isinstance(fig, go.Figure)
    assert len(fig.layout.shapes) == 0


@patch("src.visualization.network_graph.go.Figure")
def test_plot_similarity_network_mocked_plotly(mock_figure):
    """Mock Plotly figure generation to verify execution without errors."""
    data = {
        "doc1": [1.0, 0.90],
        "doc2": [0.90, 1.0],
    }
    df = pd.DataFrame(data, index=["doc1", "doc2"])

    plot_similarity_network(df, threshold=0.75)

    # Verify that the Figure constructor was invoked properly
    assert mock_figure.called


def test_plot_similarity_network_layout_autosize():
    """Verify layout has autosize=True and width=None for dynamic scaling."""
    data = {
        "doc1": [1.0, 0.90],
        "doc2": [0.90, 1.0],
    }
    df = pd.DataFrame(data, index=["doc1", "doc2"])

    fig = plot_similarity_network(df, threshold=0.75)

    assert fig.layout.autosize is True
    assert fig.layout.width is None


def test_build_network_data_colors_by_document_tags():
    """Verify nodes are colored by discrete class tags when document_tags is provided."""
    data = {
        "doc1": [1.0, 0.85, 0.20],
        "doc2": [0.85, 1.0, 0.10],
        "doc3": [0.20, 0.10, 1.0],
    }
    df = pd.DataFrame(data, index=["doc1", "doc2", "doc3"])
    document_tags = {
        "doc1": "#class_A,#hw1",
        "doc2": "#class_A",
        "doc3": "#class_B",
    }

    net_data = build_network_data(df, threshold=0.75, document_tags=document_tags)

    tag_color_map = net_data["tag_color_map"]
    assert "#class_a" in tag_color_map
    assert "#class_b" in tag_color_map
    assert tag_color_map["#class_a"] != tag_color_map["#class_b"]

    node_colors = net_data["node_trace"].marker.color
    assert node_colors[0] == tag_color_map["#class_a"]
    assert node_colors[1] == tag_color_map["#class_a"]
    assert node_colors[2] == tag_color_map["#class_b"]

    # Verify hover text contains tag info
    hover_texts = net_data["node_trace"].hovertext
    assert "<b>🏷️ Tag:</b> #class_a" in hover_texts[0]
    assert "<b>🏷️ Tag:</b> #class_b" in hover_texts[2]


def test_plot_similarity_network_with_doc_tags_alias():
    """Verify plot_similarity_network accepts doc_tags alias and colors nodes accordingly."""
    data = {
        "doc1": [1.0, 0.90],
        "doc2": [0.90, 1.0],
    }
    df = pd.DataFrame(data, index=["doc1", "doc2"])

    fig = plot_similarity_network(
        df,
        threshold=0.75,
        doc_tags={"doc1": ["#class_X"], "doc2": ["#class_Y"]},
    )

    node_trace = fig.data[1]  # node_trace is the second trace after edge_hover_trace
    node_colors = node_trace.marker.color
    assert len(node_colors) == 2
    assert node_colors[0] != node_colors[1]
    assert "<b>🏷️ Tag:</b> #class_x" in node_trace.hovertext[0]
    assert "<b>🏷️ Tag:</b> #class_y" in node_trace.hovertext[1]


def test_build_network_data_untagged_fallback():
    """Verify untagged nodes fallback to degree-based colors when partial tags exist."""
    data = {
        "doc1": [1.0, 0.10],
        "doc2": [0.10, 1.0],
    }
    df = pd.DataFrame(data, index=["doc1", "doc2"])

    # doc1 is tagged with #class_A, doc2 is untagged (degree 0)
    net_data = build_network_data(df, threshold=0.75, document_tags={"doc1": "#class_A"})

    node_colors = net_data["node_trace"].marker.color
    tag_color_map = net_data["tag_color_map"]

    assert node_colors[0] == tag_color_map["#class_a"]
    assert node_colors[1] == "#2e7d32"  # degree 0 success fallback color

