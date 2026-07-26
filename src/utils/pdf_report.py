"""
pdf_report.py
-------------
Generates professional PDF plagiarism reports using ReportLab.
Provides side-by-side comparison of suspicious paragraph pairs with visual similarity indicators.
"""

import os
from datetime import datetime
from io import BytesIO
from typing import List, Optional, Tuple

import fitz  # PyMuPDF
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def truncate_filename(filename: str, max_len: int = 30) -> str:
    """
    Truncates a filename to max_len characters with an ellipsis if needed,
    preserving its file extension.
    Example: 'final_essay_v2_final_really_final_draft_john_smith.pdf' -> 'final_essay_v2_f...h.pdf'
    """
    if len(filename) <= max_len:
        return filename

    name, ext = os.path.splitext(filename)
    needed_len = max_len - len(ext) - 3

    if needed_len <= 2:
        return filename[: max_len - 3] + "..."

    half = needed_len // 2
    truncated_name = f"{name[:half]}...{name[-(needed_len - half):]}"
    return f"{truncated_name}{ext}"


def get_similarity_color(score: float) -> HexColor:
    """
    Returns a color based on similarity score.
    - High (≥0.90): Red
    - Medium (≥0.75): Orange
    - Low (<0.75): Green
    """
    if score >= 0.90:
        return HexColor("#ff4b4b")
    elif score >= 0.75:
        return HexColor("#ffa500")
    else:
        return HexColor("#21c55d")


def wrap_text(text: str, max_chars: int = 400) -> str:
    """
    Truncates text to max_chars and adds ellipsis if needed.
    Helps prevent text overflow in PDF cells.
    """
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def generate_plagiarism_report(
    doc_a: str,
    doc_b: str,
    overall_similarity: float,
    threshold: float,
    top_pairs: List[Tuple[str, str, float]],
    report_title: str = "Plagiarism Detection Report",
    logo_image: Optional[bytes] = None,
    brand_color: Optional[str] = None,
) -> BytesIO:
    brand_hex = brand_color or "#1e3a8a"
    brand_clr = HexColor(brand_hex)

    logo_height = 0
    if logo_image:
        try:
            reader = ImageReader(BytesIO(logo_image))
            iw, ih = reader.getSize()
            logo_display_w = 1.5 * inch
            logo_display_h = logo_display_w * ih / iw
            logo_height = logo_display_h + 0.25 * inch
        except Exception:
            logo_height = 0

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72 + logo_height,
        bottomMargin=18,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=brand_clr,
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=brand_clr,
        spaceAfter=12,
        spaceBefore=20,
    )
    normal_style = styles["Normal"]
    normal_style.fontSize = 10
    normal_style.leading = 14

    def _draw_header(canvas_obj, _doc):
        if not logo_image:
            return
        canvas_obj.saveState()
        try:
            reader = ImageReader(BytesIO(logo_image))
            iw, ih = reader.getSize()
            logo_display_w = 1.5 * inch
            logo_display_h = logo_display_w * ih / iw
            x = _doc.leftMargin
            y = _doc.pagesize[1] - 36 - logo_display_h
            canvas_obj.drawImage(
                reader,
                x,
                y,
                width=logo_display_w,
                height=logo_display_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass
        canvas_obj.restoreState()

    story = []

    story.append(Paragraph(report_title, title_style))
    story.append(Spacer(1, 0.2 * inch))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    story.append(Paragraph(f"<b>Generated:</b> {timestamp}", normal_style))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("Document Comparison", heading_style))

    doc_data = [
        ["Document A", truncate_filename(doc_a, 40)],
        ["Document B", truncate_filename(doc_b, 40)],
        ["Overall Similarity", f"{overall_similarity:.1%}"],
        ["Detection Threshold", f"{threshold:.1%}"],
    ]

    doc_table = Table(doc_data, colWidths=[2 * inch, 4 * inch], hAlign=TA_LEFT)
    doc_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), HexColor("#f3f4f6")),
                ("TEXTCOLOR", (0, 0), (0, -1), HexColor("#374151")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )
    story.append(doc_table)
    story.append(Spacer(1, 0.3 * inch))

    sim_color = get_similarity_color(overall_similarity)
    story.append(Paragraph("Similarity Score Visualization", heading_style))

    bar_width = overall_similarity * 100
    bar_data = [
        ["", ""],
        ["", ""],
    ]
    bar_table = Table(
        bar_data,
        colWidths=[bar_width / 100 * 5 * inch, (100 - bar_width) / 100 * 5 * inch],
        hAlign=TA_LEFT,
    )
    bar_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), sim_color),
                ("BACKGROUND", (1, 0), (1, -1), HexColor("#e5e7eb")),
                ("HEIGHT", (0, 0), (-1, -1), 20),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(bar_table)
    story.append(Paragraph(f"{overall_similarity:.1%}", normal_style))
    story.append(Spacer(1, 0.3 * inch))

    if top_pairs:
        story.append(Paragraph("Top Suspicious Paragraph Pairs", heading_style))
        story.append(
            Paragraph(
                f"Showing top {len(top_pairs)} most similar paragraph pairs above threshold.",
                normal_style,
            )
        )
        story.append(Spacer(1, 0.1 * inch))

        for rank, (chunk_a, chunk_b, score) in enumerate(top_pairs, 1):
            pair_color = get_similarity_color(score)
            pair_header = Paragraph(
                f"<b>Pair #{rank}</b> — Similarity: <font color='{pair_color}'>{score:.1%}</font>",
                ParagraphStyle(
                    "PairHeader",
                    parent=styles["Heading3"],
                    fontSize=11,
                    textColor=HexColor("#1f2937"),
                    spaceAfter=8,
                    spaceBefore=15,
                ),
            )
            story.append(pair_header)

            wrapped_a = wrap_text(chunk_a, max_chars=500)
            wrapped_b = wrap_text(chunk_b, max_chars=500)

            pair_data = [
                [f"<b>From {truncate_filename(doc_a, 25)}:</b>", f"<b>From {truncate_filename(doc_b, 25)}:</b>"],
                [wrapped_a, wrapped_b],
            ]

            pair_table = Table(
                pair_data, colWidths=[2.5 * inch, 2.5 * inch], hAlign=TA_LEFT
            )
            pair_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#f9fafb")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#111827")),
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story.append(pair_table)
            story.append(Spacer(1, 0.15 * inch))

            if rank == 3 and len(top_pairs) > 3:
                story.append(PageBreak())
    else:
        story.append(
            Paragraph(
                "No suspicious paragraph pairs found above threshold.", normal_style
            )
        )

    story.append(PageBreak())
    story.append(Paragraph("Report Notes", heading_style))
    story.append(
        Paragraph(
            "This report was generated by the Semantic Plagiarism Detection System. "
            "Similarity scores are computed using transformer embeddings (all-MiniLM-L6-v2) "
            "and cosine similarity. High similarity scores may indicate plagiarism, "
            "but human review is recommended for final determination.",
            normal_style,
        )
    )
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            f"Threshold used: {threshold:.1%}. Pairs with similarity below this threshold are not shown.",
            normal_style,
        )
    )

    doc.build(story, onFirstPage=_draw_header, onLaterPages=_draw_header)
    buffer.seek(0)
    return buffer


def highlight_pdf_matches(
    pdf_source: str | bytes,
    matching_chunks: List[str],
    highlight_color: Tuple[float, float, float] = (1.0, 0.85, 0.0),
) -> bytes:
    if isinstance(pdf_source, bytes):
        doc = fitz.open(stream=pdf_source, filetype="pdf")
    else:
        doc = fitz.open(pdf_source)

    for page in doc:
        for chunk in matching_chunks:
            chunk_clean = str(chunk).strip()
            if len(chunk_clean) < 3:
                continue

            quad_matches = page.search_for(chunk_clean)
            for rect in quad_matches:
                annot = page.add_highlight_annot(rect)
                annot.set_colors(stroke=highlight_color)
                annot.update()

    output_bytes = doc.tobytes()
    doc.close()
    return output_bytes