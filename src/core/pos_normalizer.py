# semantic-plagiarism-detector/src/core/pos_normalizer.py

import nltk
from typing import List

# Ensure required NLTK corpuses/taggers are available
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)

class POSNormalizer:
    """
    Normalizes text into Part-of-Speech (POS) tag sequences to detect 
    syntactic structural cloning (mosaic plagiarism / patchwriting).
    """

    @staticmethod
    def extract_pos_sequence(text: str) -> List[str]:
        """
        Tokenizes text and extracts a normalized sequence of POS tags.
        Example: "The quick brown fox jumps" -> ['DT', 'JJ', 'JJ', 'NN', 'VBZ']
        """
        if not text or not text.strip():
            return []
            
        tokens = nltk.word_tokenize(text)
        tagged_tokens = nltk.pos_tag(tokens)
        
        # Extract just the POS tags and standardize/simplify if needed
        pos_tags = [tag for word, tag in tagged_tokens]
        return pos_tags

    @staticmethod
    def get_pos_string(text: str, separator: str = "-") -> str:
        """Returns the POS sequence as a hyphen-separated string."""
        tags = POSNormalizer.extract_pos_sequence(text)
        return separator.join(tags)
