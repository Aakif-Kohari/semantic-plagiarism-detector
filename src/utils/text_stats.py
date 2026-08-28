"""
text_stats.py
-------------
Text statistics and analysis utilities for document comparison.

Provides functions to compute various text metrics such as word count,
sentence count, and unique word ratio. These metrics are used in
plagiarism reports to provide additional context about compared documents.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List


def count_words(text: str) -> int:
    """
    Count the number of words in the given text.

    Words are defined as sequences of characters separated by whitespace.
    Punctuation is stripped before counting. For CJK scripts, individual
    characters are counted as individual word units.

    Args:
        text: The text to analyze

    Returns:
        Number of words in the text
    """
    if not text:
        return 0

    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    if cjk_chars:
        # Replace CJK characters with space to avoid merging adjacent English words
        non_cjk_text = re.sub(r"[\u4e00-\u9fff]", " ", text)
        words = re.findall(r"\b\w+\b", non_cjk_text.lower())
        return len(cjk_chars) + len(words)

    # Remove punctuation and split on whitespace
    words = re.findall(r"\b\w+\b", text.lower())
    return len(words)


# Common abbreviations whose trailing period does not end a sentence. Matched
# whole-word only — see ``_ABBREVIATION_RE`` for why that matters.
ABBREVIATIONS = (
    "mr",
    "mrs",
    "ms",
    "dr",
    "prof",
    "sr",
    "jr",
    "vs",
    "etc",
    "inc",
    "ltd",
    "corp",
    "co",
    "fig",
    "tbl",
    "art",
    "no",
    "pp",
    "vol",
    "jan",
    "feb",
    "mar",
    "apr",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
)

# An abbreviation only counts when the letters before the period form a whole
# word. Without the leading boundary, "co." matches inside "disco." and "no."
# inside "casino.", which swallows the real sentence break that follows.
_ABBREVIATION_RE = re.compile(
    r"\b(?:" + "|".join(ABBREVIATIONS) + r")\.",
    re.IGNORECASE,
)

# Spaced ellipsis such as ". . ." or ". . . ." — periods separated by whitespace
# that represent a pause or omitted text rather than multiple sentence breaks.
_SPACED_ELLIPSIS_RE = re.compile(r"(?:\.\s+)+\.")

# Dotted acronyms such as "U.S.", "e.u." or "N.A.V.O." — any run of two or more
# single letters each followed by a period. Written generically so the list
# above does not need an entry per acronym.
_DOTTED_ACRONYM_RE = re.compile(r"\b(?:[A-Za-z]\.){2,}")

# A period between two digits is a decimal point ("3.14", "v2.5"), never a
# sentence break.
_DECIMAL_POINT_RE = re.compile(r"(?<=\d)\.(?=\d)")

# Placeholder substituted for periods that must not be counted. A private-use
# code point is used so it cannot collide with anything in the document, and so
# masking never joins two words together the way deleting the period would.
_PROTECTED_PERIOD = "\ue000"

_SENTENCE_ENDING_RE = re.compile(r"[.!?]+")


def _mask_non_terminal_periods(text: str) -> str:
    """Replace periods that do not end a sentence with a placeholder.

    Covers abbreviations, dotted acronyms, decimal points, and spaced ellipses.
    The surrounding letters are preserved so that word boundaries elsewhere in
    the text are unaffected — only the period itself is swapped out.
    """
    masked = _SPACED_ELLIPSIS_RE.sub(_PROTECTED_PERIOD, text)
    masked = _DECIMAL_POINT_RE.sub(_PROTECTED_PERIOD, masked)
    masked = _DOTTED_ACRONYM_RE.sub(
        lambda match: match.group(0).replace(".", _PROTECTED_PERIOD),
        masked,
    )
    masked = _ABBREVIATION_RE.sub(
        lambda match: match.group(0).replace(".", _PROTECTED_PERIOD),
        masked,
    )
    return masked


def count_sentences(text: str) -> int:
    """
    Count the number of sentences in the given text.

    Sentences are identified by periods, exclamation marks, and question marks.
    Periods belonging to common abbreviations ("Dr."), dotted acronyms ("U.S."),
    decimal numbers ("3.14"), and spaced ellipses (". . .") are excluded so they
    do not inflate the count.

    Non-empty text always counts as at least one sentence, so a run of words
    with no terminal punctuation is reported as a single sentence rather than
    none.

    Args:
        text: The text to analyze

    Returns:
        Number of sentences in the text
    """
    if not text or not text.strip():
        return 0

    masked = _mask_non_terminal_periods(text)

    # Count sentence-ending punctuation. Consecutive marks ("?!", "...") are a
    # single break because the pattern matches them as one run.
    sentence_endings = _SENTENCE_ENDING_RE.findall(masked)
    return max(1, len(sentence_endings))


# Alias get_sentence_count to count_sentences for backward compatibility
get_sentence_count = count_sentences


def count_unique_words(text: str) -> int:
    """
    Count the number of unique words in the given text.

    Word comparison is case-insensitive. Populates the set directly using
    re.finditer to avoid intermediate list allocation for large texts (Issue #3706).

    Args:
        text: The text to analyze

    Returns:
        Number of unique words in the text
    """
    if not text:
        return 0

    cjk_chars = set(re.findall(r"[\u4e00-\u9fff]", text))
    if cjk_chars:
        non_cjk_text = re.sub(r"[\u4e00-\u9fff]", " ", text)
        words = set(m.group(0).lower() for m in re.finditer(r"\b\w+\b", non_cjk_text))
        return len(cjk_chars | words)

    unique_words = set(m.group(0).lower() for m in re.finditer(r"\b\w+\b", text))
    return len(unique_words)


def get_unique_words_set(text: str) -> set[str]:
    """Return the set of unique lowercased words extracted from text via generator iteration.

    Args:
        text: The text to analyze.

    Returns:
        set[str]: Set of distinct word tokens.
    """
    if not text:
        return set()

    cjk_chars = set(re.findall(r"[\u4e00-\u9fff]", text))
    if cjk_chars:
        non_cjk = re.sub(r"[\u4e00-\u9fff]", " ", text)
        words = set(m.group(0).lower() for m in re.finditer(r"\b\w+\b", non_cjk))
        return cjk_chars | words

    return set(m.group(0).lower() for m in re.finditer(r"\b\w+\b", text))


def iter_word_tokens(text: str) -> Iterable[str]:
    """Lazily yield lowercased word tokens without allocating a full list in memory.

    Args:
        text: The text to analyze.

    Yields:
        str: Individual lowercased word tokens.
    """
    if not text:
        return
    for match in re.finditer(r"\b\w+\b", text):
        yield match.group(0).lower()


def compute_vocabulary_richness(text: str) -> dict[str, float]:
    """Compute advanced lexical diversity indices based on unique and total word counts.

    Calculates:
        - types: Unique word count (V)
        - tokens: Total word count (N)
        - ttr: Type-Token Ratio (V / N)
        - guiraud_r: Guiraud's R index (V / sqrt(N))
        - herdan_c: Herdan's C index (log(V) / log(N))

    Args:
        text: The text to analyze.

    Returns:
        dict[str, float]: Dictionary of computed lexical richness metrics.
    """
    import math

    tokens = count_words(text)
    if tokens == 0:
        return {
            "tokens": 0,
            "types": 0,
            "ttr": 0.0,
            "guiraud_r": 0.0,
            "herdan_c": 0.0,
        }

    types = count_unique_words(text)
    ttr = types / tokens
    guiraud_r = types / math.sqrt(tokens) if tokens > 0 else 0.0
    herdan_c = math.log(types) / math.log(tokens) if tokens > 1 and types > 0 else 1.0

    return {
        "tokens": tokens,
        "types": types,
        "ttr": round(ttr, 4),
        "guiraud_r": round(guiraud_r, 4),
        "herdan_c": round(herdan_c, 4),
    }


def batch_count_unique_words(texts: list[str]) -> list[int]:
    """Compute unique word counts across a batch list of documents with generator efficiency.

    Args:
        texts: List of document strings.

    Returns:
        list[int]: List of unique word counts corresponding to each document.
    """
    return [count_unique_words(t) for t in texts]


def stream_word_frequencies(text: str) -> dict[str, int]:
    """Compute word occurrence frequencies using iterative token stream.

    Args:
        text: Input text string.

    Returns:
        dict[str, int]: Frequency map of lowercased word tokens.
    """
    from collections import Counter
    if not text:
        return {}
    return dict(Counter(iter_word_tokens(text)))


def compute_hapax_legomena(text: str) -> list[str]:
    """Identify words that appear exactly once in the entire text (Hapax Legomena).

    A high proportion of hapax legomena often correlates with sophisticated vocabulary
    or unique stylistic fingerprinting useful for authorship attribution.

    Args:
        text: Input text to analyze.

    Returns:
        list[str]: Sorted list of single-occurrence words.
    """
    freqs = stream_word_frequencies(text)
    return sorted([word for word, count in freqs.items() if count == 1])


def compute_hapax_dislegomena(text: str) -> list[str]:
    """Identify words that appear exactly twice in the text (Hapax Dislegomena).

    Args:
        text: Input text to analyze.

    Returns:
        list[str]: Sorted list of double-occurrence words.
    """
    freqs = stream_word_frequencies(text)
    return sorted([word for word, count in freqs.items() if count == 2])


def compute_yule_k_characteristic(text: str) -> float:
    """Calculate Yule's Characteristic K metric for vocabulary richness.

    Yule's K is a mathematically invariant measure of vocabulary diversity
    that remains relatively independent of total text length.

    Formula:
        K = 10^4 * (sum(i^2 * V_i) - N) / N^2
        where V_i is the number of words occurring i times, and N is total tokens.

    Args:
        text: Input text to analyze.

    Returns:
        float: Yule's K characteristic value (higher indicates lower lexical diversity).
    """
    from collections import Counter

    tokens = count_words(text)
    if tokens <= 1:
        return 0.0

    freqs = stream_word_frequencies(text)
    spectrum = Counter(freqs.values())

    s1 = sum(count * freq for freq, count in spectrum.items())
    s2 = sum(count * (freq ** 2) for freq, count in spectrum.items())

    if s1 <= 1:
        return 0.0

    k = 10000.0 * (s2 - s1) / (s1 ** 2)
    return round(k, 2)


def get_unique_word_ratio(text: str) -> float:
    """
    Calculate the unique word ratio (types/tokens ratio).

    This measures lexical diversity - the ratio of unique words to total words.
    Higher values indicate more diverse vocabulary.

    Args:
        text: The text to analyze

    Returns:
        Unique word ratio (0.0 to 1.0)
    """
    if not text:
        return 0.0

    total_words = count_words(text)
    if total_words == 0:
        return 0.0

    unique_words = count_unique_words(text)
    return unique_words / total_words


def compute_text_stats(text: str) -> dict[str, float]:
    """
    Compute all text statistics for the given text.

    Args:
        text: The text to analyze

    Returns:
        Dictionary containing:
            - word_count: Total number of words
            - sentence_count: Total number of sentences
            - unique_word_count: Number of unique words
            - unique_word_ratio: Ratio of unique words to total words (0-1)
    """
    word_count = count_words(text)
    sentence_count = count_sentences(text)
    unique_word_count = count_unique_words(text)
    unique_word_ratio = get_unique_word_ratio(text)

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "unique_word_count": unique_word_count,
        "unique_word_ratio": unique_word_ratio,
    }


def format_stats_for_pdf(stats: dict[str, float]) -> list[list[str]]:
    """
    Format text statistics for display in a PDF table.

    Args:
        stats: Dictionary of text statistics from compute_text_stats()

    Returns:
        List of rows for a ReportLab Table, each row is [Metric, Value]
    """
    return [
        ["Word Count", str(stats["word_count"])],
        ["Sentence Count", str(stats["sentence_count"])],
        ["Unique Words", str(stats["unique_word_count"])],
        ["Unique Word Ratio", f"{stats['unique_word_ratio']:.2%}"],
    ]


logger = logging.getLogger(__name__)


def get_word_count(text: str) -> int:
    """Deprecated alias for :func:`count_words`.

    Kept for backward compatibility with existing callers/tests. New code
    should call :func:`count_words` directly.
    """
    return count_words(text)


def get_char_count(text: str) -> int:
    return len(text)


def get_reading_time_minutes(text: str) -> float:
    """Estimate reading time in minutes.

    Average reading speed is roughly 200-250 words per minute; 200 is used as
    a conservative estimate. The result is rounded to one decimal place and
    floored at 0.1 so that any non-empty text reports a visible duration
    rather than "0 min".
    """
    word_count = count_words(text)
    return max(0.1, round(word_count / 200, 1))


def format_text_stats(text: str) -> str:
    words = count_words(text)
    chars = get_char_count(text)
    time = get_reading_time_minutes(text)
    reading_ease, grade_level = get_readability_metrics(text)
    return f"**Words:** {words} | **Characters:** {chars} | **Est. Reading Time:** {time} min | **Flesch Reading Ease:** {reading_ease} | **Flesch-Kincaid Grade:** {grade_level}"


def count_syllables(word: str) -> int:
    """
    Estimate the syllable count of a single English word.

    Uses regex-based vowel group counting with silent 'e' deductions.

    Args:
        word: The word to analyze

    Returns:
        Estimated syllable count (at least 1 for non-empty words)
    """
    word = word.lower().strip()
    if not word:
        return 0

    # Strip non-alphabetic characters
    word = re.sub(r"[^a-z]", "", word)
    if not word:
        return 0

    # Count vowel groups
    vowel_groups = re.findall(r"[aeiouy]+", word)
    count = len(vowel_groups)

    # Silent 'e' deductions
    if word.endswith("e"):
        vowels = "aeiouy"
        is_consonant_le = (
            len(word) >= 3 and word.endswith("le") and word[-3] not in vowels
        )
        if not is_consonant_le:
            count -= 1

    # Return at least 1 syllable for non-empty words
    return max(1, count)


def count_syllables_in_word(word: str) -> int:
    """Estimate the syllable count of a single word using basic heuristics."""
    return count_syllables(word)


def get_syllable_count(text: str) -> int:
    """Return the total syllable count for the text."""
    words = re.findall(r"\w+", text)
    return sum(count_syllables_in_word(w) for w in words)


def get_readability_metrics(text: str) -> tuple[float, float]:
    """Calculate Flesch Reading Ease and Flesch-Kincaid Grade Level.

    Returns (flesch_reading_ease, flesch_kincaid_grade).
    """
    words = count_words(text)
    sentences = get_sentence_count(text)
    syllables = get_syllable_count(text)

    if words == 0 or sentences == 0:
        if words == 0:
            logger.debug("Word count is zero, returning 0.0 for readability metrics.")
        return 0.0, 0.0

    reading_ease = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
    grade_level = 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59

    return round(reading_ease, 2), round(grade_level, 2)


def get_text_stats(text: str) -> dict[str, int | float]:
    """Calculate and return all text statistics in a structured dictionary.

    Returns default values with zeroes when text is empty or only whitespace.
    """
    if not text or not text.strip():
        logger.debug(
            "Empty or whitespace-only text provided. Returning default zeroes."
        )
        return {
            "words": 0,
            "characters": 0,
            "sentences": 0,
            "syllables": 0,
            "reading_ease": 0.0,
            "grade_level": 0.0,
            "reading_time": 0,
        }

    words = count_words(text)
    chars = get_char_count(text)
    sentences = count_sentences(text)
    syllables = get_syllable_count(text)
    reading_ease, grade_level = get_readability_metrics(text)
    reading_time = get_reading_time_minutes(text)

    return {
        "words": words,
        "characters": chars,
        "sentences": sentences,
        "syllables": syllables,
        "reading_ease": reading_ease,
        "grade_level": grade_level,
        "reading_time": reading_time,
    }
