"""
src/core/citation_extractor.py
------------------------------
Automated Citation Extraction Engine.

Parses bibliography sections from extracted document text using regex
and NLP heuristics. Supports APA and MLA formats to identify cited works,
enabling the detection of citation laundering and shared bibliography rings.
"""

import re
import logging
from typing import List, Dict, Any, Set
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class Citation:
    """Represents a single parsed citation."""
    raw_text: str
    authors: str
    year: str
    title: str
    source: str
    format_detected: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def get_normalized_key(self) -> str:
        """Generate a normalized key for graph node matching."""
        # Combine first author, year, and first 5 words of title
        title_words = "_".join(self.title.lower().split()[:5])
        return f"{self.authors.lower().split(',')[0]}_{self.year}_{title_words}"


# Regex patterns for common citation formats
# APA: Author, A. A. (Year). Title of work. Source.
APA_PATTERN = re.compile(
    r'^(?P<authors>[A-Z][a-z]+(?:,\s*[A-Z]\.?\s*(?:&\s*[A-Z][a-z]+)*)*)\s*'
    r'\((?P<year>\d{4})\)\.\s*'
    r'(?P<title>[^.]+)\.\s*'
    r'(?P<source>.+)$',
    re.MULTILINE
)

# MLA: Author. "Title." Source, Year.
MLA_PATTERN = re.compile(
    r'^(?P<authors>[A-Z][a-z]+(?:,\s*[A-Z][a-z]+)*)\.\s*'
    r'"(?P<title>[^"]+)"\s*'
    r'(?P<source>[^,]+),\s*'
    r'(?P<year>\d{4})',
    re.MULTILINE
)


def extract_citations(text: str) -> List[Citation]:
    """Parse the bibliography section of a document.
    
    Args:
        text: The raw text of the bibliography/references section.
        
    Returns:
        A list of Citation objects.
    """
    if not text:
        return []

    citations = []
    
    # Try APA format first
    for match in APA_PATTERN.finditer(text):
        citations.append(Citation(
            raw_text=match.group(0).strip(),
            authors=match.group('authors').strip(),
            year=match.group('year').strip(),
            title=match.group('title').strip(),
            source=match.group('source').strip(),
            format_detected="APA"
        ))
        
    # If APA didn't find much, try MLA
    if len(citations) < 2:
        mla_citations = []
        for match in MLA_PATTERN.finditer(text):
            mla_citations.append(Citation(
                raw_text=match.group(0).strip(),
                authors=match.group('authors').strip(),
                year=match.group('year').strip(),
                title=match.group('title').strip(),
                source=match.group('source').strip(),
                format_detected="MLA"
            ))
        if len(mla_citations) > len(citations):
            citations = mla_citations

    logger.info("Extracted %d citations from text.", len(citations))
    return citations


def compute_jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Compute the Jaccard similarity between two sets of citation keys."""
    if not set_a and not set_b:
        return 1.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    if union == 0:
        return 0.0
    return intersection / union

"""
src/core/citation_extractor.py
------------------------------
Bibliography parser and citation extraction engine.

Extracts structured citation data (author, year, title) from raw
bibliography text sections. Supports common academic formats including
APA, IEEE, and MLA.

Recent Additions (Issue #1958):
- Implemented regex-based parsers for APA, IEEE, and MLA formats.
- Added fuzzy hashing for cross-document citation matching.
"""

import hashlib
import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)

# Regex patterns for common citation formats
# APA: Author, A. A. (Year). Title. Journal, Vol(Issue), Pages.
_APA_PATTERN = re.compile(
    r"^(?P<authors>.+?)\s*\((?P<year>\d{4})\)\.\s*(?P<title>[^.]+)\.",
    re.MULTILINE,
)

# IEEE: [1] A. Author, "Title," Journal, vol. X, no. Y, pp. Z, Year.
_IEEE_PATTERN = re.compile(
    r'^\s*\[\d+\]\s*(?P<authors>[^,]+),\s*"(?P<title>[^"]+),"[^0-9]*(?P<year>\d{4})',
    re.MULTILINE,
)

# MLA: Author. "Title." Journal, vol. X, no. Y, Year, pp. Z.
_MLA_PATTERN = re.compile(
    r'^(?P<authors>[^.]+)\.\s*"(?P<title>[^"]+)"[^0-9]*(?P<year>\d{4})', re.MULTILINE
)


def _normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, and collapse whitespace for hashing."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _generate_citation_hash(author: str, year: str, title: str) -> str:
    """Generate a deterministic SHA-256 hash for a citation to enable matching.

    We hash the normalized author + year + title to create a unique identifier
    that can be used to find shared citations across different documents, even
    if the exact formatting differs slightly.
    """
    norm_author = _normalize_text(author)
    norm_title = _normalize_text(title)

    # Fuzzy matching: Use first 50 chars of title and first author name
    # to handle minor variations in how students copy references.
    key = f"{norm_author[:50]}|{year}|{norm_title[:80]}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def extract_citations(raw_text: str) -> List[Dict[str, str]]:
    """Parse raw bibliography text and extract structured citation entities.

    Attempts to match APA, IEEE, and MLA patterns. If a line doesn't match
    strict patterns, it falls back to a heuristic extraction of year and
    title to ensure high recall on messy student bibliographies.

    Args:
        raw_text: The raw text of the bibliography/references section.

    Returns:
        List of dictionaries containing 'author', 'year', 'title', and 'hash'.
    """
    if not raw_text or not isinstance(raw_text, str):
        return []

    citations = []
    seen_hashes = set()

    # Split by common bibliography delimiters (newlines with hanging indents)
    # For simplicity, we process line by line or block by block.
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]  # noqa: E741

    for line in lines:
        author, year, title = None, None, None

        # Try APA
        match = _APA_PATTERN.search(line)
        if match:
            author = match.group("authors")
            year = match.group("year")
            title = match.group("title")

        # Try IEEE
        if not author:
            match = _IEEE_PATTERN.search(line)
            if match:
                author = match.group("authors")
                year = match.group("year")
                title = match.group("title")

        # Try MLA
        if not author:
            match = _MLA_PATTERN.search(line)
            if match:
                author = match.group("authors")
                year = match.group("year")
                title = match.group("title")

        # Fallback Heuristic: Look for a 4-digit year and assume the rest is title
        if not author:
            year_match = re.search(r"\b(19|20)\d{2}\b", line)
            if year_match:
                year = year_match.group(0)
                # Assume text before year is author, after is title
                parts = line.split(year, 1)
                author = parts[0].strip().rstrip(",.")
                title = parts[1].strip().lstrip(",. ") if len(parts) > 1 else ""
            else:
                continue  # Skip lines without a year

        if not title:
            title = line  # Fallback to full line as title

        # Clean up extracted fields
        author = author.strip() if author else "Unknown"
        title = title.strip() if title else "Unknown"
        year = year.strip() if year else "Unknown"

        # Generate hash and deduplicate within the same document
        citation_hash = _generate_citation_hash(author, year, title)
        if citation_hash in seen_hashes:
            continue
        seen_hashes.add(citation_hash)

        citations.append(
            {
                "author": author,
                "year": year,
                "title": title,
                "hash": citation_hash,
                "raw_text": line,
            }
        )

    logger.info("Extracted %d unique citations from bibliography.", len(citations))
    return citations
