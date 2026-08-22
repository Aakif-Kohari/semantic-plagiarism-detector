import difflib

class DocumentDiffEngine:
    @staticmethod
    def compute_word_diff(parent_text: str, child_text: str) -> list[dict]:
        """
        Executes a sequence alignment loop tracking word-by-word alterations.
        Returns a list of token dictionaries containing the token text and structural action state.
        """
        parent_words = parent_text.split()
        child_words = child_text.split()
        
        matcher = difflib.SequenceMatcher(None, parent_words, child_words)
        diff_tokens = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for word in parent_words[i1:i2]:
                    diff_tokens.append({"text": word, "action": "unchanged"})
            elif tag == 'delete':
                for word in parent_words[i1:i2]:
                    diff_tokens.append({"text": word, "action": "deleted"})
            elif tag == 'insert':
                for word in child_words[j1:j2]:
                    diff_tokens.append({"text": word, "action": "added"})
            elif tag == 'replace':
                for word in parent_words[i1:i2]:
                    diff_tokens.append({"text": word, "action": "deleted"})
                for word in child_words[j1:j2]:
                    diff_tokens.append({"text": word, "action": "added"})
                    
        return diff_tokens

    @staticmethod
    def calculate_retention_metrics(diff_tokens: list[dict]) -> dict:
        """Computes summary statistics regarding text evolution between versions."""
        total = len(diff_tokens)
        if total == 0:
            return {"retention_rate": 100.0, "addition_rate": 0.0, "deletion_rate": 0.0}
            
        unchanged = sum(1 for t in diff_tokens if t["action"] == "unchanged")
        added = sum(1 for t in diff_tokens if t["action"] == "added")
        deleted = sum(1 for t in diff_tokens if t["action"] == "deleted")
        
        return {
            "retention_rate": round((unchanged / (unchanged + deleted if (unchanged + deleted) > 0 else 1)) * 100, 2),
            "addition_rate": round((added / total) * 100, 2),
            "deletion_rate": round((deleted / total) * 100, 2)
        }
