from src.core.export_engine import LMSExportEngine


def test_generate_incident_html_empty():
    """Verify that an empty list of incidents returns None."""
    result = LMSExportEngine.generate_incident_html([])
    assert result is None


def test_generate_incident_html_valid():
    """Verify that a valid list of incidents produces the expected HTML content."""
    incidents = [
        {"doc_a": "essay1.txt", "doc_b": "essay2.txt", "similarity": 0.95},
        {"doc_a": "report_a.pdf", "doc_b": "report_b.pdf", "similarity": 0.85},
        {"doc_a": "doc_x.docx", "doc_b": "doc_y.docx", "similarity": 0.70},
    ]

    html_content = LMSExportEngine.generate_incident_html(incidents)
    assert html_content is not None
    assert isinstance(html_content, str)

    # Verify key structure elements
    assert "<!DOCTYPE html>" in html_content
    assert "Plagiarism Incident Report" in html_content
    assert "Total flagged pairs: 3" in html_content

    # Verify doc names are present
    assert "essay1.txt" in html_content
    assert "report_b.pdf" in html_content
    assert "doc_x.docx" in html_content

    # Verify similarity percentages
    assert "95.0%" in html_content
    assert "85.0%" in html_content
    assert "70.0%" in html_content

    # Verify severity ranks and styling colors are present
    assert "CRITICAL" in html_content
    assert "HIGH" in html_content
    assert "MODERATE" in html_content
    assert "#ff4b4b" in html_content  # CRITICAL color
    assert "#ffa500" in html_content  # HIGH color
    assert "#21c55d" in html_content  # MODERATE color
