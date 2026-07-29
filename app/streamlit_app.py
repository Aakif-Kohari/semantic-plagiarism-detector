import os
import sys
import asyncio


# Fix Streamlit import paths by pointing to project root
FILE_PATH = Path(__file__).resolve()
ROOT_DIR = FILE_PATH.parent.parent  # Points to semantic-plagiarism-detector/
# Silence harmless Windows asyncio Proactor connection lost bugs
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# ruff: noqa: E402

import hashlib
import os
import io as _io
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import base64
import html

# Standard / Third-party imports
import time
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st

from src.security.metadata_stripper import strip_exif_metadata
from src.utils.filename import (
    InvalidFileExtensionError,
    sanitize_filename,
    unique_filename,
    validate_document_extension,
)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from typing import Any

try:
    from streamlit_plotly_events import plotly_events
except ImportError:  # pragma: no cover - optional dependency
    plotly_events = None

import logging

logger = logging.getLogger(__name__)
# Validate required environment variables during application startup
REQUIRED_ENV_VARS = [
    "REDIS_URL",
    "PLAGIARISM_WEBHOOK_URL",
    "API_BEARER_TOKEN",
]

missing_env_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]

if missing_env_vars:
    logger.warning(
        "Missing environment variables: %s. "
        "Some features may not work correctly. "
        "Please configure them in your .env file.",
        ", ".join(missing_env_vars),
    )


from app.theme import (
    back_to_top_html,
    empty_state_html,
    get_colors,
    get_theme_name,
    inject_css,
    set_theme,
    sidebar_user_badge_html,
)
from src.core.config import DEFAULT_THRESHOLDS, PLAGIARISM_THRESHOLD, severity_key
from src.core.document_parser import (
    DEFAULT_OCR_DPI,
    DEFAULT_OCR_LANGUAGE,
    SUPPORTED_OCR_LANGUAGES,
    OCRDependencyError,
    extract_text,
    remove_ignore_phrases,
)
from src.core.embedding_model import embed_chunks, embed_documents
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
from src.core.similarity import (
    document_similarity_matrix,
    find_most_similar_chunks,
    flag_plagiarism,
)
from src.core.webhook import send_plagiarism_alert
from src.i18n.translator import _SUPPORTED_LANGUAGES
from src.visualization.network_graph import plot_similarity_network
from src.utils.storage_metrics import calculate_storage_usage


class OCRFileBatchError(Exception):
    """Exception raised when OCR extraction fails on one or more files in a batch."""

    def __init__(self, failed_files: list[str], failure_details: list[str]):
        self.failed_files = failed_files
        self.failure_details = failure_details
        super().__init__(f"OCR failed for files: {failed_files}")


from src.core.export_engine import LMSExportEngine
from src.core.telemetry import TelemetryService
from src.db import (
    clear_all_data,
    delete_document,
    get_all_documents,
    get_all_embeddings,
    get_chunk_registry,
    get_unique_class_sections,
    get_documents_by_class,
)
from src.utils.pdf_report import generate_plagiarism_report, highlight_pdf_matches
from src.utils.badge_generator import (
    generate_badge_png,
    generate_badge_pdf,
)
from src.db.auth import (
    authenticate_user,
    check_login_rate_limit,
    clear_login_attempts,
    disable_2fa,
    enable_2fa,
    get_2fa_status,
    get_tour_completed,
    get_user_preferences,
    is_user_active,
    record_failed_login,
    set_tour_completed,
    set_user_active_status,
    update_notification_preferences,
    update_user_preferences,
)
from src.db.incidents import (  # noqa: E402
    get_all_incidents_above_threshold_for_export,
    get_high_severity_trends,
    get_most_plagiarized_documents,
    sync_flagged_incidents,
)
from src.utils.diff_highlighter import highlight_overlap
from src.utils.excel_export import export_similarity_matrix_to_excel

from src.utils.redis_cache import (
    cache_session_state,
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
from src.utils.warning_list import render_warning_controls
from src.visualization.analytics import (
    plot_high_severity_trends,
    plot_most_plagiarized_documents,
    plot_similarity_distribution,
)
from src.visualization.heatmap import plot_similarity_heatmap  # noqa: E402

init_db()
# Safe import for PDF Highlighting

try:

    from src.utils.pdf_highlighter import highlight_pdf_matches  # type: ignore
except Exception:
    highlight_pdf_matches = None

    # Safe import for Google Drive integration

    from src.utils.excel_export import export_similarity_matrix_to_excel
    from src.utils.json_export import export_similarity_matrix_to_json
except ImportError:

    from src.utils.excel_export import export_similarity_matrix_to_excel  # type: ignore[import-untyped,reportMissingImports]


    from src.utils.excel_export import export_similarity_matrix_to_excel  # type: ignore[import-untyped,reportMissingImports]

    from src.utils.excel_export import export_similarity_matrix_to_excel  # type: ignore
    from src.utils.json_export import export_similarity_matrix_to_json
    from utils.excel_export import export_similarity_matrix_to_excel  # type: ignore
    from utils.excel_export import export_similarity_matrix_to_excel  # type: ignore[import-untyped,reportMissingImports]



    from utils.json_export import export_similarity_matrix_to_json


# Initialize corpus database

try:
    from streamlit_tour import Tour
except ImportError:
    Tour = None


# Initialize databases

init_corpus_db()
init_db()

# Generate unique session ID for this Streamlit session
if "session_id" not in st.session_state:
    import uuid

    st.session_state.session_id = str(uuid.uuid4())

SESSION_ID = st.session_state.session_id

_BRANDING_CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "branding_config.json")
)
_BRANDING_LOGO_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "branding_logo.png")
)
_INDEX_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "corpus.index")
)

from streamlit_tour import Tour

try:
    from src.utils.google_drive import import_from_google_drive  # type: ignore
except Exception:
    import_from_google_drive = None

# -----------------------------------------------------------------------------
# Page Configuration & Session State
# -----------------------------------------------------------------------------


# Page Configuration
# NOTE: initial_sidebar_state="auto" lets Streamlit decide the sidebar's
# starting state based on viewport width. On screens narrower than the
# "md" breakpoint (768px) — phones and small tablets — the sidebar starts
# collapsed so it doesn't cover the similarity matrix / heatmap. On wider
# screens it behaves the same as "expanded". See issue #258.

st.set_page_config(
    page_title="Semantic Plagiarism Detector",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="auto",
)


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "pdf_passwords" not in st.session_state:
    st.session_state.pdf_passwords = {}
if "lang" not in st.session_state:
    st.session_state.lang = "en"

st.markdown(back_to_top_html(), unsafe_allow_html=True)
inject_css()



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
        from src.errors import UI_SESSION_EXPIRED

        st.warning(UI_SESSION_EXPIRED)
        st.stop()
    else:
        st.session_state.last_interaction = time.time()
        cache_session_state(SESSION_ID, "last_interaction", time.time())

# ── Handle OAuth Callback (GitHub / Google SSO) ──────────────────────────────
if not st.session_state.get("authenticated", False):
    if "code" in st.query_params and "state" in st.query_params:
        _code = st.query_params["code"]
        _state = st.query_params["state"]
        from src.db.auth import get_or_create_sso_user
        from src.utils.sso import exchange_github_code, exchange_google_code

        _user_info = None
        if _state.startswith("google_"):
            _user_info = exchange_google_code(_code)
        elif _state.startswith("github_"):
            _user_info = exchange_github_code(_code)
        if _user_info and _user_info.get("email"):
            _email = _user_info["email"]
            if not is_user_active(_email):
                st.error("🚨 Account suspended. Please contact your administrator.")
                st.query_params.clear()
            else:
                _role = get_or_create_sso_user(_email)
                st.session_state.authenticated = True
                st.session_state.username = _email
                st.session_state.role = _role
                st.session_state.last_interaction = time.time()
                cache_session_state(SESSION_ID, "authenticated", True)
                cache_session_state(SESSION_ID, "username", _email)
                cache_session_state(SESSION_ID, "role", _role)
                cache_session_state(SESSION_ID, "last_interaction", time.time())
                st.query_params.clear()
                st.rerun()
        else:
            st.error("🚨 SSO authentication failed. Could not retrieve your email.")
            st.query_params.clear()

# Render Login UI if not authenticated
if not st.session_state.get("authenticated", False):
    if st.session_state.get("pending_2fa", False):
        with st.form("otp_form"):
            st.subheader("🔒 Two-Factor Authentication")
            st.info(
                "Enter the 6-digit verification token from your Google Authenticator/Authy app."
            )
            otp_code = st.text_input(
                "Verification Code", max_chars=6, key="login_otp_code"
            )
            col1, col2 = st.columns(2)
            with col1:
                verify_submitted = st.form_submit_button(
                    "Verify", use_container_width=True
                )
            with col2:
                cancel_submitted = st.form_submit_button(
                    "Cancel", use_container_width=True
                )

            if verify_submitted:
                username = st.session_state.get("pending_username")
                enabled, otp_secret = get_2fa_status(username)
                if enabled and otp_secret:
                    import pyotp

                    totp = pyotp.TOTP(otp_secret)
                    if totp.verify(otp_code.strip()):
                        role = st.session_state.get("pending_role")
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.role = role
                        st.session_state.last_interaction = time.time()

                        cache_session_state(SESSION_ID, "authenticated", True)
                        cache_session_state(SESSION_ID, "username", username)
                        cache_session_state(SESSION_ID, "role", role)
                        cache_session_state(SESSION_ID, "last_interaction", time.time())
                        prefs = get_user_preferences(username)
                        st.session_state.threshold = prefs.get(
                            "threshold", DEFAULT_THRESHOLDS.plagiarism
                        )
                        st.session_state.theme = prefs.get("theme", "Light")
                        set_theme(st.session_state.theme)

                        # Clear pending state
                        del st.session_state["pending_2fa"]
                        del st.session_state["pending_username"]
                        del st.session_state["pending_role"]

                        st.success(f"✅ Welcome back, {username}!")
                        st.rerun()
                    else:
                        st.error("🚨 Invalid verification code. Please try again.")
                else:
                    st.error("🚨 2FA configuration error. Please contact admin.")

            if cancel_submitted:
                del st.session_state["pending_2fa"]
                del st.session_state["pending_username"]
                del st.session_state["pending_role"]
                st.rerun()
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

# Resolve fallback configuration variables (ensuring all roles have access to these settings)
selected_lang_name = st.session_state.get("lang_selector", "English")
_lang_reverse = {v: k for k, v in _SUPPORTED_LANGUAGES.items()}
lang_code = _lang_reverse.get(selected_lang_name, "en")

threshold = st.session_state.get("threshold_slider", DEFAULT_THRESHOLDS.plagiarism)
faiss_top_k = st.session_state.get("faiss_top_k_slider", 5)
use_chunk_matrix = st.session_state.get("chunk_matrix_checkbox", False)
chunk_size = st.session_state.get("chunk_size_slider", 500)
chunk_overlap = st.session_state.get("chunk_overlap_slider", 50)
ignore_phrases = st.session_state.get("ignore_phrases_textarea", "")
ocr_language_selector_val = st.session_state.get(
    "ocr_language_selector", DEFAULT_OCR_LANGUAGE
)
ocr_language_map = {
    "English": "eng",
    "Español": "spa",
    "Français": "fra",
    "eng": "eng",
    "spa": "spa",
    "fra": "fra",
}
ocr_language = ocr_language_map.get(ocr_language_selector_val, DEFAULT_OCR_LANGUAGE)
ocr_dpi = st.session_state.get("ocr_dpi_slider", DEFAULT_OCR_DPI)
heatmap_cmap = "OrRd"

unique_classes = ["All Classes"] + get_unique_class_sections()
selected_class = st.session_state.get("class_filter_selectbox", "All Classes")

@st.dialog("⚠️ Confirm Logout")
def logout_dialog():
    st.write("Are you sure you want to log out?")
    st.info("Your current session will be cleared.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Cancel",
            use_container_width=True,
            key="cancel_logout",
        ):
            st.rerun()

    with col2:
        if st.button(
            "Log Out",
            type="primary",
            use_container_width=True,
            key="confirm_logout",
        ):
            import logging
            from datetime import datetime, timezone

            logger = logging.getLogger(__name__)
            username = st.session_state.get("username", "unknown")
            timestamp = datetime.now(timezone.utc).isoformat()

            logger.info("User '%s' logged out at %s", username, timestamp)

            for key in ["authenticated", "username", "role"]:
                if key in st.session_state:
                    del st.session_state[key]

            clear_session(SESSION_ID)
            st.rerun()




@st.dialog("⚠️ Confirm Bulk Clear")
def clear_all_dialog():
    st.markdown(
        "**WARNING:** This action is destructive and cannot be undone. "
        "This will permanently delete all student documents, paragraph chunks, "
        "and plagiarism incidents from the database, and reset the FAISS index."
lang_code = "es" if selected_lang_name == "Español" else "en"


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


            help="Cosine similarity above which a pair is flagged.",

          

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

with theme_col:
    theme_icon = "☀️" if current_theme == "Dark" else "🌙"
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        _ctx = get_script_run_ctx()
        if _ctx and _ctx.current_form_id:
            _ctx.current_form_id = ""
    except Exception:
        pass
    if st.button(theme_icon, key="theme_toggle"):
        new_theme = "Light" if current_theme == "Dark" else "Dark"
        set_theme(new_theme)
        st.rerun()

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
# ── Sidebar (ROLE RESTRICTED Settings & i18n) ─────────────────────────────────

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
with st.sidebar:
    st.markdown(f"👤 Logged in as **{st.session_state.get('username', '')}**")

if len(file_bytes_dict) < 2:
    st.info("Upload at least 2 files to begin analysis.")
    st.stop()

    if st.button("🚪 Log Out", use_container_width=True):
        logout_dialog()
        
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

    selected_class = st.selectbox(
        "Select Class/Section",
        unique_classes,
        index=0,
        key="class_filter_selectbox",
    )


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
        st.markdown("### 💾 Storage Space Used")
        storage_info = calculate_storage_usage()
        st.metric(
            label="Total Storage Used",
            value=storage_info["formatted_total"],
            help="Combined SQLite database + FAISS index disk usage",
        )
        col_db, col_idx = st.columns(2)
        with col_db:
            st.caption(f"🗄️ DB: **{storage_info['formatted_sqlite']}**")
        with col_idx:
            st.caption(f"⚡ FAISS: **{storage_info['formatted_faiss']}**")

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

                except ImportError:
                    st.error(
                        "❌ The `faker` package is not installed. "
                        "Run `pip install faker` and restart the app."
                    )
                except (ValueError, RuntimeError, TypeError, OSError) as _mock_err:
                    st.error(f"❌ Mock data generation failed: {_mock_err}")

        st.markdown('<div class="clear-all-container">', unsafe_allow_html=True)
        if st.button(
            "🗑️ Clear All Documents",
            key="clear_all_documents_button",
            use_container_width=True,
        ):
            clear_all_dialog()
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        threshold = PLAGIARISM_THRESHOLD
        use_chunk_matrix = False
        faiss_top_k = 5
        chunk_size = 500
        chunk_overlap = 50
        ocr_language = DEFAULT_OCR_LANGUAGE
        ocr_dpi = DEFAULT_OCR_DPI

    st.markdown("---")
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
# ── MAIN APPLICATION SECTIONS (ROLE CHECKED) ──────────────────────────────────

if user_role != "admin":
    # STANDARD USER VIEW: Student Query / Search Panel Only (No admin PDF uploading)
    st.subheader("🔎 Secure Student Search Portal")
    st.caption(
        "Paste a text snippet below to check its similarity against existing indexed assignments."
    )

    st.info(
        "🔒 Note: Direct assignment uploads and detailed breakdown panels are restricted to Administrator access. Your queries are anonymized for privacy."
    )

    query_text = st.text_area(
        "Paste a text snippet to check against index:",
        height=150,
        placeholder="Paste a paragraph here to check for plagiarism...",
    )

    if st.button("🔍 Run Quick Verification", key="user_query") and query_text.strip():
        # Load existing index and registry from database
        from src.core.faiss_index import build_index_from_matrix
        from src.db.corpus_db import get_all_embeddings, get_chunk_registry

        with st.spinner("Loading index and searching..."):
            try:
                registry = get_chunk_registry()
                embeddings_matrix = get_all_embeddings()

                if embeddings_matrix.shape[0] == 0:
                    from src.errors import UI_NO_DOCUMENTS_INDEXED

                    st.warning(UI_NO_DOCUMENTS_INDEXED)
                else:
                    # Build index from stored embeddings
                    faiss_index = build_index_from_matrix(
                        embeddings_matrix, index_type="auto"
                    )

                    # Embed the query
                    from src.core.embedding_model import embed_chunks

                    query_vec = embed_chunks([query_text.strip()])[0]

                    # Search with threshold
                    faiss_threshold = threshold
                    results = search_similar_chunks(
                        query_vec,
                        faiss_index,
                        registry,
                        top_k=faiss_top_k,
                        threshold=faiss_threshold,
                    )

                    if not results:
                        st.success(
                            "✅ No significant matches found in the assignment database."
                        )
                    else:
                        st.success(
                            f"Found **{len(results)}** potentially similar passages."
                        )

                        # Anonymize document names
                        doc_id_map = {}
                        anon_counter = 1

                        for record, score in results:
                            if record.doc_name not in doc_id_map:
                                doc_id_map[record.doc_name] = (
                                    f"Document-{anon_counter:03d}"
                                )
                                anon_counter += 1

                        # Display anonymized results
                        for rank, (record, score) in enumerate(results, 1):
                            anon_doc_name = doc_id_map[record.doc_name]
                            color = "#ff4b4b" if score >= 0.90 else "#ffa500"

                            with st.expander(
                                f"#{rank} · {anon_doc_name} (chunk #{record.chunk_index+1}) "
                                f"— {score:.1%}",
                                expanded=(rank == 1),
                            ):
                                cq, cm = st.columns(2)
                                with cq:
                                    st.markdown("**Your query:**")
                                    st.info(query_text.strip())
                                with cm:
                                    st.markdown(
                                        f"**Matching passage in {anon_doc_name}:**"
                                    )
                                    st.warning(record.chunk_text)

                                st.markdown(
                                    f"<div style='text-align:right;'>"
                                    f"<span style='background:{color};color:white;padding:3px 12px;"
                                    f"border-radius:10px;font-size:0.85rem;font-weight:700;'>"
                                    f"Similarity: {score*100:.1f}%</span></div>",
                                    unsafe_allow_html=True,
                                )

                        st.caption(
                            "🔒 Document names are anonymized to protect student privacy."
                        )

            except Exception as e:
                from src.errors import UI_INDEX_LOAD_FAILED

                st.error(UI_INDEX_LOAD_FAILED.format(error=str(e)))
                st.info(
                    "Please ensure documents have been indexed by an administrator."
                )
else:
    # ADMINISTRATOR ACCESS: Full Upload Pipeline & Evaluation Dashboards

    # Load or initialize FAISS index
    if os.path.exists(_INDEX_PATH):
        faiss_index = load_index(_INDEX_PATH)
        registry = get_chunk_registry()
        if faiss_index is not None and faiss_index.ntotal != len(registry):
            all_embs = get_all_embeddings()
            if len(all_embs) > 0 and len(all_embs) == len(registry):
                faiss_index = build_index_from_matrix(all_embs)
                save_index(faiss_index, _INDEX_PATH)
            elif len(all_embs) == 0:
                faiss_index = None
                registry = []
        if faiss_index is not None:
            st.info(f"📂 Loaded existing FAISS index with {faiss_index.ntotal} vectors")
    else:
        threshold = DEFAULT_THRESHOLDS.plagiarism
        use_chunk_matrix = False
        faiss_top_k = 5
        chunk_size = 500
        chunk_overlap = 50
        ocr_language = DEFAULT_OCR_LANGUAGE
        ocr_dpi = DEFAULT_OCR_DPI
        ignore_phrases = ""
        st.info("ℹ️ Settings configuration is restricted to Administrators.")

# ── Onboarding Tour for First-Time Admin Users ───────────────────────────────────
if (
    Tour is not None
    and user_role == "admin"
    and not get_tour_completed(st.session_state.username)
):
    username = st.session_state.username

    if st.button("🎯 Start Guided Tour", key="start_tour_button", type="primary"):
        st.session_state.show_tour = True

    if st.session_state.get("show_tour", False):
        tour_steps = [
            Tour.info(
                title="👋 Welcome to the Plagiarism Detection System!",
                desc="This guided tour will walk you through the key features to help you get started.",
            ),
            Tour.bind(
                "threshold_slider",
                title="⚙️ Plagiarism Threshold",
                desc=f"Adjust the flagging threshold. Medium severity starts at {DEFAULT_THRESHOLDS.medium:.0%} and High at {DEFAULT_THRESHOLDS.high:.0%}.",
                side="right",
            ),
            Tour.bind(
                "class_filter_selectbox",
                title="🔍 Class Filter",
                desc="Filter analysis results by specific class sections.",
                side="right",
            ),
            Tour.info(
                title="📊 Analysis Dashboard",
                desc="View similarity metrics, flagged pairs, and comparisons in the tabs below.",
            ),
            Tour.info(
                title="🎉 You're All Set!",
                desc="You can now start uploading assignments and detecting plagiarism.",
            ),
        ]

        tour = Tour(steps=tour_steps)
        tour.start()

        if st.button("✅ Finish Tour", use_container_width=True):
            set_tour_completed(username, True)
            st.session_state.show_tour = False
            st.success("✅ Onboarding tour completed!")
            st.rerun()

# ── Main Header ──────────────────────────────────────────────────────────────
st.title(get_text("title", lang=lang_code))
st.markdown(get_text("subtitle", lang=lang_code))
st.divider()

# ── MAIN APPLICATION SECTIONS ──────────────────────────────────────────────────
if user_role != "admin":
    # STANDARD USER VIEW
    st.subheader("🔎 Secure Student Search Portal")
    st.caption(
        "Paste a text snippet below to check its similarity against existing indexed assignments."
    )
    st.info(
        "🔒 Note: Direct assignment uploads are restricted to Administrator access."
    )
    query_text = st.text_area(
        "Search Query Text:",
        placeholder="Paste document content here to search for matching plagiarism...",
        height=200,
    )

    if st.button("🔍 Run Quick Verification", key="user_query") and query_text.strip():

        with st.spinner("Loading index and searching..."):
            try:
                registry = get_chunk_registry()
                embeddings_matrix = get_all_embeddings()

                if embeddings_matrix.shape[0] == 0:
                    st.warning("No documents are currently indexed.")
                else:
                    memory = psutil.virtual_memory()
                    if memory.percent >= 85:
                        st.warning(
                            "⚠️ High memory usage detected (>85%). Large FAISS indexes may cause system instability or out-of-memory crashes."
                        )
                    faiss_index = build_index_from_matrix(
                        embeddings_matrix, index_type="auto"
                    )
                    processed_query = query_text.strip()
                    query_vec = embed_chunks([processed_query])[0]
                    faiss_threshold = 0.50  # Standard user default

                    results = search_similar_chunks(
                        query_vec,
                        faiss_index,
                        registry,
                        top_k=5,
                        threshold=faiss_threshold,
                    )

                    if not results:
                        st.success(
                            "✅ No significant matches found in the assignment database."
                        )
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
                            with st.expander(
                                f"#{rank} · {anon_doc_name} (chunk #{record.chunk_index+1}) — {score:.1%}",
                                expanded=(rank == 1),
                            ):
                                cq, cm = st.columns(2)
                                with cq:
                                    st.markdown("**Your query:**")
                                    st.info(query_text.strip())
                                with cm:
                                    st.markdown(
                                        f"**Matching passage in {anon_doc_name}:**"
                                    )
                                    st.warning(record.chunk_text)

                                st.markdown(
                                    f"<div style='text-align:right;'>"
                                    f"<span style='background:{color};color:white;padding:3px 12px;"
                                    f"border-radius:10px;font-size:0.85rem;font-weight:700;'>"
                                    f"Similarity: {score*100:.1f}%</span></div>",
                                    unsafe_allow_html=True,
                                )

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

        except Exception:

            if os.path.exists(_INDEX_PATH):
                faiss_index = load_index(_INDEX_PATH)
                registry = get_chunk_registry()
            else:
                faiss_index = None
                registry = []

    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None

            st.info(f"📂 Loaded FAISS index from Redis cache with {faiss_index.ntotal} vectors")
        except Exception as e:
            print(f"[Redis] Error loading cached index: {e}, falling back to disk")
            from src.core.faiss_index import load_or_rebuild_index

    if faiss_index is None:
        try:
            memory = psutil.virtual_memory()
            if memory.percent >= 85:
                st.warning(
                    "⚠️ High memory usage detected (>85%). Large FAISS indexes may cause system instability or out-of-memory crashes."
                )
            faiss_index, registry, index_recovered = load_or_rebuild_index(_INDEX_PATH)
            if index_recovered:
                if faiss_index.ntotal:
                    st.warning(
                        f"FAISS index rebuilt from {faiss_index.ntotal} stored vectors."
                    )
                else:
                    st.info(
                    "No stored embeddings were found. An empty FAISS index was "
                    "initialized safely.")
            else:
                st.info(f"Loaded and validated the existing FAISS index with "f"{faiss_index.ntotal} vectors.")

    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None
        # Try to load from Redis cache

                st.info(
                    f"Loaded existing FAISS index with {faiss_index.ntotal} vectors."
                )
        except (RuntimeError, ValueError, OSError):
            faiss_index = None
            registry = []

    def load_analysis_results_from_db():
        import numpy as np
        import pandas as pd

        docs = get_all_documents()
        if not docs:
            return None

        raw_texts = {}
        chunked_docs = {}
        embeddings = {}

        try:
            from src.db.corpus_db import _connect

            with _connect() as conn:
                rows = conn.execute(
                    "SELECT filename, chunk_index, chunk_text, embedding FROM chunks ORDER BY filename, chunk_index"
                ).fetchall()

            for fname, chunk_idx, text, emb_blob in rows:
                if fname not in raw_texts:
                    raw_texts[fname] = ""
                    chunked_docs[fname] = []
                    embeddings[fname] = []

                raw_texts[fname] += text + " "
                chunked_docs[fname].append(text)

                emb = np.frombuffer(emb_blob, dtype=np.float32)
                embeddings[fname].append(emb)

            # Convert lists to numpy arrays
            for fname in embeddings:
                embeddings[fname] = np.vstack(embeddings[fname])

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

            f_index = load_index(_INDEX_PATH) if os.path.exists(_INDEX_PATH) else None
            f_registry = get_chunk_registry()

            # Default AI probabilities for loaded documents to 0.0
            ai_probs = {
                fname: {"overall": 0.0, "max": 0.0, "chunk_scores": []}
                for fname in names
            }

            return (
                raw_texts,
                chunked_docs,
                embeddings,
                sim_df,
                chunk_sim_df,
                f_index,
                f_registry,
                ai_probs,
            )
        except (RuntimeError, ValueError, OSError, TypeError, KeyError) as err:
            print(f"Error rebuilding analysis results from DB: {err}")
        except Exception as err:
            logger.error(f"Error rebuilding analysis results from DB: {err}")
            return None

    if (
        "analysis_results" not in st.session_state
        or st.session_state.analysis_results is None
    ):
        st.session_state.analysis_results = None
        cached_results = get_analysis_results(f"{SESSION_ID}:current")
        if cached_results is not None:
            st.session_state.analysis_results = cached_results
        else:
            st.session_state.analysis_results = load_analysis_results_from_db()

    if "analysis_file_signature" not in st.session_state:
        st.session_state.analysis_file_signature = None
        cached_signature = get_session_state(SESSION_ID, "analysis_file_signature")
        if cached_signature is not None:
            st.session_state.analysis_file_signature = cached_signature

    # 1. LOCAL FILE UPLOADER (Dynamic Title Translation)
    # 1. LOCAL FILE UPLOADER
    uploaded_files = st.file_uploader(
        get_text("upload_title", lang=lang_code),
        type=["pdf", "docx", "txt", "zip", "csv"],
        accept_multiple_files=True,
        key="file_uploader",
    )
    # 2. GOOGLE DRIVE IMPORT SECTION

    if uploaded_files:
        username = st.session_state.get("username", "anonymous")
        if is_upload_rate_limited(username):
            current_count = get_upload_count(username)
            st.error(f"🚨 Upload rate limit exceeded. Current: {current_count}/100.")
            uploaded_files = None
        else:
            for _ in uploaded_files:
                increment_upload_count(username)

    # CSV Column Configuration Section
    csv_configs = {}
    csv_files = (
        [f for f in uploaded_files if f.name.lower().endswith(".csv")]
        if uploaded_files
        else []
    )
    if csv_files:
        st.markdown("### 📊 CSV Ingestion Settings")
        for f in csv_files:
            try:
                csv_bytes = f.getvalue()
                df = pd.read_csv(_io.BytesIO(csv_bytes))
                columns = list(df.columns)
                if not columns:
                    st.error(f"⚠️ CSV file '{f.name}' has no columns.")
                    continue
                # Auto-detect default text column
                default_text_idx = 0
                for i, col in enumerate(columns):
                    if any(
                        term in col.lower()
                        for term in [
                            "response",
                            "answer",
                            "text",
                            "essay",
                            "content",
                            "document",
                            "submission",
                        ]
                    ):
                        default_text_idx = i
                        break
                # Auto-detect default name/id column
                default_name_idx = None
                for i, col in enumerate(columns):
                    if (
                        any(
                            term in col.lower()
                            for term in [
                                "name",
                                "student",
                                "email",
                                "id",
                                "user",
                                "username",
                                "timestamp",
                            ]
                        )
                        and i != default_text_idx
                    ):
                        default_name_idx = i
                        break
                st.markdown(f"**Column Mapping for `{f.name}`**")
                col_text, col_name = st.columns(2)
                with col_text:
                    text_col = st.selectbox(
                        f"Text Column ({f.name})",
                        options=columns,
                        index=default_text_idx,
                        key=f"csv_text_col_{f.name}",
                        help="Select the column containing the essay/text responses to analyze.",
                    )
                with col_name:
                    name_options = ["None (Use Row Number)"] + columns
                    default_name_idx_adjusted = (
                        (default_name_idx + 1) if default_name_idx is not None else 0
                    )
                    name_col = st.selectbox(
                        f"Student Name/ID Column ({f.name})",
                        options=name_options,
                        index=default_name_idx_adjusted,
                        key=f"csv_name_col_{f.name}",
                        help="Select the column containing student names or IDs (optional).",
                    )
                csv_configs[f.name] = {
                    "df": df,
                    "text_col": text_col,
                    "name_col": (
                        None if name_col == "None (Use Row Number)" else name_col
                    ),
                }
            except (ValueError, OSError, TypeError, KeyError) as e:
                st.error(f"❌ Failed to parse CSV file '{f.name}': {str(e)}")

    st.markdown("### 🔗 Or Upload via Public URL")

    # Initialise URL-related session state keys so they persist across reruns
    if "url_text" not in st.session_state:
        st.session_state.url_text = None
    if "url_filename" not in st.session_state:
        st.session_state.url_filename = None
    if "_last_fetched_url" not in st.session_state:
        st.session_state._last_fetched_url = ""

    _url_col, _btn_col = st.columns([5, 1])
    with _url_col:
        url_input = st.text_input(
            "Paste a direct URL to a document or webpage",
            placeholder="https://example.com/paper.pdf",
            key="url_input",
            help='Enter a public URL to a PDF, DOCX, TXT file, or webpage. Click "Fetch" to load it.',
        )
    with _btn_col:
        st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        fetch_url_btn = st.button(
            "Fetch", key="fetch_url_btn", use_container_width=True
        )

    # 2. GOOGLE DRIVE IMPORT SECTION (#146)

    from src.utils.google_drive import bulk_download_drive_folder

    # Clear cached URL result when the user changes the URL field
    if url_input.strip() != st.session_state._last_fetched_url:
        if st.session_state.url_text is not None:
            st.session_state.url_text = None
            st.session_state.url_filename = None

    # Fetch only when the button is explicitly clicked
    if fetch_url_btn and url_input and url_input.strip():
        try:
            from src.core.document_parser import extract_text_from_url

            with st.spinner("🔍 Fetching and extracting text from URL..."):
                _fetched_text = extract_text_from_url(url_input.strip())
                if not _fetched_text or len(_fetched_text.strip()) < 50:
                    st.warning(
                        "⚠️ The URL did not return enough text content for analysis."
                    )
                else:
                    from urllib.parse import urlparse as _urlparse

                    _parsed = _urlparse(url_input.strip())
                    st.session_state.url_text = _fetched_text
                    st.session_state.url_filename = sanitize_filename(
                        f"webpage_{_parsed.netloc.replace('.', '_')}.txt"
                    )
                    st.session_state._last_fetched_url = url_input.strip()
                    st.success(
                        f"✅ Successfully extracted {len(_fetched_text)} characters from the URL."
                    )
        # Requires generic catch because extract_text_from_url explicitly raises generic Exception
        except Exception as _e:
            st.error(f"❌ Failed to fetch URL: {str(_e)}")
            st.session_state.url_text = None
            st.session_state.url_filename = None

    # Show status of currently loaded URL document
    if st.session_state.url_text is not None:
        st.info(
            f"🔗 URL document loaded: **{st.session_state.url_filename}** ({len(st.session_state.url_text)} characters)"
        )

    file_bytes_dict = {}
    if uploaded_files:
        for uploaded_file in uploaded_files:
            safe_name = unique_filename(
                uploaded_file.name,
                file_bytes_dict,
            )
            file_bytes_dict[safe_name] = uploaded_file.getvalue()


# -----------------------------------------------------------------------------
# Authentication Guard
# -----------------------------------------------------------------------------
if not st.session_state.authenticated:
    st.header("🔑 Login")
    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")

    if st.button("Login"):
        if authenticate_user(username_input, password_input):
            st.session_state.authenticated = True
            st.session_state.username = username_input
            st.rerun()
        else:
            st.error("Invalid username or password.")
    st.stop()
    # 2. GOOGLE DRIVE IMPORT SECTION (#146)
    try:
        from src.utils.google_drive import bulk_download_drive_folder
    except ImportError:
        bulk_download_drive_folder = None

    if "drive_files_dict" not in st.session_state:
        st.session_state.drive_files_dict = {}

    if bulk_download_drive_folder is not None:
        with st.expander("🌐 Import from Google Drive Folder", expanded=False):
            drive_folder_input = st.text_input(
                "Google Drive Folder Link / ID:", key="drive_folder_url_input"
            )
            drive_api_key = st.text_input(
                "API Key (Optional):", type="password", key="drive_api_key_input"
            )

            if st.button(
                "📥 Import Files from Drive", type="primary", use_container_width=True
            ):
                if not drive_folder_input.strip():
                    st.error("🚨 Please enter a valid Google Drive folder link or ID.")
                else:
                    with st.spinner(
                        "Connecting to Google Drive API & downloading files..."
                    ):
                        try:
                            downloaded_dict, downloaded_names = (
                                bulk_download_drive_folder(
                                    folder_url_or_id=drive_folder_input,
                                    api_key=(
                                        drive_api_key.strip() if drive_api_key else None
                                    ),
                                )
                            )

                            if downloaded_dict:
                                scrubbed_drive = {
                                    n: strip_exif_metadata(d, n)
                                    for n, d in downloaded_dict.items()
                                }
                                st.session_state.drive_files_dict.update(scrubbed_drive)
                                st.success(
                                    f"✅ Imported {len(downloaded_names)} files: {', '.join(downloaded_names)}"
                                )
                                st.rerun()
                            else:
                                st.warning(
                                    "No supported files found in this Drive folder."
                                )
                        except (RuntimeError, OSError, ValueError, ImportError) as err:
                            st.error(
                                f"🚨 Failed to import from Google Drive: {str(err)}"
                            )

    # 3. MERGE LOCAL AND DRIVE FILE BYTES & ENFORCE 10MB FILE SIZE LIMIT (#169)
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB limit
    file_bytes_dict = {}
    if uploaded_files:
        # Re-initialize to handle zip/csv extraction correctly instead of raw bytes
        file_bytes_dict = {}
        for uploaded_file in uploaded_files:
            original_name = uploaded_file.name

            try:
                validate_document_extension(
                    original_name,
                    allowed_extensions={
                        ".csv",
                        ".docx",
                        ".pdf",
                        ".txt",
                        ".zip",
                    },
                )
            except InvalidFileExtensionError as exc:
                st.error(
                    f"⚠️ File **'{sanitize_filename(original_name)}'** "
                    f"was rejected: {exc}"
                )
                continue

            safe_name = unique_filename(
                original_name,
                file_bytes_dict,
            )

            if uploaded_file.size > MAX_FILE_SIZE_BYTES:
                st.error(
                    f"⚠️ File **'{safe_name}'** exceeds the maximum size "
                    f"limit of 10MB "
                    f"({uploaded_file.size / (1024 * 1024):.2f}MB). "
                    "Please upload a smaller file."
                )
                continue

            if original_name.lower().endswith(".zip"):
                try:
                    from src.utils.zip_processor import process_zip_file

                    zip_files = process_zip_file(uploaded_file.read())
                    if not zip_files:
                        st.error(
                            f"⚠️ ZIP file '{safe_name}' contains no supported documents (.pdf, .docx, .txt)."
                        )
                    else:
                        file_bytes_dict.update(
                            {
                                name: strip_exif_metadata(data, name)
                                for name, data in zip_files.items()
                            }
                        )
                except ValueError as ve:
                    st.error(f"⚠️ Failed to process ZIP archive '{safe_name}': {str(ve)}")
                except (OSError, RuntimeError, TypeError):
                    st.error(
                        f"⚠️ Failed to process ZIP archive '{safe_name}': Unknown error occurred."
                    )
            elif original_name.lower().endswith(".csv"):
                if original_name in csv_configs:
                    config = csv_configs[original_name]
                    df = config["df"]
                    text_col = config["text_col"]
                    name_col = config["name_col"]
                    for idx, row in df.iterrows():
                        text_val = row[text_col]
                        if pd.isna(text_val) or not str(text_val).strip():
                            continue
                        if name_col and not pd.isna(row[name_col]):
                            student_name = str(row[name_col]).strip()
                        else:
                            student_name = f"Row {idx + 1}"
                        virtual_filename = unique_filename(
                            (
                                f"{student_name} "
                                f"({safe_name} - Row {idx + 1}).txt"
                            ),
                            file_bytes_dict,
                        )
                        file_bytes_dict[virtual_filename] = strip_exif_metadata(
                            str(text_val).encode("utf-8"), virtual_filename
                        )
            else:
                file_bytes_dict[safe_name] = strip_exif_metadata(
                    uploaded_file.read(),
                    safe_name,
                )
            uploaded_file.seek(0)

    # Allow analysis with existing index even without new uploads
    # Read URL result from session state (populated by the Fetch button above)
    url_text = st.session_state.url_text
    url_filename = st.session_state.url_filename

    if st.session_state.drive_files_dict:
        for drive_name, drive_bytes in st.session_state.drive_files_dict.items():
            safe_drive_name = unique_filename(
                drive_name,
                file_bytes_dict,
            )
            if len(drive_bytes) > MAX_FILE_SIZE_BYTES:
                st.error(
                    f"⚠️ Google Drive file **'{safe_drive_name}'** exceeds "
                    f"the maximum size limit of 10MB "
                    f"({len(drive_bytes) / (1024 * 1024):.2f}MB)."
                )
            else:
                file_bytes_dict[safe_drive_name] = drive_bytes

    # 3. PDF Decryption Check
    encrypted_files_detected = []
    import fitz

    for file_name, file_bytes in list(file_bytes_dict.items()):
        if file_name.lower().endswith(".pdf"):
            try:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                is_encrypted = doc.is_encrypted or doc.needs_pass
                doc.close()

                if is_encrypted:
                    user_pass = st.session_state.pdf_passwords.get(file_name, None)
                    if not user_pass:
                        encrypted_files_detected.append(file_name)
                    else:
                        doc = fitz.open(stream=file_bytes, filetype="pdf")
                        auth_success = doc.authenticate(user_pass)
                        if not auth_success:
                            encrypted_files_detected.append(file_name)
                        else:
                            file_bytes_dict[file_name] = doc.write()
                        doc.close()
            except Exception:
                pass

    if encrypted_files_detected:
        st.warning(
            "🔒 Password-protected PDF(s) detected! Please enter the password(s) below:"
        )
        for enc_file in encrypted_files_detected:
            col1, col2 = st.columns([3, 1])
            with col1:
                input_pass = st.text_input(
                    f"Password for '{enc_file}'",
                    type="password",
                    key=f"pass_input_{enc_file}",
                )
            with col2:
                st.write(" ")
                st.write(" ")
                if st.button("Decrypt PDF", key=f"btn_decrypt_{enc_file}"):
                    if input_pass:
                        st.session_state.pdf_passwords[enc_file] = input_pass
                        st.success(f"Password saved for {enc_file}!")
                        st.rerun()
                    else:
                        st.error("Please enter a password.")
        st.stop()

    # 4. PIPELINE STOP CHECK
    if len(file_bytes_dict) < 2 and url_text is None:
        if st.session_state.analysis_results is None:
            st.markdown(
                empty_state_html(
                    "Waiting for Files",
                    "Please upload or import from Drive at least 2 PDF, DOCX, or TXT assignments (under 10MB each) to begin.",
                    "📂",
                ),
                unsafe_allow_html=True,
            )
            st.stop()

    st.markdown("### 📝 Set Document Metadata")
    col1, col2 = st.columns(2)
    with col1:
        batch_class = st.text_input("Default Class/Section", value="Class A")
    with col2:
        batch_assignment = st.text_input(
            "Default Assignment Title", value="Assignment 1"
        )

    col_tags = st.columns(1)[0]
    with col_tags:
        batch_tags = st.text_input("Tags (comma separated)", placeholder="#hw1, #draft")

    metadata_dict = {}
    for filename in file_bytes_dict.keys():
        # Check if this filename is a virtual CSV document
        is_csv_doc = False
        csv_filename_matched = None
        for csv_name in csv_configs.keys():
            if f"({csv_name} - Row " in filename:
                is_csv_doc = True
                csv_filename_matched = csv_name
                break

        if is_csv_doc:
            base_name = os.path.splitext(filename)[0]
            marker = f"({csv_filename_matched} - Row "
            marker_idx = base_name.find(marker)
            if marker_idx != -1:
                student_name = base_name[:marker_idx].strip()
            else:
                student_name = base_name

            metadata_dict[filename] = {
                "student_name": student_name,
                "class_section": batch_class.strip(),
                "assignment_title": batch_assignment.strip(),
                "tags": batch_tags.strip(),
            }
        else:
            base_name = os.path.splitext(filename)[0]
            guessed_name = base_name.replace("_", " ").replace("-", " ").title()

            with st.expander(f"📄 {filename}", expanded=False):
                student_name = st.text_input(
                    f"Student Name for {filename}",
                    value=guessed_name,
                    key=f"student_{filename}",
                )
                class_section = st.text_input(
                    f"Class/Section for {filename}",
                    value=batch_class,
                    key=f"class_{filename}",
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

    if url_filename:
        with st.expander(f"🔗 {url_filename}", expanded=True):
            student_name = st.text_input(
                f"Student Name for {url_filename}",
                value="Web Source",
                key=f"student_{url_filename}",
            )
            class_section = st.text_input(
                f"Class/Section for {url_filename}",
                value=batch_class,
                key=f"class_{url_filename}",
            )
            assignment_title = st.text_input(
                f"Assignment Title for {url_filename}",
                value=batch_assignment,
                key=f"assignment_{url_filename}",
            )
            metadata_dict[url_filename] = {
                "student_name": student_name.strip(),
                "class_section": class_section.strip(),
                "assignment_title": assignment_title.strip(),
                "tags": batch_tags.strip(),
            }

    @st.cache_data(show_spinner=False)
    def run_pipeline(
        file_bytes_dict: dict[str, bytes],
        ocr_language: str,
        ocr_dpi: int,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        existing_index=None,
        existing_registry=None,
        url_text: str = None,
        url_filename: str = None,
    ):
        raw_texts = {}
        failed_files = []
        failure_details = []

        for name, data in file_bytes_dict.items():
            if not data:
                continue  # Skip dummy data used for existing index bypass
            try:
                raw_texts[name] = extract_text(
                    _io.BytesIO(data), name, ocr_language=ocr_language, ocr_dpi=ocr_dpi
                )
            except OCRDependencyError as exc:
                failed_files.append(name)
                failure_details.append(f"{name}: {exc}")

        if url_text and url_filename:
            raw_texts[url_filename] = url_text

        if failed_files:
            raise OCRFileBatchError(failed_files, failure_details)

        if "ignore_phrases" in globals() and ignore_phrases and ignore_phrases.strip():
            raw_texts = {
                name: remove_ignore_phrases(text, ignore_phrases)
                for name, text in raw_texts.items()
            }

        chunked_docs = chunk_documents(
            raw_texts, chunk_size=chunk_size, chunk_overlap=chunk_overlap
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

        memory = psutil.virtual_memory()
        if memory.percent >= 85:
            st.warning(
                "⚠️ High memory usage detected (>85%). Large FAISS indexes may cause system instability or out-of-memory crashes."
            )

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

    has_enough_files = (len(file_bytes_dict) + (1 if url_text else 0)) >= 2


    # Run Pipeline if files uploaded
    if (len(file_bytes_dict) > 0 and any(file_bytes_dict.values())) or url_text:
        try:
            with st.spinner("🧠 Processing files and building embeddings…"):
                start_time = time.time()
                analysis_results = run_pipeline(
                    file_bytes_dict=file_bytes_dict,
                    ocr_language=ocr_language,
                    ocr_dpi=ocr_dpi,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    url_text=url_text,
                    url_filename=url_filename,
                )
                elapsed_time = time.time() - start_time
                st.session_state.analysis_results = analysis_results
                st.toast(f"Successfully processed in {elapsed_time:.2f} seconds 🚀")
        except OCRFileBatchError as exc:
            from src.errors import OCR_DEPENDENCIES_MISSING

            st.error(f"🚨 {OCR_DEPENDENCIES_MISSING}")
            if exc.failed_files:
                st.warning(f"Failed files: {', '.join(exc.failed_files)}")
            st.stop()
    else:
        analysis_results = st.session_state.analysis_results

    (
        raw_texts,
        chunked_docs,
        embeddings,
        sim_df,
        chunk_sim_df,
        faiss_index,
        registry,
        ai_probabilities,
        pipeline_failed_files,
    ) = analysis_results

    if pipeline_failed_files:
        st.session_state.failed_documents.update(pipeline_failed_files)

    active_sim_df = chunk_sim_df if use_chunk_matrix else sim_df
    flags = flag_plagiarism(
        active_sim_df,
        threshold=threshold,
        chunked_docs=chunked_docs,
        embeddings=embeddings,
    )

    # Network Graph Node Click Filtering setup
    selected_document_id = st.session_state.get("selected_document_id")
    if selected_document_id:
        filtered_flags = [
            flag
            for flag in flags
            if (
                flag["doc_a"] == selected_document_id
                or flag["doc_b"] == selected_document_id
            )
        ]
    else:
        filtered_flags = flags

    from src.core.tag_manager import TagManager
    from src.db.corpus_db import get_document_tags

    # Fetch tags for filtering
    active_tag = st.session_state.get("selected_tag", "All Tags")
    if active_tag != "All Tags":
        flagged_tags_filtered = []
        for flag in filtered_flags:
            tags_a = get_document_tags(flag["doc_a"])
            tags_b = get_document_tags(flag["doc_b"])
            # Include if EITHER document has the selected tag
            if TagManager.has_matching_tag(
                tags_a, active_tag
            ) or TagManager.has_matching_tag(tags_b, active_tag):
                flagged_tags_filtered.append(flag)
        filtered_flags = flagged_tags_filtered



        # Network Graph Node Click Filtering setup
        selected_document_id = st.session_state.get("selected_document_id")
        if selected_document_id:
            filtered_flags = [
                flag
                for flag in flags
                if (
                    flag["doc_a"] == selected_document_id
                    or flag["doc_b"] == selected_document_id
                )
            ]
        else:
            filtered_flags = flags
    else:
        flags = []
        filtered_flags = []
        active_sim_df = None

    if has_enough_files:
        if "sent_alerts" not in st.session_state:
            st.session_state.sent_alerts = set()

        for flag in filtered_flags:
            alert_key = (flag["doc_a"], flag["doc_b"])
            if alert_key not in st.session_state.sent_alerts:
                try:
                    send_plagiarism_alert(
                        doc_a=flag["doc_a"],
                        doc_b=flag["doc_b"],
                        similarity=float(flag["similarity"]),
                    )
                    st.session_state.sent_alerts.add(alert_key)
                except (ConnectionError, RuntimeError, OSError):
                    pass

        st.subheader(get_text("analysis_summary", lang=lang_code))
        doc_names = list(raw_texts.keys())
        n_docs = len(doc_names)
        total_pairs = n_docs * (n_docs - 1) // 2 if n_docs > 1 else 0
        n_flagged = len(flags)

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric(get_text("metric_docs", lang=lang_code), n_docs)
        col2.metric(get_text("metric_pairs", lang=lang_code), total_pairs)
        col3.metric(get_text("metric_flagged", lang=lang_code), n_flagged)
        col4.metric(
            get_text("metric_faiss", lang=lang_code),
            faiss_index.ntotal if faiss_index is not None else 0,
        )
        col5.metric("🎯 Threshold", f"{threshold:.0%}")
        st.divider()

    # ── Application Tabs (Translated i18n Headers) ────────────────────────────
    (
        tab_warnings,
        tab_faiss,
        tab_matrix,
        tab_heatmap,
        tab_drill,
        tab_analytics,
        tab_users,
        tab_settings,
    ) = st.tabs(
        [
            get_text("tab_warnings", lang=lang_code),
            get_text("tab_faiss", lang=lang_code),
            get_text("tab_matrix", lang=lang_code),
            get_text("tab_heatmap", lang=lang_code),
            get_text("tab_drill", lang=lang_code),
            get_text("tab_analytics", lang=lang_code),
            get_text("tab_users", lang=lang_code),
            get_text("tab_settings", lang=lang_code),
        ],
        key="main_tabs",
    )

    # ══ TAB 1: WARNINGS ═══════════════════════════════════════════════════════
    with tab_warnings:
        st.markdown("🏠 Home > Dashboard > **Warnings**")
        st.subheader(get_text("tab_warnings", lang=lang_code))

        # LMS incident exports
        st.markdown("---")
        st.caption(
            "Export flagged plagiarism incidents for LMS review or "
            "human-readable offline analysis."
        )

        raw_incidents = get_all_incidents_above_threshold_for_export(
            threshold=threshold
        )
        csv_data = LMSExportEngine.generate_incident_csv(raw_incidents)
        txt_data = LMSExportEngine.generate_incident_txt(raw_incidents)

        export_csv_col, export_txt_col = st.columns(2)

        with export_csv_col:
            if csv_data:
                st.download_button(
                    label="📥 Export CSV",
                    data=csv_data,
                    file_name="plagiarism_incident_log.csv",
                    mime="text/csv",
                    key="export_incidents_csv",
                    use_container_width=True,
                )
            else:
                st.button(
                    "📥 Export CSV",
                    disabled=True,
                    key="export_incidents_csv_disabled",
                    use_container_width=True,
                )

        with export_txt_col:
            if txt_data:
                st.download_button(
                    label="📝 Export TXT",
                    data=txt_data,
                    file_name="plagiarism_incident_summary.txt",
                    mime="text/plain; charset=utf-8",
                    key="export_incidents_txt",
                    use_container_width=True,
                )
            else:
                st.button(
                    "📝 Export TXT",
                    disabled=True,
                    key="export_incidents_txt_disabled",
                    use_container_width=True,
                )

        st.markdown("---")

        if selected_document_id:
            st.info(f"Showing warnings involving: {selected_document_id}")
            if st.button("Clear Document Filter"):
                st.session_state.selected_document_id = None
                st.rerun()

            render_warning_controls(
                filtered_flags, threshold=threshold, ai_probabilities=ai_probabilities
            )

    # ══ TAB 2: FAISS ══════════════════════════════════════════════════════════
    with tab_faiss:

        st.subheader("⚡ FAISS Vector Search")

        if faiss_index is not None:
            st.info(f"Index total: {faiss_index.ntotal} vectors.")
        else:
            st.warning("FAISS index is not initialized.")

        st.markdown("🏠 Home > Dashboard > **FAISS Chunk Search**")
        st.subheader("⚡ FAISS Chunk Search")
        st.info(f"Index total: {faiss_index.ntotal if faiss_index else 0} vectors.")

        faiss_query = st.text_input(
            "Query FAISS Index:",
            placeholder="Type a text snippet to search vector index...",
            key="faiss_query_input",
        )

        if st.button("🔍 Run FAISS Search", key="run_faiss_search_btn"):
            if faiss_query.strip() and faiss_index is not None:
                try:
                    from src.core.embeddings import generate_embeddings  # type: ignore
                    from src.core.faiss_indexer import (
                        search_similar_chunks,  # type: ignore
                    )

                    q_vec = generate_embeddings([faiss_query.strip()])[0]
                    q_results = search_similar_chunks(
                        q_vec,
                        faiss_index,
                        registry,
                        top_k=faiss_top_k if "faiss_top_k" in locals() else 5,
                        threshold=threshold,
                    )
                    if q_results:
                        for rec, score in q_results:
                            st.markdown(
                                f"**{rec.doc_name}** (Chunk #{rec.chunk_index}) — Similarity: `{score:.1%}`"
                            )
                            st.caption(rec.chunk_text)
                    else:
                        st.info("No matching vector chunks found above threshold.")
                except Exception as err:
                    st.error(f"FAISS search error: {err}")
            else:
                st.warning("Please enter a valid query string.")

    # ══ TAB 3: MATRIX ═════════════════════════════════════════════════════════
    with tab_matrix:
        st.markdown("🏠 Home > Dashboard > **Similarity Matrix**")
        st.subheader("📋 Similarity Matrix")
        if active_sim_df is None:
            from src.errors import UI_SIMILARITY_MATRIX_REUPLOAD

            st.info(UI_SIMILARITY_MATRIX_REUPLOAD)
        else:

            # Apply chosen colormap to matrix styling (#186)
            st.dataframe(
                active_sim_df.style.background_gradient(cmap=heatmap_cmap).format(
                    "{:.4f}"
                ),
                use_container_width=True,
            )

            def _highlight(val: Any) -> str:
                tier = severity_key(float(val))
                if tier == "high":
                    return "background-color:#ff4b4b;color:white;font-weight:bold;"
                if tier == "medium":
                    return "background-color:#ffa500;color:white;font-weight:bold;"
                return ""

            styled_df = active_sim_df.style.format("{:.4f}").map(_highlight)
            st.dataframe(styled_df, use_container_width=True)

            # Export options row
            col_csv, col_json, col_excel = st.columns(3)
            with col_csv:
                st.download_button(
                    "Download CSV",
                    active_sim_df.to_csv().encode("utf-8"),
                    "similarity_matrix.csv",
                    "text/csv",
                    use_container_width=True,
                )
            with col_json:
                json_data = export_similarity_matrix_to_json(active_sim_df).encode(
                    "utf-8"
                )
                st.download_button(
                    "⬇️ Download JSON",
                    json_data,
                    "similarity_matrix.json",
                    "application/json",
                    key="json_export_button",
                    use_container_width=True,
                )
            with col_excel:
                excel_data = export_similarity_matrix_to_excel(
                    active_sim_df, threshold=threshold
                )
                st.download_button(
                    "Download Excel",
                    excel_data,
                    "similarity_matrix_styled.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

    # ══ TAB 4: HEATMAP & NETWORK ══════════════════════════════════════════════
    with tab_heatmap:

        st.subheader("🗺️ Similarity Heatmap")

        heatmap_fig = plot_similarity_heatmap(
            active_sim_df,
            title="Document Semantic Similarity",
            threshold=threshold,
            theme_colors=get_colors(),
            cmap=heatmap_cmap,  # Dynamic colormap support (#186)
        )
        st.pyplot(heatmap_fig, use_container_width=True)

        # ══ TAB 5: PAIR DRILL-DOWN ══════════════════════════════════════════════════

        st.markdown("🏠 Home > Dashboard > **Heatmap & Network**")
        st.subheader(get_text("tab_heatmap", lang=lang_code))
        if not has_enough_files or active_sim_df is None:
            st.markdown(
                empty_state_html(
                    "Waiting for Files",
                    "Please upload at least 2 PDF, DOCX, or TXT assignments to begin analysis.",
                    "📂",
                ),
                unsafe_allow_html=True,
            )
        else:
            heatmap_fig = plot_similarity_heatmap(
                active_sim_df,
                title="Document Semantic Similarity",
                threshold=threshold,
                theme_colors=get_colors(),
            )
            st.pyplot(heatmap_fig, use_container_width=True)

            buf = _io.BytesIO()
            heatmap_fig.savefig(
                buf,
                format="png",
                dpi=150,
                bbox_inches="tight",
            )
            buf.seek(0)

            st.download_button(
                "⬇️ Download Heatmap PNG",
                buf,
                "heatmap.png",
                "image/png",
            )

            st.divider()
            st.subheader("🕸️ Interactive Plagiarism Network")
            st.caption(
                "Documents are shown as nodes. Connections appear when "
                "their similarity is greater than or equal to the selected threshold."
            )

            network_fig = plot_similarity_network(
                similarity_df=active_sim_df,
                threshold=threshold,
                title="Interactive Document Plagiarism Network",
            )

            with st.expander(
                "🕸️ Interactive Plagiarism Network",
                expanded=False,
            ):
                st.caption(
                    "Documents are shown as nodes. Connections appear when "
                    "their similarity is greater than or equal to the "
                    "selected threshold."
                )
                load_network = st.toggle(
                    "Load network graph",
                    key="load_plagiarism_network",
                    help=(
                        "Generate the interactive network only when needed."
                    ),
                )

                max_degree = max(0, len(active_sim_df) - 1)
                min_degree = st.slider(
                    "Minimum Connected Documents",
                    min_value=0,
                    max_value=max_degree,
                    value=0,
                    key="min_connected_docs_slider",
                )

                network_fig = build_visualization_lazily(
                    load_network,
                    lambda: plot_similarity_network(
                        similarity_df=active_sim_df,
                        threshold=threshold,
                        min_degree=min_degree,
                        title=(
                            "Interactive Document Plagiarism Network"
                        ),
                        selected_node=st.session_state.get(
                            "selected_document_id"
                        ),
                    ),
                )

                if selected_points:
                    clicked_point = selected_points[0]

                    point_index = clicked_point.get("pointIndex")

                    if point_index is not None and 0 <= point_index < len(doc_names):
                        clicked_document_id = doc_names[point_index]

                        st.session_state.selected_document_id = clicked_document_id
            else:
                st.plotly_chart(network_fig, use_container_width=True)

            selected_document_id = st.session_state.get("selected_document_id")

            if selected_document_id:
                filtered_flags = [
                    flag
                    for flag in flags
                    if (
                        flag["doc_a"] == selected_document_id
                        or flag["doc_b"] == selected_document_id
                    )
                ]
            else:
                filtered_flags = flags

    # ── Summary Metrics ───────────────────────────────────────────────────────────

    if len(file_bytes_dict) < 2:
        st.markdown(
            empty_state_html(
                "Waiting for Files",
                "Please upload at least 2 PDF, DOCX, or TXT assignments to begin analysis.",
                "📂",
            ),
            unsafe_allow_html=True,
        )
        st.stop()

    if "sent_alerts" not in st.session_state:
        st.session_state.sent_alerts = set()

    for flag in filtered_flags:
        alert_key = (flag["doc_a"], flag["doc_b"])
        if alert_key not in st.session_state.sent_alerts:
            try:
                send_plagiarism_alert(
                    doc_a=flag["doc_a"],
                    doc_b=flag["doc_b"],
                    similarity=float(flag["similarity"]),
                )
                st.session_state.sent_alerts.add(alert_key)
            except Exception as e:
                logger.error(f"Failed to send webhook alert: {e}")

    # ══ TAB 5: PAIR DRILL-DOWN ════════════════════════════════════════════════

    with tab_drill:
        st.markdown("🏠 Home > Dashboard > **Pair Drill-Down**")
        st.subheader("🔬 Pair Drill-Down")
        st.caption("Inspect chunk-level similarity between any two documents.")

        if "expand_all_drill" not in st.session_state:
            st.session_state.expand_all_drill = False
        expand_all_drill = st.toggle(
            "Expand All",
            value=st.session_state.expand_all_drill,
            key="toggle_expand_all_drill",
        )
        st.session_state.expand_all_drill = expand_all_drill

        if not has_enough_files or active_sim_df is None:
            st.markdown(
                empty_state_html(
                    "Waiting for Files",
                    "Please upload at least 2 PDF, DOCX, or TXT assignments to begin analysis.",
                    "📂",
                ),
                unsafe_allow_html=True,
            )
        elif len(active_sim_df) < 2:
            from src.errors import UI_NEED_MIN_DOCUMENTS

            st.warning(UI_NEED_MIN_DOCUMENTS)
        else:
           query_doc_a = st.query_params.get("doc_a")
    query_doc_b = st.query_params.get("doc_b")

    default_a_index = (
        doc_names.index(query_doc_a)
        if query_doc_a in doc_names
        else 0
    )

    c1, c2 = st.columns(2)

    with c1:
        doc_a = st.selectbox(
            "Document A",
            doc_names,
            index=default_a_index,
            key="da",
        )

    available_doc_b = [d for d in doc_names if d != doc_a]

    default_b_index = (
        available_doc_b.index(query_doc_b)
        if query_doc_b in available_doc_b
        else 0
    )

    with c2:
        doc_b = st.selectbox(
            "Document B",
            available_doc_b,
            index=default_b_index,
            key="db",
        )

    if st.button("🔗 Share This Pair", key="share_pair"):
        st.query_params["doc_a"] = doc_a
        st.query_params["doc_b"] = doc_b
        st.success("✅ Shareable link created! Copy the URL from your browser.")

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
                    chunks_a,
                    chunks_b,
                    embeddings[doc_a],
                    embeddings[doc_b],
                    top_k=5,
                    threshold=threshold,
                )
                for rank, (ca, cb, sim) in enumerate(top_pairs, 1):
                    is_exact = "".join(ca.split()) == "".join(cb.split())
                    badge = " :green[[Exact Match]]" if is_exact else ""
                    with st.expander(
                        f"#{rank} — {doc_a} ↔ {doc_b} — {sim:.1%}{badge}",
                        expanded=st.session_state.expand_all_drill or (rank == 1),
                    ):
                        highlighted_ca, highlighted_cb = highlight_overlap(ca, cb)
                        st.markdown(
                            f"**{doc_a}:** {highlighted_ca}", unsafe_allow_html=True
                        )
                        st.markdown(
                            f"**{doc_b}:** {highlighted_cb}", unsafe_allow_html=True
                        )

    with drill_tab_viewer:
                selected_view_doc = st.radio(
                    "Select Document to Preview:",
                    options=[doc_a, doc_b],
                    horizontal=True,
                    key="doc_viewer_select",
                )
                doc_source = file_bytes_dict.get(selected_view_doc)
                matching_chunks_to_highlight = (
                    chunks_a if selected_view_doc == doc_a else chunks_b
                )

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

    # ══ TAB 6: Analytics ═════════════════════════════════════════════════════════

    with tab_analytics:
        st.markdown("🏠 Home > Dashboard > **Analytics Dashboard**")
        st.subheader("📊 Plagiarism Analytics Dashboard")
        if not has_enough_files:
            st.markdown(
                empty_state_html(
                    "Waiting for Files",
                    "Please upload at least 2 PDF, DOCX, or TXT assignments to begin analysis.",
                    "📂",
                ),
                unsafe_allow_html=True,
            )
        else:
            if flags:
                sync_flagged_incidents(flags)

            st.subheader("📈 High Severity Plagiarism Trends (Last 30 Days)")
            trend_data = get_high_severity_trends(days=30)
            doc_data = get_most_plagiarized_documents(limit=10)

            with st.expander(
                "📈 High Severity Plagiarism Trends (Last 30 Days)",
                expanded=False,
            ):
                load_trends = st.toggle(
                    "Load trend chart",
                    key="load_high_severity_trends",
                )
                trend_fig = build_visualization_lazily(
                    load_trends,
                    lambda: plot_high_severity_trends(trend_data),
                )

    assert mock_pb.progress.call_count == 4
    mock_pb.progress.assert_any_call(
        1.0,
        text="ZIP archive ready!",
    )
    with st.expander(
                "🔝 Most Frequently Plagiarized Documents",
                expanded=False,
            ):
                load_documents_chart = st.toggle(
                    "Load document chart",
                    key="load_most_plagiarized_documents",
                )
                doc_fig = build_visualization_lazily(
                    load_documents_chart,
                    lambda: plot_most_plagiarized_documents(doc_data),
                )

                if doc_fig is None:
                    st.info(
                        "Enable “Load document chart” to generate this "
                if trend_fig is None:
                    st.info(
                        "Enable “Load trend chart” to generate this "
                        "visualization."
                    )
                else:
                    st.plotly_chart(
                        doc_fig,
                        use_container_width=True,
                    )

    with st.expander(
                "📊 Similarity Score Distribution",
                expanded=False,
            ):
                analysis_results = st.session_state.get(
                    "analysis_results"
                )

                if analysis_results is None:
                    st.info(
                        "Run a plagiarism analysis to see the "
                        "similarity score distribution."
                    )
                else:
                    load_distribution = st.toggle(
                        "Load distribution chart",
                        key="load_similarity_distribution",
                    )
                    sim_matrix = (
                        analysis_results[4]
                        if use_chunk_matrix
                        else analysis_results[3]
                    )
                    dist_fig = build_visualization_lazily(
                        load_distribution,
                        lambda: plot_similarity_distribution(
                            sim_matrix
                        ),
                    )

                    if dist_fig is None:
                        st.info(
                            "Enable “Load distribution chart” to "
                            "generate this visualization."
                        )
                    else:
                        st.plotly_chart(
                            dist_fig,
                            use_container_width=True,
                        )

    st.divider()

    # Summary statistics remain lightweight and always visible.
    st.subheader("📋 Analytics Summary")
    if trend_data:
        total_high_severity = sum(
            item["count"] for item in trend_data
        )
        st.metric(
            "Total High Severity Incidents (30 days)",
            total_high_severity,
        )
    else:
        st.info(
            "No high severity incidents recorded in the last "
            "30 days."
        )

    if doc_data:
        most_plagiarized = doc_data[0]
        st.metric(
            "Most Plagiarized Document",
            (
                f"{most_plagiarized['document_name']} "
                f"({most_plagiarized['incident_count']} incidents)"
            ),
        )
    else:
        st.info("No plagiarism incidents recorded.")
            st.subheader("📊 Similarity Score Distribution")
            analysis_results = st.session_state.get("analysis_results")
            if analysis_results is not None:
                sim_matrix = (
                    analysis_results[4] if use_chunk_matrix else analysis_results[3]
                        trend_fig,
                        use_container_width=True,
                    )
            with st.expander(
                "🔝 Most Frequently Plagiarized Documents",
                expanded=False,
            ):
                load_documents_chart = st.toggle(
                    "Load document chart",
                    key="load_most_plagiarized_documents",
                )
                dist_fig = plot_similarity_distribution(sim_matrix)
                st.plotly_chart(dist_fig, use_container_width=True)
            else:
                st.info(
                    "Run a plagiarism analysis to see the similarity score distribution."
                )

            st.divider()

            # Summary statistics
            st.subheader("📋 Analytics Summary")
            if trend_data:
                total_high_severity = sum(item["count"] for item in trend_data)
                st.metric(
                    "Total High Severity Incidents (30 days)", total_high_severity
                )
            else:
                st.info("No high severity incidents recorded in the last 30 days.")

            if doc_data:
                st.metric(
                    "Most Plagiarized Document",
                    f"{doc_data[0]['document_name']} ({doc_data[0]['incident_count']} incidents)",
                )
            else:
                st.info("No plagiarism incidents recorded.")

    # ══ TAB 7: User Management ═══════════════════════════════════════════════════
    with tab_users:
        st.markdown("🏠 Home > Dashboard > **User Management**")
        st.subheader("👥 User Management")
        if user_role == "admin":
            users = get_all_users()
            if users:
                # Table Header
                col_h1, col_h2, col_h3, col_h4 = st.columns([2, 1, 1, 1])
                with col_h1:
                    st.markdown("**Username**")
                with col_h2:
                    st.markdown("**Role**")
                with col_h3:
                    st.markdown("**Status**")
                with col_h4:
                    st.markdown("**Actions**")
                st.write("---")

                # Table Rows
                for u in users:
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    with c1:
                        st.write(u["username"])
                    with c2:
                        st.write(u["role"].capitalize())
                    with c3:
                        is_active = u.get("is_active", True)
                        if is_active:
                            st.markdown(
                                "<span style='color: #28a745; font-weight: bold;'>🟢 Active</span>",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                "<span style='color: #dc3545; font-weight: bold;'>🔴 Suspended</span>",
                                unsafe_allow_html=True,
                            )
                    with c4:
                        if u["username"] == "admin" or u[
                            "username"
                        ] == st.session_state.get("username"):
                            st.button(
                                "Suspend",
                                key=f"suspend_btn_{u['username']}",
                                disabled=True,
                                use_container_width=True,
                            )
                        else:
                            is_active = u.get("is_active", True)
                            btn_label = "Suspend" if is_active else "Activate"
                            if st.button(
                                btn_label,
                                key=f"suspend_btn_{u['username']}",
                                use_container_width=True,
                            ):
                                set_user_active_status(u["username"], not is_active)
                                st.success(
                                    f"User '{u['username']}' updated successfully!"
                                )
                                st.rerun()
        else:
            st.warning(
                "⚠️ Access Denied: User Management is restricted to administrators."
            )

        st.write("---")
        st.subheader("🔐 Two-Factor Authentication (2FA)")

        current_user = st.session_state.get("username", "admin")
        enabled, otp_secret = get_2fa_status(current_user)

        if enabled:
            st.success(
                "✔️ Two-Factor Authentication is currently **enabled** for your account."
            )
            with st.expander("Deactivate Two-Factor Authentication", expanded=False):
                with st.form("disable_2fa_form"):
                    disable_code = st.text_input(
                        "Verification Code", max_chars=6, key="disable_2fa_code"
                    )
                    submit_disable = st.form_submit_button(
                        "Disable 2FA", use_container_width=True
                    )
                    if submit_disable:
                        import pyotp

                        totp = pyotp.TOTP(otp_secret)
                        if totp.verify(disable_code.strip()):
                            disable_2fa(current_user)
                            st.success(
                                "✅ Two-factor authentication has been disabled."
                            )
                            st.rerun()
                        else:
                            st.error(
                                "🚨 Invalid verification code. 2FA remains enabled."
                            )
        else:
            st.info(
                "🔒 Two-Factor Authentication (2FA) is currently **disabled** for your account. We highly recommend enabling it."
            )
            if not st.session_state.get("show_2fa_setup", False):
                if st.button("Setup 2FA", use_container_width=True):
                    st.session_state.show_2fa_setup = True
                    import pyotp

                    st.session_state.temp_2fa_secret = pyotp.random_base32()
                    st.rerun()
            else:
                temp_secret = st.session_state.get("temp_2fa_secret")
                if temp_secret:
                    import pyotp

                    totp = pyotp.TOTP(temp_secret)
                    provisioning_uri = totp.provisioning_uri(
                        name=current_user, issuer_name="PlagiarismDetector"
                    )

                    st.markdown("### ⚙️ Step 1: Scan this QR Code")
                    from io import BytesIO

                    import qrcode

                    qr = qrcode.QRCode(version=1, box_size=5, border=3)
                    qr.add_data(provisioning_uri)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    qr_bytes = buf.getvalue()

                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.image(qr_bytes, width=250)
                    with col2:
                        st.code(f"Account: {current_user}\nSecret Key: {temp_secret}")

                    st.markdown("### ⚙️ Step 2: Verify and Enable 2FA")
                    with st.form("verify_2fa_setup_form"):
                        setup_code = st.text_input(
                            "6-digit Code", max_chars=6, key="setup_2fa_code"
                        )
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            submit_setup = st.form_submit_button(
                                "Verify and Enable", use_container_width=True
                            )
                        with col_btn2:
                            cancel_setup = st.form_submit_button(
                                "Cancel Setup", use_container_width=True
                            )

                        if submit_setup:
                            if totp.verify(setup_code.strip()):
                                enable_2fa(current_user, temp_secret)
                                st.session_state.show_2fa_setup = False
                                if "temp_2fa_secret" in st.session_state:
                                    del st.session_state.temp_2fa_secret
                                st.success(
                                    "🎉 Two-Factor Authentication has been successfully enabled!"
                                )
                                st.rerun()
                            else:
                                st.error("🚨 Invalid verification code.")
                        if cancel_setup:
                            st.session_state.show_2fa_setup = False
                            if "temp_2fa_secret" in st.session_state:
                                del st.session_state.temp_2fa_secret
                            st.rerun()

    # ══ TAB 8: Settings ══════════════════════════════════════════════════════════
    with tab_settings:
        st.markdown("🏠 Home > Dashboard > **Settings**")
        st.subheader(get_text("settings", lang=lang_code))

        selected_lang_name = st.selectbox(
            "🌐 Language / Idioma",
            options=list(_SUPPORTED_LANGUAGES.values()),
            index=0,
            key="lang_selector",
        )
        lang_code = "es" if selected_lang_name == "Español" else "en"

        selected_theme = st.radio(
            get_text("theme", lang=lang_code),
            options=["Light", "Dark"],
            index=0 if current_theme == "Light" else 1,
            horizontal=True,
            key="theme_selector",
            on_change=save_preferences_callback,
        )
        if selected_theme != current_theme:
            set_theme(selected_theme)
            st.rerun()

        st.markdown("---")
        st.markdown("### 🔔 Notification Preferences")
        st.caption(
            "Choose how plagiarism alerts should be delivered to your "
            "account. These choices are saved to your profile."
        )

        notification_username = st.session_state.get("username")
        notification_state_key = (
            f"notification_preferences_loaded:{notification_username}"
        )

        if (
            notification_username
            and not st.session_state.get(notification_state_key)
        ):
            persisted_notifications = get_notification_preferences(
                notification_username
            )
            st.session_state["email_notifications_toggle"] = (
                persisted_notifications["email_notifications"]
            )
            st.session_state["webhook_notifications_toggle"] = (
                persisted_notifications["webhook_notifications"]
            )
            st.session_state[notification_state_key] = True

        email_notifications_enabled = st.checkbox(
            "📧 Email notifications",
            value=st.session_state.get(
                "email_notifications_toggle",
                True,
            ),
            key="email_notifications_toggle",
            help=(
                "Receive plagiarism alert notifications by email when "
                "email delivery is configured."
            ),
        )
        webhook_notifications_enabled = st.checkbox(
            "🔗 Webhook notifications",
            value=st.session_state.get(
                "webhook_notifications_toggle",
                True,
            ),
            key="webhook_notifications_toggle",
            help=(
                "Send plagiarism alerts to the configured webhook "
                "endpoint."
            ),
        )

        if st.button(
            "💾 Save Notification Preferences",
            key="save_notification_preferences",
            use_container_width=True,
        ):
            if not notification_username:
                st.error(
                    "Your user session is unavailable. Please sign in again."
                )
            else:
                try:
                    saved_notifications = (
                        update_notification_preferences(
                            notification_username,
                            email_notifications=(
                                email_notifications_enabled
                            ),
                            webhook_notifications=(
                                webhook_notifications_enabled
                            ),
                        )
                    )
                except (TypeError, ValueError, sqlite3.Error) as exc:
                    st.error(
                        "Unable to save notification preferences: "
                        f"{exc}"
                    )
                else:
                    st.session_state[
                        "notification_preferences"
                    ] = saved_notifications
                    st.success(
                        "✅ Notification preferences saved."
                    )

        if user_role == "admin":
            st.markdown("---")
            st.markdown("### ⚙️ Advanced Configuration")

            threshold = st.slider(
                get_text("threshold", lang=lang_code),
                min_value=0.0,
                max_value=1.0,
                value=DEFAULT_THRESHOLDS.plagiarism,
                step=0.01,
                help=(
                    "Controls which pairs are flagged. Severity remains Medium "
                    f"at {DEFAULT_THRESHOLDS.medium:.0%} and High "
                    f"at {DEFAULT_THRESHOLDS.high:.0%}."
                ),
                key="threshold_slider",
                on_change=save_preferences_callback,
            )
            st.query_params["threshold"] = f"{threshold:.2f}"
            st.session_state.last_seen_threshold_query = f"{threshold:.2f}"

            selected_class = st.selectbox(
                "Filter by Class Section",
                options=unique_classes,
                key="class_filter_selectbox",
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

            with st.expander("✂️ Ignore Phrases", expanded=False):
                st.caption(
                    "Enter common template text or standard assignment questions to ignore during analysis. "
                    "These phrases will be removed from documents before chunking and embedding."
                )
                ignore_phrases = st.text_area(
                    "Ignore Phrases (one per line)",
                    placeholder="Q1: Explain the theory of relativity\nQ2: Describe the process of photosynthesis",
                    help="Each line represents a phrase to ignore.",
                    key="ignore_phrases_textarea",
                )

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
                st.caption(
                    "Used only for scanned or image-only PDF pages. Text-based PDFs continue to use native extraction."
                )
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

            st.markdown("")
            if st.button(
                "🔄 Reset to Factory Defaults",
                key="reset_defaults_button",
                use_container_width=True,
            ):
                keys_to_reset = [
                    "theme_selector",
                    "threshold_slider",
                    "class_filter_selectbox",
                    "chunk_matrix_checkbox",
                    "faiss_top_k_slider",
                    "ignore_phrases_textarea",
                    "chunk_size_slider",
                    "chunk_overlap_slider",
                    "ocr_language_selector",
                    "ocr_dpi_slider",
                ]
                for key in keys_to_reset:
                    if key in st.session_state:
                        del st.session_state[key]
                if "threshold" in st.query_params:
                    del st.query_params["threshold"]
                set_theme("Light")
                st.success("✅ Settings reset to defaults!")
                st.rerun()

            st.markdown("")
            if st.button(
                "🔍 Ping Redis", key="ping_redis_button", use_container_width=True
            ):
                from src.utils.redis_cache import get_cache

                connected, latency = get_cache().ping()
                if connected:
                    st.success(f"✅ Connected ({latency} ms ping)")
                else:
                    st.error("🚨 Disconnected")
                st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()

st.caption("🎓 Semantic Plagiarism Detection System · Streamlit")

# ── Version / Update indicator ────────────────────────────────────────────────
# Import here (deferred) to avoid slowing down the initial module load for
# users who never reach the footer.
from src.utils.version_check import APP_VERSION, check_for_update_sync  # noqa: E402

# Cache the result for the lifetime of the Streamlit session so we don't
# hammer the GitHub API on every rerun (e.g. widget interaction).
if "_update_check_tag" not in st.session_state:
    st.session_state["_update_check_tag"] = check_for_update_sync(APP_VERSION)

_latest_tag: str | None = st.session_state["_update_check_tag"]

_footer_col1, _footer_col2 = st.columns([3, 1])
with _footer_col1:
    st.caption(
        f"🎓 Semantic Plagiarism Detection System · v{APP_VERSION} · Streamlit · [🐛 Report Bug / Feedback](https://github.com/Ganesh-403/semantic-plagiarism-detector/issues)"
    )
with _footer_col2:
    if _latest_tag:
        st.markdown(
            version_check_widget_html(
                local_version=APP_VERSION,
                latest_tag=_latest_tag,
            ),
            unsafe_allow_html=True,
        )
    else:
        st.caption("✅ Up to date")
