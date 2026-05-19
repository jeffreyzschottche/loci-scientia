"""Document parsers (PDF / DOCX / CSV / XML / TXT-MD).

Port van ``app/embedder/backend/app/Support/DocumentParsing/`` (PHP) naar
Python. Elke parser produceert een :class:`ParsedDocument` met een lijst
secties. Het verdere chunken + JSON-LD gebeurt in
:mod:`app.backend.embedder.processing`.
"""

from .parsed import ParsedDocument
from .manager import (
    DocumentParser,
    DocumentParserError,
    get_parser_for_mime,
    list_parsers,
)
from .normalizer import normalize_text

__all__ = [
    "DocumentParser",
    "DocumentParserError",
    "ParsedDocument",
    "get_parser_for_mime",
    "list_parsers",
    "normalize_text",
]
