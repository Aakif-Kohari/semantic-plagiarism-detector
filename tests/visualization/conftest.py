import sys
import importlib
from unittest.mock import MagicMock

# Stub out broken/heavy modules so heatmap tests can collect without errors
for mod in [
    "src.db",
    "src.db.auth",
    "src.db.corpus_db",
    "src.core.document_parser",
    "src.core.embedding_model",
    "src.core.faiss_index",
    "src.core.translator",
    "striprtf",
    "striprtf.striprtf",
    "pdfplumber",
    "defusedxml",
    "defusedxml.lxml",
]:
    if mod not in sys.modules:
        try:
            importlib.import_module(mod)
        except Exception:
            sys.modules[mod] = MagicMock()
