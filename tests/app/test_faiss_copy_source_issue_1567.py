from pathlib import Path


SOURCE = Path("app/components/faiss_results.py")
TESTS = Path(
    "tests/app/test_faiss_copy_button_issue_1567.py"
)


def test_matched_text_uses_streamlit_code_block():
    source = SOURCE.read_text(encoding="utf-8")

    assert 'st.caption("📋 Matched Text")' in source
    assert 'st.code(chunk_text, language="text")' in source


def test_old_truncated_caption_is_removed():
    source = SOURCE.read_text(encoding="utf-8")

    assert (
        'st.caption(chunk_text[:300]'
        not in source
    )


def test_copy_regression_covers_full_long_chunk():
    source = TESTS.read_text(encoding="utf-8")

    assert (
        "test_matched_chunk_copy_block_keeps_full_untruncated_text"
        in source
    )
    assert (
        "mock_st.code.assert_any_call("
        in source
    )
