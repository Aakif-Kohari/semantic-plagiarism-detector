import io
import zipfile

import pytest

from src.utils.zip_processor import MAX_SINGLE_FILE_SIZE, process_zip_file


def create_in_memory_zip(
    files: dict, encrypt: bool = False, password: bytes = None
) -> bytes:
    """Helper to generate a ZIP archive in memory."""
    zip_stream = io.BytesIO()
    # If encrypt is True, we can't easily use standard zipfile to write encrypted files
    # because standard zipfile.ZipFile does not support writing encrypted zip files (it only supports reading them).
    # However, we can mock or construct flag_bits or flag encryption manually.
    with zipfile.ZipFile(zip_stream, "w") as zf:
        for name, content in files.items():
            if encrypt:
                # We can write an entry and manually set flag_bits to indicate encryption
                zinfo = zipfile.ZipInfo(name)
                zinfo.flag_bits = 0x1  # Enable encryption bit
                zf.writestr(zinfo, content)
            else:
                zf.writestr(name, content)
    return zip_stream.getvalue()


def test_process_zip_valid_extraction():
    """Verify that supported files are successfully extracted from a valid ZIP archive."""
    zip_data = create_in_memory_zip(
        {
            "doc1.pdf": b"PDF text content",
            "doc2.docx": b"Word text content",
            "doc3.txt": b"Plain text content",
            "unsupported.png": b"Image data",
            "executable.sh": b"#!/bin/sh\necho 1",
        }
    )

    result = process_zip_file(zip_data)

    assert "doc1.pdf" in result
    assert result["doc1.pdf"] == b"PDF text content"
    assert "doc2.docx" in result
    assert result["doc2.docx"] == b"Word text content"
    assert "doc3.txt" in result
    assert result["doc3.txt"] == b"Plain text content"

    # Unsupported formats must be ignored
    assert "unsupported.png" not in result
    assert "executable.sh" not in result


def test_process_zip_empty():
    """Verify that empty ZIP input raises a ValueError."""
    with pytest.raises(ValueError, match="ZIP archive is empty."):
        process_zip_file(b"")


def test_process_zip_corrupted():
    """Verify that a corrupted ZIP raises a ValueError."""
    with pytest.raises(ValueError, match="Invalid or corrupted ZIP archive."):
        process_zip_file(b"this is not a zip file content")


def test_process_zip_encrypted():
    """Verify that password-protected or encrypted ZIP entries raise a ValueError."""
    from unittest.mock import patch

    info = zipfile.ZipInfo("secret.pdf")
    info.flag_bits = 0x1

    zip_data = create_in_memory_zip({"secret.pdf": b"secret contents"})

    with patch("zipfile.ZipFile.infolist", return_value=[info]):
        with pytest.raises(
            ValueError,
            match="Password-protected or encrypted ZIP files are not supported.",
        ):
            process_zip_file(zip_data)


def test_process_zip_nested_folders_and_collisions():
    """Verify nested path flattening (replacing '/' with '_') and collision resolution."""
    zip_data = create_in_memory_zip(
        {
            "assignment.pdf": b"Root version",
            "folder1/assignment.pdf": b"Folder 1 version",
            "folder2/assignment.pdf": b"Folder 2 version",
            "folder2/nested/assignment.pdf": b"Deeply nested version",
        }
    )

    result = process_zip_file(zip_data)

    # Output names must be flattened and unique
    assert "assignment.pdf" in result
    assert result["assignment.pdf"] == b"Root version"

    assert "folder1_assignment.pdf" in result
    assert result["folder1_assignment.pdf"] == b"Folder 1 version"

    assert "folder2_assignment.pdf" in result
    assert result["folder2_assignment.pdf"] == b"Folder 2 version"

    assert "folder2_nested_assignment.pdf" in result
    assert result["folder2_nested_assignment.pdf"] == b"Deeply nested version"


def test_process_zip_duplicate_name_collision_fallback():
    """Verify that name collisions at the same flattened level get unique suffixes."""
    # Since we replace '/' with '_', the files 'a/b.txt' and 'a_b.txt' would collide.
    # The collision resolution should append unique suffixes like 'a_b_1.txt'.
    zip_data = create_in_memory_zip(
        {
            "a_b.txt": b"First content",
            "a/b.txt": b"Second content",
        }
    )

    result = process_zip_file(zip_data)

    assert "a_b.txt" in result
    assert result["a_b.txt"] == b"First content"

    assert "a_b_1.txt" in result
    assert result["a_b_1.txt"] == b"Second content"


def test_process_zip_path_traversal():
    """Verify path traversal attempts are safely skipped."""
    zip_data = create_in_memory_zip(
        {
            "doc.pdf": b"Safe file",
            "../traversal.pdf": b"Traversal payload",
            "folder/../../traversal2.txt": b"Traversal payload 2",
            "/absolute.pdf": b"Absolute traversal payload",
        }
    )

    result = process_zip_file(zip_data)

    assert "doc.pdf" in result
    assert result["doc.pdf"] == b"Safe file"

    # Traversal files must be ignored/skipped
    assert "traversal.pdf" not in result
    assert "folder_../../traversal2.txt" not in result
    assert "../traversal.pdf" not in result
    assert "absolute.pdf" not in result
    assert "/absolute.pdf" not in result


def test_process_zip_bomb_safety_total_size():
    """Verify that a ZIP file exceeding total decompressed safety limit is rejected."""
    from unittest.mock import patch

    info1 = zipfile.ZipInfo("file1.txt")
    info1.file_size = 80 * 1024 * 1024
    info2 = zipfile.ZipInfo("file2.txt")
    info2.file_size = 80 * 1024 * 1024
    info3 = zipfile.ZipInfo("file3.txt")
    info3.file_size = 80 * 1024 * 1024

    zip_bytes = create_in_memory_zip({"doc.txt": b"some content"})

    with patch("zipfile.ZipFile.infolist", return_value=[info1, info2, info3]):
        with pytest.raises(
            ValueError, match="ZIP archive total decompressed size exceeds safety limit"
        ):
            process_zip_file(zip_bytes)


def test_process_zip_bomb_safety_single_file():
    """Verify that a ZIP file containing a single entry exceeding the safety limit is rejected."""
    from unittest.mock import patch

    info = zipfile.ZipInfo("huge_file.txt")
    info.file_size = MAX_SINGLE_FILE_SIZE + 100

    zip_bytes = create_in_memory_zip({"doc.txt": b"some content"})

    with patch("zipfile.ZipFile.infolist", return_value=[info]):
        with pytest.raises(
            ValueError, match="exceeds single file decompression safety limit"
        ):
            process_zip_file(zip_bytes)
