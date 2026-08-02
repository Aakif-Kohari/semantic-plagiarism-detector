import pytest
import numpy as np
from src.db.corpus_db import (
    init_corpus_db,
    add_document,
    get_document_by_hash,
    get_all_documents,
    add_chunks,
    get_chunk_registry,
    get_all_embeddings,
    delete_document,
    clear_all_data,
    get_document_chunks_count,
    get_unique_class_sections,
    get_documents_by_class,
)


@pytest.fixture(autouse=True)
def setup_test_db():
    # Initialize database
    init_corpus_db()
    # Clear any leftover records
    clear_all_data()
    yield
    # Cleanup after tests
    clear_all_data()


def test_add_document_metadata():
    # Add first document
    res1 = add_document("test1.pdf", "hash_abc_123")
    assert res1 is True

    # Try adding a duplicate hash/document
    res2 = add_document("test2.pdf", "hash_abc_123")
    assert res2 is False  # Unique hash constraint triggers

    # Try adding a duplicate filename
    res3 = add_document("test1.pdf", "different_hash")
    assert res3 is False  # Unique filename constraint triggers


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
    )
    assert res is True

    # Retrieve and check fields
    docs = get_all_documents()
    assert len(docs) == 1
    doc = docs[0]
    assert doc["filename"] == "metadata_test.pdf"
    assert doc["class_section"] == "Class B"
    assert doc["student_name"] == "Alice Smith"
    assert doc["assignment_title"] == "Homework 1"


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
    add_document("doc_empty.pdf", "hash_empty")  # No metadata class

    # Verify unique class list
    classes = get_unique_class_sections()
    assert "Class A" in classes
    assert "Class B" in classes
    assert len(classes) == 2  # None or empty string shouldn't be included

    # Verify getting documents by class
    class_a_docs = get_documents_by_class("Class A")
    assert "doc_a.pdf" in class_a_docs
    assert "doc_c.pdf" in class_a_docs
    assert len(class_a_docs) == 2

    class_b_docs = get_documents_by_class("Class B")
    assert "doc_b.pdf" in class_b_docs
    assert len(class_b_docs) == 1


def test_batch_soft_delete_documents():
    from src.db.corpus_db import batch_soft_delete_documents, _connect

    # Add some test documents
    add_document("doc_soft1.pdf", "hash_s1")
    add_document("doc_soft2.pdf", "hash_s2")
    add_document("doc_soft3.pdf", "hash_s3")

    # Fetch their IDs
    with _connect() as conn:
        rows = conn.execute("SELECT id, filename FROM documents ORDER BY id").fetchall()
        doc_ids = {row[1]: row[0] for row in rows}

    id1 = doc_ids["doc_soft1.pdf"]
    id2 = doc_ids["doc_soft2.pdf"]
    id3 = doc_ids["doc_soft3.pdf"]

    # 1. Multiple valid IDs
    count = batch_soft_delete_documents([id1, id2])
    assert count == 2

    # Check that they are deleted
    with _connect() as conn:
        deleted = conn.execute(
            "SELECT is_deleted FROM documents WHERE id IN (?, ?)", (id1, id2)
        ).fetchall()
        assert all(row[0] == 1 for row in deleted)
        not_deleted = conn.execute(
            "SELECT is_deleted FROM documents WHERE id = ?", (id3,)
        ).fetchone()
        assert not_deleted[0] == 0

    # 2. Empty list
    assert batch_soft_delete_documents([]) == 0

    # 3. Invalid/non-existing IDs
    count = batch_soft_delete_documents([9999, 10000])
    assert count == 0

    # 4. Already deleted documents
    count = batch_soft_delete_documents([id1])
    assert (
        count == 1
    )  # SQLite UPDATE rowcount still returns matched rows even if value didn't change
