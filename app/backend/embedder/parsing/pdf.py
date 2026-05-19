"""PDF parser.

Gebruikt :mod:`pypdf` (al een dependency van het hoofdproject). Combineert
alle pagina's tot één ``Inhoud``-sectie en houdt per pagina char-ranges bij,
zodat het processing-laag chunks naar pagina-nummers kan mappen.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .normalizer import normalize_text
from .parsed import ParsedDocument, slugify


class PdfParser:
    def supports(self, mime_type: str) -> bool:
        return mime_type == "application/pdf"

    def parse(self, path: str, options: dict[str, Any]) -> ParsedDocument:
        reader = PdfReader(path)
        file_path = Path(path)

        info = reader.metadata or {}

        doc_id = options.get("doc_id") or slugify(file_path.stem)
        title = (
            options.get("title")
            or (info.get("/Title") if hasattr(info, "get") else None)
            or file_path.stem
        )

        sections = self._extract_sections(reader)

        metadata = {
            "page_count": len(reader.pages),
            "author": info.get("/Author") if hasattr(info, "get") else None,
            "creator": info.get("/Creator") if hasattr(info, "get") else None,
            "creation_date": info.get("/CreationDate") if hasattr(info, "get") else None,
            "modification_date": info.get("/ModDate") if hasattr(info, "get") else None,
        }
        metadata = {k: v for k, v in metadata.items() if v}

        return ParsedDocument(
            doc_id=doc_id,
            title=str(title),
            sections=sections,
            metadata=metadata,
            description=options.get("description"),
            category=options.get("category"),
        )

    def get_mappable_fields(self, path: str) -> dict[str, str]:
        return {}

    def requires_mapping(self) -> bool:
        return False

    # ---- internals ---------------------------------------------------------

    def _extract_sections(self, reader: PdfReader) -> list[dict]:
        separator = "\n\n"
        combined_parts: list[str] = []
        page_ranges: list[dict] = []
        cursor = 0
        page_total = len(reader.pages)

        for index, page in enumerate(reader.pages):
            page_number = index + 1
            raw_text = page.extract_text() or ""
            page_text = normalize_text(raw_text)
            if not page_text:
                continue

            start = cursor
            combined_parts.append(page_text)
            cursor += len(page_text)
            end = cursor
            page_ranges.append({"page": page_number, "start": start, "end": end})

            combined_parts.append(separator)
            cursor += len(separator)

        if combined_parts and combined_parts[-1] == separator:
            combined_parts.pop()
            cursor -= len(separator)

        combined_text = "".join(combined_parts)

        return [
            {
                "title": "Inhoud",
                "slug": slugify("Inhoud", fallback="inhoud"),
                "order_index": 0,
                "text": combined_text,
                "metadata": {
                    "start_page": 1,
                    "end_page": page_total,
                    "page_ranges": page_ranges,
                },
            }
        ]
