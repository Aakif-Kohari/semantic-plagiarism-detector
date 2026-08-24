"""
tests/utils/test_file_validator.py
----------------------------------
Comprehensive unit tests for the file validation utilities (Issue #2926).

Verifies that file size limits, extension checks, and magic byte validation
work correctly to prevent RAM spikes and malicious file processing.
"""

from src.utils.file_validator import (
    MAX_FILE_SIZE_BYTES,
    FileValidator,
    validate_upload,
)


class TestFileValidatorSize:
    """Test suite for file size validation."""

    def test_valid_size_passes(self):
        """Verify files under the size limit pass validation."""
        validator = FileValidator(max_size_bytes=1024)
        result = validator.validate(b"x" * 500, "test.txt")
        assert result.is_valid is True

    def test_exact_limit_passes(self):
        """Verify files exactly at the size limit pass validation."""
        validator = FileValidator(max_size_bytes=1024)
        result = validator.validate(b"x" * 1024, "test.txt")
        assert result.is_valid is True

    def test_exceeds_limit_fails(self):
        """Verify files over the size limit fail with FILE_TOO_LARGE."""
        validator = FileValidator(max_size_bytes=1024)
        result = validator.validate(b"x" * 1025, "large.pdf")
        
        assert result.is_valid is False
        assert result.error_code == "FILE_TOO_LARGE"
        assert "too large" in result.error_message.lower()

    def test_empty_file_fails(self):
        """Verify empty files (0 bytes) fail with FILE_EMPTY."""
        validator = FileValidator()
        result = validator.validate(b"", "empty.txt")
        
        assert result.is_valid is False
        assert result.error_code == "FILE_EMPTY"

    def test_default_limit_is_50mb(self):
        """Verify the default validator uses the 50MB limit."""
        assert MAX_FILE_SIZE_BYTES == 50 * 1024 * 1024


class TestFileValidatorExtension:
    """Test suite for file extension validation."""

    def test_valid_extension_passes(self):
        """Verify allowed extensions pass validation."""
        validator = FileValidator()
        for ext in [".pdf", ".docx", ".txt", ".md"]:
            result = validator.validate(b"content", f"file{ext}")
            assert result.is_valid is True, f"Failed for {ext}"

    def test_invalid_extension_fails(self):
        """Verify unsupported extensions fail with UNSUPPORTED_EXTENSION."""
        validator = FileValidator()
        result = validator.validate(b"content", "malware.exe")
        
        assert result.is_valid is False
        assert result.error_code == "UNSUPPORTED_EXTENSION"

    def test_missing_extension_fails(self):
        """Verify files with no extension fail with MISSING_EXTENSION."""
        validator = FileValidator()
        result = validator.validate(b"content", "noextension")
        
        assert result.is_valid is False
        assert result.error_code == "MISSING_EXTENSION"

    def test_case_insensitive_extension(self):
        """Verify extension matching is case-insensitive."""
        validator = FileValidator()
        result = validator.validate(b"%PDF-1.4", "DOCUMENT.PDF")
        assert result.is_valid is True

    def test_custom_allowed_extensions(self):
        """Verify custom allowed_extensions set is respected."""
        validator = FileValidator(allowed_extensions={".custom"})
        
        assert validator.validate(b"data", "file.custom").is_valid is True
        assert validator.validate(b"data", "file.txt").is_valid is False


class TestFileValidatorMagicBytes:
    """Test suite for magic byte (content) validation."""

    def test_valid_pdf_magic_bytes(self):
        """Verify PDF magic bytes (%PDF) are recognized."""
        validator = FileValidator()
        result = validator.validate(b"%PDF-1.4\n%fake content", "test.pdf")
        assert result.is_valid is True

    def test_valid_docx_magic_bytes(self):
        """Verify DOCX magic bytes (PK\x03\x04) are recognized."""
        validator = FileValidator()
        result = validator.validate(b"PK\x03\x04\x14\x00\x06\x00", "test.docx")
        assert result.is_valid is True

    def test_mismatched_magic_bytes_logs_warning(self, caplog):
        """Verify mismatched magic bytes log a warning but don't fail hard."""
        import logging
        validator = FileValidator()
        
        # Pass a text file disguised as a PDF
        with caplog.at_level(logging.WARNING):
            result = validator.validate(b"This is plain text", "fake.pdf")
            
        # Currently configured to pass but log warning
        assert result.is_valid is True
        assert any("Magic byte mismatch" in record.message for record in caplog.records)

    def test_txt_files_skip_magic_byte_check(self):
        """Verify plain text files skip magic byte validation."""
        validator = FileValidator()
        result = validator.validate(b"Just some plain text content.", "readme.txt")
        assert result.is_valid is True


class TestStrictModeMagicByteEnforcement:
    """strict_mode turns magic-byte mismatches into hard failures (#3201).

    The permissive default exists because some valid files carry unusual
    headers — but it equally lets an executable renamed to .pdf through,
    which is unacceptable in high-security deployments. With
    ``strict_mode=True`` a mismatched header fails validation with the
    machine-readable ``MAGIC_BYTE_MISMATCH`` code.
    """

    def test_strict_mode_rejects_mismatched_header(self):
        validator = FileValidator(strict_mode=True)

        result = validator.validate(b"This is plain text", "fake.pdf")

        assert result.is_valid is False
        assert result.error_code == "MAGIC_BYTE_MISMATCH"
        assert "does not match extension" in result.error_message

    def test_strict_mode_accepts_correct_magic_bytes(self):
        validator = FileValidator(strict_mode=True)

        assert validator.validate(b"%PDF-1.7\n real pdf", "doc.pdf").is_valid is True
        assert (
            validator.validate(b"PK\x03\x04\x14\x00\x06\x00", "doc.docx").is_valid
            is True
        )

    def test_permissive_default_still_tolerates_a_mismatch(self, caplog):
        import logging
        validator = FileValidator()

        with caplog.at_level(logging.WARNING):
            result = validator.validate(b"MZ executable bytes", "evil.pdf")

        assert result.is_valid is True
        assert any("Magic byte mismatch" in r.message for r in caplog.records)

    def test_strict_mode_does_not_break_signatureless_extensions(self):
        validator = FileValidator(strict_mode=True)

        assert (
            validator.validate(b"# Just markdown", "notes.md").is_valid is True
        )
        assert validator.validate(b"plain,text", "table.csv").is_valid is True

    def test_strict_mode_still_enforces_size_and_extension_first(self):
        validator = FileValidator(strict_mode=True, max_size_bytes=10)

        too_big = validator.validate(b"x" * 11 + b"%PDF", "big.pdf")
        bad_ext = validator.validate(b"%PDF", "virus.exe")
        empty = validator.validate(b"", "empty.pdf")

        assert too_big.error_code == "FILE_TOO_LARGE"
        assert bad_ext.error_code == "UNSUPPORTED_EXTENSION"
        assert empty.error_code == "FILE_EMPTY"

    def test_strict_mode_flag_is_stored(self):
        assert FileValidator().strict_mode is False
        assert FileValidator(strict_mode=True).strict_mode is True


class TestValidateUploadConvenience:
    """Test suite for the validate_upload convenience function."""

    def test_validate_upload_uses_default_validator(self):
        """Verify validate_upload uses the global default validator."""
        # Valid file
        result = validate_upload(b"%PDF-1.4", "test.pdf")
        assert result.is_valid is True
        
        # Invalid file (too large)
        large_data = b"x" * (MAX_FILE_SIZE_BYTES + 1)
        result = validate_upload(large_data, "huge.pdf")
        assert result.is_valid is False
        assert result.error_code == "FILE_TOO_LARGE"


class TestEpubAndCsvValidation:
    """Test suite for EPUB and CSV specific content validation."""

    def test_valid_epub_with_mimetype_passes(self):
        validator = FileValidator(strict_mode=True)
        # EPUB header (PK\x03\x04) with mimetype string
        epub_bytes = b"PK\x03\x04" + b"\x00" * 26 + b"mimetypeapplication/epub+zip"
        result = validator.validate(epub_bytes, "book.epub")
        assert result.is_valid is True

    def test_invalid_epub_header_fails(self):
        validator = FileValidator(strict_mode=True)
        # Mismatched magic header
        result = validator.validate(b"NOT_A_ZIP_HEADER", "book.epub")
        assert result.is_valid is False
        assert result.error_code == "MAGIC_BYTE_MISMATCH"

    def test_epub_missing_mimetype_fails(self):
        validator = FileValidator(strict_mode=True)
        # Header matches PK\x03\x04 but missing mimetype
        result = validator.validate(b"PK\x03\x04" + b"random zip contents without mimetype", "book.epub")
        assert result.is_valid is False
        assert result.error_code == "MAGIC_BYTE_MISMATCH"

    def test_valid_csv_passes(self):
        validator = FileValidator(strict_mode=True)
        csv_bytes = b"name,age,city\nAlice,30,New York\nBob,25,London\n"
        result = validator.validate(csv_bytes, "data.csv")
        assert result.is_valid is True

    def test_csv_with_binary_null_byte_fails(self):
        validator = FileValidator(strict_mode=True)
        bad_csv = b"col1,col2\nval1,\x00val2\n"
        result = validator.validate(bad_csv, "data.csv")
        assert result.is_valid is False
        assert result.error_code == "MAGIC_BYTE_MISMATCH"

    def test_csv_invalid_encoding_fails(self):
        validator = FileValidator(strict_mode=True)
        # Invalid UTF-8 sequence
        bad_utf8 = b"col1,col2\nval1,\xff\xfe\xfa\n"
        result = validator.validate(bad_utf8, "data.csv")
        assert result.is_valid is False
        assert result.error_code == "MAGIC_BYTE_MISMATCH"


def test_filename_with_null_byte_fails():
    """Verify that a filename containing a null byte fails validation immediately."""
    validator = FileValidator()
    result = validator.validate(b"%PDF-1.4", "exploit.pdf\x00.exe")
    assert result.is_valid is False
    assert result.error_code == "INVALID_FILENAME_CHARACTERS"
    assert "invalid characters" in result.error_message.lower()


def test_max_file_size_from_env(monkeypatch):
    """Verify that MAX_FILE_SIZE_BYTES respects MAX_UPLOAD_SIZE_MB env variable on reload."""
    import importlib
    import src.utils.file_validator as fv

    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "10")
    importlib.reload(fv)
    try:
        assert fv.MAX_FILE_SIZE_BYTES == 10 * 1024 * 1024
    finally:
        # Reset back to default
        monkeypatch.delenv("MAX_UPLOAD_SIZE_MB", raising=False)
        importlib.reload(fv)




