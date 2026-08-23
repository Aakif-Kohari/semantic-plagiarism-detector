# semantic-plagiarism-detector/src/api/endpoints/tool_detection.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from src.core.paraphrase_fingerprinter import ParaphraseFingerprinter
from src.db.tool_signatures_db import ToolSignaturesDB

router = APIRouter(prefix="/api/v1/paraphrase-detection", tags=["Paraphrase Tool Fingerprinting"])
db = ToolSignaturesDB()
fingerprinter = ParaphraseFingerprinter()

class TextPayload(BaseModel):
    text: str

@router.post("/detect")
def detect_paraphrase_tool(payload: TextPayload) -> Dict[str, Any]:
    """Exposes automated paraphrase tool fingerprinting and attribution via REST."""
    try:
        features = fingerprinter.extract_fingerprint(payload.text)
        match_result = db.match_signature(features)
        
        return {
            "status": "success",
            "extracted_features": features,
            "attribution": match_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
