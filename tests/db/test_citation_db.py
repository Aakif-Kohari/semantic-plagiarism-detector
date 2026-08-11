import os
import sqlite3
import pytest

from src.db.citation_db import add_document_citations, init_citation_db
from src.db.corpus_db import _DB_PATH

@pytest.fixture(autouse=True)
def setup_teardown_db():
    # Setup test database
    if os.path.exists(_DB_PATH):
        os.remove(_DB_PATH)
    
    init_citation_db()
    yield
    # Teardown test database
    if os.path.exists(_DB_PATH):
        try:
            os.remove(_DB_PATH)
        except PermissionError:
            pass

def test_add_document_citations_duplicate_count():
    doc_name = "test_doc.pdf"
    citations = [
        {
            "hash": "hash123",
            "author": "Smith",
            "year": "2023",
            "title": "A Great Paper",
            "raw_text": "Smith, 2023, A Great Paper"
        }
    ]
    
    # First insert should return 1
    added = add_document_citations(doc_name, citations)
    assert added == 1
    
    # Second insert of the exact same citation should return 0
    added_duplicate = add_document_citations(doc_name, citations)
    assert added_duplicate == 0
