# semantic-plagiarism-detector/src/api/endpoints/calibration.py

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from src.core.reliability_engine import ReliabilityEngine
from src.db.reviewer_calibration_db import ReviewerCalibrationDB

router = APIRouter(prefix="/api/v1/calibration", tags=["Reviewer Calibration & IRR"])
db = ReviewerCalibrationDB()
engine = ReliabilityEngine()

@router.get("/reviewer/{reviewer_id}")
def get_reviewer_calibration(reviewer_id: str) -> Dict[str, Any]:
    """Fetches calibration scores and historical bias weighting for a specific reviewer."""
    history = db.fetch_reviewer_history(reviewer_id)
    if not history:
        raise HTTPException(status_code=404, detail="Reviewer history not found.")
        
    weights = engine.compute_reviewer_bias_weights(history)
    return {
        "reviewer_id": reviewer_id,
        "total_reviews": len(history),
        "calibration_weight": weights.get(reviewer_id, 1.0)
    }

@router.get("/committee/irr")
def get_committee_irr(ratings_matrix: List[List[int]]) -> Dict[str, float]:
    """Computes and returns committee Inter-Rater Reliability (Fleiss' Kappa)."""
    kappa = engine.compute_fleiss_kappa(ratings_matrix)
    return {
        "fleiss_kappa": kappa,
        "reliability_status": "High Agreement" if kappa > 0.6 else "Moderate/Low Agreement"
    }
