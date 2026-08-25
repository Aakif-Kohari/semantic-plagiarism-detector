import inspect
import io
from datetime import datetime, timezone

import openpyxl
import pandas as pd

from src.utils.bulk_export import export_incidents_xlsx_stream
from src.utils.excel_export import (
    build_similarity_workbook,
    export_similarity_matrix_to_excel,
    generate_csv_matrix_stream,
)


def test_generate_csv_matrix_stream():
    # Setup test DataFrame
    data = {
        "DocA.txt": [1.0, 0.85, 0.12],
        "DocB.txt": [0.85, 1.0, 0.45],
        "DocC.txt": [0.12, 0.45, 1.0],
    }
    df = pd.DataFrame(data, index=["DocA.txt", "DocB.txt", "DocC.txt"])

    # Test 1: Return type is a Generator
    stream = generate_csv_matrix_stream(df)
    assert inspect.isgenerator(stream)

    # Test 2: Verify chunk output
    chunks = list(stream)
    assert len(chunks) == len(df) + 1  # 1 header row + 3 data rows

    # Verify header line
    assert chunks[0].strip() == "Document,DocA.txt,DocB.txt,DocC.txt"

    # Verify data lines
    assert chunks[1].strip() == "DocA.txt,1.0,0.85,0.12"
    assert chunks[2].strip() == "DocB.txt,0.85,1.0,0.45"
    assert chunks[3].strip() == "DocC.txt,0.12,0.45,1.0"

    # Test 3: Verify complete CSV reconstruction matches Expected CSV output
    full_csv = "".join(chunks)
    reconstructed_df = pd.read_csv(io.StringIO(full_csv), index_col=0)
    pd.testing.assert_frame_equal(df, reconstructed_df, check_names=False)


def test_build_similarity_workbook_metadata_properties():
    """Verify build_similarity_workbook populates document title, creator, and created timestamp (#3438)."""
    df = pd.DataFrame({"Doc1.txt": [1.0]}, index=["Doc1.txt"])
    before = datetime.now(timezone.utc)
    wb = build_similarity_workbook(df)
    after = datetime.now(timezone.utc)

    assert wb.properties.title == "Semantic Plagiarism Similarity Report"
    assert wb.properties.creator == "Semantic Plagiarism Detector"
    assert wb.properties.created is not None
    assert isinstance(wb.properties.created, datetime)
    assert before <= wb.properties.created <= after


def test_export_similarity_matrix_to_excel_persists_metadata():
    """Verify export_similarity_matrix_to_excel persists metadata in the saved XLSX file (#3438)."""
    df = pd.DataFrame(
        {"DocA.txt": [1.0, 0.8], "DocB.txt": [0.8, 1.0]},
        index=["DocA.txt", "DocB.txt"],
    )
    xlsx_bytes = export_similarity_matrix_to_excel(df)
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 0

    # Load back with openpyxl to inspect file properties
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    assert wb.properties.title == "Semantic Plagiarism Similarity Report"
    assert wb.properties.creator == "Semantic Plagiarism Detector"
    assert wb.properties.created is not None


def test_export_incidents_xlsx_stream_persists_metadata():
    """Verify export_incidents_xlsx_stream sets title, creator, and created metadata (#3438)."""
    incidents = [
        {
            "incident_id": "INC-001",
            "document_a": "Essay1.docx",
            "document_b": "Essay2.docx",
            "similarity_score": 0.88,
            "severity_rank": "High",
            "review_status": "Pending",
            "date_flagged": "2026-08-25",
        }
    ]
    xlsx_bytes = export_incidents_xlsx_stream(incidents)
    assert isinstance(xlsx_bytes, bytes)

    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    assert wb.properties.title == "Semantic Plagiarism Similarity Report"
    assert wb.properties.creator == "Semantic Plagiarism Detector"
    assert wb.properties.created is not None

