import hashlib
from src.security.obfuscation_detector import ObfuscationDetector
# from src.db.obfuscation_logs_db import log_obfuscation_incident

class AdversarialAnalysisPipeline:
    def __init__(self):
        self.detector = ObfuscationDetector()

    def process_document_text(self, raw_text: str, document_id: str) -> dict:
        """
        Intercepts and evaluates raw text before sending it to similarity engines.
        Quarantines documents that cross the safety threshold.
        """
        # Calculate consistent SHA-256 fingerprint hash for auditing records
        doc_hash = hashlib.sha256(raw_text.encode('utf-8')).hexdigest()
        
        # Execute security inspection check
        metrics = self.detector.analyze_text(raw_text)
        
        if metrics["is_flagged"]:
            # Construct log profile structure
            log_payload = {
                "document_id": document_id,
                "document_hash": doc_hash,
                "obfuscation_score": metrics["obfuscation_score"],
                "patterns_found": {
                    "invisible_count": len(metrics["invisible_indices"]),
                    "homoglyph_count": len(metrics["homoglyph_indices"])
                }
            }
            # Commit incident to the database
            # log_obfuscation_incident(log_payload)
            print(f"🚨 [Security Alert]: Adversarial pattern discovered on file {document_id}. Hash: {doc_hash}")

        return {
            "allow_pipeline_execution": not metrics["is_flagged"],
            "security_metrics": metrics,
            "document_hash": doc_hash
        }
