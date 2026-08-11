"""
Semantic Plagiarism Detector - Main Streamlit Application Entry Point.

Lightweight coordinator responsible for page setup, routing, state management initialization,
and delegating view rendering to modular components.
"""

import asyncio
import hashlib
import io as _io
import logging
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import psutil
import streamlit as st

# 1. Fix Streamlit import paths FIRST so 'app' can be found
FILE_PATH = Path(__file__).resolve()
ROOT_DIR = FILE_PATH.parent.parent  # Points to semantic-plagiarism-detector/
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Silence harmless Windows asyncio Proactor connection lost bugs
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from dotenv import load_dotenv
load_dotenv()

from src.core.logging_config import setup_logging
setup_logging()
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
        "Missing environment variables: %s. Some features may not work correctly. "
        "Please configure them in your .env file.",
        ", ".join(missing_env_vars),
    )

# Import DB and Core initializations
from src.db.corpus_db import get_all_documents, get_total_document_count, init_corpus_db
from src.db.auth import get_all_users, get_upload_count, init_db
from src.db.incidents import get_all_incidents, get_total_incidents_count, init_incident_db, sync_flagged_incidents
from src.utils.temp_manager import purge_expired_temp_files

init_corpus_db()
init_db()
purge_expired_temp_files()

# Centralized imports & backward compatibility re-exports
from app.session_keys import SessionKeys
from app.state_manager import (
    TIMEOUT_LIMIT,
    check_session_timeout,
    get_active_sessions_count,
    init_session_state,
    save_preferences_callback,
    ui_exception_handler,
    update_global_activity,
)
from app.theme import (
    back_to_top_html,
    get_chart_colors,
    get_theme_name,
    inject_css,
    render_session_status_banner,
    set_theme,
)

from src.core.config import DEFAULT_THRESHOLDS, PLAGIARISM_THRESHOLD, get_branding_config
from src.core.app_config import FAISS_INDEX_PATH
from src.core.faiss_index import (
    build_index,
    build_index_from_matrix,
    load_index,
    load_or_rebuild_index,
    save_index,
    search_similar_chunks,
)
from src.core.pipeline import ChunkRecord, run_extraction_pipeline, run_pipeline
from src.core.similarity import cosine_similarity, document_similarity_matrix, flag_plagiarism
from src.db import clear_all_data, delete_document, get_all_embeddings, get_chunk_registry
from src.i18n.translator import _SUPPORTED_LANGUAGES, get_text
from src.utils.processing_time import estimate_processing_seconds, format_processing_duration
from src.utils.redis_cache import get_analysis_results, get_faiss_index

# Views imports
from app.views.audit_view import render_audit_view
from app.views.auth_view import handle_oauth_callbacks, render_login_view
from app.views.analytics_view import render_analytics_view
from app.views.corpus_view import (
    clear_all_dialog,
    logout_dialog,
    render_corpus_header,
    render_document_management_sidebar,
    render_onboarding_tour,
    render_sidebar,
)
from app.views.drilldown_view import render_cosine_vs_lexical_comparison_table, render_drilldown_view
from app.views.faiss_view import render_faiss_view
from app.views.heatmap_view import render_heatmap_view
from app.views.history_view import render_history_view
from app.views.matrix_view import render_matrix_view
from app.views.settings_view import render_settings_view
from app.views.upload_view import render_upload_section
from app.views.warnings_view import get_date_range_preset, render_warnings_view

_INDEX_PATH = str(FAISS_INDEX_PATH)
branding_config = get_branding_config()


def configure_page_meta(title: str, icon: str) -> None:
    """Configure Streamlit page metadata including title, favicon, and layout."""
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Page title must be a non-empty string.")
    if not isinstance(icon, str) or not icon.strip():
        raise ValueError("Page icon must be a non-empty string.")

    st.set_page_config(
        page_title=title.strip(),
        page_icon=icon.strip(),
        layout="wide",
        initial_sidebar_state="auto",
    )


def update_page_title(tab_name: str):
    """Update browser title based on active tab."""
    st.markdown(
        f"""
        <script>
            window.parent.document.title = '{tab_name} | Semantic Plagiarism Detector';
        </script>
        """,
        unsafe_allow_html=True,
    )


# Configure Page Setup
configure_page_meta(title="Semantic Plagiarism Detector - Dashboard", icon="🔍")
SESSION_ID = init_session_state()

st.markdown(back_to_top_html(), unsafe_allow_html=True)
inject_css()

# Session Timeout Check & Authentication Flow
last_interaction = check_session_timeout(SESSION_ID)
handle_oauth_callbacks(SESSION_ID)

if not st.session_state.get(SessionKeys.AUTHENTICATED, False):
    render_login_view(SESSION_ID)

user_role = st.session_state.get(SessionKeys.ROLE, "user")

# Top-right Theme Toggle
current_theme = get_theme_name()
_, theme_col = st.columns([0.94, 0.06])
with theme_col:
    theme_icon = "☀️" if current_theme == "Dark" else "🌙"
    if st.button(theme_icon, key="theme_toggle"):
        new_theme = "Light" if current_theme == "Dark" else "Dark"
        set_theme(new_theme)
        st.rerun()

# Corpus Overview Header & Quick Actions
render_corpus_header(_INDEX_PATH)

# Sidebar Rendering
faiss_index = (
    load_index(_INDEX_PATH) if os.path.exists(_INDEX_PATH) else None
)
lang_code = render_sidebar(user_role, str(ROOT_DIR), faiss_index)

# Main UI Header
st.title("🔍 Semantic Plagiarism Detection System")

# Live Scan Statistics Metrics Header (#1508)
try:
    total_scans = get_upload_count()
    corpus_size = get_total_document_count()
    flagged_incidents = get_total_incidents_count()

    _incidents = get_all_incidents(limit=10000)
    if _incidents:
        avg_sim = sum(inc.get("similarity_score", 0.0) for inc in _incidents) / len(_incidents)
    else:
        avg_sim = 0.0
except Exception as e:
    logger.error(f"Failed to load dashboard metrics: {e}")
    total_scans = 0
    corpus_size = 0
    flagged_incidents = 0
    avg_sim = 0.0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Scans", f"{total_scans:,}")
with col2:
    st.metric("Avg Similarity %", f"{avg_sim * 100:.1f}%")
with col3:
    st.metric("Flagged Incidents", f"{flagged_incidents:,}")
with col4:
    st.metric("Corpus Size", f"{corpus_size:,}")

st.markdown("---")

with st.expander("ℹ️ How Semantic Plagiarism Detection Works"):
    st.markdown("""
        - **1. Upload files** — Upload the documents you want to compare.
        - **2. AI vector embeddings generated** — The documents are converted into vector embeddings for semantic comparison.
        - **3. View similarity heatmap & incident logs** — Review detected similarities through the heatmap and incident logs.
        """)

# Render Upload & Student Portal Section
file_bytes_dict = render_upload_section(user_role, lang_code, _INDEX_PATH)

# Threshold & Chunking Parameters from Session State
threshold = st.session_state.get(SessionKeys.THRESHOLD_SLIDER, PLAGIARISM_THRESHOLD)
use_chunk_matrix = st.session_state.get(SessionKeys.CHUNK_MATRIX_CHECKBOX, False)
faiss_top_k = st.session_state.get(SessionKeys.FAISS_TOP_K_SLIDER, 5)
chunk_size = st.session_state.get(SessionKeys.CHUNK_SIZE_SLIDER, 500)
chunk_overlap = st.session_state.get(SessionKeys.CHUNK_OVERLAP_SLIDER, 50)
ocr_language = st.session_state.get(SessionKeys.OCR_LANGUAGE_SELECTOR, "eng")
ocr_dpi = st.session_state.get(SessionKeys.OCR_DPI_SLIDER, 250)

has_enough_files = len(file_bytes_dict) >= 2

if has_enough_files:
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

    init_incident_db()
    incidents = sync_flagged_incidents(flags)
else:
    flags = []
    active_sim_df = None
    raw_texts = {}
    ai_probabilities = {}
    registry = get_chunk_registry()
    faiss_index = load_index(_INDEX_PATH) if os.path.exists(_INDEX_PATH) else None

st.subheader(get_text("analysis_summary", lang=lang_code))
doc_names = list(raw_texts.keys())
n_docs = len(doc_names)
total_pairs = n_docs * (n_docs - 1) // 2 if n_docs > 1 else 0
n_flagged = len(flags)
total_doc_count = max(n_docs, get_total_document_count())

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Documents", total_doc_count)
col2.metric("Pairs Evaluated", total_pairs)
col3.metric("Flagged Pairs", n_flagged)
col4.metric("FAISS Vectors", faiss_index.ntotal if faiss_index is not None else 0)
col5.metric("🎯 Threshold", f"{threshold:.0%}")
st.divider()

# Main Application Tabs
(
    tab_warnings,
    tab_faiss,
    tab_matrix,
    tab_heatmap,
    tab_drill,
    tab_compare,
    tab_analytics,
    tab_users,
    tab_settings,
    tab_history,
    tab_audit,
) = st.tabs(
    [
        get_text("tab_warnings", lang=lang_code),
        get_text("tab_faiss", lang=lang_code),
        get_text("tab_matrix", lang=lang_code),
        get_text("tab_heatmap", lang=lang_code),
        get_text("tab_drill", lang=lang_code),
        "🔬 Comparison",
        get_text("tab_analytics", lang=lang_code),
        get_text("tab_users", lang=lang_code),
        get_text("tab_settings", lang=lang_code),
        "📊 History",
        get_text("tab_audit_logs", lang=lang_code),
    ],
    key="main_tabs",
)

# Record scan summary for historical tracking
if flags and len(file_bytes_dict) >= 2:
    from src.db.corpus_db import record_scan_summary

    all_sims = [f["similarity"] for f in flags]
    avg_sim = sum(all_sims) / len(all_sims) if all_sims else 0.0
    max_sim = max(all_sims) if all_sims else 0.0

    record_scan_summary(
        document_count=len(file_bytes_dict),
        avg_similarity=avg_sim,
        max_similarity=max_sim,
        flagged_count=len(flags),
        threshold_used=threshold,
    )

# Render View Components into Tabs
with tab_warnings:
    update_page_title("Warnings")
    render_warnings_view(flags, threshold, ai_probabilities, lang_code)

with tab_faiss:
    update_page_title("FAISS")
    render_faiss_view(faiss_index, registry, faiss_top_k, threshold, file_bytes_dict)

with tab_matrix:
    update_page_title("Matrix")
    render_matrix_view(active_sim_df)

with tab_heatmap:
    update_page_title("Heatmap")
    render_heatmap_view(active_sim_df, threshold, doc_names)

with tab_drill:
    update_page_title("Drill Down")
    render_drilldown_view(active_sim_df, raw_texts, flags, doc_names)

with tab_compare:
    update_page_title("Comparison")
    from app.components.document_comparison import render_document_comparison
    render_document_comparison()

with tab_analytics:
    update_page_title("Analytics")
    render_analytics_view()

with tab_users:
    update_page_title("Users")
    render_users_view()

with tab_settings:
    update_page_title("Settings")
    render_settings_view(user_role, lang_code, str(ROOT_DIR))

with tab_history:
    update_page_title("History")
    render_history_view()

with tab_audit:
    update_page_title("Security Audit Logs")
    render_audit_view(user_role, lang_code)

# Sidebar document management details
render_document_management_sidebar(user_role, _INDEX_PATH, SESSION_ID, last_interaction)

# Footer & Tour
st.divider()
from src.utils.version_check import APP_VERSION, check_for_update_sync

if "_update_check_tag" not in st.session_state:
    st.session_state["_update_check_tag"] = check_for_update_sync(APP_VERSION)

_latest_tag: str | None = st.session_state["_update_check_tag"]

_footer_col1, _footer_col2 = st.columns([3, 1])
with _footer_col1:
    st.caption(
        f"🎓 Semantic Plagiarism Detection System · v{APP_VERSION} · Streamlit · "
        "🐛 Report Bug / Feedback"
    )
    render_session_status_banner()

render_onboarding_tour(user_role)