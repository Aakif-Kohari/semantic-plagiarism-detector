"""
tests/visualization/test_network_graph.py
-------------------------------------------
Unit tests for plot_similarity_network edge cases.
"""

import time
from unittest.mock import patch

import networkx as nx
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.visualization.network_graph import (
    build_network_data,
    export_graph_to_gexf,
    export_network_to_gexf_bytes,
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


def test_plot_similarity_network_benchmark_200_nodes():
    """Verify rendering a 200-node graph completes in under 2.0 seconds."""
    np.random.seed(42)
    n = 200
    doc_names = [f"doc_{i}" for i in range(n)]

    matrix = np.random.uniform(0.1, 0.95, size=(n, n))
    matrix = (matrix + matrix.T) / 2.0
    np.fill_diagonal(matrix, 1.0)

    df = pd.DataFrame(matrix, index=doc_names, columns=doc_names)

    start_time = time.perf_counter()
    fig = plot_similarity_network(df, threshold=0.80)
    elapsed_time = time.perf_counter() - start_time

    assert isinstance(fig, go.Figure)
    assert (
        elapsed_time < 2.0
    ), f"Graph rendering took {elapsed_time:.3f}s, exceeding 2.0s benchmark."


def test_export_graph_to_gexf_produces_valid_xml():
    """Verify export_graph_to_gexf returns well-formed GEXF XML for a simple graph."""
    G = nx.Graph()
    G.add_node("doc1")
    G.add_node("doc2")
    G.add_edge("doc1", "doc2", similarity=0.85)

    gexf_str = export_graph_to_gexf(G)

    assert "<gexf" in gexf_str
    assert "</gexf>" in gexf_str
    assert "doc1" in gexf_str
    assert "doc2" in gexf_str
    assert 'similarity="0.85"' in gexf_str or "0.85" in gexf_str
    assert gexf_str.endswith(">")


def test_export_graph_to_gexf_empty_graph():
    """Verify export_graph_to_gexf handles an empty graph."""
    G = nx.Graph()
    gexf_str = export_graph_to_gexf(G)
    assert "<gexf" in gexf_str
    assert "</gexf>" in gexf_str


def test_export_graph_to_gexf_single_node():
    """Verify export_graph_to_gexf handles a graph with a single node and no edges."""
    G = nx.Graph()
    G.add_node("only_doc")
    gexf_str = export_graph_to_gexf(G)
    assert "<gexf" in gexf_str
    assert "only_doc" in gexf_str


def test_export_graph_to_gexf_multiple_edges():
    """Verify export_graph_to_gexf captures all edges with similarity attributes."""
    G = nx.Graph()
    G.add_node("doc1")
    G.add_node("doc2")
    G.add_node("doc3")
    G.add_edge("doc1", "doc2", similarity=0.85)
    G.add_edge("doc2", "doc3", similarity=0.92)

    gexf_str = export_graph_to_gexf(G)

    # Two edges should appear in the output (count closing edge tags)
    edge_count = gexf_str.count("</edge>")
    assert edge_count == 2, f"Expected 2 edges, found {edge_count}"


def test_export_network_to_gexf_bytes_returns_bytes():
    """Verify export_network_to_gexf_bytes returns non-empty bytes."""
    data = {
        "doc1": [1.0, 0.85, 0.20],
        "doc2": [0.85, 1.0, 0.10],
        "doc3": [0.20, 0.10, 1.0],
    }
    df = pd.DataFrame(data, index=["doc1", "doc2", "doc3"])

    result = export_network_to_gexf_bytes(df, threshold=0.75)

    assert isinstance(result, bytes)
    assert len(result) > 0


def test_export_network_to_gexf_bytes_contains_nodes_and_edges():
    """Verify GEXF output contains expected nodes and edge attributes from similarity matrix."""
    data = {
        "doc1": [1.0, 0.95],
        "doc2": [0.95, 1.0],
    }
    df = pd.DataFrame(data, index=["doc1", "doc2"])

    result = export_network_to_gexf_bytes(df, threshold=0.75)
    decoded = result.decode("utf-8")

    assert "doc1" in decoded
    assert "doc2" in decoded
    assert "<edge" in decoded
    assert "0.95" in decoded


def test_export_network_to_gexf_bytes_no_edges():
    """Verify GEXF output for a matrix with no pairs exceeding threshold."""
    data = {
        "doc1": [1.0, 0.10],
        "doc2": [0.10, 1.0],
    }
    df = pd.DataFrame(data, index=["doc1", "doc2"])

    result = export_network_to_gexf_bytes(df, threshold=0.75)
    decoded = result.decode("utf-8")

    assert "doc1" in decoded
    assert "doc2" in decoded
    assert "<edge " not in decoded and "</edge>" not in decoded


def test_export_network_to_gexf_bytes_empty_dataframe():
    """Verify GEXF export handles an empty DataFrame gracefully."""
    df = pd.DataFrame()
    result = export_network_to_gexf_bytes(df, threshold=0.75)
    assert isinstance(result, bytes)


def test_export_network_to_gexf_bytes_min_degree_filter():
    """Verify min_degree filtering is reflected in GEXF output."""
    data = {
        "doc1": [1.0, 0.85, 0.80],
        "doc2": [0.85, 1.0, 0.10],
        "doc3": [0.80, 0.10, 1.0],
    }
    df = pd.DataFrame(data, index=["doc1", "doc2", "doc3"])

    # doc1 has degree 2, doc2 and doc3 have degree 1
    result = export_network_to_gexf_bytes(df, threshold=0.75, min_degree=2)
    decoded = result.decode("utf-8")

    assert "doc1" in decoded
    assert "doc2" not in decoded
    assert "doc3" not in decoded

