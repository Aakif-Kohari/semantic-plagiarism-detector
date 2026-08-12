from pathlib import Path

SOURCE = Path("src/visualization/network_graph.py")
TESTS = Path("tests/visualization/test_network_graph.py")


def test_plot_api_has_required_default():
    source = SOURCE.read_text(encoding="utf-8")
    section = source[source.index("def plot_plagiarism_network_graph(") :]
    signature = section[: section.index(") -> go.Figure:")]
    assert "max_nodes: int = 50" in signature


def test_degree_filter_and_hidden_caption_are_implemented():
    source = SOURCE.read_text(encoding="utf-8")
    assert "-G.degree(node)" in source
    assert "hidden_node_count" in source
    assert "fig.add_annotation(" in source


def test_required_regression_tests_exist():
    tests = TESTS.read_text(encoding="utf-8")
    assert "test_build_network_data_keeps_top_highest_degree_nodes" in tests
    assert "test_render_network_plotly_displays_hidden_node_caption" in tests
