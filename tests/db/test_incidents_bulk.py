"""
tests/db/test_incidents_bulk.py
-------------------------------
Bulk operation tests for the plagiarism incidents database.

Refactored to use the centralized db_connection pytest fixture (Issue #2725),
eliminating duplicated sqlite3.connect() and conn.close() boilerplate.
"""

import pytest
import sqlite3
from datetime import datetime


class TestBulkIncidentInsertion:
    """Test suite for bulk inserting plagiarism incidents."""

    def test_bulk_insert_100_incidents(self, db_connection: sqlite3.Connection):
        """Verify 100 incidents can be inserted in a single transaction."""
        incidents = [
            (
                f"BULK-{i:05d}",
                f"doc_a_{i}.pdf",
                f"doc_b_{i}.pdf",
                0.75,
                "Medium",
                datetime.utcnow().isoformat(),
                0.59,
                "Pending",
            )
            for i in range(100)
        ]

        db_connection.executemany(
            """
            INSERT INTO plagiarism_incidents 
            (incident_id, document_a, document_b, similarity, severity, timestamp, threshold_at_time_of_flag, review_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            incidents,
        )
        db_connection.commit()

        cursor = db_connection.execute("SELECT COUNT(*) FROM plagiarism_incidents")
        count = cursor.fetchone()[0]

        assert count == 100

    def test_bulk_insert_rollback_on_duplicate(self, db_connection: sqlite3.Connection):
        """Verify transaction rolls back if a duplicate incident_id is encountered."""
        # Insert first incident
        db_connection.execute(
            """
            INSERT INTO plagiarism_incidents 
            (incident_id, document_a, document_b, similarity, severity, timestamp, threshold_at_time_of_flag, review_status)
            VALUES ('DUP-001', 'a.pdf', 'b.pdf', 0.90, 'High', '2024-01-01', 0.59, 'Pending')
            """
        )
        db_connection.commit()

        # Attempt bulk insert with duplicate
        incidents = [
            ("DUP-002", "c.pdf", "d.pdf", 0.80, "High", "2024-01-02", 0.59, "Pending"),
            (
                "DUP-001",
                "e.pdf",
                "f.pdf",
                0.85,
                "High",
                "2024-01-03",
                0.59,
                "Pending",
            ),  # Duplicate
        ]

        with pytest.raises(sqlite3.IntegrityError):
            db_connection.executemany(
                """
                INSERT INTO plagiarism_incidents 
                (incident_id, document_a, document_b, similarity, severity, timestamp, threshold_at_time_of_flag, review_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                incidents,
            )
            db_connection.commit()

        # Verify only the original incident exists
        cursor = db_connection.execute("SELECT COUNT(*) FROM plagiarism_incidents")
        assert cursor.fetchone()[0] == 1

    def test_bulk_update_review_status(
        self, populated_db_connection: sqlite3.Connection
    ):
        """Verify bulk updating review status for all pending incidents."""
        conn = populated_db_connection

        # Update all pending to reviewed
        cursor = conn.execute(
            """
            UPDATE plagiarism_incidents 
            SET review_status = 'Reviewed' 
            WHERE review_status = 'Pending'
            """
        )
        conn.commit()

        assert cursor.rowcount == 50

        # Verify no pending remain
        cursor = conn.execute(
            "SELECT COUNT(*) FROM plagiarism_incidents WHERE review_status = 'Pending'"
        )
        assert cursor.fetchone()[0] == 0


class TestBulkIncidentDeletion:
    """Test suite for bulk deleting incidents."""

    def test_bulk_delete_by_severity(self, populated_db_connection: sqlite3.Connection):
        """Verify bulk deletion of all Low severity incidents."""
        conn = populated_db_connection

        # Count Low severity before deletion
        cursor = conn.execute(
            "SELECT COUNT(*) FROM plagiarism_incidents WHERE severity = 'Low'"
        )
        low_count_before = cursor.fetchone()[0]

        # Delete all Low severity
        cursor = conn.execute("DELETE FROM plagiarism_incidents WHERE severity = 'Low'")
        conn.commit()

        assert cursor.rowcount == low_count_before

        # Verify none remain
        cursor = conn.execute(
            "SELECT COUNT(*) FROM plagiarism_incidents WHERE severity = 'Low'"
        )
        assert cursor.fetchone()[0] == 0

    def test_bulk_delete_older_than_date(
        self, populated_db_connection: sqlite3.Connection
    ):
        """Verify bulk deletion of incidents older than a specific date."""
        conn = populated_db_connection
        cutoff_date = "2024-01-15T00:00:00"

        cursor = conn.execute(
            "DELETE FROM plagiarism_incidents WHERE timestamp < ?", (cutoff_date,)
        )
        conn.commit()

        # Verify all remaining are >= cutoff
        cursor = conn.execute("SELECT MIN(timestamp) FROM plagiarism_incidents")
        min_timestamp = cursor.fetchone()[0]

        assert min_timestamp >= cutoff_date
