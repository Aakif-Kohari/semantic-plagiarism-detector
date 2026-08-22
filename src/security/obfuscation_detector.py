import re
import unicodedata

class ObfuscationDetector:
    def __init__(self):
        # 1. Zero-width and invisible control character tracking filters
        # Matches ZWSP, ZWNJ, ZWJ, BOM, and general format control characters (\p{Cf})
        self.invisible_chars_regex = re.compile(r'[\u200b-\u200d\ufeff\u200e\u200f\u202a-\u202e]')
        
        # 2. Cyrillic Homoglyphs frequently substituted into English text
        # Example: Cyrillic 'а' (U+0430) vs Latin 'a' (U+0061)
        self.cyrillic_homoglyphs = set(range(0x0400, 0x04FF))

    def detect_invisible_characters(self, text: str) -> list[int]:
        """Finds string indexes containing hidden Unicode format markers."""
        return [match.start() for match in self.invisible_chars_regex.finditer(text)]

    def detect_homoglyphs(self, text: str) -> list[int]:
        """Pins down mixed-script homoglyph character substitutions."""
        flagged_indices = []
        has_latin = any(unicodedata.name(c).startswith('LATIN') for c in text if c.isalpha())
        
        if has_latin:
            for idx, char in enumerate(text):
                if ord(char) in self.cyrillic_homoglyphs:
                    flagged_indices.append(idx)
        return flagged_indices

    def analyze_text(self, text: str) -> dict:
        """Runs the complete suite of text analysis sub-checks."""
        if not text:
            return {"obfuscation_score": 0.0, "invisible_indices": [], "homoglyph_indices": [], "is_flagged": False}

        invisible_indices = self.detect_invisible_characters(text)
        homoglyph_indices = self.detect_homoglyphs(text)
        
        total_violations = len(invisible_indices) + len(homoglyph_indices)
        total_chars = len(text)
        
        # Calculate percentage footprint density score
        obfuscation_score = round((total_violations / total_chars) * 100, 2) if total_chars > 0 else 0.0
        
        # Flag automatically if more than 1% of the document uses suspicious formatting
        is_flagged = obfuscation_score >= 1.0 or total_violations > 10

        return {
            "obfuscation_score": obfuscation_score,
            "invisible_indices": invisible_indices,
            "homoglyph_indices": homoglyph_indices,
            "is_flagged": is_flagged
        }
