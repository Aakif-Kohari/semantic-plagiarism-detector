"""Tests for src/utils/pdf_report.py PDF plagiarism report generation."""

from io import BytesIO
from PyPDF2 import PdfReader

from src.utils.pdf_report import (
    generate_plagiarism_report,
    get_similarity_color,
    wrap_text,
)


def _read_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_generates_valid_pdf_with_required_fields():
    pdf_buffer = generate_plagiarism_report(
        doc_a="student_a.pdf",
        doc_b="student_b.pdf",
        overall_similarity=0.934,
        threshold=0.59,
        top_pairs=[
            ("First matching paragraph.", "Second matching paragraph.", 0.96),
        ],
    )
    pdf_bytes = pdf_buffer.getvalue()

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000

    text = _read_text(pdf_bytes)
    assert "student_a.pdf" in text
    assert "student_b.pdf" in text
    assert "93.4%" in text
    assert "First matching paragraph" in text


def test_generates_pdf_with_qr_code():
    pdf_buffer = generate_plagiarism_report(
        doc_a="student_a.pdf",
        doc_b="student_b.pdf",
        overall_similarity=0.934,
        threshold=0.59,
        top_pairs=[
            ("First matching paragraph.", "Second matching paragraph.", 0.96),
        ],
        incident_id="INC-QR-12345"
    )
    pdf_bytes = pdf_buffer.getvalue()

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000

    text = _read_text(pdf_bytes)
    assert "student_a.pdf" in text


def test_wrap_text_truncates_long_strings():
    short = "Hello world"
    assert wrap_text(short, max_chars=20) == "Hello world"

    long_str = "A" * 100
    wrapped = wrap_text(long_str, max_chars=20)
    assert len(wrapped) == 20
    assert wrapped.endswith("...")


def test_similarity_color_palette():
    high_color = get_similarity_color(0.95)
    medium_color = get_similarity_color(0.80)
    low_color = get_similarity_color(0.50)

    assert high_color.hexval().lower() == "0xff4b4b"
    assert medium_color.hexval().lower() == "0xffa500"
    assert low_color.hexval().lower() == "0x21c55d"
