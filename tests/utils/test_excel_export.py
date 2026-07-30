"""
tests/utils/test_excel_export.py
---------------------------------
Unit tests for styled Excel export utility.
"""

import io

import pandas as pd
from openpyxl import load_workbook

from src.utils.excel_export import export_similarity_matrix_to_excel, _truncate_title


def test_export_similarity_matrix_to_excel():
    data = {
        "doc1.pdf": [1.0, 0.95, 0.20],
        "doc2.pdf": [0.95, 1.0, 0.15],
        "doc3.pdf": [0.20, 0.15, 1.0],
    }
    df = pd.DataFrame(data, index=["doc1.pdf", "doc2.pdf", "doc3.pdf"])

    excel_bytes = export_similarity_matrix_to_excel(df, threshold=0.59)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0

    # Read back generated Excel workbook using openpyxl
    wb = load_workbook(filename=io.BytesIO(excel_bytes))
    ws = wb.active
    assert ws.title == "Similarity Matrix"
    assert ws.cell(row=2, column=2).value == 1.0


def test_truncate_title_short_title():
    """Test that short titles are not truncated."""
    short_title = "short.pdf"
    assert _truncate_title(short_title) == short_title
    assert _truncate_title(short_title, max_length=60) == short_title


def test_truncate_title_long_title():
    """Test that long titles are truncated to 60 characters with '...'."""
    long_title = "A" * 100 + ".pdf"
    truncated = _truncate_title(long_title, max_length=60)
    assert len(truncated) == 60
    assert truncated.endswith("...")
    assert truncated == "A" * 57 + "..."


def test_truncate_title_exactly_max_length():
    """Test that titles exactly at max_length are not truncated."""
    exact_title = "B" * 60
    assert _truncate_title(exact_title, max_length=60) == exact_title


def test_excel_export_with_long_document_titles():
    """Test that Excel export handles long document titles (300+ characters) without breaking."""
    long_title_1 = "x" * 300 + "_document_one.pdf"
    long_title_2 = "y" * 300 + "_document_two.pdf"
    long_title_3 = "z" * 300 + "_document_three.pdf"
    
    data = {
        long_title_1: [1.0, 0.95, 0.20],
        long_title_2: [0.95, 1.0, 0.15],
        long_title_3: [0.20, 0.15, 1.0],
    }
    df = pd.DataFrame(data, index=[long_title_1, long_title_2, long_title_3])

    # Should not raise an exception
    excel_bytes = export_similarity_matrix_to_excel(df, threshold=0.59)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0

    # Verify the Excel file can be read back
    wb = load_workbook(filename=io.BytesIO(excel_bytes))
    ws = wb.active
    assert ws.title == "Similarity Matrix"


def test_excel_export_long_titles_truncated_in_display():
    """Test that long titles are truncated to 60 chars in Excel display but full name preserved in comments."""
    long_title_1 = "This is a very long document title that exceeds 60 characters maximum length" + "x" * 50
    long_title_2 = "Another extremely long document title for testing truncation" + "y" * 60
    
    data = {
        long_title_1: [1.0, 0.95],
        long_title_2: [0.95, 1.0],
    }
    df = pd.DataFrame(data, index=[long_title_1, long_title_2])

    excel_bytes = export_similarity_matrix_to_excel(df, threshold=0.59)
    
    # Read back and verify
    wb = load_workbook(filename=io.BytesIO(excel_bytes))
    ws = wb.active

    # Check header cell (column header for long_title_1)
    header_cell = ws.cell(row=1, column=2)
    header_value = header_cell.value
    assert len(header_value) <= 60, f"Header should be truncated to 60 chars, got {len(header_value)}"
    assert header_value.endswith("..."), "Truncated title should end with '...'"
    # Verify full title is preserved in comment
    assert header_cell.comment is not None, "Long title should have a comment with full name"
    assert long_title_1 in str(header_cell.comment.text), "Comment should contain full title"

    # Check row label cell (first column for long_title_1)
    row_label_cell = ws.cell(row=2, column=1)
    row_value = row_label_cell.value
    assert len(row_value) <= 60, f"Row label should be truncated to 60 chars, got {len(row_value)}"
    assert row_value.endswith("..."), "Truncated row label should end with '...'"
    # Verify full title is preserved in comment
    assert row_label_cell.comment is not None, "Long title should have a comment with full name"
    assert long_title_1 in str(row_label_cell.comment.text), "Comment should contain full title"


def test_excel_export_short_titles_no_comments():
    """Test that short titles don't get unnecessary comments."""
    short_title_1 = "doc1.pdf"
    short_title_2 = "doc2.pdf"
    
    data = {
        short_title_1: [1.0, 0.95],
        short_title_2: [0.95, 1.0],
    }
    df = pd.DataFrame(data, index=[short_title_1, short_title_2])

    excel_bytes = export_similarity_matrix_to_excel(df, threshold=0.59)
    
    # Read back and verify
    wb = load_workbook(filename=io.BytesIO(excel_bytes))
    ws = wb.active

    # Check header cell - should not have comment for short titles
    header_cell = ws.cell(row=1, column=2)
    assert header_cell.value == short_title_1
    assert header_cell.comment is None, "Short titles should not have comments"

    # Check row label cell - should not have comment for short titles
    row_label_cell = ws.cell(row=2, column=1)
    assert row_label_cell.value == short_title_1
    assert row_label_cell.comment is None, "Short titles should not have comments"
