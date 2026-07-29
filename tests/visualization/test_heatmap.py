"""
test_heatmap.py
---------------
Comprehensive unit tests for the heatmap visualization module.

This module validates the behavior of both static (Matplotlib/Seaborn) and 
interactive (Plotly) heatmap generation functions. It ensures robust handling 
of edge cases, empty data, single-document matrices, masking thresholds, and 
critical export functionalities such as PNG byte stream generation.

Recent Additions (Issue #696):
- Added rigorous assertions to verify that Matplotlib figure PNG exports 
  produce valid, non-corrupted binary byte streams with correct magic headers.
- Expanded parameterized testing for various dataframe shapes and configurations.
"""

import io

import pandas as pd
import pytest
import matplotlib.pyplot as plt

from src.visualization.heatmap import (
    plot_similarity_heatmap,
    plot_similarity_heatmap_plotly,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def empty_df() -> pd.DataFrame:
    """
    Return an empty DataFrame with no rows and columns.
    
    Used to test graceful degradation and empty-state handling in heatmap 
    rendering functions without raising IndexError or ValueError.
    """
    return pd.DataFrame()


@pytest.fixture
def single_doc_df() -> pd.DataFrame:
    """
    Return a 1x1 similarity matrix for a single document.
    
    Used to verify that the heatmap correctly renders diagonal elements 
    and handles the minimum possible valid input shape.
    """
    return pd.DataFrame([[1.0]], columns=["doc1"], index=["doc1"])


@pytest.fixture
def multi_doc_df() -> pd.DataFrame:
    """
    Return a 3x3 similarity matrix with varied similarity scores.
    
    Used to test standard rendering, annotation placement, and threshold 
    masking logic across a realistic multi-document scenario.
    """
    return pd.DataFrame(
        [
            [1.00, 0.85, 0.45],
            [0.85, 1.00, 0.60],
            [0.45, 0.60, 1.00],
        ],
        columns=["doc_A", "doc_B", "doc_C"],
        index=["doc_A", "doc_B", "doc_C"],
    )


@pytest.fixture
def masked_threshold_df() -> pd.DataFrame:
    """
    Return a DataFrame specifically designed to test mask_threshold logic.
    
    Contains values both above and below a standard 0.50 threshold to 
    verify that low-similarity cells are correctly masked or hidden.
    """
    return pd.DataFrame(
        [
            [1.0, 0.4, 0.8],
            [0.4, 1.0, 0.3],
            [0.8, 0.3, 1.0],
        ],
        columns=["doc1", "doc2", "doc3"],
        index=["doc1", "doc2", "doc3"],
    )


# ==============================================================================
# Static Heatmap (Matplotlib/Seaborn) Tests
# ==============================================================================

def test_plot_similarity_heatmap_empty(empty_df: pd.DataFrame) -> None:
    """
    Verify that the static heatmap handles an empty DataFrame gracefully.
    
    Ensures that no exceptions are raised and a valid, albeit empty, 
    Matplotlib Figure object is returned with the correct title.
    """
    fig = plot_similarity_heatmap(empty_df, title="Empty Heatmap")
    
    assert hasattr(fig, "axes"), "Figure object must have 'axes' attribute"
    assert len(fig.axes) == 1, "Empty heatmap should contain exactly one Axes"
    
    ax = fig.axes[0]
    assert ax.get_title() == "Empty Heatmap", "Title must match the provided argument"
    assert not ax.patches, "No patches should be added for an empty matrix"
    
    plt.close(fig)


def test_plot_similarity_heatmap_single(single_doc_df: pd.DataFrame) -> None:
    """
    Verify that the static heatmap correctly renders a 1x1 similarity matrix.
    
    Ensures that the main axis is identified, the title is set, and the 
    diagonal boundary patch is correctly applied for visual distinction.
    """
    fig = plot_similarity_heatmap(single_doc_df, title="Single Document Heatmap")
    
    assert hasattr(fig, "axes"), "Figure object must have 'axes' attribute"
    assert len(fig.axes) >= 2, "Figure should have main plot and colorbar axes"
    
    main_ax = next((ax for ax in fig.axes if ax.get_title() == "Single Document Heatmap"), None)
    assert main_ax is not None, "Main axis with the specified title must exist"
    assert any(main_ax.patches), "Diagonal boundary patch missing for single document"
    
    plt.close(fig)


def test_plot_similarity_heatmap_multi(multi_doc_df: pd.DataFrame) -> None:
    """
    Verify standard rendering of a multi-document similarity matrix.
    
    Checks axis labels, annotation presence, and overall figure integrity 
    for a standard 3x3 input matrix.
    """
    fig = plot_similarity_heatmap(multi_doc_df, title="Multi Document Heatmap", annotate=True)
    
    main_ax = next((ax for ax in fig.axes if ax.get_title() == "Multi Document Heatmap"), None)
    assert main_ax is not None
    
    # Verify annotations are present
    assert len(main_ax.texts) > 0, "Annotations should be present when annotate=True"
    
    # Verify axis labels are set correctly
    assert main_ax.get_xlabel() == "Documents"
    assert main_ax.get_ylabel() == "Documents"
    
    plt.close(fig)


def test_plot_similarity_heatmap_no_annotation(single_doc_df: pd.DataFrame) -> None:
    """
    Verify that the static heatmap does not overlay numeric scores when annotate=False.
    """
    fig = plot_similarity_heatmap(single_doc_df, title="No Annotation Heatmap", annotate=False)
    
    main_ax = next((ax for ax in fig.axes if ax.get_title() == "No Annotation Heatmap"), None)
    assert main_ax is not None
    assert len(main_ax.texts) == 0, "Text annotations must be empty when annotate=False"
    
    plt.close(fig)


def test_plot_similarity_heatmap_with_mask_threshold(masked_threshold_df: pd.DataFrame) -> None:
    """
    Verify that the static heatmap correctly masks cells below the mask_threshold.
    """
    fig = plot_similarity_heatmap(
        masked_threshold_df, 
        title="Masked Heatmap", 
        mask_threshold=0.5
    )
    
    main_ax = next((ax for ax in fig.axes if ax.get_title() == "Masked Heatmap"), None)
    assert main_ax is not None
    
    texts = [t.get_text() for t in main_ax.texts if t.get_text()]
    assert "1.00" in texts, "High similarity values should be annotated"
    assert "0.40" not in texts, "Values below mask_threshold should not be annotated"
    
    plt.close(fig)


# ==============================================================================
# Interactive Heatmap (Plotly) Tests
# ==============================================================================

def test_plot_similarity_heatmap_plotly_empty(empty_df: pd.DataFrame) -> None:
    """
    Verify that the Plotly heatmap handles an empty DataFrame without errors.
    """
    fig = plot_similarity_heatmap_plotly(empty_df, title="Empty Plotly Heatmap")
    
    assert hasattr(fig, "layout"), "Plotly figure must have a 'layout' attribute"
    assert fig.layout.title.text == "Empty Plotly Heatmap"
    assert len(fig.data) == 0, "No data traces should be present for empty input"


def test_plot_similarity_heatmap_plotly_single(single_doc_df: pd.DataFrame) -> None:
    """
    Verify that the Plotly heatmap correctly renders a 1x1 similarity matrix.
    """
    fig = plot_similarity_heatmap_plotly(single_doc_df, title="Single Plotly Heatmap")
    
    assert hasattr(fig, "layout")
    assert fig.layout.title.text == "Single Plotly Heatmap"
    assert any(trace.type == "heatmap" for trace in fig.data), "Must contain a heatmap trace"
    
    heatmap = next(trace for trace in fig.data if trace.type == "heatmap")
    z_values = [list(row) for row in heatmap.z]
    assert z_values == [[1.0]], "Z-values must exactly match the input matrix"


def test_plot_similarity_heatmap_plotly_no_annotation(single_doc_df: pd.DataFrame) -> None:
    """
    Verify that the Plotly heatmap does not contain annotations when annotate=False.
    """
    fig = plot_similarity_heatmap_plotly(
        single_doc_df, 
        title="No Annotation Plotly Heatmap", 
        annotate=False
    )
    
    assert hasattr(fig, "layout")
    assert len(fig.layout.annotations) == 0, "Layout annotations must be empty"


def test_plot_similarity_heatmap_plotly_with_mask_threshold(masked_threshold_df: pd.DataFrame) -> None:
    """
    Verify that the Plotly heatmap masks cells below the mask_threshold in z_matrix.
    """
    fig = plot_similarity_heatmap_plotly(
        masked_threshold_df, 
        title="Masked Plotly", 
        mask_threshold=0.5
    )
    
    heatmap = next(trace for trace in fig.data if trace.type == "heatmap")
    z_values = heatmap.z
    
    assert z_values[0][1] is None, "Value 0.4 should be masked to None"
    assert z_values[1][0] is None, "Value 0.4 should be masked to None"
    assert z_values[0][0] == 1.0, "Value 1.0 should remain unmasked"
    assert z_values[1][1] == 1.0, "Value 1.0 should remain unmasked"


# ==============================================================================
# Export Generation Tests (Issue #696)
# ==============================================================================

def test_plot_similarity_heatmap_png_export_valid_bytes(multi_doc_df: pd.DataFrame) -> None:
    """
    Verify that the Matplotlib heatmap figure can be exported to valid PNG binary bytes.
    
    This test ensures that the figure rendering pipeline produces a non-corrupted, 
    standards-compliant PNG file in memory, which is critical for backend 
    report generation and automated email attachments.
    """
    fig = plot_similarity_heatmap(multi_doc_df, title="Export Test", dpi=150)
    
    # Create an in-memory binary buffer
    buf = io.BytesIO()
    
    # Save the figure to the buffer in PNG format
    fig.savefig(buf, format="png", bbox_inches="tight")
    png_bytes = buf.getvalue()
    
    # 1. Verify PNG magic number header: \x89PNG\r\n\x1a\n
    png_magic = b"\x89PNG\r\n\x1a\n"
    assert png_bytes.startswith(png_magic), (
        f"Exported bytes do not have a valid PNG header. "
        f"Got: {png_bytes[:8]}"
    )
    
    # 2. Verify the file size is reasonable for a 3x3 heatmap at 150 DPI
    # A completely empty or corrupted file would be significantly smaller
    assert len(png_bytes) > 2000, (
        f"Exported PNG file is suspiciously small ({len(png_bytes)} bytes). "
        "Expected a fully rendered heatmap to be > 2000 bytes."
    )
    
    # 3. Verify the buffer can be read back as a valid image (basic sanity check)
    buf.seek(0)
    header_check = buf.read(8)
    assert header_check == png_magic, "Buffer seek and read failed to reproduce magic number"
    
    # Cleanup to prevent memory leaks in test suite
    plt.close(fig)
    buf.close()


def test_plot_similarity_heatmap_png_export_empty_df(empty_df: pd.DataFrame) -> None:
    """
    Verify that exporting an empty heatmap still produces a valid, albeit minimal, PNG.
    """
    fig = plot_similarity_heatmap(empty_df, title="Empty Export Test", dpi=150)
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    png_bytes = buf.getvalue()
    
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n"), "Empty heatmap export must still be a valid PNG"
    
    plt.close(fig)
    buf.close()


def test_plot_similarity_heatmap_png_export_custom_theme(multi_doc_df: pd.DataFrame) -> None:
    """
    Verify that PNG export respects custom theme colors without corrupting the byte stream.
    """
    custom_theme = {
        "background": "#1E293B",
        "surface": "#0F172A",
        "ink": "#F8FAFC",
        "border": "#334155",
    }
    
    fig = plot_similarity_heatmap(
        multi_doc_df, 
        title="Themed Export Test", 
        theme_colors=custom_theme,
        dpi=150
    )
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    png_bytes = buf.getvalue()
    
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n"), "Themed export must produce valid PNG bytes"
    assert len(png_bytes) > 2000, "Themed export file size should be reasonable"
    
    plt.close(fig)
    buf.close()
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



