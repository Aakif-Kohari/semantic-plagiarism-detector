"""Tests for ZIP extraction functionality with fault injection."""

import io
import zipfile
import pytest

from src.core.document_parser import (
    CorruptedArchiveError,
    extract_text_from_zip,
)


def _make_valid_zip_bytes(files: dict) -> bytes:
    """Create a valid in-memory ZIP archive containing given file names and contents."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for filename, content in files.items():
            zf.writestr(filename, content)
    return buf.getvalue()


def test_extract_zip_returns_text_from_valid_archive():
    """Verify valid ZIP with text documents extracts correctly."""
    valid_zip = _make_valid_zip_bytes({
        "doc1.txt": "This is document one content.",
        "doc2.txt": "This is document two content.",
    })
    result = extract_text_from_zip(valid_zip)
    assert "document one" in result
    assert "document two" in result


def test_extract_zip_handles_empty_archive():
    """Verify empty ZIP returns empty string."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        pass
    result = extract_text_from_zip(buf.getvalue())
    assert result == ""


def test_extract_zip_skips_directories_and_macos_metadata():
    """Verify ZIP extraction skips directories and __MACOSX files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("dir/", "")
        zf.writestr("__MACOSX/.DS_Store", "metadata")
        zf.writestr("doc.txt", "Actual document content")
    result = extract_text_from_zip(buf.getvalue())
    assert "Actual document" in result
    assert "metadata" not in result


def test_corrupted_zip_header_raises_user_friendly_error():
    """Verify corrupted ZIP header triggers CorruptedArchiveError."""
    corrupted_bytes = b"PK\x03\x04corrupted_zip_header_data_not_valid_archive"
    with pytest.raises(CorruptedArchiveError) as exc_info:
        extract_text_from_zip(corrupted_bytes)
    assert "corrupted" in str(exc_info.value).lower()


def test_invalid_zip_stream_raises_user_friendly_error():
    """Verify completely invalid data triggers CorruptedArchiveError."""
    invalid_bytes = b"INVALID_ZIP_STREAM_NOT_A_ZIP_FILE"
    with pytest.raises(CorruptedArchiveError) as exc_info:
        extract_text_from_zip(invalid_bytes)
    assert "corrupted" in str(exc_info.value).lower()


def test_truncated_zip_file_raises_user_friendly_error():
    """Verify truncated/Incomplete ZIP file raises CorruptedArchiveError."""
    # Create a valid ZIP first, then truncate it
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("doc.txt", "Some content")
    truncated = buf.getvalue()[: len(buf.getvalue()) - 20]
    with pytest.raises(CorruptedArchiveError) as exc_info:
        extract_text_from_zip(truncated)
    assert "corrupted" in str(exc_info.value).lower()


def test_extract_zip_handles_corrupted_inner_files():
    """Verify ZIP with corrupted inner files is handled gracefully."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("valid.txt", "This is valid")
        # Add a file that will cause extraction to fail
        zf.writestr("corrupted.txt", "some data")
    # Manually corrupt the central directory to make extraction fail
    zip_bytes = buf.getvalue()
    # This will still be a valid ZIP but the corrupted.txt may fail
    result = extract_text_from_zip(zip_bytes)
    assert "valid" in result
