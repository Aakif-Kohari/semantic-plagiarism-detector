"""
Migration 005: Add Bibliography Citation Tables
-----------------------------------------------
Creates the `citations` and `document_citations` tables to support
structural plagiarism analysis and citation graph extraction (Issue #1958).
"""


def migrate(connection):
    """Execute the migration SQL."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS citations (
            hash TEXT PRIMARY KEY,
            author TEXT,
            year TEXT,
            title TEXT,
            raw_text TEXT
        )
    """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS document_citations (
            doc_name TEXT NOT NULL,
            citation_hash TEXT NOT NULL,
            is_ghost INTEGER DEFAULT 0,
            PRIMARY KEY (doc_name, citation_hash),
            FOREIGN KEY (citation_hash) REFERENCES citations(hash) ON DELETE CASCADE
        )
    """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_doc_citations_doc 
        ON document_citations(doc_name)
    """
    )
