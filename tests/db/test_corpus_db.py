from datetime import datetime, timedelta

import numpy as np
import pytest

from src.db.corpus_db import (
    _connect,
    add_chunks,
    add_document,
    clear_all_data,
    delete_document,
    get_all_documents,
    get_all_embeddings,
    get_chunk_registry,
    get_document_by_hash,
    get_document_chunks_count,
    get_document_count_by_user,
    get_documents_by_class,
    get_unique_class_sections,
    purge_stale_trash,
    soft_delete_document,
)

@pytest.fixture(autouse=True)
def setup_test_db(mock_db):
    """
    Uses the global mock_db fixture from conftest.py for complete DB isolation
    and automatic teardown per test.
    """
    yield

def test_add_document_metadata():
    # Add first document
    res1 = add_document("test1.pdf", "hash_abc_123")
    assert res1 is True

    # Try adding a duplicate hash/document
    res2 = add_document("test2.pdf", "hash_abc_123")
    assert res2 is False # Unique hash constraint triggers

    # Try adding a duplicate filename
    res3 = add_document("test1.pdf", "different_hash")
    assert res3 is False # Unique filename constraint triggers

def test_get_document_by_hash():
    add_document("doc_alpha.txt", "hash_xyz_789")

    match = get_document_by_hash("hash_xyz_789")
    assert match == "doc_alpha.txt"

    no_match = get_document_by_hash("nonexistent_hash")
    assert no_match is None

def test_add_and_retrieve_chunks():
    add_document("doc1.pdf", "hash_1")

    # Format of chunk insertion tuples: (vector_id, filename, chunk_index, chunk_text, embedding)
    dummy_emb_1 = np.ones(384, dtype=np.float32) * 0.5
    dummy_emb_2 = np.ones(384, dtype=np.float32) * 1.5

    chunks = [
        (0, "doc1.pdf", 0, "Paragraph 1 text", dummy_emb_1),
        (1, "doc1.pdf", 1, "Paragraph 2 text", dummy_emb_2),
    ]

    add_chunks(chunks)

    # Check count
    assert get_document_chunks_count("doc1.pdf") == 2

    # Check registry loading
    registry = get_chunk_registry()
    assert len(registry) == 2
    assert registry[0].doc_name == "doc1.pdf"
    assert registry[0].chunk_text == "Paragraph 1 text"

    # Check embeddings extraction
    embs = get_all_embeddings()
    assert embs.shape == (2, 384)
    assert np.allclose(embs[0], dummy_emb_1)
    assert np.allclose(embs[1], dummy_emb_2)

def test_delete_document_cascades():
    add_document("doc1.pdf", "hash_1")
    add_document("doc2.pdf", "hash_2")

    dummy_emb = np.zeros(384, dtype=np.float32)

    chunks = [
        (0, "doc1.pdf", 0, "Paragraph 1", dummy_emb),
        (1, "doc2.pdf", 0, "Paragraph 2", dummy_emb),
    ]
    add_chunks(chunks)

    # Delete doc1
    delete_document("doc1.pdf")

    # Check document counts
    all_docs = get_all_documents()
    assert len(all_docs) == 1
    assert all_docs[0]["filename"] == "doc2.pdf"

    # Check that remaining chunks have compact vector_ids starting at 0
    registry = get_chunk_registry()
    assert len(registry) == 1
    assert registry[0].doc_name == "doc2.pdf"

    embs = get_all_embeddings()
    assert embs.shape == (1, 384)

def test_document_metadata_fields():
    # Insert with metadata fields
    res = add_document(
        "metadata_test.pdf",
        "hash_metadata_123",
        class_section="Class B",
        student_name="Alice Smith",
        assignment_title="Homework 1",
        detected_language="en",
    )
    assert res is True

    # Retrieve and check fields
    from src.db.schemas import Document
    docs = get_all_documents()
    assert len(docs) == 1
    doc = docs[0]
    assert isinstance(doc, Document)
    assert doc["filename"] == "metadata_test.pdf"
    assert doc["class_section"] == "Class B"
    assert doc["student_name"] == "Alice Smith"
    assert doc["assignment_title"] == "Homework 1"
    assert doc["detected_language"] == "en"

def test_class_queries():
    # Add documents belonging to different classes
    add_document(
        "doc_a.pdf",
        "hash_a",
        class_section="Class A",
        student_name="Student A",
        assignment_title="Title A",
    )
    add_document(
        "doc_b.pdf",
        "hash_b",
        class_section="Class B",
        student_name="Student B",
        assignment_title="Title B",
    )
    add_document(
        "doc_c.pdf",
        "hash_c",
        class_section="Class A",
        student_name="Student C",
        assignment_title="Title C",
    )
    add_document("doc_empty.pdf", "hash_empty") # No metadata class

    # Verify unique class list
    classes = get_unique_class_sections()
    assert "Class A" in classes
    assert "Class B" in classes
    assert len(classes) == 2 # None or empty string shouldn't be included

    # Verify getting documents by class
    class_a_docs = get_documents_by_class("Class A")
    assert "doc_a.pdf" in class_a_docs
    assert "doc_c.pdf" in class_a_docs
    assert len(class_a_docs) == 2

    class_b_docs = get_documents_by_class("Class B")
    assert "doc_b.pdf" in class_b_docs
    assert len(class_b_docs) == 1

def test_clear_all_data_clears_incidents(mock_db):
    from src.db.incidents import get_all_incidents, sync_flagged_incidents
    from pathlib import Path

    db_path = Path(mock_db)

    # 1. Add mock documents
    add_document("doc1.pdf", "hash1")
    add_document("doc2.pdf", "hash2")

    # 2. Add mock incidents
    flags = [
        {
            "doc_a": "doc1.pdf",
            "doc_b": "doc2.pdf",
            "similarity": 0.85,
            "severity": "High",
        }
    ]
    sync_flagged_incidents(flags, db_path=db_path)

    # Verify they exist
    incidents = get_all_incidents(db_path=db_path)
    assert len(incidents) == 1

    # 3. Clear all data
    clear_all_data()

    # Verify everything is cleared
    assert len(get_all_documents()) == 0
    assert len(get_all_incidents(db_path=db_path)) == 0

def test_get_document_word_counts():
    import numpy as np

    from src.db.corpus_db import (add_chunks, add_document, clear_all_data,
                                  get_document_word_counts)

    clear_all_data()

    # 1. Add mock documents
    add_document("doc1.txt", "hash_doc1")
    add_document("doc2.txt", "hash_doc2")

    # 2. Add chunks with text
    chunks = [
        (1, "doc1.txt", 0, "This is the first chunk.", np.zeros(384)),
        (2, "doc1.txt", 1, "And this is the second chunk of doc1.", np.zeros(384)),
        (3, "doc2.txt", 0, "Doc2 has only one single chunk.", np.zeros(384)),
    ]
    add_chunks(chunks)

    # 3. Retrieve word counts
    word_counts = get_document_word_counts()

    # "This is the first chunk." -> 5 words
    # "And this is the second chunk of doc1." -> 8 words
    # doc1 total = 13 words
    assert word_counts["doc1.txt"] == 13

    # "Doc2 has only one single chunk." -> 6 words
    assert word_counts["doc2.txt"] == 6

def test_optimize_database_vacuum(mock_db):
    from src.db.corpus_db import optimize_database

    res = optimize_database()
    assert "size_before" in res
    assert "size_after" in res
    assert "reclaimed_bytes" in res
    assert "error" in res

    assert res["error"] is None
    assert res["size_before"] > 0
    assert res["size_after"] > 0
    assert res["reclaimed_bytes"] >= 0

def test_optimize_database_error_handling():
    from src.db.corpus_db import optimize_database, configure_db_path, get_corpus_db_path

    original_path = get_corpus_db_path()
    try:
        configure_db_path("Z:\\invalid_dir_xyz_123\\corpus.db")
        res = optimize_database()
        assert res["error"] is not None
        assert res["size_before"] == 0
        assert res["size_after"] == 0
        assert res["reclaimed_bytes"] == 0
    finally:
        configure_db_path(original_path)

# ==============================================================================
# NEW TESTS FOR ISSUE #929: Soft Delete Cleanup Helper
# ==============================================================================

def test_purge_stale_trash_deletes_old_documents(mock_db):
    """Test that purge_stale_trash deletes documents older than the threshold."""
    # 1. Add a document
    add_document("old_trash_doc.pdf", "hash_old_trash")
    
    # 2. Soft delete it
    soft_delete_document("old_trash_doc.pdf")
    
    # 3. Manually backdate the deleted_at timestamp to 40 days ago
    old_date = (datetime.now() - timedelta(days=40)).isoformat()
    with _connect() as conn:
        conn.execute(
            "UPDATE documents SET deleted_at = ? WHERE filename = ?",
            (old_date, "old_trash_doc.pdf")
        )
    
    # Verify it exists as deleted
    with _connect() as conn:
        row = conn.execute(
            "SELECT is_deleted FROM documents WHERE filename = ?", 
            ("old_trash_doc.pdf",)
        ).fetchone()
        assert row is not None and row[0] == 1
    
    # 4. Purge stale trash (default 30 days)
    deleted_count = purge_stale_trash(days_in_trash=30)
    
    assert deleted_count == 1
    
    # 5. Verify it is permanently gone
    with _connect() as conn:
        row = conn.execute(
            "SELECT filename FROM documents WHERE filename = ?", 
            ("old_trash_doc.pdf",)
        ).fetchone()
        assert row is None

def test_purge_stale_trash_retains_recently_deleted(mock_db):
    """Test that purge_stale_trash retains documents deleted recently."""
    # 1. Add a document
    add_document("recent_trash_doc.pdf", "hash_recent_trash")
    
    # 2. Soft delete it (deleted_at is set to NOW)
    soft_delete_document("recent_trash_doc.pdf")
    
    # 3. Attempt to purge with 30 days threshold
    deleted_count = purge_stale_trash(days_in_trash=30)
    
    assert deleted_count == 0
    
    # 4. Verify it still exists in soft-deleted state
    with _connect() as conn:
        row = conn.execute(
            "SELECT is_deleted FROM documents WHERE filename = ?", 
            ("recent_trash_doc.pdf",)
        ).fetchone()
        assert row is not None and row[0] == 1

def test_purge_stale_trash_ignores_active_documents(mock_db):
    """Test that purge_stale_trash does not affect active (is_deleted=0) documents."""
    # 1. Add an active document
    add_document("active_old_doc.pdf", "hash_active_old")
    
    # 2. Manually backdate its upload date to 100 days ago (but is_deleted is 0 or NULL)
    old_date = (datetime.now() - timedelta(days=100)).isoformat()
    with _connect() as conn:
        conn.execute(
            "UPDATE documents SET upload_date = ? WHERE filename = ?",
            (old_date, "active_old_doc.pdf")
        )
    
    # 3. Attempt to purge
    deleted_count = purge_stale_trash(days_in_trash=30)
    
    assert deleted_count == 0
    
    # 4. Verify active document remains
    with _connect() as conn:
        row = conn.execute(
            "SELECT is_deleted FROM documents WHERE filename = ?", 
            ("active_old_doc.pdf",)
        ).fetchone()
        assert row is not None and (row[0] == 0 or row[0] is None)


def test_add_chunks_logs_memory_usage(mock_db, caplog):
    """Test that add_chunks logs memory usage before and after insertions."""
    import logging
    add_document("doc_mem_test.pdf", "hash_mem_test")
    dummy_emb = np.ones(384, dtype=np.float32) * 0.5
    chunks = [(100, "doc_mem_test.pdf", 0, "Memory test chunk", dummy_emb)]

    with caplog.at_level(logging.INFO):
        add_chunks(chunks)

    # Check for expected messages in log records
    log_messages = [record.message for record in caplog.records]
    assert any("Memory usage before batch chunk insertion:" in msg for msg in log_messages)
    assert any("Memory usage after batch chunk insertion:" in msg for msg in log_messages)


# ==============================================================================
# get_document_count_by_user — issue #1048
# ==============================================================================


def test_get_document_count_by_user_returns_zero_for_unknown_user(mock_db):
    """A username with no documents must return 0."""
    assert get_document_count_by_user("nobody") == 0


def test_get_document_count_by_user_counts_active_documents(mock_db):
    """Documents owned by the user that are NOT soft-deleted must be counted."""
    add_document("doc1.pdf", "hash_1", owner="alice")
    add_document("doc2.pdf", "hash_2", owner="alice")
    add_document("doc3.pdf", "hash_3", owner="bob")

    assert get_document_count_by_user("alice") == 2
    assert get_document_count_by_user("bob") == 1


def test_get_document_count_by_user_excludes_soft_deleted(mock_db):
    """Soft-deleted documents must not be counted (is_deleted = 0 filter)."""
    add_document("active.pdf", "hash_active", owner="alice")
    add_document("trashed.pdf", "hash_trashed", owner="alice")
    soft_delete_document("trashed.pdf")

    # Only the active document should be counted
    assert get_document_count_by_user("alice") == 1


def test_get_document_count_by_user_excludes_other_owners(mock_db):
    """Documents owned by other users must not be counted."""
    add_document("alice_doc.pdf", "hash_a", owner="alice")
    add_document("bob_doc.pdf", "hash_b", owner="bob")
    add_document("charlie_doc.pdf", "hash_c", owner="charlie")

    assert get_document_count_by_user("alice") == 1
    assert get_document_count_by_user("bob") == 1
    assert get_document_count_by_user("charlie") == 1


def test_get_document_count_by_user_handles_none_owner(mock_db):
    """Documents with owner=NULL must not be counted for any username."""
    # add_document without owner → owner is NULL
    add_document("no_owner.pdf", "hash_none")
    add_document("alice_doc.pdf", "hash_alice", owner="alice")

    # NULL owner should not match any username
    assert get_document_count_by_user("alice") == 1
    assert get_document_count_by_user("") == 0


def test_get_document_count_by_user_returns_int(mock_db):
    """The return type must be int, not None or sqlite3.Row."""
    add_document("doc.pdf", "hash", owner="alice")
    result = get_document_count_by_user("alice")
    assert isinstance(result, int)
    assert result == 1
