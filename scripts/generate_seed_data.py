"""
Generate deterministic seed databases and a FAISS index.

The optional ``--target-similarity`` flag controls the cosine
similarity of the seeded Alice/Bob plagiarism pair.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass

import numpy as np


# Ensure repository root is in sys.path.
ROOT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
sys.path.insert(0, ROOT_DIR)

SEED_DIR = os.path.join(
    ROOT_DIR,
    "tests",
    "dummy_data",
)
os.makedirs(SEED_DIR, exist_ok=True)

DEFAULT_TARGET_SIMILARITY = 0.95
BACKGROUND_SIMILARITY = 0.15
EMBEDDING_DIMENSION = 384
RANDOM_SEED = 42

import src.db.auth
import src.db.corpus_db
import src.db.incidents

src.db.auth._DB_PATH = os.path.join(seed_dir, USERS_DB_FILENAME)
src.db.corpus_db._DB_PATH = os.path.join(seed_dir, CORPUS_DB_FILENAME)
src.db.incidents.DEFAULT_DB_PATH = os.path.join(seed_dir, CORPUS_DB_FILENAME)

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




from src.db.corpus_db import (
    get_all_documents,
    get_embedding_count,
)
from src.db.incidents import get_all_incidents

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


def parse_target_similarity(value: str) -> float:
    """Parse decimal or percentage similarity into ``0.0``–``1.0``.

    Supported examples include ``0.85``, ``85``, and ``85%``.
    """
    raw_value = value.strip()
    is_percentage = raw_value.endswith("%")
    numeric_text = (
        raw_value[:-1].strip()
        if is_percentage
        else raw_value
    )

    try:
        parsed_value = float(numeric_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "target similarity must be a number such as "
            "0.85, 85, or 85%"
        ) from exc

    if is_percentage or parsed_value > 1.0:
        parsed_value /= 100.0

    if not 0.0 <= parsed_value <= 1.0:
        raise argparse.ArgumentTypeError(
            "target similarity must be between 0 and 1 "
            "(or between 0% and 100%)"
        )

    return parsed_value


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the seed-data command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic seed databases and a FAISS "
            "index for local testing."
        )
    )
    parser.add_argument(
        "--target-similarity",
        type=parse_target_similarity,
        default=DEFAULT_TARGET_SIMILARITY,
        metavar="VALUE",
        help=(
            "Cosine similarity for the flagged Alice/Bob pair. "
            "Accepts 0.85, 85, or 85%% "
            f"(default: {DEFAULT_TARGET_SIMILARITY})."
        ),
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed similarity validation output.",
    )
    return parser


def parse_args(
    argv: list[str] | None = None,
) -> SeedConfig:
    """Parse and return validated generator configuration."""
    namespace = build_argument_parser().parse_args(argv)
    return SeedConfig(
        target_similarity=namespace.target_similarity,
        verbose=namespace.verbose,
    )


def generate_similar_vector(
    base_vector: np.ndarray,
    target_similarity: float,
    random_generator: np.random.Generator,
) -> np.ndarray:
    """Create a unit vector at an exact cosine similarity."""
    noise = random_generator.standard_normal(
        base_vector.shape[0]
    )
    noise -= np.dot(noise, base_vector) * base_vector

    noise_norm = np.linalg.norm(noise)
    if noise_norm < 1e-12:
        raise RuntimeError(
            "Unable to generate an orthogonal noise vector."
        )

    noise /= noise_norm
    generated = (
        target_similarity * base_vector
        + np.sqrt(1 - target_similarity**2) * noise
    )
    generated /= np.linalg.norm(generated)
    return generated


def calculate_cosine_similarity(
    first: np.ndarray,
    second: np.ndarray,
) -> float:
    """Return cosine similarity for two non-zero vectors."""
    denominator = (
        np.linalg.norm(first)
        * np.linalg.norm(second)
    )
    if denominator == 0:
        raise ValueError(
            "Cosine similarity requires non-zero vectors."
        )
    return float(np.dot(first, second) / denominator)


def validate_target_similarity(
    base_vector: np.ndarray,
    generated_vector: np.ndarray,
    target_similarity: float,
    *,
    tolerance: float = 1e-6,
) -> float:
    """Validate the generated pair before persistence."""
    actual_similarity = calculate_cosine_similarity(
        base_vector,
        generated_vector,
    )

    if not np.isclose(
        actual_similarity,
        target_similarity,
        atol=tolerance,
        rtol=0.0,
    ):
        raise ValueError(
            "Generated similarity does not match target: "
            f"expected {target_similarity:.6f}, "
            f"got {actual_similarity:.6f}"
        )

    return actual_similarity


def _clean_seed_files() -> None:
    """Delete previously generated seed artifacts."""
    for filename in (
        "users.db",
        "corpus.db",
        "corpus.index",
    ):
        path = os.path.join(SEED_DIR, filename)
        if not os.path.exists(path):
            continue

        try:
            os.remove(path)
            print(f"Removed old seed {filename}")
        except OSError as error:
            print(
                "Warning: Could not remove old seed "
                f"{filename} ({error})"
            )


def main(
    argv: list[str] | None = None,
) -> None:
    """Generate databases, incidents, embeddings, and FAISS index."""
    config = parse_args(argv)

    # Sync plagiarism incidents
    print("Syncing plagiarism incidents...")
    flags = [
        {
            "doc_a": BOB_FILENAME,
            "doc_b": ALICE_FILENAME,
            "similarity": ALICE_BOB_SIMILARITY,
        }
    ]
    sync_flagged_incidents(flags)



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
    sync_flagged_incidents(flags, db_path=os.path.join(seed_dir, "corpus.db"))

    # Step 5: Build and Save FAISS Index
    logger.info("Building and saving FAISS index...")
    matrix = np.vstack(vectors)
    index = build_index_from_matrix(matrix)

    print("Initializing databases...")
    init_auth_db()
    add_user(
        "teacher",
        "teacher123",
        "teacher",
    )
    print("Auth DB initialized and seeded.")

    init_corpus_db()
    print("Corpus DB initialized.")

    text_alice = (
        "Artificial intelligence (AI) is intelligence "
        "demonstrated by machines, in contrast to the natural "
        "intelligence displayed by humans and other animals. "
        "Study of intelligent agents: any device that perceives "
        "its environment and takes actions that maximize its "
        "chance of successfully achieving its goals."
    )
    text_bob = (
        "Artificial intelligence (AI) is intelligence "
        "demonstrated by machines, in contrast to the natural "
        "intelligence displayed by humans and other animals. "
        "Study of intelligent agents: any device that perceives "
        "its environment and takes actions that maximize its "
        "chance of successfully achieving its goals."
    )
    text_charlie = (
        "A blockchain is a decentralized, distributed, and "
        "public digital ledger used to record transactions "
        "across many computers."
    )

    documents = [
        (
            "Introduction_to_AI.pdf",
            text_alice,
            "Alice Smith",
        ),
        (
            "AI_Concepts_Homework.pdf",
            text_bob,
            "Bob Jones",
        ),
        (
            "Introduction_to_Blockchain.pdf",
            text_charlie,
            "Charlie Brown",
        ),
    ]

    print("Adding dummy documents...")
    for filename, text, student_name in documents:
        add_document(
            filename=filename,
            file_hash=hashlib.sha256(
                text.encode()
            ).hexdigest(),
            class_section="CS-101",
            student_name=student_name,
            assignment_title="Final Essay",
        )

    print(
        "Generating mock embeddings with mathematical "
        "similarities..."
    )
    random_generator = np.random.default_rng(
        RANDOM_SEED
    )

    alice_vector = random_generator.standard_normal(
        EMBEDDING_DIMENSION
    )
    alice_vector /= np.linalg.norm(alice_vector)

    bob_vector = generate_similar_vector(
        alice_vector,
        config.target_similarity,
        random_generator,
    )
    actual_target_similarity = validate_target_similarity(
        alice_vector,
        bob_vector,
        config.target_similarity,
    )

    charlie_vector = generate_similar_vector(
        alice_vector,
        BACKGROUND_SIMILARITY,
        random_generator,
    )
    validate_target_similarity(
        alice_vector,
        charlie_vector,
        BACKGROUND_SIMILARITY,
    )

    if config.verbose:
        print(
            "Validated target pair similarity: "
            f"requested={config.target_similarity:.6f}, "
            f"actual={actual_target_similarity:.6f}"
        )

    chunks = [
        (
            0,
            "Introduction_to_AI.pdf",
            0,
            text_alice,
            alice_vector,
        ),
        (
            1,
            "AI_Concepts_Homework.pdf",
            0,
            text_bob,
            bob_vector,
        ),
        (
            2,
            "Introduction_to_Blockchain.pdf",
            0,
            text_charlie,
            charlie_vector,
        ),
    ]

    print("Inserting chunks...")
    add_chunks(chunks)

    print("Syncing plagiarism incidents...")
    sync_flagged_incidents(
        [
            {
                "doc_a": "AI_Concepts_Homework.pdf",
                "doc_b": "Introduction_to_AI.pdf",
                "similarity": actual_target_similarity,
                "severity": (
                    "High"
                    if actual_target_similarity >= 0.80
                    else "Medium"
                ),
            }
        ]
    )

    print("Building and saving FAISS index...")
    matrix = np.vstack(
        [
            alice_vector,
            bob_vector,
            charlie_vector,
        ]
    )
    index = build_index_from_matrix(matrix)
    save_index(
        index,
        os.path.join(SEED_DIR, "corpus.index"),
    )

    print(
        "Seed data successfully generated with target "
        f"similarity {actual_target_similarity:.1%} and stored "
        "in tests/dummy_data/!"
    )


if __name__ == "__main__":
    main()
