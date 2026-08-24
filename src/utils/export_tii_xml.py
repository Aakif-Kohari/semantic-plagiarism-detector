"""
src/utils/export_tii_xml.py
---------------------------
Export engine for Turnitin-compatible Originality XML reports.

Generates XML schemas containing document metadata, highlight coordinates,
and similarity scores that can be ingested by Turnitin or compatible
LMS platforms for archival and review.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def generate_tii_xml(report_data: dict[str, Any], include_text: bool = True) -> str:
    """Generate a Turnitin-compatible Originality XML report.

    Args:
        report_data: Dictionary containing:
            - 'document_id': Unique document identifier.
            - 'author': Author name.
            - 'title': Document title.
            - 'submission_date': ISO 8601 timestamp.
            - 'similarity_score': Overall similarity percentage (0-100).
            - 'matches': List of match dictionaries with 'source', 'score', 'start', 'end'.
            - 'text_content': Full text of the document (optional).
        include_text: Whether to include the full text in the XML.

    Returns:
        A formatted XML string.
    """
    root = ET.Element("originalityReport")
    root.set(
        "xmlns",
        "http://www.turnitin.com/static/resources/files/turnitin_sdk_v1p0p0.xsd",
    )
    root.set("version", "1.0.0")

    # Submission metadata
    submission = ET.SubElement(root, "submission")
    ET.SubElement(submission, "id").text = str(
        report_data.get("document_id", "unknown")
    )
    ET.SubElement(submission, "title").text = report_data.get("title", "Untitled")
    ET.SubElement(submission, "author").text = report_data.get("author", "Unknown")
    ET.SubElement(submission, "date").text = report_data.get(
        "submission_date", datetime.utcnow().isoformat()
    )

    # Overall score
    score_elem = ET.SubElement(submission, "overallSimilarity")
    score_elem.text = str(int(report_data.get("similarity_score", 0)))
    score_elem.set("unit", "percent")

    # Matches/Sources
    matches_elem = ET.SubElement(root, "matches")
    matches = report_data.get("matches", [])

    for match in matches:
        match_elem = ET.SubElement(matches_elem, "match")
        ET.SubElement(match_elem, "source").text = match.get("source", "Internet")
        ET.SubElement(match_elem, "score").text = str(int(match.get("score", 0)))

        # Highlight coordinates
        if "start" in match and "end" in match:
            highlight = ET.SubElement(match_elem, "highlight")
            highlight.set("start", str(match["start"]))
            highlight.set("end", str(match["end"]))

    # Full text (optional)
    if include_text and "text_content" in report_data:
        text_elem = ET.SubElement(root, "text")
        text_elem.text = report_data["text_content"]

    # Pretty print the XML
    rough_string = ET.tostring(root, encoding="unicode")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def validate_tii_xml(xml_string: str) -> bool:
    """Basic validation to ensure the XML is well-formed and contains required tags."""
    try:
        root = ET.fromstring(xml_string)
        if root.tag != "originalityReport":
            return False
        if root.find("submission") is None:
            return False
        if root.find("overallSimilarity") is None:
            return False
        return True
    except ET.ParseError:
        return False
