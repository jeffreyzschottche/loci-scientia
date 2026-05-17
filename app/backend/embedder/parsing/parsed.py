"""ParsedDocument DTO en bijbehorende Section-shape."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

# Een sectie is een dict met op zijn minst ``title``, ``slug``, ``order_index``,
# ``text`` en optioneel ``metadata`` (waarin bijv. ``page_ranges`` zit voor
# PDF's). We modelleren het bewust als dict zodat parsers vrij kunnen blijven
# in welke extra velden ze meegeven — net als de PHP-versie.
Section = dict[str, Any]


_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+", re.UNICODE)
_SLUG_TRIM = re.compile(r"^-+|-+$")


def slugify(value: str, fallback: str = "section") -> str:
    """Compatibele slug-functie voor section/slug en doc_id sanitatie.

    Houdt het simpel (ASCII-lowercase, niet-alfanumerieke chars → '-') zoals
    Laravel's ``Str::slug`` default — voor onze use-case voldoende.
    """

    if not value:
        return fallback
    lower = value.strip().lower()
    slug = _SLUG_NON_ALNUM.sub("-", lower)
    slug = _SLUG_TRIM.sub("", slug)
    return slug or fallback


@dataclass
class ParsedDocument:
    doc_id: str
    title: str
    sections: list[Section] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None
    category: Optional[str] = None

    def word_count(self) -> int:
        words = 0
        for section in self.sections:
            text = section.get("text") or ""
            words += len(re.findall(r"\w+", text, flags=re.UNICODE))
        return words

    def character_count(self) -> int:
        return sum(len(section.get("text") or "") for section in self.sections)
