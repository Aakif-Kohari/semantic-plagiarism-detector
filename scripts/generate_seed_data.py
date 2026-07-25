"""
scripts/generate_seed_data.py
----------------------------
Programmatic script to generate seed databases and FAISS index with realistic dummy data.
Uses mathematical mock embeddings to avoid downloading a large SentenceTransformer model.
"""

import hashlib
import os
import sys

import numpy as np

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Create seed directory tests/dummy_data/ if it doesn't exist
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
seed_dir = os.path.join(root_dir, "tests", "dummy_data")
if not os.path.exists(seed_dir):
    os.makedirs(seed_dir, exist_ok=True)

# Patch the DB paths to point to the tests/dummy_data/ folder directly!
# This avoids file locks and permission errors when moving files on Windows.
import src.db.auth
import src.db.corpus_db
import src.db.incidents

src.db.auth._DB_PATH = os.path.join(seed_dir, "users.db")
src.db.corpus_db._DB_PATH = os.path.join(seed_dir, "corpus.db")
src.db.incidents.DEFAULT_DB_PATH = os.path.join(seed_dir, "corpus.db")

from src.core.faiss_index import build_index_from_matrix, save_index
from src.db.auth import add_user
from src.db.auth import init_db as init_auth_db
from src.db.corpus_db import add_chunks, add_document, init_corpus_db
from src.db.incidents import sync_flagged_incidents


def main():
    # Files to generate
    db_files = ["users.db", "corpus.db", "corpus.index"]

    print("Cleaning existing local databases...")
    for f in db_files:
        path = os.path.join(seed_dir, f)
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"Removed old seed {f}")
            except Exception as err:
                print(f"Warning: Could not remove old seed {f} ({err})")

    print("Initializing databases...")
    # Initialize Auth DB (Creates users.db and seeds admin/admin123)
    init_auth_db()
    # Add a teacher user
    add_user("teacher", "teacher123", "teacher")
    print("Auth DB initialized and seeded.")

    # Initialize Corpus DB (Creates corpus.db with schema and migrations)
    init_corpus_db()
    print("Corpus DB initialized.")

    # Document contents
    text_alice = (
        "Artificial intelligence (AI) is intelligence demonstrated by machines, in contrast to the natural "
        "intelligence displayed by humans and other animals. Study of intelligent agents: any device that "
        "perceives its environment and takes actions that maximize its chance of successfully achieving its goals."
    )
    text_bob = (
        "Artificial intelligence (AI) is intelligence demonstrated by machines, in contrast to the natural "
        "intelligence displayed by humans and other animals. Study of intelligent agents: any device that "
        "perceives its environment and takes actions that maximize its chance of successfully achieving its goals. "
    )
    text_charlie = (
        "A blockchain is a decentralized, distributed, and public digital ledger that is used to record transactions "
        "across many computers so that the record cannot be altered retroactively without the alteration of all "
        "subsequent blocks."
    )

    # Document hashes
    hash_alice = hashlib.sha256(text_alice.encode()).hexdigest()
    hash_bob = hashlib.sha256(text_bob.encode()).hexdigest()
    hash_charlie = hashlib.sha256(text_charlie.encode()).hexdigest()

    print("Adding dummy documents...")
    add_document(
        filename="Introduction_to_AI.pdf",
        file_hash=hash_alice,
        class_section="CS-101",
        student_name="Alice Smith",
        assignment_title="Final Essay",
    )
    add_document(
        filename="AI_Concepts_Homework.pdf",
        file_hash=hash_bob,
        class_section="CS-101",
        student_name="Bob Jones",
        assignment_title="Final Essay",
    )
    add_document(
        filename="Introduction_to_Blockchain.pdf",
        file_hash=hash_charlie,
        class_section="CS-101",
        student_name="Charlie Brown",
        assignment_title="Final Essay",
    )

    # Generate mock embeddings (384-dimensional) with exact similarities
    print("Generating mock embeddings with mathematical similarities...")
    dim = 384
    np.random.seed(42)  # For deterministic seed generation

    # Alice vector (random normalized unit vector)
    va = np.random.randn(dim)
    va /= np.linalg.norm(va)

    # Bob vector (similarity with Alice = 0.95)
    noise_b = np.random.randn(dim)
    noise_b -= np.dot(noise_b, va) * va
    noise_b /= np.linalg.norm(noise_b)
    vb = 0.95 * va + np.sqrt(1 - 0.95**2) * noise_b
    vb /= np.linalg.norm(vb)

    # Charlie vector (similarity with Alice = 0.15)
    noise_c = np.random.randn(dim)
    noise_c -= np.dot(noise_c, va) * va
    noise_c -= np.dot(noise_c, vb) * vb
    noise_c /= np.linalg.norm(noise_c)
    vc = 0.15 * va + np.sqrt(1 - 0.15**2) * noise_c
    vc /= np.linalg.norm(vc)

    # Format chunks: (vector_id, filename, chunk_index, chunk_text, embedding)
    chunks = [
        (0, "Introduction_to_AI.pdf", 0, text_alice, va),
        (1, "AI_Concepts_Homework.pdf", 0, text_bob, vb),
        (2, "Introduction_to_Blockchain.pdf", 0, text_charlie, vc),
    ]

    print("Inserting chunks...")
    add_chunks(chunks)

    # Sync plagiarism incidents
    print("Syncing plagiarism incidents...")
    flags = [
        {
            "doc_a": "AI_Concepts_Homework.pdf",
            "doc_b": "Introduction_to_AI.pdf",
            "similarity": 0.95,
            "severity": "High",
        }
    ]
    sync_flagged_incidents(flags)

    # Build and save FAISS index directly to tests/dummy_data/
    print("Building and saving FAISS index...")
    matrix = np.vstack([va, vb, vc])
    index = build_index_from_matrix(matrix)
    index_path = os.path.join(seed_dir, "corpus.index")
    save_index(index, index_path)

    print("Seed data successfully generated and stored in tests/dummy_data/!")


if __name__ == "__main__":
    main()
