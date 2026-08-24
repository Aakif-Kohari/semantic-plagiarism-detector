# semantic-plagiarism-detector/src/api/endpoints/patchwriting_scan.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from src.core.patchwriting_detector import PatchwritingDetector
from src.db.patchwriting_logs_db import PatchwritingLogsDB

router = APIRouter(prefix="/api/v1/patchwriting", tags=["Mosaic Plagiarism Detection"])
db = PatchwritingLogsDB()

class ScanRequest(BaseModel):
    submission_id: str
    source_id: str
    source_text: str
    student_text: str

@router.post("/scan")
def scan_mosaic_plagiarism(payload: ScanRequest) -> Dict[str, Any]:
    """Exposes syntactic POS analysis and mosaic plagiarism detection via REST."""
    try:
        results = PatchwritingDetector.compute_syntactic_similarity(
            payload.source_text, payload.student_text
        )
        
        # Log detection event
        db.log_structural_clone(
            submission_id=payload.submission_id,
            source_id=payload.source_id,
            similarity_score=results["similarity_score"],
            metrics=results
        )
        
        return {
            "status": "success",
            "submission_id": payload.submission_id,
            "analysis": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
