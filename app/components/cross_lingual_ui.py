"""
Cross-lingual UI Components for Plagiarism Detection.

Provides UI elements for displaying language badges, translation metadata,
and cross-lingual match indicators in the Streamlit dashboard.
"""

import streamlit as st
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from src.core.cross_lingual import get_language_name, SUPPORTED_LANGUAGES


# ============================================================================
# LANGUAGE BADGE RENDERERS
# ============================================================================

def render_language_badge(lang_code: str, show_name: bool = True) -> str:
    """
    Generate HTML badge for language display.
    
    Args:
        lang_code: Language code (e.g., 'en', 'es', 'fr')
        show_name: Whether to show the full language name
        
    Returns:
        HTML string for the badge
    """
    lang_name = get_language_name(lang_code)
    
    colors = {
        "en": "#3B82F6",
        "es": "#F59E0B",
        "fr": "#10B981",
        "de": "#EF4444",
        "it": "#8B5CF6",
        "pt": "#EC4899",
        "nl": "#06B6D4",
        "ru": "#6B7280",
        "zh-cn": "#EF4444",
        "zh-tw": "#DC2626",
        "ja": "#F472B6",
        "ko": "#8B5CF6",
        "ar": "#059669",
        "hi": "#F97316",
        "ur": "#FCD34D",
        "bn": "#F59E0B",
        "te": "#10B981",
        "ta": "#EC4899",
        "mr": "#8B5CF6",
        "gu": "#F472B6",
        "kn": "#06B6D4",
        "ml": "#3B82F6",
        "or": "#F59E0B",
        "pa": "#FCD34D",
        "ne": "#10B981",
        "si": "#EC4899",
        "th": "#EF4444",
        "vi": "#F59E0B",
        "id": "#8B5CF6",
        "ms": "#06B6D4",
        "fil": "#3B82F6",
        "pl": "#F472B6",
        "cs": "#10B981",
        "sk": "#EC4899",
        "hu": "#F59E0B",
        "ro": "#EF4444",
        "bg": "#8B5CF6",
        "el": "#06B6D4",
        "tr": "#3B82F6",
        "he": "#FCD34D",
        "fa": "#F97316",
        "sw": "#10B981",
    }
    
    color = colors.get(lang_code, "#6B7280")
    
    if show_name:
        return f'<span style="background:{color};color:white;padding:2px 10px;border-radius:12px;font-size:0.75rem;font-weight:500;">🌐 {lang_name}</span>'
    else:
        return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:12px;font-size:0.7rem;font-weight:500;">{lang_code.upper()}</span>'


def render_translation_indicator(is_translated: bool, lang_code: str = None) -> str:
    """
    Generate HTML indicator for translated content.
    
    Args:
        is_translated: Whether the content was translated
        lang_code: Original language code
        
    Returns:
        HTML string for the indicator
    """
    if not is_translated:
        return ""
    
    lang_name = get_language_name(lang_code) if lang_code else "Unknown"
    
    return f'''
    <span style="background:#3B82F6;color:white;padding:2px 10px;border-radius:12px;font-size:0.7rem;font-weight:500;margin-left:8px;">
        🔄 Translated from {lang_name}
    </span>
    '''


# ============================================================================
# CROSS-LINGUAL METADATA DISPLAY
# ============================================================================

def render_document_language_metadata(
    metadata: Dict[str, List[Dict[str, Any]]],
    doc_name: str
) -> None:
    """
    Render language metadata for a document.
    
    Args:
        metadata: Translation metadata dict
        doc_name: Document name to display metadata for
    """
    if not metadata or doc_name not in metadata:
        return
    
    doc_metadata = metadata[doc_name]
    if not doc_metadata:
        return
    
    # Count languages in document
    lang_counts = {}
    total_chunks = 0
    translated_count = 0
    
    for chunk_meta in doc_metadata:
        lang = chunk_meta.get("detected_language", "unknown")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
        total_chunks += 1
        if chunk_meta.get("translated", False):
            translated_count += 1
    
    # Display summary
    with st.expander(f"🌐 Language Info - {doc_name}", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Chunks", total_chunks)
        with col2:
            st.metric("Translated Chunks", translated_count)
        with col3:
            main_lang = max(lang_counts, key=lang_counts.get) if lang_counts else "unknown"
            lang_name = get_language_name(main_lang)
            st.metric("Main Language", lang_name)
        
        st.divider()
        
        # Language breakdown
        if lang_counts:
            df = pd.DataFrame([
                {"Language": get_language_name(lang), "Chunks": count}
                for lang, count in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)


def render_chunk_language_metadata(
    chunk_text: str,
    metadata: List[Dict[str, Any]],
    chunk_index: int
) -> None:
    """
    Render language metadata for a specific chunk.
    
    Args:
        chunk_text: The chunk text
        metadata: List of chunk metadata
        chunk_index: Index of the chunk in the document
    """
    if not metadata or chunk_index >= len(metadata):
        return
    
    chunk_meta = metadata[chunk_index]
    lang = chunk_meta.get("detected_language", "en")
    is_translated = chunk_meta.get("translated", False)
    translation_failed = chunk_meta.get("translation_failed", False)
    
    # Display language badge
    st.markdown(render_language_badge(lang), unsafe_allow_html=True)
    
    if is_translated:
        st.caption(f"🔄 Translated from {get_language_name(lang)} to English")
    
    if translation_failed:
        st.warning("⚠️ Translation failed - showing original text")


# ============================================================================
# CROSS-LINGUAL MATCH DISPLAY
# ============================================================================

def render_cross_lingual_match(
    match: Tuple[str, str, float, str],
    rank: int,
    expanded: bool = False
) -> None:
    """
    Render a single cross-lingual match in the UI.
    
    Args:
        match: Tuple of (chunk_a, chunk_b, score, match_type)
        rank: Rank of the match
        expanded: Whether to expand by default
    """
    chunk_a, chunk_b, score, match_type = match
    
    # Determine color based on score
    if score >= 0.90:
        color = "#ff4b4b"
    elif score >= 0.75:
        color = "#ffa500"
    else:
        color = "#ffd700"
    
    with st.expander(
        f"#{rank} 🌐 Cross-Lingual Match — {score:.1%}",
        expanded=expanded
    ):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📄 Document A**")
            st.info(chunk_a[:300] + "..." if len(chunk_a) > 300 else chunk_a)
        
        with col2:
            st.markdown("**📄 Document B**")
            st.info(chunk_b[:300] + "..." if len(chunk_b) > 300 else chunk_b)
        
        st.markdown(f"**Match Type:** {match_type}")
        st.markdown(
            f'<div style="background:{color};color:white;padding:8px;border-radius:4px;text-align:center;font-weight:bold;">'
            f'Similarity: {score * 100:.1f}%</div>',
            unsafe_allow_html=True
        )


def render_cross_lingual_analysis(
    matches: List[Tuple[str, str, float, str]],
    analysis: Dict[str, Any]
) -> None:
    """
    Render full cross-lingual analysis dashboard.
    
    Args:
        matches: List of matches
        analysis: Analysis dictionary from analyze_cross_lingual_similarity
    """
    if not matches:
        st.info("No cross-lingual matches found above threshold.")
        return
    
    st.subheader("🌐 Cross-Lingual Analysis")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Matches", analysis["total_matches"])
    with col2:
        st.metric("Max Similarity", f"{analysis['max_score']:.1%}")
    with col3:
        st.metric("Avg Similarity", f"{analysis['avg_score']:.1%}")
    with col4:
        st.metric("Cross-Lingual", analysis["cross_lingual_count"])
    
    st.divider()
    
    # Match types breakdown
    if analysis["match_types"]:
        df = pd.DataFrame([
            {"Match Type": k, "Count": v}
            for k, v in analysis["match_types"].items()
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # Render each match
    for rank, match in enumerate(matches, 1):
        render_cross_lingual_match(match, rank, expanded=(rank == 1))


# ============================================================================
# CROSS-LINGUAL SETTINGS PANEL
# ============================================================================

def render_cross_lingual_settings() -> bool:
    """
    Render cross-lingual settings panel in sidebar.
    
    Returns:
        bool: Whether cross-lingual mode is enabled
    """
    with st.expander("🌐 Cross-Lingual Settings", expanded=False):
        st.markdown("""
        **Cross-lingual detection** enables plagiarism detection across different languages.
        
        When enabled:
        - Chunks are translated to English before embedding
        - Language badges are displayed
        - Translation matches are highlighted
        """)
        
        enabled = st.toggle(
            "🌐 Enable Cross-Lingual Detection",
            value=st.session_state.get("cross_lingual_mode_toggle", False),
            key="cross_lingual_mode_toggle",
            help=(
                "Enable back-translation to detect translated plagiarism. "
                "May increase processing time."
            )
        )
        
        if enabled:
            st.info("🔵 Cross-lingual detection is **enabled**. Documents in foreign languages will be translated.")
            
            # Show supported languages
            with st.expander("🌍 Supported Languages"):
                langs = sorted(SUPPORTED_LANGUAGES.items())
                cols = st.columns(3)
                for idx, (code, name) in enumerate(langs[:30]):
                    col_idx = idx % 3
                    with cols[col_idx]:
                        st.caption(f"• {name} ({code})")
                
                if len(langs) > 30:
                    st.caption(f"... and {len(langs) - 30} more languages")
        else:
            st.info("⚪ Cross-lingual detection is **disabled**.")
        
        return enabled


# ============================================================================
# CROSS-LINGUAL STATISTICS
# ============================================================================

def render_cross_lingual_stats(metadata: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    Render cross-lingual statistics from metadata.
    
    Args:
        metadata: Translation metadata dict
    """
    if not metadata:
        st.info("No cross-lingual data available. Enable cross-lingual detection and re-run analysis.")
        return
    
    total_chunks = 0
    translated_chunks = 0
    language_counts = {}
    
    for doc_metadata in metadata.values():
        for chunk_meta in doc_metadata:
            total_chunks += 1
            lang = chunk_meta.get("detected_language", "unknown")
            language_counts[lang] = language_counts.get(lang, 0) + 1
            if chunk_meta.get("translated", False):
                translated_chunks += 1
    
    if total_chunks == 0:
        st.info("No chunks processed.")
        return
    
    st.subheader("📊 Cross-Lingual Statistics")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Chunks Processed", total_chunks)
    with col2:
        st.metric("Translated Chunks", translated_chunks)
    with col3:
        translation_rate = (translated_chunks / total_chunks) * 100
        st.metric("Translation Rate", f"{translation_rate:.1f}%")
    
    st.divider()
    
    # Language distribution
    if language_counts:
        df = pd.DataFrame([
            {"Language": get_language_name(lang), "Chunks": count}
            for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True)
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Simple bar chart
        st.bar_chart(df.set_index("Language"))


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

def get_cross_lingual_metadata() -> Dict[str, List[Dict[str, Any]]]:
    """Get cross-lingual metadata from session state."""
    return st.session_state.get("translation_metadata", {})


def is_cross_lingual_enabled() -> bool:
    """Check if cross-lingual mode is enabled."""
    return st.session_state.get("cross_lingual_mode_toggle", False)


def render_cross_lingual_ui_in_drilldown(
    doc_name: str,
    chunk_index: int,
    metadata: Dict[str, List[Dict[str, Any]]]
) -> None:
    """
    Render cross-lingual UI in drill-down view.
    
    Args:
        doc_name: Document name
        chunk_index: Chunk index
        metadata: Translation metadata
    """
    if not is_cross_lingual_enabled() or not metadata:
        return
    
    if doc_name not in metadata:
        return
    
    doc_metadata = metadata[doc_name]
    if not doc_metadata or chunk_index >= len(doc_metadata):
        return
    
    chunk_meta = doc_metadata[chunk_index]
    lang = chunk_meta.get("detected_language", "en")
    is_translated = chunk_meta.get("translated", False)
    
    if lang != "en" or is_translated:
        st.markdown(render_language_badge(lang), unsafe_allow_html=True)
        if is_translated:
            st.caption(f"🔄 Translated from {get_language_name(lang)} to English")


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'render_language_badge',
    'render_translation_indicator',
    'render_document_language_metadata',
    'render_chunk_language_metadata',
    'render_cross_lingual_match',
    'render_cross_lingual_analysis',
    'render_cross_lingual_settings',
    'render_cross_lingual_stats',
    'get_cross_lingual_metadata',
    'is_cross_lingual_enabled',
    'render_cross_lingual_ui_in_drilldown',
]