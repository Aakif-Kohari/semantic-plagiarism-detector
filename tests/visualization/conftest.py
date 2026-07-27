import sys
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
    sys.modules.setdefault(mod, MagicMock())
