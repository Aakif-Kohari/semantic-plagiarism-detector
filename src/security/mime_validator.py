import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Strict mapping of file extension to allowed MIME types/signatures
ALLOWED_MIME_TYPES = {
    "pdf": {"application/pdf"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
    "doc": {
        "application/msword",
        "application/vnd.ms-office",
        "application/octet-stream",
    },
    "zip": {"application/zip", "application/x-zip-compressed", "application/octet-stream"},
    "txt": {"text/plain", "text/x-python", "text/markdown"},
    "csv": {"text/csv", "text/plain", "application/csv"},
    "md": {"text/markdown", "text/plain", "application/octet-stream"},
    "rtf": {"application/rtf", "text/rtf", "text/plain"},
    "epub": {"application/epub+zip", "application/zip", "application/octet-stream"},
    "odt": {
        "application/vnd.oasis.opendocument.text",
        "application/zip",
        "application/octet-stream",
    },
    "png": {"image/png"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
}

# Fallback headers checking if python-magic is unavailable or has issues
ALLOWED_MAGIC_HEADERS = {
    "pdf": [b"%PDF-"],
    "docx": [b"PK\x03\x04"],
    "zip": [b"PK\x03\x04"],
    "epub": [b"PK\x03\x04"],
    "odt": [b"PK\x03\x04"],
    "doc": [b"\xd0\xcf\x11\xe0"],
    "rtf": [b"{\\rtf"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
}


def _check_magic_bytes(file_bytes: bytes, extension: str, filename: str) -> Optional[bool]:
    """Attempt MIME type validation using python-magic.

    Returns:
        True: MIME type is verified and valid.
        False: Mismatch detected; explicit validation failure.
        None: python-magic failed or is unavailable; caller should trigger fallback.
    """
    try:
        import magic

        mime_type = magic.from_buffer(file_bytes, mime=True)
        if mime_type:
            mime_type_clean = mime_type.split(";")[0].strip().lower()
            allowed = ALLOWED_MIME_TYPES[extension]

            if mime_type_clean in allowed:
                return True

            if mime_type_clean.startswith("text/") and extension in {"txt", "csv", "md", "rtf"}:
                return True

            logger.warning(
                f"[mime_validator] Security warning: MIME type mismatch for '{filename}'. "
                f"Expected one of {allowed}, got '{mime_type_clean}'."
            )
            return False
    except (ImportError, ModuleNotFoundError) as e:
        logger.debug(f"[mime_validator] python-magic not installed, falling back to header validation: {e}")
        return None
    except Exception as e:
        logger.debug(f"[mime_validator] python-magic execution failed, falling back to header validation: {e}")
        return None

    return None


def _check_extension_fallback(file_bytes: bytes, extension: str, filename: str) -> bool:
    """Fallback validation checking binary header magic bytes or text encoding."""
    if extension in ALLOWED_MAGIC_HEADERS:
        headers = ALLOWED_MAGIC_HEADERS[extension]
        for header in headers:
            if file_bytes.lstrip().startswith(header):
                return True
        logger.warning(f"[mime_validator] Security warning: Fallback magic bytes check failed for '{filename}'.")
        return False

    if extension in {"txt", "csv", "md"}:
        if b"\x00" in file_bytes:
            logger.warning(
                f"[mime_validator] Security warning: Text validation check failed for '{filename}' "
                f"(contains binary null bytes)."
            )
            return False

        for encoding in ("utf-8", "utf-16"):
            try:
                file_bytes.decode(encoding, errors="strict")
                return True
            except UnicodeDecodeError:
                continue

        logger.warning(
            f"[mime_validator] Security warning: Text validation check failed for '{filename}' "
            f"(not valid UTF-8/UTF-16)."
        )
        return False

    return False


def validate_mime_type(file_bytes: bytes, filename: str) -> bool:
    """Validate uploaded file bytes against allowed MIME signatures based on file extension.

    Returns True if valid, False otherwise.
    """
    if not file_bytes:
        return False

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if not extension or extension not in ALLOWED_MIME_TYPES:
        logger.warning(f"[mime_validator] Security check: Unsupported file extension '{extension}' for file '{filename}'.")
        return False

    magic_result = _check_magic_bytes(file_bytes, extension, filename)
    if magic_result is not None:
        return magic_result

    return _check_extension_fallback(file_bytes, extension, filename)
