"""
src/core/embeddings.py
----------------------
Generates semantic embeddings for text documents using SentenceTransformers.
"""

from sentence_transformers import SentenceTransformer

# Load a lightweight, fast model for semantic embeddings
_model = SentenceTransformer("all-MiniLM-L6-v2")


def generate_embeddings(texts: list[str]):
    """
    Generate dense vector embeddings for a list of input text strings.
    """
    if not texts:
        return []
    embeddings = _model.encode(texts, convert_to_numpy=True)
    return embeddings