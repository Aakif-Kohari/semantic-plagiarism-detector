# semantic-plagiarism-detector/src/db/reviewer_calibration_db.py

from typing import List, Dict, Any

class ReviewerCalibrationDB:
    """
    Persists historical review overrides and computes reviewer bias metrics.
    """
    def __init__(self):
        # In-memory storage mock for demonstration (replace with SQL/ORM in production)
        self.overrides_store: List[Dict[str, Any]] = []

    def save_review_override(self, submission_id: str, reviewer_id: str, assigned_score: float, consensus_score: float) -> None:
        """Persists a reviewer override event along with its deviation from consensus."""
        deviation = assigned_score - consensus_score
        record = {
            "submission_id": submission_id,
            "reviewer_id": reviewer_id,
            "assigned_score": assigned_score,
            "consensus_score": consensus_score,
            "consensus_deviation": deviation
        }
        self.overrides_store.append(record)

    def fetch_reviewer_history(self, reviewer_id: str) -> List[Dict[str, Any]]:
        """Retrieves all historical review overrides for a specific reviewer."""
        return [r for r in self.overrides_store if r["reviewer_id"] == reviewer_id]

    def fetch_all_overrides(self) -> List[Dict[str, Any]]:
        """Retrieves entire override dataset for committee IRR calculations."""
        return self.overrides_store
