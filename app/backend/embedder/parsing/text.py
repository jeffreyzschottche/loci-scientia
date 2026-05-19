"""TXT / Markdown parser.

Markdown wordt gesplitst per heading (``#``, ``##`` ...). Plain text wordt als
één ``Inhoud``-sectie behandeld.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .normalizer import normalize_text
from .parsed import ParsedDocument, slugify


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")


class TextParser:
    _SUPPORTED_MIMES = {"text/plain", "text/markdown"}

    def supports(self, mime_type: str) -> bool:
        return mime_type in self._SUPPORTED_MIMES

    def parse(self, path: str, options: dict[str, Any]) -> ParsedDocument:
        file_path = Path(path)
        text = file_path.read_text(encoding="utf-8", errors="replace")
        is_markdown = file_path.suffix.lower() == ".md"

        doc_id = options.get("doc_id") or slugify(file_path.stem)
        title = options.get("title") or file_path.stem

        if is_markdown:
            sections = self._parse_markdown_sections(text)
        else:
            sections = self._parse_plain_sections(text)

        metadata = {
            "line_count": text.count("\n") + 1,
            "format": "markdown" if is_markdown else "plain",
        }

        return ParsedDocument(
            doc_id=doc_id,
            title=title,
            sections=sections,
            metadata=metadata,
            description=options.get("description"),
            category=options.get("category"),
        )

    def get_mappable_fields(self, path: str) -> dict[str, str]:
        return {}

    def requires_mapping(self) -> bool:
        return False

    # ---- markdown ----------------------------------------------------------

    def _parse_markdown_sections(self, text: str) -> list[dict]:
        sections: list[dict] = []
        current: dict | None = None
        buffer: list[str] = []
        section_index = 0

        for line in text.split("\n"):
            match = _HEADING_RE.match(line)
            if match:
                if current is not None and any(part.strip() for part in buffer):
                    sections.append(
                        self._make_section(
                            section_index, current, "\n".join(buffer)
                        )
                    )
                    section_index += 1
                level = len(match.group(1))
                section_title = match.group(2).strip()
                current = {
                    "title": section_title,
                    "slug": slugify(section_title, fallback=f"sectie-{section_index}"),
                    "level": level,
                }
                buffer = []
            else:
                buffer.append(line)

        if any(part.strip() for part in buffer):
            if current is None:
                current = {"title": "Inhoud", "slug": "inhoud", "level": 0}
            sections.append(self._make_section(section_index, current, "\n".join(buffer)))

        if not sections:
            sections.append(
                {
                    "title": "Inhoud",
                    "slug": "inhoud",
                    "order_index": 0,
                    "text": normalize_text(text),
                    "metadata": {},
                }
            )
        return sections

    @staticmethod
    def _make_section(order_index: int, header: dict, raw_text: str) -> dict:
        return {
            "title": header["title"],
            "slug": header["slug"],
            "order_index": order_index,
            "text": normalize_text(raw_text),
            "metadata": {"level": header.get("level", 0)},
        }

    # ---- plain text --------------------------------------------------------

    def _parse_plain_sections(self, text: str) -> list[dict]:
        return [
            {
                "title": "Inhoud",
                "slug": "inhoud",
                "order_index": 0,
                "text": normalize_text(text),
                "metadata": {},
            }
        ]
