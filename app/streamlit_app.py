import sys
import asyncio

# Silence harmless Windows asyncio Proactor connection lost bugs
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# ruff: noqa: E402

import hashlib
import os
import io as _io
import time
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st
import base64

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.theme import (
    empty_state_html,
    format_similarity_html,
    get_colors,
    get_theme_name,
    inject_css,
    pipeline_progress_html,
    set_theme,
    sidebar_user_badge_html,
)
from sklearn.metrics.pairwise import cosine_similarity
from typing import Any
from src.utils.warning_list import render_warning_controls
from src.core.text_chunking import chunk_documents
from src.core.embedding_model import embed_documents
from src.core.similarity import (
    document_similarity_matrix,
    flag_plagiarism,
    find_most_similar_chunks,
    PLAGIARISM_THRESHOLD,
)
from src.core.faiss_index import (
    build_index,
    find_plagiarised_chunks,
    search_similar_chunks,
    save_index,
    load_or_rebuild_index,
    build_index_from_matrix,
)
from src.core.webhook import send_plagiarism_alert
from src.core.ai_detector import detect_documents_ai_probability
from src.visualization.network_graph import plot_similarity_network
from src.db import (
    init_corpus_db,
    get_all_documents,
    delete_document,
    get_all_embeddings,
    get_chunk_registry,
    add_document,
    get_document_by_hash,
    add_chunks,
    get_unique_class_sections,
    get_documents_by_class,
)
from src.db.incidents import (
    init_incident_db,
    get_all_incidents,
    sync_flagged_incidents,
)
from src.utils.pdf_report import generate_plagiarism_report, highlight_pdf_matches
from src.utils.badge_generator import (
    generate_badge_png,
    generate_badge_pdf,
)
from src.utils.redis_cache import (
    cache_session_state,
    get_session_state,
    clear_session,
    cache_faiss_index,
    get_faiss_index,
    cache_analysis_results,
    get_analysis_results,
)
from src.visualization.heatmap import (
    plot_chunk_similarity_comparison,
    plot_similarity_heatmap,
)
from src.core.document_parser import (
    DEFAULT_OCR_DPI,
    DEFAULT_OCR_LANGUAGE,
    OCRDependencyError,
    SUPPORTED_OCR_LANGUAGES,
    extract_text,
    prepare_text_for_embedding,
)
from src.db.auth import (
    init_db,
    verify_user,
    get_user_role,
    add_user,
    get_all_users,
    delete_user,
    update_password,
    get_tour_completed,
    set_tour_completed,
)
try:
    from src.utils.excel_export import export_similarity_matrix_to_excel
except ImportError:
    from utils.excel_export import export_similarity_matrix_to_excel

# Initialize corpus database
init_corpus_db()

# Generate unique session ID for this Streamlit session
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

SESSION_ID = st.session_state.session_id


_BRANDING_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "branding_config.json"))
_BRANDING_LOGO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "branding_logo.png"))
_INDEX_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "corpus.index")
)
try:
    from streamlit_tour import Tour
except ImportError:
    Tour = None

# Initialize auth database
init_db()

# Page Configuration
st.set_page_config(
    page_title="Semantic Plagiarism Detector",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

init_db()


st.markdown(
    """
<style>
    .block-container { padding-top: 2rem; }
    .stAlert { border-radius: 8px; }
</style>
""",
    unsafe_allow_html=True,
)
# ── SESSION TIMEOUT & ROUTE PROTECTION ────────────────────────────────────────
TIMEOUT_LIMIT = 15 * 60  # 15 minutes in seconds


# 1. Handle Automatic Session Expiration (Inactivity Check)
cached_last_interaction = get_session_state(SESSION_ID, "last_interaction")
if cached_last_interaction is not None:
    last_interaction = cached_last_interaction
elif "last_interaction" in st.session_state:
    last_interaction = st.session_state.last_interaction
else:
    last_interaction = None

if last_interaction and st.session_state.get("authenticated", False):
    elapsed_time = time.time() - last_interaction
    if elapsed_time > TIMEOUT_LIMIT:
        for key in ["authenticated", "username", "role", "last_interaction"]:
            if key in st.session_state:
                del st.session_state[key]
        clear_session(SESSION_ID)
        st.warning("⏱️ Your session has expired due to 15 minutes of inactivity. Please log in again.")
        st.stop()
    else:
        st.session_state.last_interaction = time.time()
        cache_session_state(SESSION_ID, "last_interaction", time.time())

# Render Login UI if not authenticated
if not st.session_state.get("authenticated", False):
    with st.form("login_form"):
        username = st.text_input("Username", value="admin")
        password = st.text_input("Password", type="password", value="admin")
        login_submitted = st.form_submit_button("Log In", use_container_width=True)

        if login_submitted:
            username = username.strip().lower()

            if not username or not password:
                st.error("Please enter both username and password.")
            elif verify_user(username, password):
                role = get_user_role(username)
                if role is not None:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.role = role
                    st.session_state.last_interaction = time.time()

                    cache_session_state(SESSION_ID, "authenticated", True)
                    cache_session_state(SESSION_ID, "username", username)
                    cache_session_state(SESSION_ID, "role", role)
                    cache_session_state(SESSION_ID, "last_interaction", time.time())

                    st.success(f"Welcome back, {username}!")

                    st.rerun()
            else:

                st.error("Invalid username or password.")
    st.stop()
    st.error("Invalid username or password. Try admin / admin123")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()



# Active user role

user_role = st.session_state.get("role", "user")


# ── Top-right Theme Toggle ───────────────────────────────────────────────────
current_theme = get_theme_name()

# Create a narrow right-aligned column for the theme toggle
_, theme_col = st.columns([0.94, 0.06])

with theme_col:
    theme_icon = "☀️" if current_theme == "Dark" else "🌙"

    if st.button(
        theme_icon,
        key="theme_toggle",
    ):
        new_theme = "Light" if current_theme == "Dark" else "Dark"
        set_theme(new_theme)
        st.rerun()


# ── Sidebar (ROLE RESTRICTED Settings) ────────────────────────────────────────
# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")



    selected_theme = st.radio(
        "Theme",
        options=["Light", "Dark"],
        index=0 if current_theme == "Light" else 1,
        horizontal=True,
        key="theme_selector",
    )
    if selected_theme != current_theme:
        set_theme(selected_theme)
        st.rerun()


    if user_role == "admin":
        threshold = st.slider(
            "Plagiarism Threshold",
            0.50,
            0.99,
            value=PLAGIARISM_THRESHOLD,
            step=0.01,
            help="Cosine similarity threshold for flagging.",

            key="threshold_slider",
        )
        use_chunk_matrix = st.checkbox(
            "Use chunk-level similarity matrix",
            value=False,
            key="chunk_matrix_checkbox",
        )
        faiss_top_k = st.slider(
            "FAISS: matches per chunk",
            1,
            20,
            value=5,
            key="faiss_top_k_slider",
        )


        # ── Customizable Chunk Size & Overlap Sliders (#153) ─────────────────
        st.markdown("### ✂️ Chunking Settings")
        chunk_size = st.slider(
            "Chunk Size (characters)",
            200,
            2000,
            value=500,
            step=50,
            help="Target character length for text chunks during embedding.",
            key="chunk_size_slider",
        )
        chunk_overlap = st.slider(
            "Chunk Overlap (characters)",
            0,
            500,
            value=50,
            step=10,
            help="Character overlap between consecutive chunks to preserve contextual boundary.",
            key="chunk_overlap_slider",
        )

        ocr_language = DEFAULT_OCR_LANGUAGE
        ocr_dpi = DEFAULT_OCR_DPI

        with st.expander("🔤 OCR Settings", expanded=False):
            ocr_language_labels = {
                display_name: code
                for code, display_name in SUPPORTED_OCR_LANGUAGES.items()
            }
            language_names = list(ocr_language_labels)
            default_language_name = SUPPORTED_OCR_LANGUAGES[DEFAULT_OCR_LANGUAGE]
            selected_ocr_language_name = st.selectbox(
                "OCR Language",
                options=language_names,
                index=language_names.index(default_language_name),
                key="ocr_language_selector",
            )
            ocr_language = ocr_language_labels[selected_ocr_language_name]

            ocr_dpi = st.slider(
                "OCR DPI Resolution",
                min_value=150,
                max_value=400,
                value=DEFAULT_OCR_DPI,
                step=25,
                key="ocr_dpi_slider",
            )

    else:
        threshold = PLAGIARISM_THRESHOLD
        use_chunk_matrix = False
        faiss_top_k = 5
        chunk_size = 500
        chunk_overlap = 50
        ocr_language = DEFAULT_OCR_LANGUAGE
        ocr_dpi = DEFAULT_OCR_DPI

    unique_classes = ["All Classes"] + get_unique_class_sections()

    selected_class = st.selectbox("Select Class/Section", unique_classes, index=0)

# ── Main UI ───────────────────────────────────────────────────────────────────
st.title("🔍 Semantic Plagiarism Detection System")

uploaded_files = st.file_uploader(
    "📂 Upload Assignments",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True,
    key="file_uploader",
)

file_bytes_dict = {f.name: f.getvalue() for f in uploaded_files} if uploaded_files else {}

if len(file_bytes_dict) < 2:
    st.info("Upload at least 2 files to begin analysis.")
    st.stop()

# ── Pipeline Execution ────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def run_pipeline(
    file_bytes_dict: dict[str, bytes],
    ocr_language: str,
    ocr_dpi: int,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
):
    raw_texts = {}
    for name, data in file_bytes_dict.items():
        raw_texts[name] = extract_text(
            _io.BytesIO(data),
            name,
            ocr_language=ocr_language,
            ocr_dpi=ocr_dpi,
        )

    chunked_docs = chunk_documents(
        raw_texts,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
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
                score = float(np.max(cosine_similarity(ea, eb))) if ea.size and eb.size else 0.0
                chunk_mat[i, j] = score
                chunk_mat[j, i] = score

    chunk_sim_df = pd.DataFrame(chunk_mat, index=names, columns=names)
    faiss_index, registry = build_index(embeddings, chunked_docs)
    ai_probabilities = detect_documents_ai_probability(chunked_docs)

    return (
        raw_texts,
        chunked_docs,
        embeddings,
        sim_df,
        chunk_sim_df,
        faiss_index,
        registry,
        ai_probabilities,
    )

with st.spinner("🧠 Processing files and building embeddings…"):
    analysis_results = run_pipeline(
        file_bytes_dict,
        ocr_language,
        ocr_dpi,
        chunk_size,
        chunk_overlap,
    )

(
    raw_texts,
    chunked_docs,
    embeddings,
    sim_df,
    chunk_sim_df,
    faiss_index,
    registry,
    ai_probabilities,
) = analysis_results

active_sim_df = chunk_sim_df if use_chunk_matrix else sim_df
flags = flag_plagiarism(active_sim_df, threshold=threshold)

st.subheader("📊 Analysis Summary")
st.write(f"Processed **{len(raw_texts)}** documents with Chunk Size: `{chunk_size}` and Overlap: `{chunk_overlap}`.")

st.markdown("---")
st.markdown("""
**How it works**
1. Upload **PDF, DOCX, or TXT** assignment files or import from Google Drive
2. Text is extracted according to the file type
3. Text is split into **paragraph chunks**
4. Chunks are embedded with **all-MiniLM-L6-v2**
5. A **FAISS index** is built over all chunk vectors
6. Pairs above the threshold are flagged
""")
st.markdown("---")
st.caption("Semantic Plagiarism Detector · FAISS edition")

if user_role == "admin":
    st.markdown("---")
    st.markdown("### 📁 Document Management")
    existing_docs = get_all_documents()
    if existing_docs:
        st.write(f"**{len(existing_docs)}** documents in database")
        for doc in existing_docs:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"📄 {doc['filename']}")
                with col2:
                    if st.button("🗑️", key=f"del_{doc['filename']}"):
                        delete_document(doc["filename"])
                        embeddings_matrix = get_all_embeddings()
                        if embeddings_matrix.size > 0:
                            new_index = build_index_from_matrix(embeddings_matrix)
                            save_index(new_index, _INDEX_PATH)
                        else:
                            if os.path.exists(_INDEX_PATH):
                                os.remove(_INDEX_PATH)
                        st.rerun()



    st.markdown("---")
    if st.button("🚪 Log Out", use_container_width=True, key="logout_button"):
        for key in ["authenticated", "username", "role", "last_interaction"]:
            if key in st.session_state:
                del st.session_state[key]
        clear_session(SESSION_ID)
        st.rerun()


# ── Onboarding Tour for First-Time Admin Users ───────────────────────────────────
if Tour is not None and user_role == "admin" and not get_tour_completed(st.session_state.username):
    username = st.session_state.username
    
    if st.button("🎯 Start Guided Tour", key="start_tour_button", type="primary"):
        st.session_state.show_tour = True
    
    if st.session_state.get("show_tour", False):
        tour_steps = [
            Tour.info(
                title="👋 Welcome to the Plagiarism Detection System!",
                desc="This guided tour will walk you through the key features to help you get started."
            ),
            Tour.bind("threshold_slider", 
                      title="⚙️ Plagiarism Threshold",
                      desc="Adjust similarity threshold. Recommended: 0.59",
                      side="right"),
            Tour.bind("class_filter_selectbox",
                      title="🔍 Class Filter",
                      desc="Filter analysis results by specific class sections.",
                      side="right"),
            Tour.info(
                title="📊 Analysis Dashboard",
                desc="View similarity metrics, flagged pairs, and comparisons in the tabs below."
            ),
            Tour.info(
                title="🎉 You're All Set!",
                desc="You can now start uploading assignments and detecting plagiarism."
            ),
        ]
        
        tour = Tour(steps=tour_steps)
        tour.start()
        
        set_tour_completed(username, True)
        st.session_state.show_tour = False
        st.success("✅ Onboarding tour completed!")
        st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🔍 Semantic Plagiarism Detection System")
st.markdown(
    "Upload student PDF, DOCX, or TXT files. Detects **semantic similarity** "
    "(even paraphrased text) using transformer embeddings + **FAISS vector search**."
)
st.divider()

# ── MAIN APPLICATION SECTIONS ──────────────────────────────────────────────────

if user_role != "admin":
    # STANDARD USER VIEW
    st.subheader("🔎 Secure Student Search Portal")
    st.caption("Paste a text snippet below to check its similarity against existing indexed assignments.")

    st.info("🔒 Note: Direct assignment uploads are restricted to Administrator access.")

    query_text = st.text_area(
        "Paste a text snippet to check against index:",
        height=150,
        placeholder="Paste a paragraph here to check for plagiarism...",
    )

    if st.button("🔍 Run Quick Verification", key="user_query") and query_text.strip():
        from src.db.corpus_db import get_chunk_registry, get_all_embeddings
        from src.core.faiss_index import build_index_from_matrix

        with st.spinner("Loading index and searching..."):
            try:
                registry = get_chunk_registry()
                embeddings_matrix = get_all_embeddings()

                if embeddings_matrix.shape[0] == 0:
                    st.warning("No documents are currently indexed.")
                else:
                    faiss_index = build_index_from_matrix(embeddings_matrix, index_type="auto")
                    from src.core.embedding_model import embed_chunks

                    query_vec = embed_chunks([query_text.strip()])[0]
                    faiss_threshold = threshold
                    results = search_similar_chunks(
                        query_vec,
                        faiss_index,
                        registry,
                        top_k=faiss_top_k,
                        threshold=faiss_threshold,
                    )

                    if selected_class != "All Classes":
                        class_docs = get_documents_by_class(selected_class)
                        results = [
                            (record, score)
                            for record, score in results
                            if record.doc_name in class_docs
                        ]

                    if not results:
                        st.success("✅ No significant matches found in the assignment database.")
                    else:
                        st.success(f"Found **{len(results)}** potentially similar passages.")

            except Exception as e:
                st.error(f"Error loading index: {str(e)}")
else:
    # ADMINISTRATOR ACCESS: Full Upload & Pipeline UI
    index_key = "corpus_index"
    cached_index_data = get_faiss_index(index_key)

# ── Main Header ───────────────────────────────────────────────────────────────
st.title("🔍 Semantic Plagiarism Detection System")
st.markdown(
    "Upload student PDF, DOCX, or TXT files. Detects **semantic similarity** "
    "using transformer embeddings + **FAISS vector search**."
)
st.divider()

if user_role != "admin":
    # STUDENT PORTAL VIEW
    st.subheader("🔎 Secure Student Search Portal")
    query_text = st.text_area("Paste a text snippet to check against index:", height=150)
    if st.button("🔍 Run Quick Verification", key="user_query") and query_text.strip():
        # Search logic
        st.info("Query processed.")
else:
    # ADMIN FULL ACCESS VIEW
    cached_index_data = get_faiss_index("corpus_index")

    if cached_index_data is not None and os.path.exists(_INDEX_PATH):
        try:
            import faiss
            index_buffer = _io.BytesIO(cached_index_data)
            faiss_index = faiss.deserialize_index(faiss.read_index(index_buffer))
            registry = get_chunk_registry()
            st.info(f"📂 Loaded FAISS index from Redis cache with {faiss_index.ntotal} vectors")
        except Exception as e:
            print(f"[Redis] Error loading cached index: {e}, falling back to disk")
            from src.core.faiss_index import load_or_rebuild_index

            faiss_index, registry, index_recovered = load_or_rebuild_index(_INDEX_PATH)

            if index_recovered:
                if faiss_index.ntotal:
                    st.warning("FAISS index was missing, corrupted, or inconsistent and was "f"automatically rebuilt from {faiss_index.ntotal} stored vectors.")
                else:
                    st.info(
                    "No stored embeddings were found. An empty FAISS index was "
                    "initialized safely.")
            else:
                st.info(f"Loaded and validated the existing FAISS index with "f"{faiss_index.ntotal} vectors.")
    else:
        if os.path.exists(_INDEX_PATH):
            faiss_index = load_index(_INDEX_PATH)
            registry = get_chunk_registry()
        else:
            faiss_index = None
            registry = []

    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None
        # Try to load from Redis cache

        cached_results = get_analysis_results(f"{SESSION_ID}:current")
        if cached_results is not None:
            st.session_state.analysis_results = cached_results

    if "analysis_file_signature" not in st.session_state:
        st.session_state.analysis_file_signature = None

        cached_signature = get_session_state(SESSION_ID, "analysis_file_signature")
        if cached_signature is not None:
            st.session_state.analysis_file_signature = cached_signature

            faiss_index = load_index(_INDEX_PATH) if os.path.exists(_INDEX_PATH) else None
            registry = get_chunk_registry()
    else:
        faiss_index = load_index(_INDEX_PATH) if os.path.exists(_INDEX_PATH) else None
        registry = get_chunk_registry()

        # Try to load from Redis cache
        cached_signature = get_session_state(SESSION_ID, "analysis_file_signature")
        if cached_signature is not None:
            st.session_state.analysis_file_signature = cached_signature
    



    # 1. LOCAL FILE UPLOADER
    uploaded_files = st.file_uploader(
        "📂 Upload Assignments",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="file_uploader",
    )


    # 2. GOOGLE DRIVE IMPORT SECTION (#146)
    from src.utils.google_drive import bulk_download_drive_folder

    if "drive_files_dict" not in st.session_state:
        st.session_state.drive_files_dict = {}

    with st.expander("🌐 Import from Google Drive Folder", expanded=False):
        st.caption("Paste a shared Google Drive folder link or ID to bulk-download assignments.")
        
        drive_folder_input = st.text_input(
            "Google Drive Folder Link / ID:",
            placeholder="https://drive.google.com/drive/folders/1A2B3C...",
            key="drive_folder_url_input",
        )
        
        drive_api_key = st.text_input(
            "API Key (Optional):",
            type="password",
            key="drive_api_key_input",
        )

        if st.button("📥 Import Files from Drive", type="primary", use_container_width=True):
            if not drive_folder_input.strip():
                st.error("Please enter a valid Google Drive folder link or ID.")
            else:
                with st.spinner("Connecting to Google Drive API & downloading files..."):
                    try:
                        downloaded_dict, downloaded_names = bulk_download_drive_folder(
                            folder_url_or_id=drive_folder_input,
                            api_key=drive_api_key.strip() if drive_api_key else None,
                        )
                        
                        if downloaded_dict:
                            st.session_state.drive_files_dict.update(downloaded_dict)
                            st.success(f"✅ Imported {len(downloaded_names)} files: {', '.join(downloaded_names)}")
                            st.rerun()
                        else:
                            st.warning("No supported files (.pdf, .docx, .txt) found in this Drive folder.")
                    except Exception as err:
                        st.error(f"Failed to import from Google Drive: {str(err)}")

    # 3. MERGE LOCAL AND DRIVE FILE BYTES
    file_bytes_dict = {}


    file_bytes_dict = {}

    if uploaded_files:
        for f in uploaded_files:
            file_bytes_dict[f.name] = f.read()
            f.seek(0)


    if st.session_state.drive_files_dict:
        file_bytes_dict.update(st.session_state.drive_files_dict)

    # 4. PIPELINE STOP CHECK
    if len(file_bytes_dict) < 2:
        if st.session_state.analysis_results is None:
            st.markdown(
                empty_state_html(
                    "Waiting for Files",
                    "Please upload or import from Drive at least 2 PDF, DOCX, or TXT assignments to begin.",
                    "📂",
                ),
                unsafe_allow_html=True,
            )
            st.stop()

    # ── Metadata Editor Section ──────────────────────────────────────────────────
    st.markdown("### 📝 Set Document Metadata")

    col1, col2 = st.columns(2)
    with col1:
        batch_class = st.text_input(
            "Default Class/Section",
            value="Class A",
            help="Default class section for all files in this batch.",
        )
    with col2:
        batch_assignment = st.text_input(
            "Default Assignment Title",
            value="Assignment 1",
            help="Default assignment title for all files in this batch.",
        )

    metadata_dict = {}
    for filename in file_bytes_dict.keys():
        base_name = os.path.splitext(filename)[0]
        guessed_name = base_name.replace("_", " ").replace("-", " ").title()

        with st.expander(f"📄 {filename}", expanded=False):
            student_name = st.text_input(
                f"Student Name for {filename}",
                value=guessed_name,
                key=f"student_{filename}",
            )
            class_section = st.text_input(
                f"Class/Section for {filename}", value=batch_class, key=f"class_{filename}"
            )
            assignment_title = st.text_input(
                f"Assignment Title for {filename}",
                value=batch_assignment,
                key=f"assignment_{filename}",
            )

            metadata_dict[filename] = {
                "student_name": student_name.strip(),
                "class_section": class_section.strip(),
                "assignment_title": assignment_title.strip(),
            }

    # ── Pipeline Execution ────────────────────────────────────────────────────────
    @st.cache_data(show_spinner=False)
    def run_pipeline(
        file_bytes_dict: dict[str, bytes],
        ocr_language: str,
        ocr_dpi: int,
    ):
        raw_texts = {}
        for name, data in file_bytes_dict.items():
            raw_texts[name] = extract_text(
                _io.BytesIO(data),
                name,
                ocr_language=ocr_language,
                ocr_dpi=ocr_dpi,
            )

        chunked_docs = chunk_documents(raw_texts)
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
                    score = float(np.max(cosine_similarity(ea, eb))) if ea.size and eb.size else 0.0
                    chunk_mat[i, j] = score
                    chunk_mat[j, i] = score

        chunk_sim_df = pd.DataFrame(chunk_mat, index=names, columns=names)
        faiss_index, registry = build_index(embeddings, chunked_docs)
        ai_probabilities = detect_documents_ai_probability(chunked_docs)

        return (
            raw_texts,
            chunked_docs,
            embeddings,
            sim_df,
            chunk_sim_df,
            faiss_index,
            registry,
            ai_probabilities,
        )

    with st.spinner("🧠 Processing files and building embeddings…"):
        analysis_results = run_pipeline(file_bytes_dict, ocr_language, ocr_dpi)

    (
        raw_texts,
        chunked_docs,
        embeddings,
        sim_df,
        chunk_sim_df,
        faiss_index,
        registry,
        ai_probabilities,
    ) = analysis_results

    active_sim_df = chunk_sim_df if use_chunk_matrix else sim_df
    flags = flag_plagiarism(active_sim_df, threshold=threshold)

    # ── Summary Metrics ───────────────────────────────────────────────────────────

    if not uploaded_files or len(uploaded_files) < 2:
        st.markdown(
            empty_state_html(
                "Waiting for Files",
                "Please upload at least 2 PDF, DOCX, or TXT assignments to begin analysis.",
                "📂",
            ),
            unsafe_allow_html=True,
        )
        st.stop()

    # Process files pipeline
    raw_texts = {}
    for name, data in file_bytes_dict.items():
        raw_texts[name] = extract_text(_io.BytesIO(data), name, ocr_language=ocr_language, ocr_dpi=ocr_dpi)

    chunked_docs = chunk_documents(raw_texts)
    embeddings = embed_documents(chunked_docs)
    sim_df = document_similarity_matrix(embeddings)
    faiss_index, registry = build_index(embeddings, chunked_docs)
    ai_probabilities = detect_documents_ai_probability(chunked_docs)

    active_sim_df = sim_df
    flags = flag_plagiarism(active_sim_df, threshold=threshold)
    
    # Sync incidents to database
    init_incident_db()
    incidents = sync_flagged_incidents(flags)

    # ── Summary Metrics ───────────────────────────────────────────────────────

    st.subheader("📊 Analysis Summary")
    doc_names = list(raw_texts.keys())
    n_docs = len(doc_names)
    total_pairs = n_docs * (n_docs - 1) // 2 if n_docs > 1 else 0
    n_flagged = len(flags)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📄 Documents", n_docs)
    col2.metric("🔗 Pairs", total_pairs)
    col3.metric("🚨 Flagged", n_flagged)
    col4.metric("🗂️ FAISS Vectors", faiss_index.ntotal if faiss_index is not None else 0)
    st.divider()

    # ── Application Tabs ──────────────────────────────────────────────────────
    tab_warnings, tab_incidents, tab_faiss, tab_matrix, tab_heatmap, tab_drill, tab_users = st.tabs(
        [
            "⚠️ Plagiarism Warnings",
            "📋 Incidents",
            "⚡ FAISS Chunk Search",
            "📋 Similarity Matrix",
            "🗺️ Heatmap",
            "🔬 Pair Drill-Down",
            "👥 User Management",
        ]
    )



    # ══ TAB 1: WARNINGS ═══════════════════════════════════════════════════════

    with tab_warnings:
        st.subheader("⚠️ Plagiarism Warnings")
        render_warning_controls(flags, threshold=threshold, ai_probabilities=ai_probabilities)

    # ══ TAB 2: INCIDENTS ═══════════════════════════════════════════════════════
    
    with tab_incidents:
        st.subheader("📋 Incidents")
        
        # Add search input
        search_query = st.text_input(
            "Search incidents",
            placeholder="Search by Student Name, Assignment Title, or Document Name…",
            key="incidents_search",
        )
        
        # Get all documents for metadata lookup
        all_docs = get_all_documents()
        doc_metadata = {doc["filename"]: doc for doc in all_docs}
        
        # Filter incidents based on search query
        filtered_incidents = []
        query = search_query.strip().casefold()
        
        for incident in incidents:
            doc_a = incident["document_a"]
            doc_b = incident["document_b"]
            
            # Get metadata for both documents
            meta_a = doc_metadata.get(doc_a, {})
            meta_b = doc_metadata.get(doc_b, {})
            
            student_name_a = meta_a.get("student_name", "")
            assignment_title_a = meta_a.get("assignment_title", "")
            student_name_b = meta_b.get("student_name", "")
            assignment_title_b = meta_b.get("assignment_title", "")
            
            # Check if search query matches any field
            if not query:
                filtered_incidents.append(incident)
            elif (
                query in student_name_a.casefold() or
                query in assignment_title_a.casefold() or
                query in doc_a.casefold() or
                query in student_name_b.casefold() or
                query in assignment_title_b.casefold() or
                query in doc_b.casefold()
            ):
                filtered_incidents.append(incident)
        
        # Show status line
        total_incidents = len(incidents)
        matching_count = len(filtered_incidents)
        
        if matching_count > 0:
            st.markdown(f"Showing **{matching_count}** of **{total_incidents}** incidents")
        else:
            st.info("No incidents match the current search.")
        
        # Display incidents table if there are matches
        if filtered_incidents:
            incidents_df = pd.DataFrame([
                {
                    "Incident ID": inc["incident_id"],
                    "Document A": inc["document_a"],
                    "Document B": inc["document_b"],
                    "Similarity Score": f"{inc['similarity_score']:.4f}",
                    "Severity Rank": inc["severity_rank"],
                    "Review Status": inc["review_status"],
                    "Date Flagged": inc["date_flagged"],
                }
                for inc in filtered_incidents
            ])
            st.dataframe(incidents_df, use_container_width=True)


    with tab_faiss:
        st.subheader("⚡ FAISS Vector Search")
        st.info(f"FAISS Index contains **{faiss_index.ntotal}** vectors.")

    with tab_matrix:
        st.subheader("📋 Similarity Matrix")

        if active_sim_df is None:
            st.markdown(
                empty_state_html(
                    "No Similarity Matrix",
                    "Ensure at least 2 documents are uploaded to compute similarities.",
                    "📋",
                ),
                unsafe_allow_html=True,
            )
        else:

            def _highlight(val: Any) -> str:
                numeric_val = float(val)
                if numeric_val >= 0.90:
                    return "background-color:#ff4b4b;color:white;font-weight:bold;"
                elif numeric_val >= threshold:
                    return "background-color:#ffa500;color:white;font-weight:bold;"
                return ""

            styled_df = active_sim_df.style.format("{:.4f}").map(_highlight)
            st.dataframe(styled_df, use_container_width=True)

            # Export options row
            col_csv, col_excel = st.columns(2)

            with col_csv:
                st.download_button(
                    "⬇️ Download CSV",
                    active_sim_df.to_csv().encode("utf-8"),
                    "similarity_matrix.csv",
                    "text/csv",
                    use_container_width=True,
                )

            with col_excel:
                excel_data = export_similarity_matrix_to_excel(
                    active_sim_df, threshold=threshold
                )
                st.download_button(
                    "📊 Export as Styled Excel (.xlsx)",
                    excel_data,
                    "similarity_matrix_styled.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

    with tab_heatmap:
        st.subheader("🗺️ Similarity Heatmap")
        if active_sim_df is not None:
            heatmap_fig = plot_similarity_heatmap(
                active_sim_df, title="Document Semantic Similarity", threshold=threshold, theme_colors=get_colors()
            )
            st.pyplot(heatmap_fig, use_container_width=True)

    with tab_drill:
        st.subheader("🔬 Pair Drill-Down")
        if n_docs >= 2:
            c1, c2 = st.columns(2)
            with c1:
                doc_a = st.selectbox("Document A", doc_names, index=0, key="da")
            with c2:
                doc_b = st.selectbox("Document B", [d for d in doc_names if d != doc_a], index=0, key="db")

            score = float(active_sim_df.loc[doc_a, doc_b])
            st.markdown(f"**Overall Similarity:** `{score:.1%}`")
            st.progress(float(score))
            st.divider()

            drill_tab_analysis, drill_tab_viewer = st.tabs(
                ["📊 Chunk Matches & Report", "📄 Document Viewer"]
            )

            chunks_a = chunked_docs.get(doc_a, [])
            chunks_b = chunked_docs.get(doc_b, [])

            with drill_tab_analysis:
                top_pairs = find_most_similar_chunks(
                    chunks_a, chunks_b, embeddings[doc_a], embeddings[doc_b], top_k=5, threshold=threshold
                )
                for rank, (ca, cb, sim) in enumerate(top_pairs, 1):
                    with st.expander(f"#{rank} — Similarity: {sim:.1%}"):
                        st.write(f"**{doc_a}:** {ca}")
                        st.write(f"**{doc_b}:** {cb}")

            # --- In-App PDF Preview with Highlighted Matches (#145) ---
            with drill_tab_viewer:
                st.subheader("📄 In-App PDF Preview with Highlighted Matches")
                selected_view_doc = st.radio(
                    "Select Document to Preview:",
                    options=[doc_a, doc_b],
                    horizontal=True,
                    key="doc_viewer_select",
                )

                # Retrieve file bytes directly from uploaded files dict
                doc_source = file_bytes_dict.get(selected_view_doc)
                matching_chunks_to_highlight = chunks_a if selected_view_doc == doc_a else chunks_b

                if doc_source and str(selected_view_doc).lower().endswith(".pdf"):
                    with st.spinner("Generating highlighted PDF preview..."):
                        try:
                            highlighted_pdf_bytes = highlight_pdf_matches(
                                pdf_source=doc_source,
                                matching_chunks=matching_chunks_to_highlight,
                            )

                            base64_pdf = base64.b64encode(highlighted_pdf_bytes).decode("utf-8")
                            pdf_display = f"""
                                <iframe 
                                    src="data:application/pdf;base64,{base64_pdf}" 
                                    width="100%" 
                                    height="850px" 
                                    type="application/pdf">
                                </iframe>
                            """
                            st.markdown(pdf_display, unsafe_allow_html=True)
                        except Exception as err:
                            st.error(f"Unable to render PDF preview: {str(err)}")
                else:
                    st.info(f"PDF Preview is only available for uploaded `.pdf` files.")

    # ══ TAB 6: USERS ══════════════════════════════════════════════════════════
    with tab_users:
        st.subheader("👥 User Management")
        users = get_all_users()
        if users:
            st.dataframe(pd.DataFrame(users), use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("🎓 Semantic Plagiarism Detection System · Streamlit")
