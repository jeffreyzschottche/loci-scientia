"""Document-processing orchestrator.

Port van ``DocumentProcessingService`` (Laravel). Voert per document de fasen
parse → chunk → JSON-LD-flag uit, met live stage/progress-tracking in de DB.
Synchroon (geen queue worker) — single-tenant device, een blocking POST is
prima.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from . import models
from .chunking import (
    chunk_text,
    estimate_token_count,
    hash_chunk,
    make_chunk_id,
)
from .parsing import get_parser_for_mime, normalize_text  # noqa: F401  (re-export)
from .parsing.parsed import ParsedDocument


logger = logging.getLogger(__name__)


# ---- ProcessingStage equivalent ---------------------------------------------

STAGE_UPLOADED = "uploaded"
STAGE_QUEUED = "queued"
STAGE_PARSING = "parsing"
STAGE_CHUNKING = "chunking"
STAGE_GENERATING_JSONLD = "generating_jsonld"
STAGE_READY = "ready"
STAGE_FAILED = "failed"


_STAGE_LABEL = {
    STAGE_UPLOADED: "Geüpload",
    STAGE_QUEUED: "In wachtrij",
    STAGE_PARSING: "Tekst extraheren",
    STAGE_CHUNKING: "Opdelen in chunks",
    STAGE_GENERATING_JSONLD: "JSON-LD genereren",
    STAGE_READY: "Klaar",
    STAGE_FAILED: "Mislukt",
}


_PROCESSING_STAGES = {
    STAGE_QUEUED,
    STAGE_PARSING,
    STAGE_CHUNKING,
    STAGE_GENERATING_JSONLD,
}


def stage_label(stage: Optional[str]) -> Optional[str]:
    if stage is None:
        return None
    return _STAGE_LABEL.get(stage, stage)


def is_processing_stage(stage: Optional[str]) -> bool:
    return stage in _PROCESSING_STAGES


def is_ready_stage(stage: Optional[str]) -> bool:
    return stage == STAGE_READY


def is_failed_stage(stage: Optional[str]) -> bool:
    return stage == STAGE_FAILED


# ---- helpers ----------------------------------------------------------------


def _update_stage(document_id: int, stage: str, progress: int) -> None:
    models.update_document(
        document_id,
        {"processing_stage": stage, "processing_progress": progress},
    )


def _mark_failed(document_id: int, error_message: str) -> None:
    document = models.get_document(document_id)
    metadata = (document.get("metadata") if document else None) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    metadata.update({"error": error_message, "failed_at": _isoformat_now()})
    models.update_document(
        document_id,
        {
            "status": "failed",
            "processing_stage": STAGE_FAILED,
            "processing_progress": 0,
            "metadata": metadata,
        },
    )


def _isoformat_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _upload_root(upload_dir: Optional[Path]) -> Path:
    if upload_dir is None:
        upload_dir = Path(__file__).resolve().parents[3] / "devices_db" / "embedder_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def upload_path_for(filename: str, upload_dir: Optional[Path] = None) -> Path:
    return _upload_root(upload_dir) / filename


def delete_upload_for(document: dict, upload_dir: Optional[Path] = None) -> None:
    stored = document.get("filename")
    if not stored:
        return
    path = upload_path_for(stored, upload_dir)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        logger.warning("Kon upload niet verwijderen %s: %s", path, exc)


# ---- mapping helpers --------------------------------------------------------


def get_mappable_fields(document: dict, upload_dir: Optional[Path] = None) -> dict[str, str]:
    parser = get_parser_for_mime(document.get("mime_type") or "")
    path = upload_path_for(document["filename"], upload_dir)
    try:
        return parser.get_mappable_fields(str(path))
    except Exception:
        logger.exception("Kon mappable fields niet bepalen voor document %s", document.get("id"))
        return {}


def requires_mapping(document: dict) -> bool:
    try:
        parser = get_parser_for_mime(document.get("mime_type") or "")
    except Exception:
        return False
    return bool(parser.requires_mapping())


# ---- main orchestrator -----------------------------------------------------


def process_document(
    document_id: int,
    options: Optional[dict] = None,
    upload_dir: Optional[Path] = None,
) -> dict:
    """Voer parsing + chunking uit voor het opgegeven document.

    Werkt de DB-rij bij met sectie/chunk-rows en de status/stage-velden.
    Returnt de geüpdate document-dict; gooit bij parsing/IO-fouten en markeert
    de status dan als ``failed`` voordat de exception doorgereikt wordt.
    """

    options = options or {}
    document = models.get_document(document_id)
    if document is None:
        raise FileNotFoundError(f"Document {document_id} niet gevonden")

    try:
        _update_stage(document_id, STAGE_PARSING, 30)
        parsed = _parse(document, options, upload_dir)

        _update_stage(document_id, STAGE_CHUNKING, 60)
        chunk_total = _store_sections_and_chunks(document, parsed)

        _update_stage(document_id, STAGE_GENERATING_JSONLD, 85)
        merged_metadata = _merge_metadata(
            document.get("metadata"),
            parsed.metadata,
            {
                "embedding": _embedding_metadata(),
                "last_embedded_at": _isoformat_now(),
            },
        )

        models.update_document(
            document_id,
            {
                "status": "formatted",
                "processing_stage": STAGE_READY,
                "processing_progress": 100,
                "parsed_at": _isoformat_now(),
                "chunk_count": chunk_total,
                "metadata": merged_metadata,
            },
        )
        logger.info("Document %s succesvol verwerkt (%d chunks)", document_id, chunk_total)
        return models.get_document(document_id) or {}
    except Exception as exc:
        logger.exception("Document %s verwerking mislukt", document_id)
        _mark_failed(document_id, str(exc))
        raise


# ---- internals --------------------------------------------------------------


def _parse(
    document: dict, options: dict, upload_dir: Optional[Path]
) -> ParsedDocument:
    mime_type = document.get("mime_type") or ""
    parser = get_parser_for_mime(mime_type)
    path = upload_path_for(document["filename"], upload_dir)
    if not path.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {path}")

    parse_options = {
        "doc_id": document["doc_id"],
        "title": document["title"],
        "description": document.get("description"),
        "category": document.get("category"),
        **options,
    }
    return parser.parse(str(path), parse_options)


def _store_sections_and_chunks(document: dict, parsed: ParsedDocument) -> int:
    document_id = document["id"]
    doc_id = document["doc_id"]
    content_date = document.get("content_date")

    # Reset bestaande sections/chunks zoals de Laravel-versie doet.
    models.delete_chunks_for_document(document_id)
    models.delete_sections_for_document(document_id)

    total_chunks = 0
    section_total = len(parsed.sections) or 1

    for index, section_data in enumerate(parsed.sections):
        section_text = section_data.get("text", "")
        section = models.create_section(
            {
                "document_id": document_id,
                "title": section_data.get("title", "Inhoud"),
                "slug": section_data.get("slug", f"sectie-{index + 1}"),
                "order_index": int(section_data.get("order_index", index)),
                "text": section_text,
                "metadata": section_data.get("metadata"),
            }
        )

        chunks = chunk_text(section_text)
        page_ranges = (section_data.get("metadata") or {}).get("page_ranges", [])

        for chunk_index_in_section, chunk in enumerate(chunks):
            token_count = chunk.token_count or estimate_token_count(chunk.text)
            pages = _map_chunk_to_pages(chunk.char_start, chunk.char_end, page_ranges)
            chunk_metadata: dict[str, Any] = {}
            if chunk.word_count:
                chunk_metadata["word_count"] = chunk.word_count
            if content_date:
                chunk_metadata["content_date"] = content_date
            chunk_metadata["embedding_model"] = _embedding_model_name()
            if pages:
                chunk_metadata["pages"] = pages

            chunk_id_value = make_chunk_id(
                doc_id, section["slug"], chunk_index_in_section
            )

            models.create_chunk(
                {
                    "document_id": document_id,
                    "section_id": section["id"],
                    "chunk_id": chunk_id_value,
                    "chunk_index": total_chunks,
                    "text": chunk.text,
                    "token_count": token_count,
                    "content_hash": hash_chunk(chunk.text),
                    "metadata": chunk_metadata or None,
                }
            )

            total_chunks += 1

        progress = 60 + int(((index + 1) / section_total) * 25)
        _update_stage(document_id, STAGE_CHUNKING, min(progress, 84))

    return total_chunks


def _map_chunk_to_pages(
    chunk_start: int, chunk_end: int, page_ranges: list[dict]
) -> list[int]:
    if not page_ranges:
        return []
    pages: list[int] = []
    for entry in page_ranges:
        start = int(entry.get("start", 0))
        end = int(entry.get("end", 0))
        if chunk_start < end and chunk_end > start:
            pages.append(int(entry["page"]))
    # uniek + volgorde behouden
    seen: set[int] = set()
    return [p for p in pages if not (p in seen or seen.add(p))]


def _merge_metadata(*sources: Optional[dict]) -> dict:
    merged: dict[str, Any] = {}
    for src in sources:
        if not src:
            continue
        if not isinstance(src, dict):
            continue
        for key, value in src.items():
            existing = merged.get(key)
            if isinstance(existing, dict) and isinstance(value, dict):
                merged[key] = {**existing, **value}
            else:
                merged[key] = value
    return merged


def _embedding_metadata() -> dict:
    return {
        "model": _embedding_model_name(),
        "vector_dimension": _int_env("EMBEDDING_VECTOR_DIMENSION", 768),
        "chunk_tokens": _int_env("EMBEDDING_CHUNK_TOKENS", 150),
        "chunk_overlap_tokens": _int_env("EMBEDDING_CHUNK_OVERLAP_TOKENS", 80),
    }


def _embedding_model_name() -> str:
    import os
    return (
        os.environ.get("EMBEDDING_MODEL")
        or os.environ.get("FASTEMBED_MODEL")
        or "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )


def _int_env(key: str, default: int) -> int:
    import os
    raw = (os.environ.get(key) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default
