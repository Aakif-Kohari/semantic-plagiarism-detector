"""
tests/utils/test_file_parser.py
--------------------------------
Includes tests for password-protected PDF parsing and MIME categorization.
"""

import logging
from typing import Any, List, Optional, Tuple, Union

import fitz
import pytest

from src.utils.file_parser import (
    EncryptedPDFError,
    extract_text_from_pdf,
    get_file_mime_category,
    get_file_size_formatted,
    get_supported_mime_categories,
    is_extension_supported,
    validate_pdf_page_count,
)

logger = logging.getLogger(__name__)


# ── String & Name Formatting ─────────────────────────────────────────────────


def truncate_filename(name: str, max_len: int = 35) -> str:
    """Truncate filename with ellipsis if it exceeds max_len."""
    if len(name) <= max_len:
        return name
    return name[: max_len - 3] + "..."


# ── Magic Byte Signatures (Issue #1570) ──────────────────────────────────────

# Magic byte signatures for common document and image formats.
# Each tuple contains (byte_signature, mime_type, description).
_MAGIC_SIGNATURES = [
    # PDF: %PDF-
    (b"%PDF", "application/pdf", "Portable Document Format"),
    # ZIP Archive (also used for DOCX, XLSX, PPTX, ODT, EPUB)
    (b"PK\x03\x04", "application/zip", "ZIP Archive / Office Open XML"),
    (b"PK\x05\x06", "application/zip", "ZIP Empty Archive"),
    (b"PK\x07\x08", "application/zip", "ZIP Spanned Archive"),
    # Microsoft Compound File Binary (DOC, XLS, PPT, MSG)
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "application/msword", "MS Compound Document"),
    # Rich Text Format
    (b"{\\rtf", "application/rtf", "Rich Text Format"),
    # Images
    (b"\xff\xd8\xff", "image/jpeg", "JPEG Image"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "PNG Image"),
    (b"GIF87a", "image/gif", "GIF Image (87a)"),
    (b"GIF89a", "image/gif", "GIF Image (89a)"),
    (b"BM", "image/bmp", "BMP Image"),
    (b"RIFF", "image/webp", "WebP Image (RIFF header)"),
    # Plain Text / Markdown (Heuristic: starts with printable ASCII)
    # Handled as fallback below.
]

# Maximum number of bytes to read for signature inspection
_MAX_INSPECTION_BYTES = 16


# ── Custom Exceptions ─────────────────────────────────────────────────────────


class EncryptedPDFError(Exception):
    pass


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


class TestPDFPageCountValidation:
    """Tests for the PDF page-count safety guard."""

    @staticmethod
    def _make_pdf(page_count: int) -> bytes:
        doc = fitz.open()
        for page_number in range(page_count):
            page = doc.new_page()
            page.insert_text(
                (50, 50),
                f"Page {page_number + 1}",
            )
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def test_validate_pdf_page_count_returns_page_count(self):
        pdf_bytes = self._make_pdf(3)

        assert validate_pdf_page_count(pdf_bytes) == 3

    def test_validate_pdf_page_count_allows_exact_limit(self):
        pdf_bytes = self._make_pdf(5)

        assert (
            validate_pdf_page_count(
                pdf_bytes,
                max_pages=5,
            )
            == 5
        )

    def test_validate_pdf_page_count_rejects_over_default_limit(
        self,
    ):
        # Avoid constructing 501 real pages by mocking the opened document.
        class FakePDF:
            page_count = 501

            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        fake_pdf = FakePDF()

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "src.utils.file_parser.fitz.open",
                lambda **_kwargs: fake_pdf,
            )
            with pytest.raises(
                ValueError,
                match=(r"^PDF exceeds maximum allowed page limit " r"\(500 pages\)$"),
            ):
                validate_pdf_page_count(b"%PDF-test")

        assert fake_pdf.closed is True

    def test_validate_pdf_page_count_rejects_custom_limit(self):
        pdf_bytes = self._make_pdf(4)

        with pytest.raises(
            ValueError,
            match=(r"^PDF exceeds maximum allowed page limit " r"\(3 pages\)$"),
        ):
            validate_pdf_page_count(
                pdf_bytes,
                max_pages=3,
            )

    @pytest.mark.parametrize("max_pages", [0, -1])
    def test_validate_pdf_page_count_rejects_non_positive_limit(
        self,
        max_pages,
    ):
        with pytest.raises(
            ValueError,
            match="max_pages must be at least 1",
        ):
            validate_pdf_page_count(
                b"%PDF-test",
                max_pages=max_pages,
            )

    @pytest.mark.parametrize(
        "max_pages",
        [True, 1.5, "500", None],
    )
    def test_validate_pdf_page_count_rejects_non_integer_limit(
        self,
        max_pages,
    ):
        with pytest.raises(
            TypeError,
            match="max_pages must be an integer",
        ):
            validate_pdf_page_count(
                b"%PDF-test",
                max_pages=max_pages,
            )

    @pytest.mark.parametrize(
        "file_bytes",
        ["pdf", 123, None],
    )
    def test_validate_pdf_page_count_rejects_non_bytes_input(
        self,
        file_bytes,
    ):
        with pytest.raises(
            TypeError,
            match="file_bytes must be bytes-like",
        ):
            validate_pdf_page_count(file_bytes)

    def test_validate_pdf_page_count_rejects_malformed_pdf(self):
        with pytest.raises(fitz.FileDataError):
            validate_pdf_page_count(
                b"this is not a valid PDF",
            )

    def test_extract_text_from_pdf_applies_page_count_guard(
        self,
        monkeypatch,
    ):
        calls = []

        def fake_guard(file_bytes, max_pages=500):
            calls.append((file_bytes, max_pages))
            raise ValueError("PDF exceeds maximum allowed page limit (500 pages)")

        monkeypatch.setattr(
            "src.utils.file_parser.validate_pdf_page_count",
            fake_guard,
        )

        with pytest.raises(
            ValueError,
            match=(r"^PDF exceeds maximum allowed page limit " r"\(500 pages\)$"),
        ):
            extract_text_from_pdf(b"oversized")

        assert calls == [(b"oversized", 500)]


# ── MIME Type Detection from Bytes (Issue #1570) ─────────────────────────────


def get_file_mime_type_from_bytes(
    file_bytes: Union[bytes, bytearray, memoryview],
) -> str:
    """Inspect raw byte headers to determine the file's MIME type.

    This function analyzes the magic bytes (file signature) at the beginning
    of the byte stream to identify the file format. This is critical for
    security validation to ensure a file's actual content matches its
    claimed extension, preventing malicious payload execution.

    Args:
        file_bytes: The raw bytes of the file to inspect. Can be bytes,
                    bytearray, or memoryview.

    Returns:
        A standard MIME type string (e.g., 'application/pdf').
        Returns 'text/plain' if the content appears to be valid ASCII/UTF-8 text.
        Returns 'application/octet-stream' if the MIME type cannot be determined.

    Examples:
        >>> get_file_mime_type_from_bytes(b'%PDF-1.4\\n...')
        'application/pdf'

        >>> get_file_mime_type_from_bytes(b'PK\\x03\\x04...')
        'application/zip'
    """
    if not file_bytes:
        logger.debug("get_file_mime_type_from_bytes: Empty byte stream provided.")
        return "application/octet-stream"

    # Extract the header bytes for inspection
    try:
        header = bytes(file_bytes[:_MAX_INSPECTION_BYTES])
    except Exception as exc:
        logger.warning(
            "get_file_mime_type_from_bytes: Failed to read header bytes: %s", exc
        )
        return "application/octet-stream"

    # Check against known magic signatures
    for signature, mime_type, description in _MAGIC_SIGNATURES:
        if header.startswith(signature):
            logger.debug(
                "get_file_mime_type_from_bytes: Matched signature for %s (%s)",
                description,
                mime_type,
            )
            return mime_type

    # Fallback 1: Check if it's likely plain text / markdown
    # If the first 1024 bytes are mostly printable ASCII/UTF-8, treat as text
    try:
        sample = bytes(file_bytes[:1024])
        # Decode to UTF-8 to verify it's valid text
        decoded = sample.decode("utf-8", errors="strict")

        # Count printable characters vs control characters
        printable_count = sum(1 for c in decoded if c.isprintable() or c in "\n\r\t")
        ratio = printable_count / len(decoded) if decoded else 0

        if ratio > 0.90:
            logger.debug("get_file_mime_type_from_bytes: Detected as plain text/UTF-8.")
            return "text/plain"
    except (UnicodeDecodeError, ValueError):
        # Not valid UTF-8 text
        pass

    # Fallback 2: Unknown binary format
    logger.debug(
        "get_file_mime_type_from_bytes: No matching signature found. "
        "Returning application/octet-stream."
    )
    return "application/octet-stream"


def is_office_open_xml(file_bytes: Union[bytes, bytearray]) -> bool:
    """Check if a ZIP file is specifically an Office Open XML document (DOCX, XLSX).

    Office documents are ZIP archives containing a specific [Content_Types].xml
    file at the root. This helper inspects the ZIP central directory or local
    file headers to verify its presence.

    Args:
        file_bytes: Raw bytes of a ZIP file.

    Returns:
        True if the ZIP contains OOXML markers, False otherwise.
    """
    if not file_bytes:
        return False

    # Quick string search in the first 4KB for the OOXML content types marker
    # This is a heuristic but highly reliable for standard Office files
    try:
        header_sample = bytes(file_bytes[:4096])
        return (
            b"[Content_Types].xml" in header_sample or b"_rels/.rels" in header_sample
        )
    except Exception:
        return False


# ── File Size Formatting ─────────────────────────────────────────────────────


def get_file_size_formatted(num_bytes: int) -> str:
    """
    Convert a file size in bytes to a human-readable string.

    Args:
        num_bytes (int): File size in bytes.

    Returns:
        str: Human-readable file size using B, KB, MB, or GB.
    """
    units = ["B", "KB", "MB", "GB"]
    size = float(num_bytes)

    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024

    return f"{size:.2f} {units[-1]}"


def get_file_size_formatted_short(num_bytes: int) -> str:
    """
    Convert a file size in bytes to a compact human-readable string.

    Args:
        num_bytes (int): File size in bytes.

    Returns:
        str: Compact file size using B, KB, MB, or GB with no spaces
            and no trailing zeros (e.g. "1MB", "500KB", "12B").
    """
    units = ["B", "KB", "MB", "GB"]
    size = float(num_bytes)

    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)}{unit}"
            rounded = round(size, 2)
            if rounded == int(rounded):
                return f"{int(rounded)}{unit}"
            return f"{rounded:g}{unit}"
        size /= 1024

    return f"{size:g}{units[-1]}"


# ── PDF Extraction & Metadata ────────────────────────────────────────────────


def get_pdf_page_count(file_bytes: bytes) -> int:
    """Return the total page count of a PDF file from its bytes.

    Returns 0 if the bytes are empty, invalid, or corrupted.
    """
    if not file_bytes:
        return 0
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            return doc.page_count
    except Exception:
        return 0


def extract_text_from_pdf(
    file_bytes: bytes, password: Optional[str] = None
) -> Tuple[str, bool]:
    """
    Extracts text from PDF bytes.

    Args:
        file_bytes (bytes): Raw bytes of the uploaded PDF file.
        password (str, optional): Password to decrypt the PDF if protected.

    Returns:
        Tuple[str, bool]: Extracted text, and a boolean flag indicating if the PDF was password-protected.

    Raises:
        EncryptedPDFError: If the PDF is encrypted and no password (or an incorrect password) is provided.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    is_protected = doc.is_encrypted or doc.needs_pass

    if is_protected:
        if not password:
            raise EncryptedPDFError("PDF is password-protected. Password required.")

        # doc.authenticate returns > 0 on success
        auth_success = doc.authenticate(password)
        if not auth_success:
            raise EncryptedPDFError("Incorrect password for PDF.")

    text_content = []
    for page in doc:
        text_content.append(page.get_text())

    doc.close()
    return "\n".join(text_content), is_protected


def extract_pdf_metadata(file_bytes: bytes) -> dict[str, Any]:
    """
    Extract document metadata from PDF bytes.

    Args:
        file_bytes (bytes): Raw bytes of the uploaded PDF file.

    Returns:
        dict[str, Any]: Dictionary with keys 'title', 'author', 'creation_date',
            'mod_date', and 'page_count'. Missing or empty fields default to None.

    Raises:
        EncryptedPDFError: If the PDF is encrypted and requires a password.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    if doc.is_encrypted or doc.needs_pass:
        doc.close()
        raise EncryptedPDFError("PDF is password-protected. Password required.")

    metadata = doc.metadata or {}
    page_count = doc.page_count
    doc.close()

    return {
        "title": metadata.get("title") or None,
        "author": metadata.get("author") or None,
        "creation_date": metadata.get("creationDate") or None,
        "mod_date": metadata.get("modDate") or None,
        "page_count": page_count,
    }


# ── File Categorization Helpers ──────────────────────────────────────────────


def get_file_mime_category(filename: str) -> str:
    """
    Categorize an uploaded file into a high-level MIME group based on its extension.

    This helper simplifies routing and validation logic by grouping specific
    file extensions into broader, semantic categories.

    Args:
        filename: The name of the file (e.g., "document.pdf", "script.PY").

    Returns:
        str: The MIME category. One of: 'pdf', 'word_document', 'text', 'code', 'archive', 'unknown'.
    """
    if not filename or not isinstance(filename, str):
        return "unknown"

    ext = filename.split(".")[-1].lower() if "." in filename else ""

    mime_mapping = {
        "pdf": "pdf",
        "doc": "word_document",
        "docx": "word_document",
        "txt": "text",
        "md": "text",
        "markdown": "text",
        "mdown": "text",
        "csv": "text",
        "rtf": "text",
        "py": "code",
        "js": "code",
        "java": "code",
        "cpp": "code",
        "c": "code",
        "html": "code",
        "css": "code",
        "zip": "archive",
        "rar": "archive",
        "tar": "archive",
        "gz": "archive",
        "7z": "archive",
    }

    return mime_mapping.get(ext, "unknown")


def get_supported_mime_categories() -> List[str]:
    """
    Retrieve a list of all supported high-level MIME categories.

    Returns:
        List[str]: A list of unique category names.
    """
    return ["pdf", "word_document", "text", "code", "archive", "unknown"]


def is_extension_supported(
    filename: str, allowed_categories: Optional[List[str]] = None
) -> bool:
    """
    Check if a file's extension belongs to an allowed list of MIME categories.

    Args:
        filename: The name of the file to check.
        allowed_categories: List of allowed categories. Defaults to all known categories except 'unknown'.

    Returns:
        bool: True if the file's category is in the allowed list, False otherwise.
    """
    if allowed_categories is None:
        allowed_categories = ["pdf", "word_document", "text", "code", "archive"]

    category = get_file_mime_category(filename)
    return category in allowed_categories
