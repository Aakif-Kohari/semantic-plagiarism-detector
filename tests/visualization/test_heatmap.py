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


def test_plot_similarity_heatmap_no_annotation(single_doc_df):
    """Heatmap should not overlay numeric scores when annotate=False."""
    fig = plot_similarity_heatmap(single_doc_df, title="No Annotation Heatmap", annotate=False)
    assert hasattr(fig, "axes")
    main_ax = next(ax for ax in fig.axes if ax.get_title() == "No Annotation Heatmap")
    # Verify that the text annotations are empty
    assert len(main_ax.texts) == 0


def test_plot_similarity_heatmap_plotly_no_annotation(single_doc_df):
    """Plotly heatmap should not contain annotations when annotate=False."""
    fig = plot_similarity_heatmap_plotly(single_doc_df, title="No Annotation Plotly Heatmap", annotate=False)
    assert hasattr(fig, "layout")
    # In Plotly, annotations are stored in layout.annotations
    assert len(fig.layout.annotations) == 0


def test_plot_similarity_heatmap_with_mask_threshold():
    """Heatmap should mask cells below the mask_threshold."""
    df = pd.DataFrame(
        [[1.0, 0.4], [0.4, 1.0]],
        columns=["doc1", "doc2"],
        index=["doc1", "doc2"]
    )
    fig = plot_similarity_heatmap(df, title="Masked Heatmap", mask_threshold=0.5)
    assert hasattr(fig, "axes")
    main_ax = next(ax for ax in fig.axes if ax.get_title() == "Masked Heatmap")
    texts = [t.get_text() for t in main_ax.texts if t.get_text()]
    assert "1.00" in texts
    assert "0.40" not in texts


def test_plot_similarity_heatmap_plotly_with_mask_threshold():
    """Plotly heatmap should mask cells below the mask_threshold in z_matrix."""
    df = pd.DataFrame(
        [[1.0, 0.4], [0.4, 1.0]],
        columns=["doc1", "doc2"],
        index=["doc1", "doc2"]
    )
    fig = plot_similarity_heatmap_plotly(df, title="Masked Plotly", mask_threshold=0.5)
    assert hasattr(fig, "layout")
    heatmap = next(trace for trace in fig.data if trace.type == "heatmap")
    z_values = heatmap.z
    assert z_values[0][1] is None
    assert z_values[1][0] is None
    assert z_values[0][0] == 1.0
    assert z_values[1][1] == 1.0


def test_filter_heatmap_by_class_tag_matches_subset():
    """filter_heatmap_by_class_tag should filter matrix rows and columns to matching documents."""
    from src.visualization.heatmap import filter_heatmap_by_class_tag

    df = pd.DataFrame(
        [
            [1.0, 0.8, 0.2],
            [0.8, 1.0, 0.3],
            [0.2, 0.3, 1.0],
        ],
        columns=["doc1.pdf", "doc2.pdf", "doc3.pdf"],
        index=["doc1.pdf", "doc2.pdf", "doc3.pdf"],
    )
    doc_class_map = {
        "doc1.pdf": "Class A",
        "doc2.pdf": "Class A",
        "doc3.pdf": "Class B",
    }

    filtered_df = filter_heatmap_by_class_tag(
        df, class_tag="Class A", doc_class_map=doc_class_map
    )

    assert list(filtered_df.columns) == ["doc1.pdf", "doc2.pdf"]
    assert list(filtered_df.index) == ["doc1.pdf", "doc2.pdf"]
    assert filtered_df.shape == (2, 2)


def test_filter_heatmap_by_class_tag_all_classes_returns_full():
    """class_tag='All Classes' or None should return the complete matrix without filtering."""
    from src.visualization.heatmap import filter_heatmap_by_class_tag

    df = pd.DataFrame(
        [[1.0, 0.5], [0.5, 1.0]],
        columns=["doc1.pdf", "doc2.pdf"],
        index=["doc1.pdf", "doc2.pdf"],
    )

    full_all = filter_heatmap_by_class_tag(df, class_tag="All Classes")
    full_none = filter_heatmap_by_class_tag(df, class_tag=None)

    assert full_all.shape == (2, 2)
    assert full_none.shape == (2, 2)


def test_filter_heatmap_by_class_tag_no_match_returns_empty():
    """Non-existent class tag should return an empty DataFrame."""
    from src.visualization.heatmap import filter_heatmap_by_class_tag

    df = pd.DataFrame(
        [[1.0, 0.5], [0.5, 1.0]],
        columns=["doc1.pdf", "doc2.pdf"],
        index=["doc1.pdf", "doc2.pdf"],
    )
    doc_class_map = {"doc1.pdf": "Class A", "doc2.pdf": "Class A"}

    empty_filtered = filter_heatmap_by_class_tag(
        df, class_tag="Class Nonexistent", doc_class_map=doc_class_map
    )

    assert empty_filtered.empty


def test_plot_similarity_heatmap_with_class_tag_filter():
    """Static heatmap should apply class_tag filter when passed."""
    df = pd.DataFrame(
        [
            [1.0, 0.8, 0.2],
            [0.8, 1.0, 0.3],
            [0.2, 0.3, 1.0],
        ],
        columns=["doc1.pdf", "doc2.pdf", "doc3.pdf"],
        index=["doc1.pdf", "doc2.pdf", "doc3.pdf"],
    )
    doc_class_map = {
        "doc1.pdf": "Class A",
        "doc2.pdf": "Class A",
        "doc3.pdf": "Class B",
    }

    fig = plot_similarity_heatmap(
        df,
        title="Class A Heatmap",
        class_tag="Class A",
        doc_class_map=doc_class_map,
    )
    assert hasattr(fig, "axes")


def test_plot_similarity_heatmap_plotly_with_class_tag_filter():
    """Plotly heatmap should apply class_tag filter and render subset."""
    df = pd.DataFrame(
        [
            [1.0, 0.8, 0.2],
            [0.8, 1.0, 0.3],
            [0.2, 0.3, 1.0],
        ],
        columns=["doc1.pdf", "doc2.pdf", "doc3.pdf"],
        index=["doc1.pdf", "doc2.pdf", "doc3.pdf"],
    )
    doc_class_map = {
        "doc1.pdf": "Class A",
        "doc2.pdf": "Class A",
        "doc3.pdf": "Class B",
    }

    fig = plot_similarity_heatmap_plotly(
        df,
        title="Plotly Class A Heatmap",
        class_tag="Class A",
        doc_class_map=doc_class_map,
    )
    assert hasattr(fig, "layout")
    heatmap = next(trace for trace in fig.data if trace.type == "heatmap")
    assert list(heatmap.x) == ["doc1.pdf", "doc2.pdf"]



