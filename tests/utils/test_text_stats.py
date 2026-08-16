from src.utils.text_stats import (format_text_stats, get_char_count,
                                   get_reading_time_minutes, count_words, count_sentences,
                                   get_sentence_count, get_syllable_count,
                                   get_readability_metrics, get_text_stats)
from src.utils.text_stats import (
    count_syllables_in_word,
    count_words,
    format_text_stats,
    get_char_count,
    get_readability_metrics,
    get_reading_time_minutes,
    get_sentence_count,
    get_syllable_count,
    get_text_stats,
)



def test_count_syllables_in_word():
    assert count_syllables_in_word("apple") == 2
    assert count_syllables_in_word("table") == 2
    assert count_syllables_in_word("blue") == 1
    assert count_syllables_in_word("the") == 1

def test_count_words():
    assert count_words("This is a test.") == 4
    assert count_words("") == 0
    assert count_words("   Spaces   ") == 1
    assert count_words("hello,world") == 2
    assert count_words("hello-world") == 2
    assert count_words("HELLO hello") == 2


def test_get_char_count():
    assert get_char_count("abc") == 3
    assert get_char_count("") == 0


def test_get_reading_time_minutes():
    assert get_reading_time_minutes("word " * 100) == 1
    assert get_reading_time_minutes("word " * 400) == 2
    assert get_reading_time_minutes("") == 1


def test_get_sentence_count():
    assert get_sentence_count("Hello world. How are you? Fine!") == 3
    assert get_sentence_count("") == 0
    assert get_sentence_count("No punctuation") == 0
    assert get_sentence_count("Dr. Smith arrived. He stayed.") == 2


def test_get_syllable_count():
    assert get_syllable_count("the") == 1
    # "science" -> s-ci-ence (2 syllables)
    assert get_syllable_count("science") == 2
    assert get_syllable_count("") == 0


def test_get_readability_metrics():
    # Empty / safe handling
    ease, grade = get_readability_metrics("")
    assert ease == 0.0
    assert grade == 0.0

    text = "This is a simple sentence."
    ease, grade = get_readability_metrics(text)
    assert isinstance(ease, float)
    assert isinstance(grade, float)


def test_format_text_stats():
    text = "This is a test sentence."
    stats = format_text_stats(text)
    assert "**Words:** 5" in stats
    assert "**Characters:** 24" in stats
    assert "**Est. Reading Time:** 1 min" in stats
    assert "**Flesch Reading Ease:**" in stats
    assert "**Flesch-Kincaid Grade:**" in stats


def test_get_text_stats():
    # Empty text
    stats = get_text_stats("")
    assert stats == {
        "words": 0,
        "characters": 0,
        "sentences": 0,
        "syllables": 0,
        "reading_ease": 0.0,
        "grade_level": 0.0,
        "reading_time": 0,
    }

    # Whitespace-only
    stats = get_text_stats("   \n   ")
    assert stats == {
        "words": 0,
        "characters": 7,
        "sentences": 0,
        "syllables": 0,
        "reading_ease": 0.0,
        "grade_level": 0.0,
        "reading_time": 0,
    }

    # Punctuation-only
    stats = get_text_stats("... !!! ???")
    assert stats["words"] == 0
    assert stats["reading_ease"] == 0.0
    assert stats["grade_level"] == 0.0
