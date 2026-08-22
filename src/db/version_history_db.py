import hashlib
from datetime import datetime

# In-memory document storage mock engine; replace with your active Prisma/Supabase models seamlessly
VERSION_LINEAGE_CACHE = {}

def register_document_draft(user_id: str, document_text: str, filename: str) -> dict:
    """
    Saves and maps draft relationships inside the version control schema.
    
    Expected Database Schema Target:
    CREATE TABLE document_drafts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL,
        doc_hash CHAR(64) UNIQUE NOT NULL,
        parent_hash CHAR(64) REFERENCES document_drafts(doc_hash),
        version_number INT DEFAULT 1,
        filename VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    doc_hash = hashlib.sha256(document_text.encode('utf-8')).hexdigest()
    
    # Query history to locate existing user versions to build parent connections
    user_history = [v for v in VERSION_LINEAGE_CACHE.values() if v["user_id"] == user_id]
    
    parent_hash = None
    version_number = 1
    
    if user_history:
        # Sort to find the immediate prior draft configuration
        user_history.sort(key=lambda x: x["version_number"], reverse=True)
        latest_draft = user_history[0]
        
        if latest_draft["doc_hash"] != doc_hash:
            parent_hash = latest_draft["doc_hash"]
            version_number = latest_draft["version_number"] + 1
        else:
            return latest_draft # Document already archived, bypass insertion loops

    draft_record = {
        "user_id": user_id,
        "doc_hash": doc_hash,
        "parent_hash": parent_hash,
        "version_number": version_number,
        "filename": filename,
        "created_at": datetime.utcnow().isoformat()
    }
    
    VERSION_LINEAGE_CACHE[doc_hash] = draft_record
    return draft_record
