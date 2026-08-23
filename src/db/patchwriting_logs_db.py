# semantic-plagiarism-detector/src/db/patchwriting_logs_db.py

from typing import List, Dict, Any
from datetime import datetime

class PatchwritingLogsDB:
    """
    Logs detected structural clones and the specific POS patterns matched 
    during mosaic plagiarism detection scans.
    """
    def __init__(self):
        self.logs_store: List[Dict[str, Any]] = []

    def log_structural_clone(self, submission_id: str, source_id: str, similarity_score: float, metrics: Dict[str, Any]) -> None:
        """Persists a structural clone detection record."""
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "submission_id": submission_id,
            "source_id": source_id,
            "similarity_score": similarity_score,
            "metrics": metrics
        }
        self.logs_store.append(record)

    def fetch_logs_by_submission(self, submission_id: str) -> List[Dict[str, Any]]:
        """Retrieves all patchwriting logs for a given submission."""
        return [log for log in self.logs_store if log["submission_id"] == submission_id]

    def fetch_all_logs(self) -> List[Dict[str, Any]]:
        """Retrieves all recorded patchwriting logs."""
        return self.logs_store
