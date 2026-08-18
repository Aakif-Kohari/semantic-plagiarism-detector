import sqlite3

import pytest

from src.db.corpus_db import clear_all_data
from src.db.incidents import (
    _fetch_all_incidents,
    init_incident_db,
    sync_flagged_incidents,
)


@pytest.fixture(autouse=True)
def setup_teardown():
    init_incident_db()
    clear_all_data()
    yield
    clear_all_data()


def test_sync_flagged_incidents_bulk():
    flags = [
        {
            "doc_a": "doc1.pdf",
            "doc_b": "doc2.pdf",
            "similarity": 0.85,
            "severity": "High",
        },
        {
            "doc_a": "doc2.pdf",
            "doc_b": "doc3.pdf",
            "similarity": 0.45,
            "severity": "Low",
        },
        {
            "doc_a": "doc1.pdf",
            "doc_b": "doc3.pdf",
            "similarity": 0.95,
            "severity": "Critical",
        },
    ]

    # Bulk insert via executemany implementation
    sync_flagged_incidents(flags)

    # Verify records in database
    conn = sqlite3.connect(r"corpus.db")
    incidents = _fetch_all_incidents(conn)
    conn.close()

    assert len(incidents) == 3

    # Check if similarity scores correctly inserted
    scores = [inc["similarity_score"] for inc in incidents]
    assert 0.85 in scores
    assert 0.45 in scores
    assert 0.95 in scores


def test_sync_flagged_incidents_bulk_upsert():
    flags = [
        {
            "doc_a": "doc1.pdf",
            "doc_b": "doc2.pdf",
            "similarity": 0.50,
            "severity": "Medium",
        }
    ]
    sync_flagged_incidents(flags)

    conn = sqlite3.connect(r"corpus.db")
    assert len(_fetch_all_incidents(conn)) == 1
    conn.close()

    # Update the existing record with new similarity
    flags_update = [
        {
            "doc_a": "doc1.pdf",
            "doc_b": "doc2.pdf",
            "similarity": 0.99,
            "severity": "Critical",
        }
    ]
    sync_flagged_incidents(flags_update)

    conn = sqlite3.connect(r"corpus.db")
    incidents = _fetch_all_incidents(conn)
    conn.close()

    assert len(incidents) == 1
    assert incidents[0]["similarity_score"] == 0.99
    assert incidents[0]["severity_rank"] == "High"


def test_sync_flagged_incidents_bulk_invalid():
    # Test skipping invalid pairs
    flags = [
        {"doc_a": "doc1.pdf", "doc_b": "doc1.pdf", "similarity": 1.0},  # Same doc
        {"doc_a": "", "doc_b": "doc2.pdf", "similarity": 0.8},  # Missing doc A
        {
            "doc_a": "doc1.pdf",
            "doc_b": "doc2.pdf",
            "similarity": 0.85,
        },  # Valid incident
    ]
    sync_flagged_incidents(flags)

    conn = sqlite3.connect(r"corpus.db")
    incidents = _fetch_all_incidents(conn)
    conn.close()

    assert len(incidents) == 1
    assert incidents[0]["document_a"] == "doc1.pdf"
    assert incidents[0]["document_b"] == "doc2.pdf"


def test_sync_flagged_incidents_validates_date_flagged_format():
    """Ensure valid ISO 8601 strings are preserved while invalid/missing dates fallback to current timestamp."""
    valid_iso = "2024-05-10T14:30:00+00:00"
    valid_z_iso = "2024-06-15T09:00:00Z"
    flags = [
        {
            "doc_a": "doc1.pdf",
            "doc_b": "doc2.pdf",
            "similarity": 0.85,
            "date_flagged": valid_iso,
        },
        {
            "doc_a": "doc2.pdf",
            "doc_b": "doc3.pdf",
            "similarity": 0.75,
            "date_flagged": valid_z_iso,
        },
        {
            "doc_a": "doc1.pdf",
            "doc_b": "doc3.pdf",
            "similarity": 0.90,
            "date_flagged": "invalid-non-iso-date",
        },
        {
            "doc_a": "doc3.pdf",
            "doc_b": "doc4.pdf",
            "similarity": 0.65,
            # date_flagged missing
        },
    ]

    results = sync_flagged_incidents(flags)
    assert len(results) == 4

    result_by_pair = {f"{r['document_a']}-{r['document_b']}": r for r in results}

    # Valid ISO strings preserved
    assert result_by_pair["doc1.pdf-doc2.pdf"]["date_flagged"] == valid_iso
    assert result_by_pair["doc2.pdf-doc3.pdf"]["date_flagged"] == valid_z_iso

    # Invalid / missing dates auto-populated with valid ISO timestamp
    invalid_date = result_by_pair["doc1.pdf-doc3.pdf"]["date_flagged"]
    missing_date = result_by_pair["doc3.pdf-doc4.pdf"]["date_flagged"]

    assert invalid_date != "invalid-non-iso-date"
    assert "T" in invalid_date
    assert "T" in missing_date

