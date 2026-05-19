"""JSON-LD serializers.

Port van ``app/embedder/backend/app/Support/JsonLd/{Document,Section,Chunk}Serializer.php``.

In de nieuwe architectuur is JSON-LD **niet** meer het interne uitwissel-formaat
tussen embedder en device (zie commit waarin we de ZIP-bundle hebben gedropt).
We houden de serializers wel beschikbaar voor optionele export-downloads en
debug-doeleinden.

De serializers werken op gewone dicts, niet op ORM-objecten — caller geeft
gewoon de relevante kolommen door (`doc_id`, `title`, ...). Dat houdt deze
module losgekoppeld van de SQLite-laag.
"""

from __future__ import annotations

import os
import re
from typing import Any, Optional


# ---- config helpers ---------------------------------------------------------


def _embedding_model() -> str:
    return os.environ.get(
        "EMBEDDING_MODEL"
    ) or os.environ.get(
        "FASTEMBED_MODEL"
    ) or "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"


def _vector_dimension() -> int:
    raw = (os.environ.get("EMBEDDING_VECTOR_DIMENSION") or "768").strip()
    try:
        return int(raw)
    except ValueError:
        return 768


def embedding_metadata() -> dict[str, Any]:
    return {
        "model": _embedding_model(),
        "vectorDimension": _vector_dimension(),
    }


# ---- helpers ----------------------------------------------------------------


def _properties_from_metadata(metadata: Optional[dict]) -> list[dict]:
    if not metadata:
        return []
    props: list[dict] = []
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            props.append({"@type": "PropertyValue", "name": key, "value": value})
    return props


_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text or ""))


# ---- chunk ------------------------------------------------------------------


def serialize_chunk(chunk: dict, document: dict, section: Optional[dict]) -> dict:
    """Serialize a chunk row + parent document/section to JSON-LD.

    ``chunk`` minimaal: chunk_id, text, chunk_index, token_count, content_hash,
    metadata (dict|None).
    ``document`` minimaal: doc_id, content_date (str|None).
    ``section`` optioneel: slug.
    """

    metadata = chunk.get("metadata") or {}
    word_count = metadata.get("word_count") or _word_count(chunk.get("text", ""))
    pages = metadata.get("pages")

    payload: dict[str, Any] = {
        "@type": "TextDigitalDocument",
        "@id": f"chunk:{chunk['chunk_id']}",
        "identifier": chunk.get("content_hash"),
        "text": chunk.get("text", ""),
        "position": chunk.get("chunk_index"),
        "wordCount": word_count,
        "tokenCount": chunk.get("token_count"),
        "contentDate": document.get("content_date"),
        "embedding": embedding_metadata(),
        "isPartOf": (
            {"@id": f"sec:{document['doc_id']}#{section['slug']}"}
            if section
            else {"@id": f"doc:{document['doc_id']}"}
        ),
        "inDocument": {"@id": f"doc:{document['doc_id']}"},
    }

    if isinstance(pages, list) and pages:
        payload["pages"] = [int(p) for p in pages]

    return payload


def serialize_chunks(
    chunks: list[dict], document: dict, sections_by_id: dict[int, dict]
) -> list[dict]:
    return [
        serialize_chunk(chunk, document, sections_by_id.get(chunk.get("section_id")))
        for chunk in chunks
    ]


# ---- section ----------------------------------------------------------------


def serialize_section(
    section: dict,
    document: dict,
    chunks: Optional[list[dict]] = None,
    include_chunks: bool = False,
) -> dict:
    payload: dict[str, Any] = {
        "@type": "Chapter",
        "@id": f"sec:{document['doc_id']}#{section['slug']}",
        "name": section["title"],
        "position": section.get("order_index", 0),
        "text": section.get("text", ""),
        "wordCount": _word_count(section.get("text", "")),
        "isPartOf": {"@id": f"doc:{document['doc_id']}"},
    }

    if include_chunks and chunks:
        payload["hasPart"] = [
            serialize_chunk(chunk, document, section) for chunk in chunks
        ]

    props = _properties_from_metadata(section.get("metadata"))
    if props:
        payload["additionalProperty"] = props

    return payload


# ---- document ---------------------------------------------------------------


def serialize_document(
    document: dict,
    sections: Optional[list[dict]] = None,
    chunks_by_section_id: Optional[dict[int, list[dict]]] = None,
    include_sections: bool = True,
    include_chunks: bool = False,
) -> dict:
    payload: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Article",
        "@id": f"doc:{document['doc_id']}",
        "identifier": document["doc_id"],
        "name": document.get("title"),
        "dateCreated": document.get("created_at"),
        "dateModified": document.get("updated_at"),
    }

    if document.get("filename"):
        payload["originalFilename"] = document["filename"]
    if document.get("description"):
        payload["description"] = document["description"]
    if document.get("category"):
        payload["articleSection"] = document["category"]
    if document.get("version_tag"):
        payload["version"] = document["version_tag"]
    if document.get("content_date"):
        payload["datePublished"] = document["content_date"]
    if document.get("language"):
        payload["inLanguage"] = document["language"]

    if include_sections and sections:
        chunks_map = chunks_by_section_id or {}
        payload["hasPart"] = [
            serialize_section(
                section,
                document,
                chunks=chunks_map.get(section.get("id")),
                include_chunks=include_chunks,
            )
            for section in sections
        ]

    priority = document.get("priority") or 0
    extras: list[dict] = []
    if priority > 0:
        payload["position"] = priority
        extras.append(
            {
                "@type": "PropertyValue",
                "name": "embeddingPriority",
                "value": priority,
            }
        )

    extras.extend(_properties_from_metadata(document.get("metadata")))
    if extras:
        payload["additionalProperty"] = extras

    return payload


def serialize_document_tree(document: dict) -> dict:
    payload: dict[str, Any] = {
        "@type": "Article",
        "@id": f"doc:{document['doc_id']}",
        "name": document.get("title"),
        "position": document.get("position", 0),
    }
    if document.get("category"):
        payload["articleSection"] = document["category"]
    return payload
