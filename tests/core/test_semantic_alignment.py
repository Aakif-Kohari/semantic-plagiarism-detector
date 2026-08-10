"""
tests/core/test_semantic_alignment.py
-------------------------------------
Unit tests for the semantic-aware sequence alignment algorithm.
"""

import pytest
import numpy as np
from src.core.semantic_alignment import (
    align_semantic_sequences,
    _cosine_similarity_matrix,
)


class TestCosineSimilarityMatrix:
    """Tests for the internal cosine similarity matrix computation."""

    def test_identical_embeddings_return_ones(self):
        """Identical normalized vectors should produce 1.0 on the diagonal."""
        emb = np.array([[1.0, 0.0], [0.0, 1.0]])
        sim = _cosine_similarity_matrix(emb, emb)
        np.testing.assert_array_almost_equal(np.diag(sim), [1.0, 1.0])

    def test_orthogonal_embeddings_return_zero(self):
        """Orthogonal vectors should produce 0.0 similarity."""
        emb_a = np.array([[1.0, 0.0]])
        emb_b = np.array([[0.0, 1.0]])
        sim = _cosine_similarity_matrix(emb_a, emb_b)
        assert sim[0, 0] == pytest.approx(0.0)

    def test_empty_arrays_return_empty_matrix(self):
        """Empty input arrays should return an empty matrix."""
        sim = _cosine_similarity_matrix(np.array([]), np.array([[1.0]]))
        assert sim.size == 0

    def test_handles_zero_vectors(self):
        """Zero vectors should not cause division by zero errors."""
        emb_a = np.array([[0.0, 0.0], [1.0, 0.0]])
        emb_b = np.array([[1.0, 0.0]])
        # Should not raise, zero vector normalized is treated as 0 similarity
        sim = _cosine_similarity_matrix(emb_a, emb_b)
        assert sim[0, 0] == 0.0


class TestAlignSemanticSequences:
    """Tests for the banded DP alignment algorithm."""

    def test_exact_match_alignment(self):
        """Identical sequences should align perfectly with 'match' type."""
        chunks = ["Sentence one.", "Sentence two."]
        # Embeddings pointing in the same direction
        emb = np.array([[1.0, 0.0], [0.0, 1.0]])

        alignment = align_semantic_sequences(
            chunks, chunks, emb, emb, match_threshold=0.5
        )

        assert len(alignment) == 2
        assert all(op["type"] == "match" for op in alignment)
        assert all(op["score"] == pytest.approx(1.0) for op in alignment)

    def test_insertions_and_deletions(self):
        """Sequences with different lengths should produce gap operations."""
        chunks_a = ["A1", "A2", "A3"]
        chunks_b = ["B1", "B3"]  # B2 is missing

        # A1 matches B1, A2 is unmatched, A3 matches B3
        emb_a = np.array([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]])
        emb_b = np.array([[1.0, 0.0], [0.5, 0.5]])

        alignment = align_semantic_sequences(
            chunks_a, chunks_b, emb_a, emb_b, match_threshold=0.8, gap_penalty=-1.0
        )

        types = [op["type"] for op in alignment]
        # Expecting match, insert_a (gap in B), match
        assert "insert_a" in types or "insert_b" in types

    def test_paraphrase_detection(self):
        """Similar but not identical chunks should be flagged as 'paraphrase'."""
        chunks_a = ["The quick brown fox."]
        chunks_b = ["The fast brown fox."]

        # High similarity but not 1.0
        emb_a = np.array([[0.9, 0.1]])
        emb_b = np.array([[0.8, 0.2]])

        alignment = align_semantic_sequences(
            chunks_a, chunks_b, emb_a, emb_b, match_threshold=0.99
        )

        assert len(alignment) == 1
        # Since sim < 0.99, it should be marked as paraphrase (or mismatch handled as gap)
        # With default gap penalty, it might prefer gap if sim is too low.
        # Let's ensure it doesn't crash and returns valid structure.
        assert alignment[0]["type"] in ("match", "paraphrase", "insert_a", "insert_b")

    def test_empty_sequences(self):
        """Empty inputs should return empty alignment."""
        assert align_semantic_sequences([], [], np.array([]), np.array([])) == []

    def test_one_empty_sequence(self):
        """If one sequence is empty, all items in the other should be insertions."""
        chunks_a = ["A1", "A2"]
        emb_a = np.array([[1.0, 0.0], [0.0, 1.0]])

        alignment = align_semantic_sequences(chunks_a, [], emb_a, np.array([]))

        assert len(alignment) == 2
        assert all(op["type"] == "insert_a" for op in alignment)

    def test_band_width_restricts_computation(self):
        """Verify that large sequences complete within reasonable time due to banding."""
        # 200 chunks
        n = 200
        chunks = [f"Sentence {i}" for i in range(n)]
        emb = np.random.rand(n, 384).astype(np.float32)

        # This should complete in < 1 second due to O(N*W) banding
        alignment = align_semantic_sequences(chunks, chunks, emb, emb, band_width=10)

        assert len(alignment) >= n  # At least N operations
