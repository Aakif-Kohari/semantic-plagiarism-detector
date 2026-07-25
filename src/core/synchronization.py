import os
import shutil
import logging
from datetime import datetime, timezone
from src.core.faiss_index import load_index, save_index, build_index_from_matrix
from src.db.corpus_db import get_embedding_count, get_all_embeddings

logger = logging.getLogger(__name__)

def verify_and_repair_index(index_path: str) -> None:
    """
    Verifies that the FAISS index vector count perfectly matches the number of durable
    chunk embeddings in the SQLite corpus database. 
    
    If there is a mismatch (caused by a crash during an upload/commit phase), 
    this function triggers a self-healing rebuild of the FAISS index from the source of truth (SQLite).
    """
    try:
        # 1. Check if FAISS index exists
        if not os.path.exists(index_path):
            logger.warning(f"FAISS index missing at {index_path}. Rebuilding from database.")
            _rebuild_index(index_path)
            return

        # 2. Load FAISS and get count
        index = load_index(index_path)
        faiss_count = index.ntotal
        
        # 3. Get SQLite count
        db_count = get_embedding_count()
        
        # 4. Compare
        if faiss_count == db_count:
            logger.info(f"FAISS sync verified: {faiss_count} vectors match database.")
        else:
            logger.error(f"FAISS desync detected! FAISS has {faiss_count} vectors, DB has {db_count}. Forcing rebuild.")
            _backup_corrupted_index(index_path)
            _rebuild_index(index_path)
            
    except Exception as e:
        logger.error(f"Failed during FAISS synchronization check: {e}. Attempting forced rebuild.")
        try:
            if os.path.exists(index_path):
                _backup_corrupted_index(index_path)
            _rebuild_index(index_path)
        except Exception as rebuild_err:
            logger.critical(f"FATAL: Database and FAISS are out of sync and rebuild failed: {rebuild_err}")

def _backup_corrupted_index(index_path: str) -> None:
    """
    Creates a backup of the corrupted/desynced FAISS index before overwriting it.
    This ensures that in the event of an ingestion fault, security forensics can 
    evaluate what vectors were lost.
    """
    try:
        if not os.path.exists(index_path):
            return
            
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(os.path.dirname(index_path), "backups")
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        backup_path = os.path.join(backup_dir, f"corpus_{timestamp}.index.bak")
        shutil.copy2(index_path, backup_path)
        logger.info(f"Backed up corrupted index to {backup_path}")
    except Exception as e:
        logger.warning(f"Failed to backup corrupted FAISS index: {e}")

def _rebuild_index(index_path: str) -> None:
    """
    Forces a complete rebuild of the FAISS index directly from the SQLite chunk BLOBs.
    """
    logger.info("Initiating full FAISS index rebuild from SQLite chunks...")
    
    # Extract matrix of all embeddings from DB
    matrix = get_all_embeddings()
    
    # Build a fresh index
    new_index = build_index_from_matrix(matrix)
    
    # Overwrite the corrupt/missing index on disk
    save_index(new_index, index_path)
    logger.info(f"FAISS index successfully rebuilt and saved with {new_index.ntotal} vectors.")
