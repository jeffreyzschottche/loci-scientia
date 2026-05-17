"""XML / XHTML parser met optionele XPath-mapping.

Equivalent van de Laravel ``XmlParser``. Gebruikt stdlib ``xml.etree`` voor
parsing — geen externe deps. Voor mapping kunnen XPath-expressies worden
meegegeven; zonder mapping wordt de structuur auto-gedetecteerd (root met
repeating children → 1 sectie per child).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
from xml.etree import ElementTree as ET

from .normalizer import normalize_text
from .parsed import ParsedDocument, slugify


_TITLE_TAGS = ("title", "name", "heading", "header", "Title", "Name")
_TITLE_ATTRS = ("title", "name", "id")


class XmlParser:
    _SUPPORTED_MIMES = {"text/xml", "application/xml", "application/xhtml+xml"}

    def supports(self, mime_type: str) -> bool:
        return mime_type in self._SUPPORTED_MIMES

    def parse(self, path: str, options: dict[str, Any]) -> ParsedDocument:
        file_path = Path(path)
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            raise RuntimeError(f"Ongeldige XML: {exc}") from exc

        root = tree.getroot()

        doc_id = options.get("doc_id") or slugify(file_path.stem)
        title = (
            options.get("title")
            or self._extract_title(root)
            or file_path.stem
        )

        mapping = options.get("mapping")
        sections = self._xml_to_sections(root, mapping)

        metadata = {
            "root_element": _localname(root.tag),
            "child_count": len(list(root)),
        }

        return ParsedDocument(
            doc_id=doc_id,
            title=title,
            sections=sections,
            metadata={k: v for k, v in metadata.items() if v},
            description=options.get("description"),
            category=options.get("category"),
        )

    def get_mappable_fields(self, path: str) -> dict[str, str]:
        try:
            tree = ET.parse(path)
        except (ET.ParseError, OSError):
            return {}
        return self._extract_xpaths(tree.getroot())

    def requires_mapping(self) -> bool:
        return True

    # ---- title detection ---------------------------------------------------

    def _extract_title(self, element: ET.Element) -> Optional[str]:
        for tag in _TITLE_TAGS:
            child = self._find_child(element, tag)
            if child is not None and (child.text or "").strip():
                return child.text.strip()
        for attr in _TITLE_ATTRS:
            value = element.attrib.get(attr)
            if value:
                return value
        return None

    @staticmethod
    def _find_child(element: ET.Element, tag: str) -> Optional[ET.Element]:
        for child in element:
            if _localname(child.tag) == tag:
                return child
        return None

    # ---- sectioning --------------------------------------------------------

    def _xml_to_sections(
        self, root: ET.Element, mapping: Optional[dict]
    ) -> list[dict]:
        if mapping and mapping.get("section_xpath"):
            return self._mapped_sections(root, mapping)
        return self._auto_detect_sections(root)

    def _mapped_sections(
        self, root: ET.Element, mapping: dict
    ) -> list[dict]:
        section_xpath = mapping["section_xpath"]
        title_xpath = mapping.get("title_xpath")
        content_xpath = mapping.get("content_xpath")

        elements = root.findall(section_xpath)
        sections: list[dict] = []
        for index, element in enumerate(elements):
            section_title = f"Sectie {index + 1}"
            if title_xpath:
                hit = element.find(title_xpath)
                if hit is not None and (hit.text or "").strip():
                    section_title = hit.text.strip()
            if content_xpath:
                content_hit = element.find(content_xpath)
                content = (content_hit.text or "") if content_hit is not None else ""
            else:
                content = self._element_to_text(element)

            sections.append(
                {
                    "title": section_title,
                    "slug": slugify(section_title, fallback=f"sectie-{index}"),
                    "order_index": index,
                    "text": normalize_text(content),
                    "metadata": {"xpath": f"{section_xpath}[{index + 1}]"},
                }
            )

        if not sections:
            sections.append(
                {
                    "title": "Inhoud",
                    "slug": "inhoud",
                    "order_index": 0,
                    "text": normalize_text(self._element_to_text(root)),
                    "metadata": {},
                }
            )
        return sections

    def _auto_detect_sections(self, root: ET.Element) -> list[dict]:
        children = list(root)
        if not children:
            return [
                {
                    "title": "Inhoud",
                    "slug": "inhoud",
                    "order_index": 0,
                    "text": normalize_text(self._element_to_text(root)),
                    "metadata": {},
                }
            ]

        names = [_localname(child.tag) for child in children]
        unique_names = set(names)
        sections: list[dict] = []

        if len(unique_names) == 1 and len(children) > 1:
            for index, child in enumerate(children):
                child_name = _localname(child.tag)
                title = self._extract_title(child) or f"{child_name} {index + 1}"
                sections.append(
                    {
                        "title": title,
                        "slug": slugify(title, fallback=f"{child_name}-{index}"),
                        "order_index": index,
                        "text": normalize_text(self._element_to_text(child)),
                        "metadata": {"element": child_name},
                    }
                )
        else:
            for index, child in enumerate(children):
                child_name = _localname(child.tag)
                title = self._extract_title(child) or child_name.capitalize()
                sections.append(
                    {
                        "title": title,
                        "slug": slugify(title, fallback=child_name),
                        "order_index": index,
                        "text": normalize_text(self._element_to_text(child)),
                        "metadata": {"element": child_name},
                    }
                )

        return sections

    # ---- xpath extraction --------------------------------------------------

    def _extract_xpaths(
        self, element: ET.Element, prefix: str = ""
    ) -> dict[str, str]:
        paths: dict[str, str] = {}
        name = _localname(element.tag)
        current = f"{prefix}/{name}" if prefix else f"/{name}"
        paths[current] = name

        for attr in element.attrib:
            paths[f"{current}/@{attr}"] = f"{name}/@{attr}"

        if current.count("/") < 5:
            for child in element:
                paths.update(self._extract_xpaths(child, current))

        return paths

    # ---- text extraction ---------------------------------------------------

    def _element_to_text(self, element: ET.Element) -> str:
        parts: list[str] = []
        direct = (element.text or "").strip()
        if direct:
            parts.append(direct)

        for child in element:
            child_name = _localname(child.tag)
            child_text = (child.text or "").strip()

            if child.attrib:
                attr_parts = [f"{name}: {value}" for name, value in child.attrib.items()]
                parts.append(f"{child_name}: {', '.join(attr_parts)}")

            grandchildren = list(child)
            if child_text and not grandchildren:
                parts.append(f"{child_name}: {child_text}")
            elif grandchildren:
                parts.append(f"\n{child_name}:")
                parts.append(self._element_to_text(child))

        return "\n".join(parts)


def _localname(tag: str) -> str:
    """Strip ``{namespace}`` voorvoegsel uit een ETree-tag."""

    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag
