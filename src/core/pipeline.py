"""
Document Execution Pipeline Module.

Encapsulates document processing, chunking orchestration, vector embedding,
FAISS index construction, similarity matrix calculation, and AI detection.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.core.ai_detector import detect_documents_ai_probability
from src.core.document_parser import (
    extract_text,
    prepare_text_for_embedding,
)
from src.core.embedding_model import embed_chunks, embed_documents
from src.core.faiss_index import (
    build_index,
    build_index_from_matrix,
)
from src.core.similarity import (
    cosine_similarity,
    document_similarity_matrix,
)
from src.core.text_chunking import chunk_documents

logger = logging.getLogger(__name__)


class ChunkRecord:
    """Record container representing an extracted text chunk."""

    def __init__(self, doc_name, chunk_index, chunk_text, chunk_id=None):
        self.doc_name = doc_name
        self.chunk_index = chunk_index
        self.chunk_text = chunk_text
        self.chunk_id = chunk_id


def run_pipeline(
    file_bytes_dict: dict,
    ocr_language: str,
    ocr_dpi: int,
    chunk_size: int,
    chunk_overlap: int,
):
    """Run the document parsing -> chunking -> embedding -> similarity pipeline.

    Parameters
    ----------
    file_bytes_dict : dict
        Mapping of filename to raw file bytes.
    ocr_language : str
        OCR language code (e.g., 'eng').
    ocr_dpi : int
        DPI resolution for OCR rendering.
    chunk_size : int
        Target character length for chunking.
    chunk_overlap : int
        Character overlap between consecutive chunks.

    Returns
    -------
    tuple
        (raw_texts, chunked_docs, emb_matrix, sim_df, chunk_sim_df, faiss_index, registry, ai_probabilities)
    """
    raw_texts = []
    chunked_docs = []
    embeddings = []
    registry = []
    ai_probabilities = []

    if not file_bytes_dict:
        empty_sim_df = pd.DataFrame(columns=["doc_a", "doc_b", "similarity"])
        empty_chunk_df = pd.DataFrame(
            columns=["doc_name", "chunk_index", "chunk_text", "similarity"]
        )
        return (
            raw_texts,
            chunked_docs,
            np.empty((0, 0), dtype=float),
            empty_sim_df,
            empty_chunk_df,
            None,
            registry,
            ai_probabilities,
        )

    for filename, file_bytes in file_bytes_dict.items():
        try:
            extracted_text = extract_text(
                file_bytes,
                filename=filename,
                language=ocr_language,
                dpi=ocr_dpi,
            )
        except Exception:
            extracted_text = ""

        if not extracted_text:
            continue

        prepared_text = prepare_text_for_embedding(extracted_text)
        raw_texts.append(prepared_text)

        text_chunks = chunk_documents(
            [prepared_text],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        if not text_chunks:
            continue

        chunked_docs.extend(text_chunks)
        chunk_vectors = embed_chunks(text_chunks)
        if isinstance(chunk_vectors, np.ndarray):
            embeddings.extend(chunk_vectors.tolist())
        else:
            embeddings.extend(chunk_vectors)

        for chunk_index, chunk_text in enumerate(text_chunks):
            registry.append(
                ChunkRecord(
                    doc_name=filename,
                    chunk_index=chunk_index,
                    chunk_text=chunk_text,
                    chunk_id=f"{filename}:{chunk_index}",
                )
            )

    if embeddings:
        emb_matrix = np.asarray(embeddings, dtype=float)
        if emb_matrix.ndim == 1:
            emb_matrix = emb_matrix.reshape(1, -1)
        faiss_index = build_index_from_matrix(emb_matrix)
    else:
        emb_matrix = np.empty((0, 0), dtype=float)
        faiss_index = None

    doc_names = [Path(name).stem for name in file_bytes_dict.keys()]
    if len(raw_texts) > 1:
        doc_embeddings = []
        for text in raw_texts:
            text_chunks = chunk_documents(
                [text],
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            if not text_chunks:
                continue
            chunk_vectors = embed_chunks(text_chunks)
            if isinstance(chunk_vectors, np.ndarray):
                doc_embeddings.append(np.mean(chunk_vectors, axis=0))
            else:
                doc_embeddings.append(
                    np.mean(np.asarray(chunk_vectors, dtype=float), axis=0)
                )

        if doc_embeddings:
            doc_matrix = np.asarray(doc_embeddings, dtype=float)
            if doc_matrix.ndim == 1:
                doc_matrix = doc_matrix.reshape(1, -1)
            sim_matrix = cosine_similarity(doc_matrix)
            sim_rows = []
            for i in range(len(doc_names)):
                for j in range(i + 1, len(doc_names)):
                    sim_rows.append(
                        {
                            "doc_a": doc_names[i],
                            "doc_b": doc_names[j],
                            "similarity": float(sim_matrix[i, j]),
                        }
                    )
            sim_df = pd.DataFrame(sim_rows)
        else:
            sim_df = pd.DataFrame(columns=["doc_a", "doc_b", "similarity"])
    else:
        sim_df = pd.DataFrame(columns=["doc_a", "doc_b", "similarity"])

    chunk_sim_df = pd.DataFrame(
        columns=["doc_name", "chunk_index", "chunk_text", "similarity"]
    )

    return (
        raw_texts,
        chunked_docs,
        emb_matrix,
        sim_df,
        chunk_sim_df,
        faiss_index,
        registry,
        ai_probabilities,
    )


def run_extraction_pipeline(
    raw_texts_items: tuple,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
):
    """Cached extraction pipeline for text dictionary processing.

    Parameters
    ----------
    raw_texts_items : tuple
        Tuple of (filename, text) pairs.
    chunk_size : int
        Target character chunk size.
    chunk_overlap : int
        Chunk character overlap.

    Returns
    -------
    tuple
        (chunked_docs, embeddings, sim_df, chunk_sim_df, faiss_index, registry, ai_probabilities)
    """
    raw_texts_dict = dict(raw_texts_items)
    chunked_docs = chunk_documents(
        raw_texts_dict, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    translated_chunked_docs = {}

    for doc_name, chunks in chunked_docs.items():
        translated_chunked_docs[doc_name] = []
        for chunk in chunks:
            prepared = prepare_text_for_embedding(chunk)
            translated_chunked_docs[doc_name].append(prepared["embedding_text"])

    embeddings = embed_documents(translated_chunked_docs)
    sim_df = document_similarity_matrix(embeddings)

    names = list(embeddings.keys())
    n = len(names)
    chunk_mat = np.zeros((n, n))

    for i, na in enumerate(names):
        for j, nb in enumerate(names):
            if i == j:
                chunk_mat[i, j] = 1.0
            elif j > i:
                ea, eb = embeddings[na], embeddings[nb]
                score = (
                    float(np.max(cosine_similarity(ea, eb)))
                    if ea.size and eb.size
                    else 0.0
                )
                chunk_mat[i, j] = score
                chunk_mat[j, i] = score

    chunk_sim_df = pd.DataFrame(chunk_mat, index=names, columns=names)
    faiss_index, registry = build_index(embeddings, chunked_docs)
    ai_probabilities = detect_documents_ai_probability(chunked_docs)

    return (
        chunked_docs,
        embeddings,
        sim_df,
        chunk_sim_df,
        faiss_index,
        registry,
        ai_probabilities,
    )
