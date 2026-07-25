import io
import zipfile
import json
from datetime import datetime

def generate_bulk_reports_zip(flags: list) -> bytes:
    """Generate a ZIP file containing JSON reports for all flagged pairs."""
    memory_file = io.BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for idx, flag in enumerate(flags):
            doc1 = flag.get("doc1", f"docA_{idx}")
            doc2 = flag.get("doc2", f"docB_{idx}")
            score = flag.get("similarity_score", 0.0)
            
            # Clean filenames
            safe_doc1 = "".join([c for c in doc1 if c.isalnum() or c in ('-', '_')]).rstrip()
            safe_doc2 = "".join([c for c in doc2 if c.isalnum() or c in ('-', '_')]).rstrip()
            
            filename = f"report_{safe_doc1}_{safe_doc2}.json"
            
            report_data = {
                "generated_at": datetime.now().isoformat(),
                "document_1": doc1,
                "document_2": doc2,
                "similarity_score": score,
                "chunks": flag.get("matched_chunks", []),
            }
            
            zf.writestr(filename, json.dumps(report_data, indent=2))
            
    return memory_file.getvalue()
