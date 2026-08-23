# semantic-plagiarism-detector/src/core/reliability_engine.py

import numpy as np
from typing import List, Dict, Any

class ReliabilityEngine:
    """
    Statistical engine for calculating Inter-Rater Reliability (IRR) metrics
    such as Fleiss' Kappa, Cohen's Kappa, and reviewer calibration weights.
    """

    @staticmethod
    def compute_cohens_kappa(rater1: List[int], rater2: List[int]) -> float:
        """Computes Cohen's Kappa for agreement between two reviewers."""
        if len(rater1) != len(rater2) or not rater1:
            return 0.0
            
        r1 = np.array(rater1)
        r2 = np.array(rater2)
        n = len(r1)
        
        # Observed agreement
        obs_agreement = np.sum(r1 == r2) / n
        
        # Expected agreement by chance
        classes = np.unique(np.concatenate([r1, r2]))
        p_e = 0.0
        for c in classes:
            p1 = np.sum(r1 == c) / n
            p2 = np.sum(r2 == c) / n
            p_e += p1 * p2
            
        if p_e == 1.0:
            return 1.0
            
        kappa = (obs_agreement - p_e) / (1.0 - p_e)
        return float(kappa)

    @staticmethod
    def compute_fleiss_kappa(ratings_matrix: List[List[int]]) -> float:
        """
        Computes Fleiss' Kappa for multi-rater agreement across review committees.
        Ratings matrix shape: N subjects x K categories, where each cell is the number of raters who assigned that category.
        """
        mat = np.array(ratings_matrix)
        if mat.size == 0:
            return 0.0
            
        n_subjects, n_categories = mat.shape
        # Total number of raters per subject (assumed constant)
        N = np.sum(mat[0])
        if N <= 1:
            return 0.0
            
        # Proportion of all assignments assigned to the j-th category
        p_j = np.sum(mat, axis=0) / (n_subjects * N)
        
        # Extent to which raters agree for the i-th subject
        P_i = (np.sum(mat ** 2, axis=1) - N) / (N * (N - 1))
        
        # Mean of P_i across all subjects
        P_bar = np.mean(P_i)
        
        # Sum of squares of proportions
        P_e_bar = np.sum(p_j ** 2)
        
        if P_e_bar == 1.0:
            return 1.0
            
        kappa = (P_bar - P_e_bar) / (1.0 - P_e_bar)
        return float(kappa)

    @staticmethod
    def compute_reviewer_bias_weights(historical_overrides: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Computes calibration bias weights for reviewers based on historical deviation from committee consensus.
        """
        weights = {}
        for record in historical_overrides:
            reviewer_id = record.get("reviewer_id")
            deviation = record.get("consensus_deviation", 0.0)
            # Higher deviation from consensus reduces override confidence weight
            weight = max(0.1, 1.0 - abs(float(deviation)))
            weights[reviewer_id] = round(weight, 3)
            
        return weights
