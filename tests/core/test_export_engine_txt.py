from src.core.export_engine import LMSExportEngine


def test_generate_incident_txt_empty_returns_none():
    assert LMSExportEngine.generate_incident_txt([]) is None


def test_generate_incident_txt_formats_flagged_pairs():
    incidents = [
        {
            "doc_a": "student1.pdf",
            "doc_b": "student2.pdf",
            "similarity": 0.95,
        },
        {
            "doc_a": "essay.docx",
            "doc_b": "reference.txt",
            "similarity": 0.82,
        },
    ]

    report = LMSExportEngine.generate_incident_txt(incidents)

    assert report is not None
    assert report.startswith("SEMANTIC PLAGIARISM INCIDENT REPORT")
    assert "Total flagged pairs: 2" in report
    assert "Incident #1" in report
    assert "Document A: student1.pdf" in report
    assert "Document B: student2.pdf" in report
    assert "Similarity: 95.0% (0.9500)" in report
    assert "Severity: High" in report
    assert "Incident #2" in report
    assert "Similarity: 82.0% (0.8200)" in report
    assert "Severity: Medium" in report
    assert report.endswith("End of report\n")


def test_generate_incident_txt_handles_missing_keys():
    report = LMSExportEngine.generate_incident_txt(
        [
            {
                "doc_a": "known.pdf",
            }
        ]
    )

    assert report is not None
    assert "Document A: known.pdf" in report
    assert "Document B: Unknown" in report
    assert "Similarity: 0.0% (0.0000)" in report
    assert "Severity: Low" in report


def test_generate_incident_txt_includes_optional_details():
    report = LMSExportEngine.generate_incident_txt(
        [
            {
                "doc_a": "a.pdf",
                "doc_b": "b.pdf",
                "similarity": 0.91,
                "matched_length": 42,
                "matched_text": "A matching paragraph.",
            }
        ]
    )

    assert report is not None
    assert "Matched length: 42 words" in report
    assert "Matching text:" in report
    assert "A matching paragraph." in report


def test_generate_incident_txt_preserves_unicode():
    report = LMSExportEngine.generate_incident_txt(
        [
            {
                "doc_a": "निबंध.pdf",
                "doc_b": "résumé.txt",
                "similarity": 0.88,
            }
        ]
    )

    assert report is not None
    assert "निबंध.pdf" in report
    assert "résumé.txt" in report


def test_generate_incident_txt_invalid_similarity_returns_none():
    report = LMSExportEngine.generate_incident_txt(
        [
            {
                "doc_a": "a.pdf",
                "doc_b": "b.pdf",
                "similarity": "not-a-number",
            }
        ]
    )

    assert report is None


def test_generate_incident_txt_includes_date_flagged_and_threshold():
    report = LMSExportEngine.generate_incident_txt(
        [
            {
                "doc_a": "a.pdf",
                "doc_b": "b.pdf",
                "similarity": 0.85,
                "date_flagged": "2024-06-01T12:00:00",
                "threshold_at_time_of_flag": 0.59,
            }
        ]
    )

    assert report is not None
    assert "Date flagged: 2024-06-01T12:00:00" in report
    assert "Threshold at time of flag: 0.59" in report


def test_generate_incident_txt_omits_audit_fields_when_absent():
    report = LMSExportEngine.generate_incident_txt(
        [{"doc_a": "a.pdf", "doc_b": "b.pdf", "similarity": 0.75}]
    )

    assert report is not None
    assert "Date flagged:" not in report
    assert "Threshold at time of flag:" not in report
