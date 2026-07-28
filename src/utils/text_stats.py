"""
text_stats.py
-------------
Text statistics and analysis utilities for document comparison.

Provides functions to compute various text metrics such as word count,
sentence count, and unique word ratio. These metrics are used in
plagiarism reports to provide additional context about compared documents.
"""

import re
from typing import Dict, List


def count_words(text: str) -> int:
    """
    Count the number of words in the given text.
    
    Words are defined as sequences of characters separated by whitespace.
    Punctuation is stripped before counting.
    
    Args:
        text: The text to analyze
        
    Returns:
        Number of words in the text
    """
    if not text:
        return 0
    
    # Remove punctuation and split on whitespace
    words = re.findall(r'\b\w+\b', text.lower())
    return len(words)


def count_sentences(text: str) -> int:
    """
    Count the number of sentences in the given text.
    
    Sentences are identified by periods, exclamation marks, and question marks.
    Also handles common abbreviations to avoid over-counting.
    
    Args:
        text: The text to analyze
        
    Returns:
        Number of sentences in the text
    """
    if not text:
        return 0
    
    # Common abbreviations that end with period but aren't sentence ends
    abbreviations = [
        'mr.', 'mrs.', 'ms.', 'dr.', 'prof.', 'sr.', 'jr.',
        'vs.', 'etc.', 'inc.', 'ltd.', 'corp.', 'co.',
        'fig.', 'tbl.', 'art.', 'no.', 'pp.', 'vol.',
        'jan.', 'feb.', 'mar.', 'apr.', 'jun.', 'jul.',
        'aug.', 'sep.', 'oct.', 'nov.', 'dec.',
        'u.s.', 'u.k.', 'e.u.', 'n.a.v.o.'
    ]
    
    # Replace abbreviations temporarily
    text_lower = text.lower()
    for abbr in abbreviations:
        text_lower = text_lower.replace(abbr, abbr.replace('.', ''))
    
    # Count sentence-ending punctuation
    sentence_endings = re.findall(r'[.!?]+', text_lower)
    return len(sentence_endings)


def count_unique_words(text: str) -> int:
    """
    Count the number of unique words in the given text.
    
    Word comparison is case-insensitive.
    
    Args:
        text: The text to analyze
        
    Returns:
        Number of unique words in the text
    """
    if not text:
        return 0
    
    # Get all words (lowercase)
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Count unique words
    unique_words = set(words)
    return len(unique_words)


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


def compute_text_stats(text: str) -> Dict[str, float]:
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
        'word_count': word_count,
        'sentence_count': sentence_count,
        'unique_word_count': unique_word_count,
        'unique_word_ratio': unique_word_ratio
    }


def format_stats_for_pdf(stats: Dict[str, float]) -> List[List[str]]:
    """
    Format text statistics for display in a PDF table.
    
    Args:
        stats: Dictionary of text statistics from compute_text_stats()
        
    Returns:
        List of rows for a ReportLab Table, each row is [Metric, Value]
    """
    return [
        ['Word Count', str(stats['word_count'])],
        ['Sentence Count', str(stats['sentence_count'])],
        ['Unique Words', str(stats['unique_word_count'])],
        ['Unique Word Ratio', f"{stats['unique_word_ratio']:.2%}"],
    ]
