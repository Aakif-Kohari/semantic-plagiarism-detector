"""
tests/utils/test_file_parser.py
-------------------------------
Includes tests for password-protected PDF parsing, MIME categorization,
and magic-byte MIME type detection (Issue #1570).
"""

import fitz
import pytest

from src.utils.file_parser import (
    EncryptedPDFError,
    extract_pdf_metadata,
    extract_text_from_pdf,
    get_file_mime_type_from_bytes,
    get_file_size_formatted,
    get_file_mime_category,
    get_pdf_page_count,
    get_supported_mime_categories,
    is_extension_supported,
    is_office_open_xml,
)


# ── PDF Page Count Tests ─────────────────────────────────────────────────────


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


# ── Encrypted PDF Handling Tests ─────────────────────────────────────────────


class TestEncryptedPDFHandling:
    """Test suite for password-protected PDF parsing."""

    def test_encrypted_pdf_handling(self):
        """Test reading encrypted PDFs with no password, wrong password, and correct password."""
        # 1. Create an in-memory encrypted PDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Confidential Student Assignment")

        pdf_bytes = doc.tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw="secret123",
            owner_pw="owner123",
        )
        doc.close()

        # 2. Test reading without password -> should raise EncryptedPDFError
        with pytest.raises(EncryptedPDFError):
            extract_text_from_pdf(pdf_bytes)

        # 3. Test reading with wrong password -> should raise EncryptedPDFError
        with pytest.raises(EncryptedPDFError):
            extract_text_from_pdf(pdf_bytes, password="wrongpass")

        # 4. Test reading with correct password -> should succeed
        text, is_protected = extract_text_from_pdf(pdf_bytes, password="secret123")
        assert "Confidential Student Assignment" in text
        assert is_protected is True


# ── File Size Formatting Tests ───────────────────────────────────────────────


class TestFileSizeFormatting:
    """Test suite for file size formatting utility."""

    def test_get_file_size_formatted_bytes(self):
        assert get_file_size_formatted(500) == "500 B"

    def test_get_file_size_formatted_kb(self):
        assert get_file_size_formatted(1024) == "1.00 KB"

    def test_get_file_size_formatted_mb(self):
        assert get_file_size_formatted(1024 * 1024) == "1.00 MB"

    def test_get_file_size_formatted_gb(self):
        assert get_file_size_formatted(1024 * 1024 * 1024) == "1.00 GB"

    def test_get_file_size_formatted_fractional(self):
        assert get_file_size_formatted(1536) == "1.50 KB"


# ── MIME Category Tests ──────────────────────────────────────────────────────


class TestFileMimeCategory:
    """Test suite for MIME categorization helpers."""

    @pytest.mark.parametrize(
        "filename, expected_category",
        [
            ("document.pdf", "pdf"),
            ("report.PDF", "pdf"),  # Case insensitive
            ("essay.docx", "word_document"),
            ("notes.doc", "word_document"),
            ("readme.txt", "text"),
            ("documentation.md", "text"),
            ("guide.markdown", "text"),
            ("notes.mdown", "text"),
            ("NOTES.MARKDOWN", "text"),  # Case insensitive
            ("data.csv", "text"),
            ("script.py", "code"),
            ("app.js", "code"),
            ("Main.java", "code"),
            ("archive.zip", "archive"),
            ("backup.tar.gz", "archive"),  # Splits on last dot, so 'gz' -> archive
            ("no_extension", "unknown"),
            ("", "unknown"),
            (".hidden_file", "unknown"),
            (None, "unknown"),
            (12345, "unknown"),  # Non-string input
        ],
    )
    def test_get_file_mime_category(self, filename, expected_category):
        """Test MIME categorization for various file extensions and edge cases."""
        assert get_file_mime_category(filename) == expected_category

    def test_get_supported_mime_categories(self):
        """Test retrieval of supported categories list."""
        categories = get_supported_mime_categories()
        assert isinstance(categories, list)
        assert "pdf" in categories
        assert "word_document" in categories
        assert "text" in categories
        assert "code" in categories
        assert "archive" in categories
        assert "unknown" in categories

    @pytest.mark.parametrize(
        "filename, allowed_categories, expected_result",
        [
            ("document.pdf", ["pdf", "text"], True),
            ("script.py", ["pdf", "text"], False),
            ("notes.txt", None, True),  # Defaults to all known except unknown
            ("guide.markdown", None, True),
            ("notes.mdown", None, True),
            ("archive.zip", ["text", "code"], False),
        ],
    )
    def test_is_extension_supported(
        self, filename, allowed_categories, expected_result
    ):
        """Test extension support validation against allowed categories."""
        assert is_extension_supported(filename, allowed_categories) == expected_result


# ── PDF Metadata Extraction Tests ────────────────────────────────────────────


class TestPdfMetadataExtraction:
    """Test suite for PDF metadata extraction."""

    def _create_pdf(self, metadata: dict) -> bytes:
        """Create an in-memory PDF with the given metadata."""
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Metadata Test Content")
        doc.set_metadata(metadata)
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def test_extract_pdf_metadata_with_all_fields(self):
        """Test extracting metadata from a PDF with complete metadata."""
        pdf_bytes = self._create_pdf(
            {
                "title": "Test Report",
                "author": "Rishab",
                "creationDate": "D:20240101120000Z",
                "modDate": "D:20240201120000Z",
            }
        )
        result = extract_pdf_metadata(pdf_bytes)
        assert result["title"] == "Test Report"
        assert result["author"] == "Rishab"
        assert result["creation_date"] == "D:20240101120000Z"
        assert result["mod_date"] == "D:20240201120000Z"
        assert result["page_count"] == 1

    def test_extract_pdf_metadata_missing_fields_default_to_none(self):
        """Test that empty or missing metadata fields become None."""
        pdf_bytes = self._create_pdf({})
        result = extract_pdf_metadata(pdf_bytes)
        assert result["title"] is None
        assert result["author"] is None
        assert result["creation_date"] is None
        assert result["mod_date"] is None
        assert result["page_count"] == 1

    def test_extract_pdf_metadata_page_count(self):
        """Test that page_count reflects the number of pages in the PDF."""
        doc = fitz.open()
        doc.new_page()
        doc.new_page()
        doc.new_page()
        pdf_bytes = doc.tobytes()
        doc.close()
        result = extract_pdf_metadata(pdf_bytes)
        assert result["page_count"] == 3

    def test_extract_pdf_metadata_encrypted_raises(self):
        """Test that encrypted PDFs raise EncryptedPDFError."""
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Confidential")
        pdf_bytes = doc.tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw="secret123",
            owner_pw="owner123",
        )
        doc.close()
        with pytest.raises(EncryptedPDFError):
            extract_pdf_metadata(pdf_bytes)


# ── Magic Byte MIME Type Detection Tests (Issue #1570) ───────────────────────


class TestGetFileMimeTypeFromBytes:
    """Test suite for magic byte MIME type detection."""

    def test_pdf_detection(self):
        """Verify PDF magic bytes are correctly identified."""
        pdf_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        assert get_file_mime_type_from_bytes(pdf_bytes) == "application/pdf"

    def test_zip_detection(self):
        """Verify standard ZIP magic bytes are identified."""
        zip_bytes = b"PK\x03\x04\x14\x00\x00\x00"
        assert get_file_mime_type_from_bytes(zip_bytes) == "application/zip"

    def test_docx_detection_as_zip(self):
        """Verify DOCX (which is a ZIP) returns application/zip."""
        # DOCX starts with standard ZIP header
        docx_bytes = b"PK\x03\x04\x14\x00\x06\x00[Content_Types].xml"
        assert get_file_mime_type_from_bytes(docx_bytes) == "application/zip"

    def test_legacy_doc_detection(self):
        """Verify legacy MS Compound Document (DOC) magic bytes."""
        doc_bytes = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\x00\x00\x00\x00"
        assert get_file_mime_type_from_bytes(doc_bytes) == "application/msword"

    def test_rtf_detection(self):
        """Verify Rich Text Format magic bytes."""
        rtf_bytes = b"{\\rtf1\\ansi\\ansicpg1252\\deff0"
        assert get_file_mime_type_from_bytes(rtf_bytes) == "application/rtf"

    def test_jpeg_detection(self):
        """Verify JPEG image magic bytes."""
        jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        assert get_file_mime_type_from_bytes(jpeg_bytes) == "image/jpeg"

    def test_png_detection(self):
        """Verify PNG image magic bytes."""
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        assert get_file_mime_type_from_bytes(png_bytes) == "image/png"

    def test_plain_text_detection(self):
        """Verify standard ASCII/UTF-8 text is detected as text/plain."""
        text_bytes = b"This is a standard plain text document.\nIt has multiple lines."
        assert get_file_mime_type_from_bytes(text_bytes) == "text/plain"

    def test_markdown_detection_as_text(self):
        """Verify Markdown files are detected as text/plain."""
        md_bytes = b"# Heading\n\nThis is **bold** text.\n- List item"
        assert get_file_mime_type_from_bytes(md_bytes) == "text/plain"

    def test_unknown_binary_returns_octet_stream(self):
        """Verify unknown binary data returns application/octet-stream."""
        binary_bytes = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09"
        assert get_file_mime_type_from_bytes(binary_bytes) == "application/octet-stream"

    def test_empty_bytes_returns_octet_stream(self):
        """Verify empty byte stream returns application/octet-stream."""
        assert get_file_mime_type_from_bytes(b"") == "application/octet-stream"
        assert get_file_mime_type_from_bytes(None) == "application/octet-stream"

    def test_memoryview_input(self):
        """Verify function accepts memoryview objects."""
        pdf_bytes = memoryview(b"%PDF-1.4\n")
        assert get_file_mime_type_from_bytes(pdf_bytes) == "application/pdf"

    def test_bytearray_input(self):
        """Verify function accepts bytearray objects."""
        pdf_bytes = bytearray(b"%PDF-1.4\n")
        assert get_file_mime_type_from_bytes(pdf_bytes) == "application/pdf"


class TestIsOfficeOpenXml:
    """Test suite for OOXML specific ZIP detection."""

    def test_valid_docx_bytes(self):
        """Verify ZIP with OOXML markers returns True."""
        docx_bytes = b"PK\x03\x04\x14\x00\x06\x00[Content_Types].xml"
        assert is_office_open_xml(docx_bytes) is True

    def test_standard_zip_returns_false(self):
        """Verify standard ZIP without OOXML markers returns False."""
        zip_bytes = b"PK\x03\x04\x14\x00\x00\x00random_file.txt"
        assert is_office_open_xml(zip_bytes) is False

    def test_empty_bytes_returns_false(self):
        """Verify empty input returns False."""
        assert is_office_open_xml(b"") is False
        assert is_office_open_xml(None) is False
