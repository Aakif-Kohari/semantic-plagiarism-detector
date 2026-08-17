import base64
from unittest.mock import patch, MagicMock, call

import pytest

from src.utils.warning_list import (
    build_key_extractor,
    filter_warnings,
    paginate_warnings,
    prepare_warning_page,
    render_copy_button,
    render_warning_controls,
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
    import streamlit as st
    from collections import namedtuple
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


def test_render_copy_button_html():
    """Verify the HTML structure and base64 encoding logic of the copy button for issue #2470."""
    test_payload = "ECSoC26_test_string"
    
    # Generate the expected base64 string
    expected_b64 = base64.b64encode(test_payload.encode('utf-8')).decode('utf-8')
    
    with patch("streamlit.components.v1.html") as mock_html:
        render_copy_button(test_payload)
        
        # Ensure the HTML generation was called
        assert mock_html.called, "streamlit.components.v1.html was not called"
        html_output = mock_html.call_args[0][0]
        
        # Acceptance Criteria 1: Assert the result contains a <button> tag
        assert "<button" in html_output.lower(), "The HTML output is missing a <button> tag."
        
        # Acceptance Criteria 2: Assert the payload string is correctly base64 encoded
        assert expected_b64 in html_output, f"The base64 encoded payload '{expected_b64}' was not found in the HTML/JS output."


def test_filter_warnings_early_exit_and_process_extract():
    """Verify exact substring matches early exit without calling fuzzy process.extract."""
    warnings = [
        {"doc_a": "report_100.pdf", "doc_b": "essay_200.pdf", "similarity": 0.9, "severity": "High"},
        {"doc_a": "thesis.pdf", "doc_b": "assignment.pdf", "similarity": 0.8, "severity": "Medium"},
    ]

    with patch("src.utils.warning_list._extract_matching_indices") as mock_extract:
        mock_extract.return_value = set()
        
        # Search for exact substring "report"
        results = filter_warnings(warnings, "report")
        assert len(results) == 1
        assert results[0]["doc_a"] == "report_100.pdf"
        
        # Verify fuzzy extract was only run for non-exact remaining items (thesis.pdf / assignment.pdf)
        # and NOT for report_100.pdf (early exit)
        if mock_extract.called:
            for call in mock_extract.call_args_list:
                choices = call[0][1]
                assert 0 not in choices  # Index 0 (exact match) early exited and was skipped


def test_normalise_warning_logs_invalid_similarity(caplog):
    """Verify that invalid similarity scores log a warning."""
    import logging
    from src.utils.warning_list import _normalise_warning

    invalid_item = {"doc_a": "a.pdf", "doc_b": "b.pdf", "similarity": "N/A"}
    with caplog.at_level(logging.WARNING):
        result = _normalise_warning(invalid_item)

    assert result["similarity"] == 0.0
    assert "Invalid similarity score found in incident data: N/A" in caplog.text


class TestRenderWarningControls:
    """Test suite for render_warning_controls() function."""

    @patch("src.utils.warning_list.st")
    def test_empty_flags_shows_info_message(self, mock_st):
        """Verify empty flags list displays an info message."""
        render_warning_controls([])
        
        mock_st.info.assert_called_once_with("No plagiarism warnings to display.")
        mock_st.expander.assert_not_called()

    @patch("src.utils.warning_list.st")
    def test_single_flag_renders_expander(self, mock_st):
        """Verify single flag creates one expander with correct header."""
        flags = [
            {"doc_a": "essay1.pdf", "doc_b": "essay2.pdf", "similarity": 0.85}
        ]
        
        render_warning_controls(flags, threshold=0.59)
        
        # Verify header was created
        mock_st.markdown.assert_any_call("### 🚨 1 Plagiarism Warning Detected")
        
        # Verify expander was created
        mock_st.expander.assert_called_once()
        call_args = mock_st.expander.call_args
        assert "essay1.pdf" in call_args[0][0]
        assert "essay2.pdf" in call_args[0][0]
        assert "High" in call_args[0][0]  # 0.85 >= 0.80

    @patch("src.utils.warning_list.st")
    def test_multiple_flags_render_multiple_expanders(self, mock_st):
        """Verify multiple flags create multiple expanders."""
        flags = [
            {"doc_a": "a.pdf", "doc_b": "b.pdf", "similarity": 0.85},
            {"doc_a": "c.pdf", "doc_b": "d.pdf", "similarity": 0.65},
            {"doc_a": "e.pdf", "doc_b": "f.pdf", "similarity": 0.45},
        ]
        
        render_warning_controls(flags)
        
        # Verify plural header
        mock_st.markdown.assert_any_call("### 🚨 3 Plagiarism Warnings Detected")
        
        # Verify 3 expanders were created
        assert mock_st.expander.call_count == 3

    @patch("src.utils.warning_list.st")
    def test_severity_classification_high(self, mock_st):
        """Verify similarity >= 0.80 is classified as High severity."""
        flags = [{"doc_a": "a.pdf", "doc_b": "b.pdf", "similarity": 0.85}]
        
        render_warning_controls(flags)
        
        expander_call = mock_st.expander.call_args
        header = expander_call[0][0]
        assert "High" in header
        assert "#ef4444" in header  # Red color

    @patch("src.utils.warning_list.st")
    def test_severity_classification_medium(self, mock_st):
        """Verify 0.50 <= similarity < 0.80 is classified as Medium severity."""
        flags = [{"doc_a": "a.pdf", "doc_b": "b.pdf", "similarity": 0.65}]
        
        render_warning_controls(flags)
        
        expander_call = mock_st.expander.call_args
        header = expander_call[0][0]
        assert "Medium" in header
        assert "#f59e0b" in header  # Orange color

    @patch("src.utils.warning_list.st")
    def test_severity_classification_low(self, mock_st):
        """Verify similarity < 0.50 is classified as Low severity."""
        flags = [{"doc_a": "a.pdf", "doc_b": "b.pdf", "similarity": 0.45}]
        
        render_warning_controls(flags)
        
        expander_call = mock_st.expander.call_args
        header = expander_call[0][0]
        assert "Low" in header
        assert "#10b981" in header  # Green color

    @patch("src.utils.warning_list.st")
    def test_ai_probabilities_displayed_when_provided(self, mock_st):
        """Verify AI probabilities are displayed when ai_probabilities dict is provided."""
        flags = [{"doc_a": "a.pdf", "doc_b": "b.pdf", "similarity": 0.75}]
        ai_probs = {"a.pdf": 0.90, "b.pdf": 0.85}
        
        render_warning_controls(flags, ai_probabilities=ai_probs)
        
        # Verify AI probability markdown was called
        markdown_calls = [call[0][0] for call in mock_st.markdown.call_args_list]
        assert any("a.pdf AI Probability" in text for text in markdown_calls)
        assert any("b.pdf AI Probability" in text for text in markdown_calls)

    @patch("src.utils.warning_list.st")
    def test_matched_chunks_displayed_when_available(self, mock_st):
        """Verify matched chunks are displayed when available in flag data."""
        flags = [{
            "doc_a": "a.pdf",
            "doc_b": "b.pdf",
            "similarity": 0.75,
            "matched_chunks": [
                {"text": "This is a matching chunk."}
            ]
        }]
        
        render_warning_controls(flags)
        
        # Verify st.code was called for the chunk
        mock_st.code.assert_called()

    @patch("src.utils.warning_list.st")
    def test_expanded_parameter_controls_default_state(self, mock_st):
        """Verify expanded parameter controls expander default state."""
        flags = [{"doc_a": "a.pdf", "doc_b": "b.pdf", "similarity": 0.75}]
        
        render_warning_controls(flags, expanded=True)
        
        expander_call = mock_st.expander.call_args
        assert expander_call[1]["expanded"] is True

    @patch("src.utils.warning_list.st")
    def test_threshold_displayed_in_expander(self, mock_st):
        """Verify threshold value is displayed inside the expander."""
        flags = [{"doc_a": "a.pdf", "doc_b": "b.pdf", "similarity": 0.75}]
        
        render_warning_controls(flags, threshold=0.59)
        
        markdown_calls = [call[0][0] for call in mock_st.markdown.call_args_list]
        assert any("Threshold: 59.0%" in text for text in markdown_calls)


class TestRenderCopyButton:
    """Test suite for render_copy_button() function."""

    @patch("src.utils.warning_list.st")
    def test_renders_code_block_with_text(self, mock_st):
        """Verify st.code is called with the provided text."""
        text = "Suspicious text snippet"
        
        render_copy_button(text)
        
        mock_st.code.assert_called_once_with(text, language=None)

    @patch("src.utils.warning_list.st")
    def test_empty_text_returns_early(self, mock_st):
        """Verify empty text does not render any components."""
        render_copy_button("")
        
        mock_st.code.assert_not_called()

    @patch("src.utils.warning_list.st")
    def test_none_text_returns_early(self, mock_st):
        """Verify None text does not render any components."""
        render_copy_button(None)
        
        mock_st.code.assert_not_called()


# ── Exact Substring Filtering Tests ───────────────────────────────────────────


class TestFilterWarningsExact:
    """Test suite for exact substring filtering."""

    def test_filter_empty_query_returns_all(self):
        """Verify empty query returns all warnings."""
        warnings = [{"doc_a": "a.pdf", "doc_b": "b.pdf"}]
        assert filter_warnings(warnings, "") == warnings
        assert filter_warnings(warnings, None) == warnings
        assert filter_warnings(warnings, "   ") == warnings

    def test_filter_exact_match_doc_a(self):
        """Verify exact substring match in doc_a includes the warning."""
        warnings = [
            {"doc_a": "alice_essay.pdf", "doc_b": "bob_essay.pdf"},
            {"doc_a": "charlie.pdf", "doc_b": "dave.pdf"}
        ]
        
        result = filter_warnings(warnings, "alice", use_fuzzy=False)
        assert len(result) == 1
        assert result[0]["doc_a"] == "alice_essay.pdf"

    def test_filter_exact_match_doc_b(self):
        """Verify exact substring match in doc_b includes the warning."""
        warnings = [
            {"doc_a": "alice.pdf", "doc_b": "bob_essay.pdf"}
        ]
        
        result = filter_warnings(warnings, "bob", use_fuzzy=False)
        assert len(result) == 1

    def test_filter_case_insensitive(self):
        """Verify filtering is case-insensitive."""
        warnings = [{"doc_a": "Alice_Essay.PDF", "doc_b": "bob.pdf"}]
        
        result = filter_warnings(warnings, "alice", use_fuzzy=False)
        assert len(result) == 1
        
        result_upper = filter_warnings(warnings, "ALICE", use_fuzzy=False)
        assert len(result_upper) == 1

    def test_filter_no_match_returns_empty(self):
        """Verify no match returns an empty list."""
        warnings = [{"doc_a": "alice.pdf", "doc_b": "bob.pdf"}]
        
        result = filter_warnings(warnings, "charlie", use_fuzzy=False)
        assert len(result) == 0

    def test_filter_multiple_matches(self):
        """Verify multiple warnings can match the same query."""
        warnings = [
            {"doc_a": "essay_1.pdf", "doc_b": "source.pdf"},
            {"doc_a": "essay_2.pdf", "doc_b": "essay_1.pdf"},
            {"doc_a": "random.pdf", "doc_b": "other.pdf"}
        ]
        
        result = filter_warnings(warnings, "essay", use_fuzzy=False)
        assert len(result) == 2

    def test_filter_handles_missing_keys(self):
        """Verify filtering handles warnings with missing doc_a/doc_b keys."""
        warnings = [
            {"doc_a": "alice.pdf"},  # Missing doc_b
            {"doc_b": "bob.pdf"},   # Missing doc_a
            {}                      # Missing both
        ]
        
        result = filter_warnings(warnings, "alice", use_fuzzy=False)
        assert len(result) == 1

def test_paginate_warnings_negative_page_clamps_to_first_page():
    """Negative page numbers must resolve to page 1."""
    page = paginate_warnings(WARNINGS, page=-1, page_size=2)

    assert page.page == 1
    assert page.items == [dict(WARNINGS[0]), dict(WARNINGS[1])]


def test_paginate_warnings_zero_page_clamps_to_first_page():
    """Page zero must resolve to page 1."""
    page = paginate_warnings(WARNINGS, page=0, page_size=2)

    assert page.page == 1
    assert page.items == [dict(WARNINGS[0]), dict(WARNINGS[1])]

