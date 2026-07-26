"""Application-level environment configuration."""

from __future__ import annotations

import os
from typing import Final


DEFAULT_APP_TITLE: Final[str] = (
    "Semantic Plagiarism Detection System"
)
DEFAULT_PDF_FOOTER_TEXT: Final[str] = ""


def get_app_title() -> str:
    """Return the configured application title.

    Empty or whitespace-only values fall back to the default so a
    malformed environment variable cannot leave the browser or page
    title blank.
    """
    configured_title = os.getenv("APP_TITLE", "").strip()
    return configured_title or DEFAULT_APP_TITLE


def get_pdf_footer_text() -> str:
    """Return the configured PDF footer text.

    Empty or whitespace-only values fall back to the default.
    """
    configured_footer = os.getenv("PDF_FOOTER_TEXT", "").strip()
    return configured_footer or DEFAULT_PDF_FOOTER_TEXT
