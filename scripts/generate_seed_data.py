# filepath: scripts/generate_seed_data.py
"""
scripts/generate_seed_data.py
----------------------------
Programmatic script to generate seed databases and FAISS index with realistic dummy data.
Uses mathematical mock embeddings to avoid downloading a large SentenceTransformer model.
Now includes robust CLI argument parsing for configurable dataset generation.
"""

import argparse
import hashlib
import logging
import os
import random
import sys
from dataclasses import dataclass
from typing import Tuple

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.faiss_index import build_index_from_matrix, save_index
from src.db.auth import (
    add_user,
    configure_db_path as configure_auth_db_path,
    init_db as init_auth_db,
)
from src.db.corpus_db import (
    add_chunks,
    add_document,
    configure_db_path as configure_corpus_db_path,
    init_corpus_db,
)
from src.db.incidents import sync_flagged_incidents

import numpy as np

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("SeedDataGenerator")

# Create seed directory tests/dummy_data/ if it doesn't exist
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
seed_dir = os.path.join(root_dir, "tests", "dummy_data")
os.makedirs(seed_dir, exist_ok=True)

# Explicit seed database paths
auth_db_path = os.path.join(seed_dir, "users.db")
corpus_db_path = os.path.join(seed_dir, "corpus.db")

# ============================================================================
# EXTENSIVE MOCK DATA DICTIONARIES FOR GENERATION
# ============================================================================
MOCK_SUBJECTS = [
    "Artificial Intelligence", "Machine Learning", "Quantum Computing",
    "Blockchain Technology", "Cybersecurity", "Data Science",
    "Software Engineering", "Cloud Computing", "Internet of Things",
    "Augmented Reality", "Virtual Reality", "Robotics",
    "Bioinformatics", "Computational Linguistics", "Computer Vision",
    "Natural Language Processing", "Distributed Systems", "Operating Systems",
    "Database Management", "Computer Networks", "Cryptography",
    "Human-Computer Interaction", "Computer Graphics", "Game Development",
    "Embedded Systems", "Information Retrieval", "Knowledge Representation",
    "Logic Programming", "Machine Translation", "Neural Networks",
    "Pattern Recognition", "Speech Recognition", "Data Mining",
    "Data Warehousing", "Information Security", "Network Security",
    "Software Architecture", "Software Testing", "Agile Methodologies",
    "DevOps", "Microservices", "Serverless Computing",
    "Edge Computing", "Fog Computing", "Grid Computing",
    "Parallel Computing", "High-Performance Computing", "Supercomputing",
    "Quantum Algorithms", "Quantum Cryptography", "Quantum Teleportation",
]


from src.core.faiss_index import build_index_from_matrix, save_index
from src.db.auth import add_user
from src.db.auth import init_db as init_auth_db
from src.db.corpus_db import (
    add_chunks,
    add_document,
    get_all_documents,
    get_embedding_count,
    init_corpus_db,
)
from src.db.incidents import get_all_incidents, sync_flagged_incidents

MOCK_VERBS = [
    "analyzes", "evaluates", "investigates", "explores", "demonstrates",
    "illustrates", "examines", "proposes", "introduces", "presents",
    "discusses", "reviews", "summarizes", "outlines", "details",
    "describes", "explains", "clarifies", "defines", "identifies",
    "highlights", "emphasizes", "focuses on", "addresses", "tackles",
    "solves", "resolves", "overcomes", "mitigates", "reduces",
    "minimizes", "maximizes", "optimizes", "improves", "enhances",
    "augments", "extends", "expands", "broadens", "widens",
    "deepens", "strengthens", "fortifies", "secures", "protects",
    "defends", "guards", "shields", "safeguards", "preserves",
]


MOCK_OBJECTS = [
    "complex systems", "algorithmic efficiency", "data structures",
    "computational models", "network protocols", "security mechanisms",
    "software frameworks", "hardware architectures", "user interfaces",
    "machine learning models", "deep learning architectures", "neural network layers",
    "optimization algorithms", "heuristic search methods", "evolutionary algorithms",
    "genetic algorithms", "swarm intelligence", "ant colony optimization",
    "particle swarm optimization", "simulated annealing", "tabu search",
    "local search", "greedy algorithms", "divide and conquer strategies",
    "dynamic programming techniques", "branch and bound methods", "backtracking algorithms",
    "randomized algorithms", "approximation algorithms", "online algorithms",
    "streaming algorithms", "sublinear time algorithms", "quantum algorithms",
    "cryptographic protocols", "secure multiparty computation", "zero-knowledge proofs",
    "homomorphic encryption", "post-quantum cryptography", "lattice-based cryptography",
    "hash functions", "digital signatures", "public key infrastructure",
    "access control models", "intrusion detection systems", "firewalls",
    "antivirus software", "malware analysis", "vulnerability assessment",
    "penetration testing", "incident response", "digital forensics",
]

MOCK_NAMES = [
    "Alice Smith", "Bob Jones", "Charlie Brown", "David Miller",
    "Eve Davis", "Frank Wilson", "Grace Taylor", "Heidi Anderson",
    "Ivan Thomas", "Judy Jackson", "Kevin White", "Linda Harris",
    "Michael Martin", "Nancy Thompson", "Oscar Garcia", "Pamela Martinez",
    "Quinn Robinson", "Rachel Clark", "Steve Rodriguez", "Tina Lewis",
    "Ursula Lee", "Victor Walker", "Wendy Hall", "Xavier Allen",
    "Yvonne Young", "Zachary Hernandez", "Aaron King", "Betty Wright",
    "Carl Lopez", "Diana Hill", "Ethan Scott", "Fiona Green",
    "George Adams", "Hannah Baker", "Ian Gonzalez", "Julia Nelson",
    "Kyle Carter", "Laura Mitchell", "Matthew Perez", "Nora Roberts",
    "Owen Turner", "Paula Phillips", "Quincy Campbell", "Rebecca Parker",
    "Samuel Evans", "Tara Edwards", "Ulysses Collins", "Victoria Stewart",
    "William Sanchez", "Xena Morris", "Yusuf Rogers", "Zoe Reed",
]

MOCK_CLASSES = [
    "CS-101", "CS-102", "CS-201", "CS-202", "CS-301", "CS-302", "CS-401", "CS-402",
    "ENG-101", "ENG-102", "MATH-101", "MATH-102", "PHYS-101", "PHYS-102", "CHEM-101",
    "BIO-101", "HIST-101", "PSYCH-101", "SOC-101", "PHIL-101", "ART-101", "MUSIC-101",
    "ECON-101", "POLSCI-101", "ANTHRO-101", "GEO-101", "ASTR-101", "STAT-101",
    "DATA-101", "INFO-101", "SEC-101", "NET-101", "WEB-101", "MOBILE-101", "AI-101",
]


@dataclass
class ConfigArgs:
    """Dataclass to hold parsed configuration arguments."""
    documents: int
    pairs: int
    seed: int
    dim: int = 384
    verbose: bool = False


class ArgumentParserManager:
    """Manages CLI argument parsing for the seed data generator."""

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="Programmatic script to generate seed databases and FAISS index with realistic dummy data.",
            formatter_class=argparse.RawTextHelpFormatter,
        )
        self._setup_arguments()

    def _setup_arguments(self):
        """Configure all CLI flags and arguments."""
        self.parser.add_argument(
            "--documents",
            type=int,
            default=3,
            help="Number of unique mock documents to generate (default: 3).\n"
                 "Higher values will increase generation time but provide a larger test corpus.",
        )
        self.parser.add_argument(
            "--pairs",
            type=int,
            default=1,
            help="Number of flagged plagiarism pairs to generate (default: 1).\n"
                 "Must be less than or equal to (documents * (documents - 1)) / 2.",
        )
        self.parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for deterministic generation (default: 42).",
        )
        self.parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Enable verbose logging output.",
        )

    def parse(self) -> ConfigArgs:
        """Parse arguments and return a strictly validated ConfigArgs object."""
        args = self.parser.parse_args()
        
        if args.documents < 1:
            self.parser.error("Number of documents must be at least 1.")
            
        max_possible_pairs = (args.documents * (args.documents - 1)) // 2
        if args.pairs > max_possible_pairs:
            self.parser.error(
                f"Requested {args.pairs} pairs, but only {max_possible_pairs} "
                f"are possible with {args.documents} documents."
            )

        return ConfigArgs(
            documents=args.documents,
            pairs=args.pairs,
            seed=args.seed,
            verbose=args.verbose,
        )


class MockDocumentGenerator:
    """Generates realistic mock documents using stochastic combination models."""

    def __init__(self, seed: int):
        self.random_state = random.Random(seed)

    def _generate_sentence(self) -> str:
        """Generates a single structurally coherent academic sentence."""
        subject = self.random_state.choice(MOCK_SUBJECTS)
        verb = self.random_state.choice(MOCK_VERBS)
        obj = self.random_state.choice(MOCK_OBJECTS)
        
        structures = [
            f"The field of {subject.lower()} frequently {verb} various {obj}.",
            f"Recent advancements in {subject.lower()} have shown how it {verb} modern {obj}.",
            f"An essential aspect of {subject.lower()} is the way it {verb} critical {obj}.",
            f"By leveraging {subject.lower()}, researchers can ensure the system {verb} {obj}.",
            f"Traditional approaches to {subject.lower()} lack the capacity to properly handle {obj}, which this methodology {verb}."
        ]
        return self.random_state.choice(structures)

    def generate_paragraph(self, min_sentences: int = 3, max_sentences: int = 7) -> str:
        """Generates a full paragraph of text."""
        count = self.random_state.randint(min_sentences, max_sentences)
        sentences = [self._generate_sentence() for _ in range(count)]
        return " ".join(sentences)

    def generate_document(self, min_paragraphs: int = 2, max_paragraphs: int = 5) -> str:
        """Generates a full document corpus."""
        count = self.random_state.randint(min_paragraphs, max_paragraphs)
        paragraphs = [self.generate_paragraph() for _ in range(count)]
        return "\n\n".join(paragraphs)

    def generate_metadata(self) -> Tuple[str, str, str]:
        """Generates mock metadata: (student_name, class_section, filename)."""
        student = self.random_state.choice(MOCK_NAMES)
        cls = self.random_state.choice(MOCK_CLASSES)
        topic = self.random_state.choice(MOCK_SUBJECTS).replace(" ", "_")
        filename = f"{student.replace(' ', '_')}_{topic}_Essay.pdf"
        return student, cls, filename


class VectorMathGenerator:
    """Handles high-dimensional math for semantic embedding mocks."""

    def __init__(self, seed: int, dim: int = 384):
        self.seed = seed
        self.dim = dim
        self.rng = np.random.default_rng(seed)

    def generate_base_vector(self) -> np.ndarray:
        """Generates a random normalized unit vector."""
        vec = self.rng.standard_normal(self.dim)
        vec /= np.linalg.norm(vec)
        return vec

    def generate_similar_vector(self, base_vec: np.ndarray, target_similarity: float) -> np.ndarray:
        """
        Generates a new vector that has exactly `target_similarity` 
        cosine similarity with `base_vec`.
        """
        target_similarity = np.clip(target_similarity, -1.0, 1.0)
        noise = self.rng.standard_normal(self.dim)
        
        # Orthogonalize noise against base_vec
        noise -= np.dot(noise, base_vec) * base_vec
        
        # Handle edge case where noise is zero vector
        norm = np.linalg.norm(noise)
        if norm < 1e-10:
            noise = self.rng.standard_normal(self.dim)
            noise -= np.dot(noise, base_vec) * base_vec
            norm = np.linalg.norm(noise)
            
        noise /= norm
        
        # Combine
        new_vec = target_similarity * base_vec + np.sqrt(1 - target_similarity**2) * noise
        new_vec /= np.linalg.norm(new_vec)
        return new_vec


def clear_existing_databases(verbose: bool):
    """Removes old database files to ensure a clean slate."""
    db_files = ["users.db", "corpus.db", "corpus.index"]
    if verbose:
        logger.info("Cleaning existing local databases...")
        
    for f in db_files:
        path = os.path.join(seed_dir, f)
        if os.path.exists(path):
            try:
                os.remove(path)
                if verbose:
                    logger.info(f"Removed old seed file: {f}")
            except PermissionError as err:
                logger.warning(
                    f"Permission denied while removing seed file {f} "
                    f"({err}). The file may be locked or in use."
                )
            except OSError as err:
                logger.warning(f"OS error while removing seed file {f}: {err}")


def initialize_databases(verbose: bool):
    """Configures paths and initializes sqlite tables."""
    if verbose:
        logger.info("Configuring database paths...")
    configure_auth_db_path(auth_db_path)
    configure_corpus_db_path(corpus_db_path)

    if verbose:
        logger.info("Initializing Auth DB...")
    init_auth_db()

    add_user("teacher", "teacher123", "teacher")
    
    if verbose:
        logger.info("Initializing Corpus DB...")
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

    # Validate generated cosine similarities before persisting embeddings.
    # Since the vectors are normalized, their dot product equals cosine similarity.
    alice_bob_similarity = float(np.dot(va, vb))
    alice_charlie_similarity = float(np.dot(va, vc))

    expected_alice_bob_similarity = 0.95
    expected_alice_charlie_similarity = 0.15
    similarity_tolerance = 1e-6

    if not np.isclose(
        alice_bob_similarity,
        expected_alice_bob_similarity,
        atol=similarity_tolerance,
        rtol=0.0,
    ):
        raise ValueError(
            "Mock embedding validation failed for Alice/Bob: "
            f"expected {expected_alice_bob_similarity}, "
            f"got {alice_bob_similarity:.6f}"
        )

    if not np.isclose(
        alice_charlie_similarity,
        expected_alice_charlie_similarity,
        atol=similarity_tolerance,
        rtol=0.0,
    ):
        raise ValueError(
            "Mock embedding validation failed for Alice/Charlie: "
            f"expected {expected_alice_charlie_similarity}, "
            f"got {alice_charlie_similarity:.6f}"
        )

    print(
        "Validated mock similarities: "
        f"Alice/Bob={alice_bob_similarity:.6f}, "
        f"Alice/Charlie={alice_charlie_similarity:.6f}"
    )

    # Format chunks: (vector_id, filename, chunk_index, chunk_text, embedding)
    chunks = [
        (0, "Introduction_to_AI.pdf", 0, text_alice, va),
        (1, "AI_Concepts_Homework.pdf", 0, text_bob, vb),
        (2, "Introduction_to_Blockchain.pdf", 0, text_charlie, vc),
    ]

    print("Inserting chunks...")
    add_chunks(chunks)



def main():
    parser_manager = ArgumentParserManager()
    args = parser_manager.parse()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug(f"Starting execution with configuration: {args}")

    clear_existing_databases(args.verbose)
    initialize_databases(args.verbose)

    # Initialize generators
    doc_gen = MockDocumentGenerator(args.seed)
    vec_gen = VectorMathGenerator(args.seed, args.dim)

    # Step 1: Generate Base Documents
    logger.info(f"Generating {args.documents} unique mock documents...")
    documents_data = []
    vectors = []
    chunks = []
    
    for i in range(args.documents):
        text = doc_gen.generate_document()
        student, cls, filename = doc_gen.generate_metadata()
        file_hash = hashlib.sha256(text.encode()).hexdigest()
        
        add_document(
            filename=filename,
            file_hash=file_hash,
            class_section=cls,
            student_name=student,
            assignment_title=f"Assignment {i+1}",
        )
        
        # Generate base vector for this document
        vec = vec_gen.generate_base_vector()
        vectors.append(vec)
        
        doc_info = {
            "id": i,
            "filename": filename,
            "text": text,
            "hash": file_hash,
            "student": student,
            "class": cls
        }
        documents_data.append(doc_info)
        
        # Add to chunk format: (vector_id, filename, chunk_index, chunk_text, embedding)
        chunks.append((i, filename, 0, text, vec))

    # Step 2: Generate High-Similarity Pairs (Plagiarism Incidents)
    logger.info(f"Generating {args.pairs} flagged plagiarism pairs...")
    
    # Select random pairs to be highly similar
    rng = random.Random(args.seed + 1)
    available_indices = list(range(args.documents))
    flags = []
    
    for p_idx in range(args.pairs):
        if len(available_indices) < 2:
            break
            
        idx_a = rng.choice(available_indices)
        available_indices.remove(idx_a)
        idx_b = rng.choice(available_indices)
        # Put idx_b back so a document can plagiarize from multiple sources, 
        # but remove idx_a to avoid self-loops or bidirectional exact duplicates in generation
        
        doc_a = documents_data[idx_a]
        doc_b = documents_data[idx_b]
        
        # Target similarity between 0.85 and 0.99
        sim = rng.uniform(0.85, 0.99)
        severity = "High" if sim > 0.90 else "Medium"
        
        # Override the vector of document A to be similar to document B
        new_vec = vec_gen.generate_similar_vector(vectors[idx_b], sim)
        vectors[idx_a] = new_vec
        
        # Update chunk for doc A
        chunks[idx_a] = (idx_a, doc_a["filename"], 0, doc_a["text"], new_vec)
        
        flags.append({
            "doc_a": doc_a["filename"],
            "doc_b": doc_b["filename"],
            "similarity": float(sim),
            "severity": severity,
        })
        
        if args.verbose:
            logger.debug(f"Created pair: {doc_a['filename']} <-> {doc_b['filename']} (Sim: {sim:.4f})")

    # Step 3: Insert Chunks
    logger.info("Inserting chunks into Corpus DB...")
    add_chunks(chunks)

    # Step 4: Sync Incidents
    logger.info("Syncing plagiarism incidents...")
    sync_flagged_incidents(flags, db_path=corpus_db_path)

    # Step 5: Build and Save FAISS Index
    logger.info("Building and saving FAISS index...")
    matrix = np.vstack(vectors)
    index = build_index_from_matrix(matrix)
    
    index_path = os.path.join(seed_dir, "corpus.index")
    save_index(index, index_path)


    # Validate generated seed data before reporting success
    print("Validating generated seed data...")

    expected_documents = 3
    expected_chunks = 3
    expected_incidents = 1
    expected_vectors = 3

    actual_documents = len(get_all_documents())
    actual_chunks = get_embedding_count()

    # Pass the seed DB path explicitly because incidents.py accepts a db_path
    # parameter and its function defaults are evaluated at definition time.
    corpus_db_path = os.path.join(seed_dir, "corpus.db")
    actual_incidents = len(get_all_incidents(db_path=corpus_db_path))

    # FAISS exposes the number of stored vectors through ntotal.
    actual_vectors = index.ntotal

    validation_checks = {
        "documents": (actual_documents, expected_documents),
        "chunks": (actual_chunks, expected_chunks),
        "incidents": (actual_incidents, expected_incidents),
        "FAISS vectors": (actual_vectors, expected_vectors),
    }

    validation_errors = []

    for name, (actual, expected) in validation_checks.items():
        if actual != expected:
            validation_errors.append(
                f"{name}: expected {expected}, found {actual}"
            )

    if validation_errors:
        raise RuntimeError(
            "Seed data validation failed: " + "; ".join(validation_errors)
        )

    print(
        "Seed data validation passed: "
        f"{actual_documents} documents, "
        f"{actual_chunks} chunks, "
        f"{actual_incidents} incident, "
        f"{actual_vectors} FAISS vectors."
    )

    print("Seed data successfully generated and stored in tests/dummy_data/!")

    logger.info("==========================================================")
    logger.info("Seed data successfully generated and stored in tests/dummy_data/!")
    logger.info(f"Total Documents: {args.documents}")
    logger.info(f"Total Flagged Pairs: {args.pairs}")
    logger.info(f"Dimensionality: {args.dim}")
    logger.info("==========================================================")



if __name__ == "__main__":
    main()