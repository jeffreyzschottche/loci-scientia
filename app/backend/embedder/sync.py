"""In-process Qdrant-sync.

Vervangt het oude JSON-LD-via-ZIP push-pad. Werkt direct op de embedder
SQLite-tabellen:

1. Verzamel chunks waarvan ``last_synced_hash`` afwijkt van ``content_hash``
   (NULL = nooit gesynced).
2. Embed elk via :mod:`app.backend.rag.embedder`.
3. Scroll de bestaande Qdrant-collection om te bepalen welke chunks in Qdrant
   staan maar niet meer in de embedder-DB — die worden verwijderd.
4. Upsert nieuwe/gewijzigde chunks; payload-shape blijft compatibel met de
   bestaande RAG-routes (``apiAsk.py`` leest ``doc_id`` / ``text`` /
   ``document_title`` / ``pages`` etc uit de payload).
5. Markeer succesvol-gesyncede chunks met ``last_synced_hash = content_hash``.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from qdrant_client.models import Distance, PointStruct, VectorParams

from app.backend.kennisbank_sync import (
    KNOWLEDGE_COLLECTION,
    _chunk_id_to_qdrant_id,
    _knowledge_embedded_path,
    write_sync_state,
)
from app.backend.qdrant_utils import get_qdrant_client
from app.backend.rag.embedder import embed_text

from . import models


logger = logging.getLogger(__name__)


# ---- public API -------------------------------------------------------------


def sync_changed_chunks_to_qdrant() -> dict:
    pending = models.chunks_needing_sync()
    current_chunk_ids = set(models.all_chunk_ids())

    documents_by_id = {doc["id"]: doc for doc in models.list_documents()}
    sections_by_id = _load_sections_by_id(documents_by_id.keys())

    embedded: list[tuple[dict, list[float]]] = []
    failed = 0
    for chunk in pending:
        try:
            vector = list(embed_text(chunk["text"]).vector)
        except Exception as exc:  # pragma: no cover
            logger.exception("Embedding faalde voor chunk %s: %s", chunk.get("chunk_id"), exc)
            failed += 1
            continue
        embedded.append((chunk, vector))

    vector_size = len(embedded[0][1]) if embedded else _expected_vector_size()

    with get_qdrant_client(_knowledge_embedded_path()) as client:
        _ensure_collection(client, vector_size)
        existing_chunk_ids = _scroll_existing_chunk_ids(client)
        to_delete = existing_chunk_ids - current_chunk_ids

        if to_delete:
            try:
                qdrant_ids = [_chunk_id_to_qdrant_id(cid) for cid in to_delete]
                client.delete(
                    collection_name=KNOWLEDGE_COLLECTION,
                    points_selector=qdrant_ids,
                )
            except Exception as exc:
                logger.warning("Kon Qdrant-punten niet verwijderen: %s", exc)

        if embedded:
            points = [
                PointStruct(
                    id=_chunk_id_to_qdrant_id(chunk["chunk_id"]),
                    vector=vector,
                    payload=_build_payload(chunk, documents_by_id, sections_by_id),
                )
                for chunk, vector in embedded
            ]
            client.upsert(collection_name=KNOWLEDGE_COLLECTION, points=points)

        try:
            info = client.get_collection(KNOWLEDGE_COLLECTION)
            total_points = info.points_count or 0
        except Exception:
            total_points = -1

    if embedded:
        models.mark_chunks_synced([chunk["chunk_id"] for chunk, _ in embedded])

    result = {
        "collection": KNOWLEDGE_COLLECTION,
        "upserted": len(embedded),
        "deleted": len(to_delete),
        "failed": failed,
        "points": total_points,
        "vector_size": vector_size,
    }
    write_sync_state(result)
    return result


# ---- helpers ----------------------------------------------------------------


def _load_sections_by_id(document_ids: Iterable[int]) -> dict[int, dict]:
    sections: dict[int, dict] = {}
    for document_id in document_ids:
        for section in models.list_sections(document_id):
            sections[section["id"]] = section
    return sections


def _build_payload(
    chunk: dict,
    documents_by_id: dict[int, dict],
    sections_by_id: dict[int, dict],
) -> dict:
    document = documents_by_id.get(chunk["document_id"]) or {}
    section = sections_by_id.get(chunk.get("section_id")) if chunk.get("section_id") else None
    metadata = chunk.get("metadata") or {}

    return {
        "doc_id": document.get("doc_id"),
        "chunk_id": chunk["chunk_id"],
        "position": chunk.get("chunk_index"),
        "section": section["slug"] if section else None,
        "pages": (metadata.get("pages") if isinstance(metadata, dict) else None) or [],
        "text": chunk.get("text"),
        "metadata": metadata,
        "document_title": document.get("title") or document.get("doc_id"),
        "document_category": document.get("category"),
        "document_date": document.get("content_date"),
        "original_filename": document.get("original_filename"),
    }


def _ensure_collection(client, vector_size: int) -> None:
    """Maak/herschep collection als-ie ontbreekt of een afwijkende vector-size heeft."""

    try:
        info = client.get_collection(KNOWLEDGE_COLLECTION)
        vectors = info.config.params.vectors
        if isinstance(vectors, VectorParams):
            current = vectors.size
        elif isinstance(vectors, dict):
            first = next(iter(vectors.values()), None)
            current = first.size if isinstance(first, VectorParams) else None
        else:
            current = None
        if current != vector_size:
            logger.info(
                "Vector-size mismatch (%s vs %s), recreate kennisbank-collection",
                current,
                vector_size,
            )
            client.recreate_collection(
                collection_name=KNOWLEDGE_COLLECTION,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
    except Exception:
        client.recreate_collection(
            collection_name=KNOWLEDGE_COLLECTION,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def _scroll_existing_chunk_ids(client) -> set[str]:
    """Lees alle chunk_ids uit de payload van de Qdrant-collection."""

    chunk_ids: set[str] = set()
    next_offset: Optional[str] = None
    try:
        while True:
            points, next_offset = client.scroll(
                collection_name=KNOWLEDGE_COLLECTION,
                limit=512,
                with_payload=True,
                with_vectors=False,
                offset=next_offset,
            )
            for point in points:
                cid = (point.payload or {}).get("chunk_id")
                if cid:
                    chunk_ids.add(cid)
            if not next_offset:
                break
    except Exception as exc:
        # Collection bestaat nog niet — dan is de set leeg.
        logger.debug("Kon Qdrant niet scrollen (collectie bestaat mogelijk nog niet): %s", exc)
    return chunk_ids


def _expected_vector_size() -> int:
    """Fallback dimensie wanneer er geen chunks zijn — voor de eerste sync ooit."""

    import os
    raw = (os.environ.get("EMBEDDING_VECTOR_DIMENSION") or "").strip()
    try:
        value = int(raw)
        if value > 0:
            return value
    except ValueError:
        pass
    return 768
