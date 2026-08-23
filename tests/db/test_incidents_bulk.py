import sqlite3
import pytest
from unittest.mock import patch

# --- Pytest Fixtures Layer ---

@pytest.fixture(scope="function")
def isolated_test_db():
    """
    Provides a transient, in-memory SQLite database session connection.
    Guarantees zero file leakage into the developer's working environment.
    """
    connection = sqlite3.connect(":memory:")
    # Initialize basic schema prerequisites required for the bulk worker test
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            severity TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    connection.commit()
    
    yield connection
    
    # Teardown hook: Close out connection securely
    connection.close()


# --- Refactored Test Suite ---

def test_incidents_bulk_insertion_pipeline(isolated_test_db):
    """
    Scenario: Validate bulk record operations execute completely inside 
              the isolated mock database context hook.
    """
    conn = isolated_test_db
    cursor = conn.cursor()
    
    # Mock dataset payload matching operational structures
    bulk_payload = [
        ("Network Outage East", "CRITICAL"),
        ("Database Replica Delay", "WARNING"),
        ("Expired SSL Alert", "INFO")
    ]
    
    # Execute batch insertion execution steps
    cursor.executemany(
        "INSERT INTO incidents (title, severity) VALUES (?, ?);", 
        bulk_payload
    )
    conn.commit()
    
    # Verify count metrics match the injected parameters
    cursor.execute("SELECT COUNT(*) FROM incidents;")
    record_count = cursor.fetchone()[0]
    assert record_count == 3
    
    # Validate structural content properties
    cursor.execute("SELECT title FROM incidents ORDER BY id ASC;")
    inserted_titles = [row[0] for row in cursor.fetchall()]
    assert inserted_titles[0] == "Network Outage East"
