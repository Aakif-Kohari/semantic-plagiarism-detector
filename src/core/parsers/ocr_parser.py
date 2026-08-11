"""src/core/parsers/ocr_parser.py - Optical Character Recognition (OCR) strategies."""

import io
import logging
import os
from src.core.parsers.common import DEFAULT_OCR_DPI, DEFAULT_OCR_LANGUAGE, PDFInput

logger = logging.getLogger(__name__)


class OCRDependencyError(RuntimeError):
    """Raised when Tesseract or system dependencies required for OCR are missing."""
    pass


def _configure_tesseract(pytesseract_module) -> None:
    """Use an optional explicit Tesseract path on Windows or other systems."""
    configured_path = os.getenv("TESSERACT_CMD", "").strip()
    if configured_path:
        pytesseract_module.pytesseract.tesseract_cmd = configured_path


def _is_blank_scanned_page(
    pdf_bytes: bytes,
    page_index: int,
    *,
    dpi: int = DEFAULT_OCR_DPI,
    variance_threshold: float = 5.0,
) -> bool:
    """Return True if a rendered page looks blank (very low pixel variance)."""
    try:
        import fitz
        from PIL import Image
    except ImportError:
        return False

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            page = document.load_page(page_index)
            scale = dpi / 72
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(scale, scale),
                alpha=False,
            )
            image = Image.frombytes(
                "RGB",
                (pixmap.width, pixmap.height),
                pixmap.samples,
            ).convert("L")

        histogram = image.histogram()
        pixel_count = image.width * image.height
        if pixel_count == 0:
            return True

        mean = sum(i * count for i, count in enumerate(histogram)) / pixel_count
        variance = (
            sum(count * ((i - mean) ** 2) for i, count in enumerate(histogram))
            / pixel_count
        )
        return variance < variance_threshold
    except Exception as exc:
        logger.error(f"[document_parser] Error checking blank page {page_index}: {exc}")
        return False


def _ocr_pdf_page(
    pdf_bytes: bytes,
    page_index: int,
    *,
    dpi: int = DEFAULT_OCR_DPI,
    language: str = DEFAULT_OCR_LANGUAGE,
) -> str:
    """Render one PDF page and extract text with Tesseract."""
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        from src.errors import OCR_DEPENDENCIES_MISSING
        raise OCRDependencyError(OCR_DEPENDENCIES_MISSING) from exc

    _configure_tesseract(pytesseract)

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            page = document.load_page(page_index)
            scale = dpi / 72
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(scale, scale),
                alpha=False,
            )
            image = Image.frombytes(
                "RGB",
                (pixmap.width, pixmap.height),
                pixmap.samples,
            )
            return pytesseract.image_to_string(
                image,
                lang=language,
                config="--oem 3 --psm 3",
            ).strip()
    except Exception as exc:
        logger.error(f"[document_parser] OCR page extraction failed: {exc}")
        return ""


def extract_text_from_image(
    file: PDFInput, *, ocr_language: str = DEFAULT_OCR_LANGUAGE
) -> str:
    """Extract text from an image (PNG, JPG) using Tesseract OCR."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        from src.errors import OCR_DEPENDENCIES_MISSING
        raise OCRDependencyError(OCR_DEPENDENCIES_MISSING) from exc

    _configure_tesseract(pytesseract)

    from src.core.parsers.pdf_parser import _read_pdf_bytes
    file_bytes = _read_pdf_bytes(file)
    try:
        image = Image.open(io.BytesIO(file_bytes))
        try:
            return pytesseract.image_to_string(
                image,
                lang=ocr_language,
                config="--oem 3 --psm 3",
            ).strip()
        except (MemoryError, Exception) as exc:
            if isinstance(exc, MemoryError):
                logger.warning(
                    f"[document_parser] OCR image extraction failed due to memory exhaustion: {exc}"
                )
            else:
                logger.warning(f"[document_parser] OCR image extraction failed: {exc}")
            return "[OCR extraction failed for the file]"
    except pytesseract.TesseractNotFoundError as exc:
        from src.errors import OCR_TESSERACT_NOT_FOUND
        raise OCRDependencyError(OCR_TESSERACT_NOT_FOUND) from exc
    except Exception as exc:
        logger.error(f"[document_parser] Error reading image: {exc}")
        return ""
