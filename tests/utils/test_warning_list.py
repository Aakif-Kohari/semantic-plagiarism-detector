from unittest.mock import patch

from src.utils.warning_list import (
    build_key_extractor,
    filter_warnings,
    paginate_warnings,
    prepare_warning_page,
    render_copy_button,
    reset_warning_page,
    sort_warnings,
)

WARNINGS = [
    {"doc_a": "Zeta.pdf", "doc_b": "Alpha.pdf", "similarity": 0.91, "severity": "High"},
    {
        "doc_a": "Beta.pdf",
        "doc_b": "Gamma.pdf",
        "similarity": 0.78,
        "severity": "Medium",
    },
    {
        "doc_a": "Alpha.pdf",
        "doc_b": "Delta.pdf",
        "similarity": 0.91,
        "severity": "High",
    },
    {
        "doc_a": "Notes.pdf",
        "doc_b": "Essay.pdf",
        "similarity": 0.81,
        "severity": "Medium",
    },
]


def test_build_key_extractor():
    extractor_doc_a = build_key_extractor("doc_a")
    extractor_sim = build_key_extractor("similarity")

    assert extractor_doc_a(WARNINGS[0]) == "zeta.pdf"
    assert extractor_sim(WARNINGS[0]) == 0.91


def test_search_matches_either_document_case_insensitively():
    results = filter_warnings(WARNINGS, "ALPHA")
    assert len(results) == 2


def test_empty_search_returns_everything():
    assert len(filter_warnings(WARNINGS, " ")) == 4
    assert len(filter_warnings(WARNINGS, "")) == 4
    assert len(filter_warnings(WARNINGS, None)) == 4


def test_search_query_is_truncated_to_max_length():
    long_query = "a" * 201
    results = filter_warnings(WARNINGS, long_query)
    assert len(results) == 4

    truncated = filter_warnings(WARNINGS, "a" * 201)
    assert truncated == filter_warnings(WARNINGS, "a" * 200)


def test_fuzzy_search_handles_minor_typos():
    # "Alpaha" is a typo for "Alpha"
    results = filter_warnings(WARNINGS, "Alpaha")
    assert len(results) == 2

    # "Ztaa" is a typo for "Zeta"
    results_zeta = filter_warnings(WARNINGS, "Ztaa")
    assert len(results_zeta) == 1
    assert results_zeta[0]["doc_a"] == "Zeta.pdf"


def test_multi_column_sorting():
    results = sort_warnings(
        WARNINGS,
        primary_field="similarity",
        primary_descending=True,
        secondary_field="doc_a",
        secondary_descending=False,
    )
    assert [item["similarity"] for item in results] == [0.91, 0.91, 0.81, 0.78]
    assert results[0]["doc_a"] == "Alpha.pdf"
    assert results[1]["doc_a"] == "Zeta.pdf"


def test_filename_sorting():
    results = sort_warnings(
        WARNINGS,
        primary_field="doc_a",
        primary_descending=False,
    )
    assert [item["doc_a"] for item in results] == [
        "Alpha.pdf",
        "Beta.pdf",
        "Notes.pdf",
        "Zeta.pdf",
    ]


def test_pagination_and_page_clamping():
    warnings = [
        {
            "doc_a": f"A-{i}.pdf",
            "doc_b": f"B-{i}.pdf",
            "similarity": 0.8,
            "severity": "Medium",
        }
        for i in range(23)
    ]
    page_two = paginate_warnings(warnings, page=2, page_size=10)
    final_page = paginate_warnings(warnings, page=99, page_size=10)

    assert len(page_two.items) == 10
    assert page_two.start_index == 11
    assert page_two.end_index == 20
    assert final_page.page == 3
    assert len(final_page.items) == 3


def test_filtering_occurs_before_pagination():
    warnings = [
        {
            "doc_a": f"target-{i}.pdf" if i < 12 else f"other-{i}.pdf",
            "doc_b": "reference.pdf",
            "similarity": 0.7 + i / 100,
            "severity": "Medium",
        }
        for i in range(20)
    ]

    filtered, page = prepare_warning_page(
        warnings,
        search_query="target",
        page=2,
        page_size=10,
    )
    assert len(filtered) == 12
    assert len(page.items) == 2
    assert page.total_pages == 2


def test_reset_warning_page_returns_first_page():
    assert reset_warning_page() == 1


def test_filter_warnings_by_minimum_match_length():
    warnings = [
        {
            "doc_a": "doc1.pdf",
            "doc_b": "doc2.pdf",
            "similarity": 0.8,
            "severity": "Medium",
            "matched_length": 5,
        },
        {
            "doc_a": "doc1.pdf",
            "doc_b": "doc3.pdf",
            "similarity": 0.85,
            "severity": "High",
            "matched_length": 150,
        },
        {
            "doc_a": "doc2.pdf",
            "doc_b": "doc3.pdf",
            "similarity": 0.75,
            "severity": "Medium",
            "matched_length": 50,
        },
    ]

    # Filter with min_match_length = 50 -> should exclude the 5-word match
    filtered = filter_warnings(warnings, min_match_length=50)
    assert len(filtered) == 2
    assert all(item["matched_length"] >= 50 for item in filtered)

    # Filter with min_match_length = 200 -> should exclude all matches
    filtered_none = filter_warnings(warnings, min_match_length=200)
    assert len(filtered_none) == 0

    # Filter routing in prepare_warning_page
    sorted_items, page = prepare_warning_page(warnings, min_match_length=50)
    assert len(sorted_items) == 2
    assert page.total_items == 2


def test_page_size_clamping_to_max_100():
    """Verify that a page_size parameter larger than 100 is clamped to 100."""
    warnings = [
        {
            "doc_a": f"A-{i}.pdf",
            "doc_b": f"B-{i}.pdf",
            "similarity": 0.8,
            "severity": "Medium",
        }
        for i in range(150)
    ]
    # Request a page size of 200
    page = paginate_warnings(warnings, page=1, page_size=200)
    # The safe_page_size must be clamped to 100
    assert page.page_size == 100
    assert len(page.items) == 100
    assert page.total_pages == 2


def test_has_exact_match_no_results():
    """Verify that _has_exact_match returns False if analysis_results is missing from session state."""
    import streamlit as st

    from src.utils.warning_list import _has_exact_match

    # Ensure analysis_results is not in session state
    if "analysis_results" in st.session_state:
        del st.session_state["analysis_results"]

    assert _has_exact_match("doc_a.pdf", "doc_b.pdf") is False


def test_has_exact_match_with_matching_tuple_results():
    """Verify that _has_exact_match works with legacy tuple format where index 1 is chunked_docs."""
    import streamlit as st

    from src.utils.warning_list import _has_exact_match

    chunked_docs = {
        "doc_a.pdf": ["hello world", "some other chunk"],
        "doc_b.pdf": ["hello world", "different chunk"]
    }
    legacy_results = (None, chunked_docs, None, None, None, None, None, None, None)
    st.session_state.analysis_results = legacy_results

    assert _has_exact_match("doc_a.pdf", "doc_b.pdf") is True


def test_has_exact_match_with_non_matching_tuple_results():
    """Verify that _has_exact_match returns False when no chunks match."""
    import streamlit as st

    from src.utils.warning_list import _has_exact_match

    chunked_docs = {
        "doc_a.pdf": ["hello world"],
        "doc_b.pdf": ["different chunk"]
    }
    legacy_results = (None, chunked_docs, None, None, None, None, None, None, None)
    st.session_state.analysis_results = legacy_results

    assert _has_exact_match("doc_a.pdf", "doc_b.pdf") is False


def test_has_exact_match_with_named_tuple_results():
    """Verify that _has_exact_match works with NamedTuple format, accessing chunked_docs attribute."""
    from collections import namedtuple

    import streamlit as st

    from src.utils.warning_list import _has_exact_match

    MockPipelineResult = namedtuple("MockPipelineResult", ["raw_texts", "chunked_docs"])
    chunked_docs = {
        "doc_a.pdf": ["exact match chunk"],
        "doc_b.pdf": ["exact match chunk"]
    }
    named_results = MockPipelineResult(raw_texts={}, chunked_docs=chunked_docs)
    st.session_state.analysis_results = named_results

    assert _has_exact_match("doc_a.pdf", "doc_b.pdf") is True


def test_has_exact_match_with_pure_attribute():
    """Verify that _has_exact_match works with an object that only has chunked_docs attribute."""
    import streamlit as st

    from src.utils.warning_list import _has_exact_match

    class MockNamedTuple:
        def __init__(self, chunked_docs):
            self.chunked_docs = chunked_docs

    chunked_docs = {
        "doc_a.pdf": ["exact match"],
        "doc_b.pdf": ["exact match"]
    }
    st.session_state.analysis_results = MockNamedTuple(chunked_docs)

    assert _has_exact_match("doc_a.pdf", "doc_b.pdf") is True


def test_render_copy_button_xss_sanitization():
    """Verify that button_id is properly sanitized to prevent XSS."""
    malicious_id = '"><script>alert(1)</script><div id="'

    with patch("streamlit.components.v1.html") as mock_html:
        render_copy_button("Sample text", button_id=malicious_id)

        # Verify Streamlit HTML component was called
        assert mock_html.called
        rendered_html = mock_html.call_args[0][0]

        # Assert no unescaped/raw <script> tag from button_id appears
        assert 'id=""><script>alert(1)</script>' not in rendered_html
        assert '&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;' in rendered_html

def test_filter_warnings_missing_matched_length():
    """Test that warning items lacking the 'matched_length' key default to 0 and are filtered out when a minimum length is required."""
    from src.utils.warning_list import filter_warnings
    
    # Warning dictionary completely lacking "matched_length"
    warnings = [
        {
            "doc_a": "doc1.txt",
            "doc_b": "doc2.txt",
            "similarity": 0.85,
            "severity": "High"
            # "matched_length" is intentionally omitted here
        }
    ]
    
    # Filtering with min_match_length = 50 should exclude items with default matched_length (0)
    filtered = filter_warnings(warnings, min_match_length=50)
    
    assert len(filtered) == 0
