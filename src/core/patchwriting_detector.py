# semantic-plagiarism-detector/src/core/patchwriting_detector.py

from typing import Dict, Any, List
from src.core.pos_normalizer import POSNormalizer
import difflib

class PatchwritingDetector:
    """
    Computes syntactic similarity using n-gram overlap on POS sequences and 
    structural edit distance to detect mosaic plagiarism.
    """

    @staticmethod
    def _get_ngrams(sequence: List[str], n: int = 3) -> set:
        """Generates n-grams from a sequence of POS tags."""
        if len(sequence) < n:
            return {tuple(sequence)}
        return {tuple(sequence[i:i+n]) for i in range(len(sequence) - n + 1)}

    @classmethod
    def compute_syntactic_similarity(cls, source_text: str, student_text: str, n: int = 3) -> Dict[str, Any]:
        """
        Computes structural similarity between source and student text using POS n-grams and sequence matching.
        """
        source_pos = POSNormalizer.extract_pos_sequence(source_text)
        student_pos = POSNormalizer.extract_pos_sequence(student_text)

        if not source_pos or not student_pos:
            return {"similarity_score": 0.0, "matched_patterns": []}

        # N-gram overlap calculation
        source_ngrams = cls._get_ngrams(source_pos, n)
        student_ngrams = cls._get_ngrams(student_pos, n)

        if not source_ngrams or not student_ngrams:
            ngram_similarity = 0.0
        else:
            intersection = source_ngrams.intersection(student_ngrams)
            union = source_ngrams.union(student_ngrams)
            ngram_similarity = len(intersection) / len(union) if union else 0.0

        # Sequence edit-distance alignment score
        matcher = difflib.SequenceMatcher(None, source_pos, student_pos)
        sequence_score = matcher.ratio()

        # Combined composite structural similarity score
        composite_score = round((0.6 * sequence_score) + (0.4 * ngram_similarity), 3)

        return {
            "similarity_score": composite_score,
            "ngram_similarity": round(ngram_similarity, 3),
            "sequence_alignment_score": round(sequence_score, 3),
            "source_pos_sample": "-".join(source_pos[:10]),
            "student_pos_sample": "-".join(student_pos[:10])
        }
