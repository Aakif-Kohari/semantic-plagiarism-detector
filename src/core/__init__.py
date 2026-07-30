from .document_parser import (
    extract_text_from_pdf,
    extract_texts_from_pdfs,
    extract_text,
    extract_texts,
)
from .text_chunking import chunk_document, chunk_documents
from .embedding_model import embed_chunks, embed_documents, get_document_embedding
from .similarity import (
    document_similarity_matrix,
    chunk_similarity_matrix,
    flag_plagiarism,
    find_most_similar_chunks,
    PLAGIARISM_THRESHOLD,
)
from .faiss_index import (
    build_index,
    search_similar_chunks,
    find_plagiarised_chunks,
    save_index,
    load_index,
    ChunkRecord,
    build_index_from_matrix,
)
from .translator import translate_text
from .webhook import send_plagiarism_alert
from .config import (
    BrandingConfig,
    get_branding_config,
    reload_branding_config,
    load_branding_config,
)

__all__ = [
    "extract_text_from_pdf",
    "extract_texts_from_pdfs",
    "extract_text",
    "extract_texts",
    "chunk_document",
    "chunk_documents",
    "embed_chunks",
    "embed_documents",
    "get_document_embedding",
    "document_similarity_matrix",
    "chunk_similarity_matrix",
    "flag_plagiarism",
    "find_most_similar_chunks",
    "PLAGIARISM_THRESHOLD",
    "build_index",
    "search_similar_chunks",
    "find_plagiarised_chunks",
    "save_index",
    "load_index",
    "ChunkRecord",
    "build_index_from_matrix",
    "translate_text",
    "send_plagiarism_alert",
    "BrandingConfig",
    "get_branding_config",
    "reload_branding_config",
    "load_branding_config",
]
