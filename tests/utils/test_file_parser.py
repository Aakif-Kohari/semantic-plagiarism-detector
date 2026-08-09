import fitz
from src.utils.file_parser import get_pdf_page_count


def test_get_pdf_page_count_single_page():
    """Verify that a valid single-page PDF returns 1."""
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.write()
    doc.close()

    assert get_pdf_page_count(pdf_bytes) == 1


def test_get_pdf_page_count_multi_page():
    """Verify that a valid multi-page PDF returns the correct number of pages."""
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    doc.new_page()
    pdf_bytes = doc.write()
    doc.close()

    assert get_pdf_page_count(pdf_bytes) == 3


def test_get_pdf_page_count_corrupted():
    """Verify that corrupted or invalid PDF bytes return 0."""
    assert get_pdf_page_count(b"invalid pdf data") == 0


def test_get_pdf_page_count_empty():
    """Verify that empty bytes return 0."""
    assert get_pdf_page_count(b"") == 0
