"""Library-overzicht voor de device-zijde Kennisbank-pagina.

Sinds de Aitje Embedding Application in-process draait (zie
``app.backend.embedder``) is de embedder-SQLite (devices_db/embedder.db) het
canonieke document-register. Deze module wikkelt de embedder-DB in de shape
die de Qt-frontend (`app/frontend/widgets/knowledge_page.py`) verwacht zodat
beide views — de embedder web-client en de device Kennisbank-pagina — exact
dezelfde records tonen.
"""

from __future__ import annotations

from typing import Any

from .embedder import jsonld, models


def get_library_overview() -> dict[str, Any]:
    """Geef de lijst van documenten + per-categorie tellingen terug.

    Verzamelt rechtstreeks uit de embedder-DB; ``kennisbank_cache.db`` is na
    de port overbodig.
    """

    raw_documents = models.list_documents(order="category, priority, title")
    documents: list[dict[str, Any]] = []
    categories: dict[str, dict[str, Any]] = {}

    for doc in raw_documents:
        metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        documents.append(
            {
                "doc_id": doc.get("doc_id"),
                "title": doc.get("title"),
                "category": doc.get("category"),
                "version": doc.get("version_tag"),
                "content_date": doc.get("content_date"),
                "chunk_count": int(doc.get("chunk_count") or 0),
                "priority": doc.get("priority"),
                "source_url": None,
                "description": doc.get("description") or (metadata or {}).get("description"),
                "status": doc.get("status"),
            }
        )

        cat = doc.get("category") or "uncategorized"
        bucket = categories.setdefault(cat, {"category": cat, "document_count": 0})
        bucket["document_count"] += 1

    return {
        "documents": documents,
        "categories": list(categories.values()),
    }


def load_document_detail(doc_id: str) -> dict[str, Any]:
    """Genereer JSON-LD voor ``doc_id`` op basis van de embedder-DB.

    Wordt door de Qt-frontend gebruikt om de preview te tekenen (title,
    description, hasPart-secties). De shape is identiek aan wat de oude
    ``kennisbank_latest/`` JSON-LD bestanden bevatten, dus de Qt-UI hoeft niet
    aangepast te worden.
    """

    if not doc_id:
        raise FileNotFoundError("Document id ontbreekt")

    normalized = doc_id.strip()
    if normalized.lower().startswith("doc:"):
        normalized = normalized[4:]

    document = models.get_document_by_doc_id(normalized)
    if document is None:
        raise FileNotFoundError(f"Document {doc_id} niet gevonden")

    sections = models.list_sections(document["id"])
    chunks_by_section: dict[int, list[dict]] = {}
    for section in sections:
        section["chunks"] = models.list_chunks_for_section(section["id"])
        chunks_by_section[section["id"]] = section["chunks"]

    return jsonld.serialize_document(
        document,
        sections=sections,
        chunks_by_section_id=chunks_by_section,
        include_sections=True,
        include_chunks=False,
    )
