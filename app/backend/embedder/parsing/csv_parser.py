"""CSV parser met optionele kolom-mapping.

Equivalent van de Laravel ``CsvParser``. Vereist een ``mapping``-stap (vandaar
``requires_mapping() -> True``); zonder mapping gaat alle data in één ``Data``-
sectie.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Optional

from .normalizer import normalize_text
from .parsed import ParsedDocument, slugify


_SUPPORTED_DELIMITERS = (",", ";", "\t", "|")


class CsvParser:
    _SUPPORTED_MIMES = {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
    }

    def supports(self, mime_type: str) -> bool:
        return mime_type in self._SUPPORTED_MIMES

    def parse(self, path: str, options: dict[str, Any]) -> ParsedDocument:
        file_path = Path(path)
        delimiter = options.get("delimiter") or self._detect_delimiter(path)
        has_header = options.get("has_header", True)
        mapping = options.get("mapping")

        headers: list[str] = []
        rows: list[dict] = []

        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            for line_index, data in enumerate(reader):
                if line_index == 0 and has_header:
                    headers = [str(cell) for cell in data]
                    continue
                if has_header and headers:
                    row = {
                        headers[i] if i < len(headers) else f"column_{i}": value
                        for i, value in enumerate(data)
                    }
                else:
                    row = {f"column_{i}": value for i, value in enumerate(data)}
                rows.append(row)

        doc_id = options.get("doc_id") or slugify(file_path.stem)
        title = options.get("title") or file_path.stem

        sections = self._rows_to_sections(rows, headers, mapping)

        metadata = {
            "row_count": len(rows),
            "column_count": len(headers),
            "columns": headers,
            "delimiter": delimiter,
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
        file_path = Path(path)
        try:
            delimiter = self._detect_delimiter(path)
            with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle, delimiter=delimiter)
                headers = next(reader, None)
        except OSError:
            return {}
        if not headers:
            return {}
        fields: dict[str, str] = {}
        for index, header in enumerate(headers):
            key = slugify(header, fallback=f"column_{index}")
            fields[key] = header
        return fields

    def requires_mapping(self) -> bool:
        return True

    # ---- internals ---------------------------------------------------------

    def _detect_delimiter(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                line = handle.readline()
        except OSError:
            return ","
        if not line:
            return ","
        counts = {delim: line.count(delim) for delim in _SUPPORTED_DELIMITERS}
        return max(counts, key=counts.get) or ","

    def _rows_to_sections(
        self,
        rows: list[dict],
        headers: list[str],
        mapping: Optional[dict],
    ) -> list[dict]:
        if not mapping:
            text = self._rows_to_text(rows, headers)
            return [
                {
                    "title": "Data",
                    "slug": "data",
                    "order_index": 0,
                    "text": normalize_text(text),
                    "metadata": {"row_count": len(rows)},
                }
            ]

        title_column = mapping.get("title_column")
        content_column = mapping.get("content_column")
        group_column = mapping.get("group_column")

        if group_column and rows and group_column in rows[0]:
            grouped: dict[str, list[dict]] = {}
            for row in rows:
                key = row.get(group_column) or "Overig"
                grouped.setdefault(str(key), []).append(row)

            sections: list[dict] = []
            for index, (group_name, group_rows) in enumerate(grouped.items()):
                parts: list[str] = []
                for row in group_rows:
                    if title_column and title_column in row:
                        parts.append(f"### {row[title_column]}")
                    if content_column and content_column in row:
                        parts.append(str(row[content_column]))
                        parts.append("")
                    else:
                        parts.append(self._row_to_text(row, headers))
                        parts.append("")
                sections.append(
                    {
                        "title": group_name,
                        "slug": slugify(group_name, fallback=f"groep-{index}"),
                        "order_index": index,
                        "text": normalize_text("\n".join(parts)),
                        "metadata": {"row_count": len(group_rows)},
                    }
                )
            return sections

        if title_column:
            sections = []
            for index, row in enumerate(rows):
                row_title = row.get(title_column) or f"Rij {index + 1}"
                content = (
                    str(row[content_column])
                    if content_column and content_column in row
                    else self._row_to_text(row, headers)
                )
                sections.append(
                    {
                        "title": str(row_title),
                        "slug": slugify(str(row_title), fallback=f"rij-{index}"),
                        "order_index": index,
                        "text": normalize_text(content),
                        "metadata": {"row_data": row},
                    }
                )
            return sections

        text = self._rows_to_text(rows, headers)
        return [
            {
                "title": "Data",
                "slug": "data",
                "order_index": 0,
                "text": normalize_text(text),
                "metadata": {"row_count": len(rows)},
            }
        ]

    def _rows_to_text(self, rows: list[dict], headers: list[str]) -> str:
        parts: list[str] = []
        for index, row in enumerate(rows):
            parts.append(f"--- Rij {index + 1} ---")
            parts.append(self._row_to_text(row, headers))
            parts.append("")
        return "\n".join(parts).strip()

    @staticmethod
    def _row_to_text(row: dict, headers: list[str]) -> str:
        lines = []
        for key, value in row.items():
            if value in (None, ""):
                continue
            lines.append(f"{key}: {value}")
        return "\n".join(lines)
