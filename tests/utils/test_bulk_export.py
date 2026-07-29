import io
import json
import zipfile

from src.utils.bulk_export import generate_bulk_reports_zip


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


def test_generate_bulk_reports_zip_with_progress_bar():
    from unittest.mock import Mock

    flags = [
        {
            "doc1": "Alice.pdf",
            "doc2": "Bob.docx",
            "similarity_score": 0.85,
            "matched_chunks": [],
        },
        {
            "doc1": "Charlie.txt",
            "doc2": "Dave.pdf",
            "similarity_score": 0.95,
            "matched_chunks": ["chunk1"],
        },
    ]

    mock_pb = Mock()

    generate_bulk_reports_zip(flags, progress_bar=mock_pb)

    assert mock_pb.progress.call_count == 4

    mock_pb.progress.assert_any_call(
        1.0,
        text="ZIP archive ready!",
    )