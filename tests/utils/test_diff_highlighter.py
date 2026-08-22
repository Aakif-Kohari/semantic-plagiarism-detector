"""Regression tests for diff highlighter overlap edge cases."""

import html
import random
import time

from src.utils.diff_highlighter import MARK_OPEN_TAG, _sanitize_color, highlight_overlap

SAFE_FALLBACK = "rgba(250, 204, 21, 0.3)"


def test_sanitize_color_accepts_valid_hex_and_rgba():
    assert _sanitize_color("#fef08a") == "#fef08a"
    assert _sanitize_color("#abc") == "#abc"
    assert _sanitize_color("rgba(250, 204, 21, 0.3)") == "rgba(250, 204, 21, 0.3)"
    assert _sanitize_color("rgb(255, 0, 0)") == "rgb(255, 0, 0)"


def test_sanitize_color_rejects_injection_vectors():
    assert _sanitize_color("red; background: url(evil.com)") == SAFE_FALLBACK
    assert _sanitize_color("rgba(0,0,0,0);</style><script>") == SAFE_FALLBACK


def test_no_overlap():
    """Completely different texts should not produce highlight tags."""
    result_a, result_b = highlight_overlap(
        "alpha beta gamma delta",
        "one two three four",
    )

    assert "<mark" not in result_a
    assert "</mark>" not in result_a
    assert "<mark" not in result_b
    assert "</mark>" not in result_b


def test_full_overlap():
    """Identical text should be fully wrapped in a highlight tag."""
    text = "alpha beta gamma delta"
    result_a, result_b = highlight_overlap(text, text)

    assert "<mark" in result_a
    assert "</mark>" in result_a
    assert "<mark" in result_b
    assert "</mark>" in result_b
    assert text in result_a
    assert text in result_b


def test_one_empty_input():
    """An empty input should return escaped text without highlight tags."""
    text = "<script>alert('x')</script>"
    result_a, result_b = highlight_overlap(text, "")

    assert result_a == html.escape(text)
    assert result_b == ""
    assert "<mark" not in result_a
    assert "<mark" not in result_b


def test_short_overlap_below_threshold_is_not_highlighted():
    """Two shared words fall short of the four-word default."""
    result_a, result_b = highlight_overlap(
        "the quick brown fox",
        "a quick brown dog",
    )

    assert "<mark" not in result_a
    assert "<mark" not in result_b


def test_overlap_at_exactly_the_threshold_is_highlighted():
    """A run of exactly min_match_length words counts as a match."""
    result_a, result_b = highlight_overlap(
        "opening words alpha beta gamma delta closing words",
        "different start alpha beta gamma delta different end",
    )

    assert "<mark" in result_a
    assert "<mark" in result_b
    assert "alpha beta gamma delta" in result_a
    assert "alpha beta gamma delta" in result_b


def test_run_one_word_short_of_the_threshold_is_not_highlighted():
    """The boundary is inclusive on one side only."""
    result_a, result_b = highlight_overlap(
        "opening alpha beta gamma closing",
        "different alpha beta gamma other",
    )

    assert "<mark" not in result_a
    assert "<mark" not in result_b


def test_custom_min_match_length_is_honoured():
    """Lowering the threshold picks up a shorter shared run."""
    result_a, result_b = highlight_overlap(
        "the quick brown fox",
        "a quick brown dog",
        min_match_length=2,
    )

    assert "quick brown" in result_a
    assert "quick brown" in result_b
    assert "<mark" in result_a


def test_min_match_length_below_one_is_clamped():
    """A zero or negative window must not produce empty or nested marks."""
    for window in (0, -3):
        result_a, result_b = highlight_overlap("alpha beta", "beta gamma", window)

        assert result_a.count("<mark") == result_a.count("</mark>")
        assert result_b.count("<mark") == result_b.count("</mark>")


def test_marks_never_nest():
    """Adjacent and overlapping runs merge into a single mark."""
    text = "alpha beta gamma delta epsilon zeta eta theta"
    result_a, result_b = highlight_overlap(text, text)

    for result in (result_a, result_b):
        assert result.count("<mark") == 1
        assert result.count("</mark>") == 1


def test_output_stays_escaped_around_a_match():
    """Markup in the source text must not survive next to a highlight.

    A ``<mark>`` boundary can land between the ``&lt;`` and the tag name,
    because ``<b>`` tokenizes to the word ``b``. The angle brackets are still
    escaped either way, which is the property that matters.
    """
    payload = "<b>alpha beta gamma delta</b> <script>alert(1)</script>"
    result_a, result_b = highlight_overlap(payload, payload)

    for result in (result_a, result_b):
        assert "<script>" not in result
        assert "<b>" not in result
        assert "</b>" not in result
        # Every angle bracket from the payload is escaped; the only raw tags
        # left are the <mark> wrappers this function adds itself.
        stripped = result.replace(MARK_OPEN_TAG, "").replace("</mark>", "")
        assert "<" not in stripped
        assert ">" not in stripped
        assert "&lt;" in stripped


def test_both_inputs_empty():
    """Two empty inputs return two empty strings, not a crash."""
    assert highlight_overlap("", "") == ("", "")


def test_punctuation_only_input_has_no_word_tokens():
    """Text with no word characters cannot match anything."""
    result_a, result_b = highlight_overlap("!!! ??? ...", "alpha beta gamma delta")

    assert "<mark" not in result_a
    assert "<mark" not in result_b


def test_document_shorter_than_the_window():
    """A document with fewer words than min_match_length cannot match."""
    result_a, result_b = highlight_overlap("alpha beta", "alpha beta gamma delta")

    assert "<mark" not in result_a
    assert "<mark" not in result_b


def test_matching_is_case_insensitive_but_output_preserves_case():
    """Tokens are lowercased for comparison only."""
    result_a, result_b = highlight_overlap(
        "ALPHA Beta GAMMA delta",
        "alpha BETA gamma DELTA",
    )

    assert "<mark" in result_a
    assert "ALPHA Beta GAMMA delta" in result_a
    assert "alpha BETA gamma DELTA" in result_b


def test_two_separate_runs_produce_two_marks():
    """Non-adjacent matches must not be merged into one span."""
    shared_one = "alpha beta gamma delta"
    shared_two = "kappa lambda mu nu"
    text_a = f"{shared_one} unrelated filler words here {shared_two}"
    text_b = f"{shared_one} entirely different bridging text {shared_two}"

    result_a, _ = highlight_overlap(text_a, text_b)

    assert result_a.count("<mark") == 2
    assert result_a.count("</mark>") == 2


def _reference_highlight_overlap(text_a, text_b, min_match_length=4):
    """The original nested-scan implementation, kept as a test oracle.

    This is the pre-#3047 body verbatim. It is correct but cubic, so it is
    only ever run here on inputs of a few dozen words.
    """
    import re as _re

    if not text_a or not text_b:
        return html.escape(text_a or ""), html.escape(text_b or "")

    safe_a = html.escape(text_a)
    safe_b = html.escape(text_b)
    words_a = _re.findall(r"\b\w+\b", text_a.lower())
    words_b = _re.findall(r"\b\w+\b", text_b.lower())
    if not words_a or not words_b:
        return safe_a, safe_b

    matches = []
    for i in range(len(words_a)):
        for j in range(len(words_b)):
            k = 0
            while (
                i + k < len(words_a)
                and j + k < len(words_b)
                and words_a[i + k] == words_b[j + k]
            ):
                k += 1
            if k >= min_match_length:
                matches.append((i, i + k, j, j + k))

    if not matches:
        return safe_a, safe_b

    def highlight_text(text, word_matches):
        if not word_matches:
            return html.escape(text)
        word_positions = [(m.start(), m.end()) for m in _re.finditer(r"\b\w+\b", text)]
        result = []
        last_end = 0
        for start_word, end_word in sorted(word_matches):
            if start_word >= len(word_positions):
                continue
            char_start = word_positions[start_word][0]
            char_end = word_positions[min(end_word - 1, len(word_positions) - 1)][1]
            result.append(html.escape(text[last_end:char_start]))
            result.append(
                '<mark style="background-color: #fef08a; '
                'padding: 2px 4px; border-radius: 3px;">'
            )
            result.append(html.escape(text[char_start:char_end]))
            result.append("</mark>")
            last_end = char_end
        result.append(html.escape(text[last_end:]))
        return "".join(result)

    def merge_ranges(ranges):
        if not ranges:
            return []
        merged = [ranges[0]]
        for start, end in ranges[1:]:
            if start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return merged

    ranges_a = merge_ranges(sorted({(m[0], m[1]) for m in matches}))
    ranges_b = merge_ranges(sorted({(m[2], m[3]) for m in matches}))
    return highlight_text(text_a, ranges_a), highlight_text(text_b, ranges_b)


def test_output_matches_the_original_implementation():
    """Differential test against the pre-#3047 nested scan.

    The rewrite is meant to be a pure speed-up, so every generated pair must
    produce byte-identical HTML from both implementations.
    """
    vocabulary = "alpha beta gamma delta epsilon zeta eta theta the of and a to".split()
    rng = random.Random(20260820)

    for _ in range(400):
        length_a = rng.randint(0, 25)
        length_b = rng.randint(0, 25)
        text_a = " ".join(rng.choice(vocabulary) for _ in range(length_a))
        text_b = " ".join(rng.choice(vocabulary) for _ in range(length_b))

        # Splice a run of A into B often enough to exercise real overlaps.
        if length_a > 5 and rng.random() < 0.5:
            cut = rng.randint(0, length_a - 5)
            segment = " ".join(text_a.split()[cut : cut + rng.randint(2, 8)])
            text_b = f"{text_b} {segment} {text_b}".strip()

        for window in (1, 2, 3, 4, 6):
            assert highlight_overlap(text_a, text_b, window) == (
                _reference_highlight_overlap(text_a, text_b, window)
            ), f"diverged for window={window}, a={text_a!r}, b={text_b!r}"


def test_large_identical_documents_complete_quickly():
    """Guard against the cubic scan coming back.

    On the old implementation this input took roughly 24 seconds. The bound
    is deliberately loose — two orders of magnitude of headroom — so it fails
    on an algorithmic regression rather than on a slow CI runner.
    """
    document = " ".join(f"word{index % 37}" for index in range(3000))

    started = time.perf_counter()
    result_a, result_b = highlight_overlap(document, document)
    elapsed = time.perf_counter() - started

    assert "<mark" in result_a
    assert "<mark" in result_b
    assert elapsed < 2.0, f"highlight_overlap took {elapsed:.2f}s for 3000 words"
