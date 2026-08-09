"""Utility for parsing files and extracting metadata."""

import fitz


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
