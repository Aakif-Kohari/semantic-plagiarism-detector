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


# ---------------------------------------------------------------------------
# Seed data configuration
# ---------------------------------------------------------------------------

# Generated files
SEED_DB_FILES = ("users.db", "corpus.db", "corpus.index")
USERS_DB_FILENAME = "users.db"
CORPUS_DB_FILENAME = "corpus.db"
FAISS_INDEX_FILENAME = "corpus.index"

# Seed user
TEACHER_USERNAME = "teacher"
TEACHER_PASSWORD = "teacher123"
TEACHER_ROLE = "teacher"

# Shared document metadata
CLASS_SECTION = "CS-101"
ASSIGNMENT_TITLE = "Final Essay"

# Seed document filenames
ALICE_FILENAME = "Introduction_to_AI.pdf"
BOB_FILENAME = "AI_Concepts_Homework.pdf"
CHARLIE_FILENAME = "Introduction_to_Blockchain.pdf"

# Seed student names
ALICE_STUDENT_NAME = "Alice Smith"
BOB_STUDENT_NAME = "Bob Jones"
CHARLIE_STUDENT_NAME = "Charlie Brown"

# Mock embedding configuration
EMBEDDING_DIM = 384
RANDOM_SEED = 42
ALICE_BOB_SIMILARITY = 0.95
ALICE_CHARLIE_SIMILARITY = 0.15

# Incident configuration
INCIDENT_SEVERITY = "High"


# Patch the DB paths to point to the tests/dummy_data/ folder directly!
# This avoids file locks and permission errors when moving files on Windows.
import src.db.auth
import src.db.corpus_db
import src.db.incidents

src.db.auth._DB_PATH = os.path.join(seed_dir, USERS_DB_FILENAME)
src.db.corpus_db._DB_PATH = os.path.join(seed_dir, CORPUS_DB_FILENAME)
src.db.incidents.DEFAULT_DB_PATH = os.path.join(seed_dir, CORPUS_DB_FILENAME)

from src.core.faiss_index import build_index_from_matrix, save_index
from src.db.auth import add_user
from src.db.auth import init_db as init_auth_db
from src.db.corpus_db import add_chunks, add_document, init_corpus_db
from src.db.incidents import sync_flagged_incidents


def main():
    print("Cleaning existing local databases...")
    for filename in SEED_DB_FILES:
        path = os.path.join(seed_dir, filename)
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"Removed old seed {filename}")
            except Exception as err:
                print(f"Warning: Could not remove old seed {filename} ({err})")

    print("Initializing databases...")

    # Initialize Auth DB (Creates users.db and seeds admin/admin123)
    init_auth_db()

    # Add a teacher user
    add_user(TEACHER_USERNAME, TEACHER_PASSWORD, TEACHER_ROLE)
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
        filename=ALICE_FILENAME,
        file_hash=hash_alice,
        class_section=CLASS_SECTION,
        student_name=ALICE_STUDENT_NAME,
        assignment_title=ASSIGNMENT_TITLE,
    )

    add_document(
        filename=BOB_FILENAME,
        file_hash=hash_bob,
        class_section=CLASS_SECTION,
        student_name=BOB_STUDENT_NAME,
        assignment_title=ASSIGNMENT_TITLE,
    )

    add_document(
        filename=CHARLIE_FILENAME,
        file_hash=hash_charlie,
        class_section=CLASS_SECTION,
        student_name=CHARLIE_STUDENT_NAME,
        assignment_title=ASSIGNMENT_TITLE,
    )

    # Generate mock embeddings with deterministic similarities
    print("Generating mock embeddings with mathematical similarities...")
    np.random.seed(RANDOM_SEED)

    # Alice vector (random normalized unit vector)
    va = np.random.randn(EMBEDDING_DIM)
    va /= np.linalg.norm(va)

    # Bob vector
    noise_b = np.random.randn(EMBEDDING_DIM)
    noise_b -= np.dot(noise_b, va) * va
    noise_b /= np.linalg.norm(noise_b)

    vb = (
        ALICE_BOB_SIMILARITY * va
        + np.sqrt(1 - ALICE_BOB_SIMILARITY**2) * noise_b
    )
    vb /= np.linalg.norm(vb)

    # Charlie vector
    noise_c = np.random.randn(EMBEDDING_DIM)
    noise_c -= np.dot(noise_c, va) * va
    noise_c -= np.dot(noise_c, vb) * vb
    noise_c /= np.linalg.norm(noise_c)

    vc = (
        ALICE_CHARLIE_SIMILARITY * va
        + np.sqrt(1 - ALICE_CHARLIE_SIMILARITY**2) * noise_c
    )
    vc /= np.linalg.norm(vc)

    # Format chunks:
    # (vector_id, filename, chunk_index, chunk_text, embedding)
    chunks = [
        (0, ALICE_FILENAME, 0, text_alice, va),
        (1, BOB_FILENAME, 0, text_bob, vb),
        (2, CHARLIE_FILENAME, 0, text_charlie, vc),
    ]

    print("Inserting chunks...")
    add_chunks(chunks)

    # Sync plagiarism incidents
    print("Syncing plagiarism incidents...")
    flags = [
        {
            "doc_a": BOB_FILENAME,
            "doc_b": ALICE_FILENAME,
            "similarity": ALICE_BOB_SIMILARITY,
            "severity": INCIDENT_SEVERITY,
        }
    ]
    sync_flagged_incidents(flags)

    # Build and save FAISS index directly to tests/dummy_data/
    print("Building and saving FAISS index...")
    matrix = np.vstack([va, vb, vc])
    index = build_index_from_matrix(matrix)

    index_path = os.path.join(seed_dir, FAISS_INDEX_FILENAME)
    save_index(index, index_path)

    print("Seed data successfully generated and stored in tests/dummy_data/!")


if __name__ == "__main__":
    main()