import io
import shutil
import zipfile
from unittest.mock import MagicMock, patch

import docx
import pytest

from src.core.document_parser import (
    CorruptedArchiveError,
    extract_text,
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_txt,
    extract_text_from_zip,
    extract_texts,
    strip_bibliography,
)

# Skip OCR tests when Tesseract binary is not present on this machine
TESSERACT_AVAILABLE = shutil.which("tesseract") is not None


def _make_pdf_bytes(text: str) -> bytes:
    """Create a minimal in-memory PDF containing the given text."""
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    # Ensure there are enough words to bypass OCR fallback (at least 8 words)
    words = (text + " word" * 10).split()
    c.drawString(50, 150, " ".join(words))
    c.showPage()
    c.save()
    return buf.getvalue()


def _make_docx_bytes(text: str) -> bytes:
    """Create a minimal in-memory DOCX containing the given text."""
    doc = docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_valid_zip_bytes(files: dict) -> bytes:
    """Create a valid in-memory ZIP archive containing given file names and contents."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for filename, content in files.items():
            zf.writestr(filename, content)
    return buf.getvalue()


@pytest.mark.skipif(
    not TESSERACT_AVAILABLE, reason="Tesseract OCR is not installed on this machine"
)
def test_extract_from_pdf_bytes():
    pdf_bytes = _make_pdf_bytes("Hello PDF")
    # For blank page PDF, pdfplumber might return empty string, but it shouldn't error
    result = extract_text_from_pdf(pdf_bytes)
    assert isinstance(result, str)


def test_extract_from_pdf_filters_repeated_headers_page_numbers_and_whitespace():
    # Build mock pages where header/footer lines are REPEATED across pages
    # and page numbers sit on their own dedicated lines (so the filter strips them)
    page_one = MagicMock()
    page_one.extract_text.return_value = (
        "Research Report\n"
        "Introduction\n"
        "This section introduces the topic in detail with enough words.\n"
        "Page 1"
    )
    page_two = MagicMock()
    page_two.extract_text.return_value = (
        "Research Report\n"
        "Body content is written here at length for analysis purposes.\n"
        "Page 2"
    )

    fake_pdf = MagicMock()
    fake_pdf.pages = [page_one, page_two]
    fake_pdf.__enter__ = MagicMock(return_value=fake_pdf)
    fake_pdf.__exit__ = MagicMock(return_value=False)

    with patch("src.core.document_parser.pdfplumber.open", return_value=fake_pdf):
        result = extract_text_from_pdf(io.BytesIO(b"fake-pdf"))

    # Repeated header across all pages must be stripped
    assert "Research Report" not in result
    # Standalone page-number lines must be stripped
    assert "Page 1" not in result
    assert "Page 2" not in result
    # Body content must survive
    assert "Introduction" in result
    assert "Body content" in result
    assert "\n\n\n" not in result


def test_extract_from_docx_bytes():
    docx_bytes = _make_docx_bytes("Hello DOCX")
    result = extract_text_from_docx(docx_bytes)
    assert result == "Hello DOCX"


def test_extract_from_txt_bytes():
    txt_bytes = b"Hello TXT"
    result = extract_text_from_txt(txt_bytes)
    assert result == "Hello TXT"


# ---------------------------------------------------------------------------
# Corrupted Zip Submission Tests (#580)
# ---------------------------------------------------------------------------


class TestCorruptedZipHandling:

    def test_extract_text_from_valid_zip(self):
        zip_bytes = _make_valid_zip_bytes({"essay1.txt": "First student essay text.", "essay2.txt": "Second student submission."})
        result = extract_text_from_zip(zip_bytes)
        assert "First student essay text." in result
        assert "Second student submission." in result

    def test_corrupted_zip_header_raises_user_friendly_error(self):
        corrupted_bytes = b"PK\x03\x04corrupted_zip_header_data_not_valid_archive"
        with pytest.raises(CorruptedArchiveError) as exc_info:
            extract_text_from_zip(corrupted_bytes)
        assert "corrupted" in str(exc_info.value).lower()

    def test_routing_corrupted_zip_via_extract_text(self):
        corrupted_bytes = b"INVALID_ZIP_STREAM"
        with pytest.raises(CorruptedArchiveError):
            extract_text(corrupted_bytes, "submission_batch.zip")


@pytest.mark.skipif(
    not TESSERACT_AVAILABLE, reason="Tesseract OCR is not installed on this machine"
)
def test_extract_text_routing():
    pdf_bytes = _make_pdf_bytes("Hello PDF")
    docx_bytes = _make_docx_bytes("Hello DOCX")
    txt_bytes = b"Hello TXT"

    assert isinstance(extract_text(pdf_bytes, "test.pdf"), str)
    assert extract_text(docx_bytes, "test.docx") == "Hello DOCX"
    assert extract_text(txt_bytes, "test.txt") == "Hello TXT"
    # Fallback case
    assert extract_text(txt_bytes, "test.unknown") == "Hello TXT"


def test_extract_texts_mixed():
    docx_bytes = _make_docx_bytes("Hello DOCX")
    txt_bytes = b"Hello TXT"

    mock_file1 = MagicMock()
    mock_file1.name = "doc1.docx"
    mock_file1.read.return_value = docx_bytes

    mock_file2 = MagicMock()
    mock_file2.name = "doc2.txt"
    mock_file2.read.return_value = txt_bytes

    # Mock extract_text to isolate testing of extract_texts structure
    with patch(
        "src.core.document_parser.extract_text",
        side_effect=lambda f, name, **kwargs: f"Parsed {name}",
    ):
        results = extract_texts([mock_file1, mock_file2])

    assert results["doc1.docx"] == "Parsed doc1.docx"
    assert results["doc2.txt"] == "Parsed doc2.txt"


# ---------------------------------------------------------------------------
# strip_bibliography tests (Issue #116)
# ---------------------------------------------------------------------------


class TestStripBibliography:

    def test_strips_references_header(self):
        text = "Some body text.\n\nReferences\n[1] Smith, 2020.\n[2] Jones, 2021."
        result = strip_bibliography(text)
        assert result == "Some body text."
        assert "Smith" not in result

    def test_strips_works_cited(self):
        text = "Analysis complete.\n\nWorks Cited\nDoe, J. (2019). Paper."
        result = strip_bibliography(text)
        assert result == "Analysis complete."

    def test_strips_bibliography_header(self):
        text = "Conclusion drawn.\n\nBibliography\nAdams, B. Book."
        result = strip_bibliography(text)
        assert result == "Conclusion drawn."

    def test_strips_citations_header(self):
        text = "Findings discussed.\n\nCitations\nLee, 2018."
        result = strip_bibliography(text)
        assert result == "Findings discussed."

    def test_strips_reference_list_header(self):
        text = "Summary provided.\n\nReference List\nWang, 2022."
        result = strip_bibliography(text)
        assert result == "Summary provided."

    def test_strips_sources_header(self):
        text = "Method described.\n\nSources\nData from WHO."
        result = strip_bibliography(text)
        assert result == "Method described."

    def test_case_insensitive(self):
        text = "Body here.\n\nREFERENCES\n[1] entry."
        result = strip_bibliography(text)
        assert result == "Body here."

    def test_preserves_normal_text(self):
        text = (
            "Introduction section with enough words to be meaningful.\n\n"
            "Methodology describes the approach used in this study.\n\n"
            "Results show significant improvement over baseline.\n\n"
            "Conclusion summarizes key findings."
        )
        result = strip_bibliography(text)
        assert result == text

    def test_no_bibliography_unchanged(self):
        text = "Just a plain document with no special headers at all."
        assert strip_bibliography(text) == text

    def test_empty_string(self):
        assert strip_bibliography("") == ""

    def test_inline_references_not_stripped(self):
        text = "The references to prior work are important.\nMore text follows."
        result = strip_bibliography(text)
        assert result == text

    def test_bibliography_not_at_start_of_line_not_stripped(self):
        text = "The Bibliography section was reviewed.\nMore text."
        result = strip_bibliography(text)
        assert result == text

    def test_extract_text_strips_bibliography_from_txt(self):
        txt_bytes = b"Body text.\n\nReferences\n[1] Entry one."
        result = extract_text(txt_bytes, "test.txt")
        assert "References" not in result
        assert "Body text" in result

    def test_extract_text_strips_bibliography_from_docx(self):
        docx_bytes = _make_docx_bytes("Body content.\n\nBibliography\nEntry one.")
        result = extract_text(docx_bytes, "test.docx")
        assert "Bibliography" not in result
        assert "Body content" in result
        