"""Parser-registry. Kiest de juiste parser op basis van MIME-type."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .parsed import ParsedDocument


class DocumentParserError(RuntimeError):
    """Foutmelding voor parser-problemen (mime niet ondersteund, IO etc.)."""


@runtime_checkable
class DocumentParser(Protocol):
    """Contract voor alle parsers.

    Bewust een Protocol (geen ABC) zodat individuele parser-modules niet
    hoeven te erven; ze hoeven alleen de juiste methodes te hebben.
    """

    def supports(self, mime_type: str) -> bool: ...

    def parse(self, path: str, options: dict[str, Any]) -> ParsedDocument: ...

    def get_mappable_fields(self, path: str) -> dict[str, str]: ...

    def requires_mapping(self) -> bool: ...


def list_parsers() -> list[DocumentParser]:
    """Lazy import om circulaire imports bij module-initialisatie te vermijden."""

    from .pdf import PdfParser
    from .docx import DocxParser
    from .csv_parser import CsvParser
    from .xml_parser import XmlParser
    from .text import TextParser

    # Volgorde is van belang: meest specifiek eerst, generic text-parser als
    # vangnet. PHP-versie registreert ze in dezelfde volgorde via de container.
    return [
        PdfParser(),
        DocxParser(),
        CsvParser(),
        XmlParser(),
        TextParser(),
    ]


def get_parser_for_mime(mime_type: str) -> DocumentParser:
    for parser in list_parsers():
        if parser.supports(mime_type):
            return parser
    raise DocumentParserError(f"Geen parser voor mime type {mime_type}")
