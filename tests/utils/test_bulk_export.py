import io
import json
import zipfile

from src.utils.bulk_export import export_incidents_csv_stream, generate_bulk_reports_zip


def test_generate_bulk_reports_zip():
    # Flags matching the bulk_export expected schema
    flags = [
        {
            "doc_a": "Alice.pdf",
            "doc_b": "Bob.docx",
            "similarity": 0.85,
            "threshold_at_time_of_flag": 0.5,
        },
        {
            "doc_a": "Charlie.txt",
            "doc_b": "Dave.pdf",
            "similarity": 0.95,
            "threshold_at_time_of_flag": 0.5,
        },
    ]

    # Use default arguments (include all artifact types)
    zip_bytes = generate_bulk_reports_zip(flags)
    assert isinstance(zip_bytes, bytes)

    # Inspect the zip archive
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        names = zf.namelist()
        # Expect two PDF reports, a summary CSV, and a metadata JSON file
        pdf_names = [n for n in names if n.lower().endswith(".pdf")]
        assert len(pdf_names) == 2

        # New export artifacts
        assert "summary.csv" in names
        assert "metadata.json" in names

        # Verify metadata JSON content
        meta_content = zf.read("metadata.json").decode("utf-8")
        meta = json.loads(meta_content)

        assert "generated_at" in meta
        assert "flags" in meta
        assert len(meta["flags"]) == 2

        input_set = {(f["doc_a"], f["doc_b"]) for f in flags}
        meta_set = {(f["doc_a"], f["doc_b"]) for f in meta["flags"]}
        assert input_set == meta_set


# ---------------------------------------------------------------------------
# Tests for export_incidents_csv_stream (Issue #942)
# ---------------------------------------------------------------------------

_SAMPLE_INCIDENTS = [
    {
        "incident_id": "INC-001",
        "document_a": "alice.pdf",
        "document_b": "bob.pdf",
        "similarity_score": 0.95,
        "severity_rank": "High",
        "review_status": "Pending",
        "date_flagged": "2024-01-15T10:00:00+00:00",
    },
    {
        "incident_id": "INC-002",
        "document_a": "charlie.docx",
        "document_b": "dave.docx",
        "similarity_score": 0.72,
        "severity_rank": "Medium",
        "review_status": "Reviewed",
        "date_flagged": "2024-01-16T08:30:00+00:00",
    },
]


def test_export_incidents_csv_stream_returns_bytes():
    """export_incidents_csv_stream must return UTF-8-SIG encoded bytes."""
    csv_bytes = export_incidents_csv_stream(_SAMPLE_INCIDENTS)

    assert isinstance(csv_bytes, bytes)
    # Must start with UTF-8 BOM (EF BB BF)
    assert csv_bytes.startswith(b"\xef\xbb\xbf")


def test_export_incidents_csv_stream_excel_compatibility():
    """Exported CSV must be readable by Excel on Windows (UTF-8-SIG with BOM)."""
    csv_bytes = export_incidents_csv_stream(_SAMPLE_INCIDENTS)

    # Verify UTF-8-SIG encoding (BOM + valid UTF-8)
    text = csv_bytes.decode("utf-8-sig")
    assert "INC-001" in text
    assert "alice.pdf" in text
    assert "95.00%" in text

    # Verify BOM is present at start (not in decoded text)
    assert csv_bytes[:3] == b"\xef\xbb\xbf"


def test_export_incidents_csv_stream_headers():
    """First row must contain all required column headers."""
    expected_headers = [
        "Incident ID",
        "Doc A",
        "Doc B",
        "Similarity",
        "Severity",
        "Status",
        "Date",
    ]

    csv_bytes = export_incidents_csv_stream(_SAMPLE_INCIDENTS)
    # Decode without BOM for CSV parsing
    text = csv_bytes.decode("utf-8-sig")
    first_line = text.splitlines()[0].strip()
    actual_headers = [h.strip() for h in first_line.split(",")]

    assert actual_headers == expected_headers


def test_export_incidents_csv_stream_row_values():
    """CSV rows must reflect incident field values with correct formatting."""
    import csv as _csv
    import io

    csv_bytes = export_incidents_csv_stream(_SAMPLE_INCIDENTS)
    text = csv_bytes.decode("utf-8-sig")
    reader = _csv.DictReader(io.StringIO(text))
    rows = list(reader)

    assert len(rows) == 2

    # First row
    assert rows[0]["Incident ID"] == "INC-001"
    assert rows[0]["Doc A"] == "alice.pdf"
    assert rows[0]["Doc B"] == "bob.pdf"
    assert rows[0]["Similarity"] == "95.00%"
    assert rows[0]["Severity"] == "High"
    assert rows[0]["Status"] == "Pending"
    assert rows[0]["Date"] == "2024-01-15T10:00:00+00:00"

    # Second row
    assert rows[1]["Incident ID"] == "INC-002"
    assert rows[1]["Similarity"] == "72.00%"
    assert rows[1]["Severity"] == "Medium"
    assert rows[1]["Status"] == "Reviewed"


def test_export_incidents_csv_stream_empty_list():
    """An empty incidents list should produce only the header row with BOM."""
    import csv as _csv
    import io

    csv_bytes = export_incidents_csv_stream([])
    assert csv_bytes.startswith(b"\xef\xbb\xbf")

    text = csv_bytes.decode("utf-8-sig")
    reader = _csv.DictReader(io.StringIO(text))
    rows = list(reader)

    assert rows == []
    # Rewind and confirm only one line (the header) exists
    lines = [line for line in text.splitlines() if line.strip()]
    assert len(lines) == 1


def test_export_incidents_csv_stream_non_numeric_similarity():
    """Non-numeric similarity_score should be written as-is without raising."""
    import csv as _csv
    import io

    incidents = [
        {
            "incident_id": "INC-X",
            "document_a": "a.pdf",
            "document_b": "b.pdf",
            "similarity_score": "N/A",
            "severity_rank": "Low",
            "review_status": "Pending",
            "date_flagged": "2024-01-17",
        }
    ]

    csv_bytes = export_incidents_csv_stream(incidents)
    assert csv_bytes.startswith(b"\xef\xbb\xbf")

    text = csv_bytes.decode("utf-8-sig")
    reader = _csv.DictReader(io.StringIO(text))
    rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["Similarity"] == "N/A"
