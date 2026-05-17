"""FastAPI-router voor de embedder.

Wordt gemount onder ``/embedder/api/v1`` door ``app/backend/main.py``. Houdt
exact dezelfde paden + JSON-shapes aan als de oude Laravel-routes zodat de
Nuxt-SPA ongewijzigd blijft werken.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from pydantic import BaseModel, Field

from app.backend.auth_tokens import TokenRecord
from app.backend.settings import settings

from . import jsonld, models, processing
from .auth import (
    admin_user_payload,
    issue_token,
    require_embedder_user,
    revoke_token,
    verify_credentials,
)
from .parsing.parsed import slugify


router = APIRouter()
logger = logging.getLogger(__name__)


# ---- constants ---------------------------------------------------------------

_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
_ALLOWED_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/csv",
    "application/csv",
    "text/xml",
    "application/xml",
    "text/plain",
    "text/markdown",
}


# ---- request schemas --------------------------------------------------------


class LoginRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    category: Optional[str] = Field(default=None, max_length=100)
    version_tag: Optional[str] = Field(default=None, max_length=50)
    content_date: Optional[str] = None
    language: Optional[str] = Field(default=None, max_length=10)
    description: Optional[str] = Field(default=None, max_length=1000)


class LibraryDocumentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    category: Optional[str] = Field(default=None, max_length=100)
    version_tag: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None, max_length=1000)


class SectionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    text: Optional[str] = None
    metadata: Optional[dict] = None


class MappingRequest(BaseModel):
    mapping: dict = Field(default_factory=dict)


class PriorityUpdate(BaseModel):
    priority: int = Field(ge=0)


class PriorityItem(BaseModel):
    id: int
    priority: int = Field(ge=0)


class PriorityBulkRequest(BaseModel):
    priorities: list[PriorityItem]


class MessageResponse(BaseModel):
    message: str


# ---- helpers ----------------------------------------------------------------


def _upload_dir() -> Path:
    target = settings.embedder_upload_dir
    if target is None:
        target = Path(__file__).resolve().parents[3] / "devices_db" / "embedder_uploads"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _today_iso_date() -> str:
    return date.today().isoformat()


def _coerce_content_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def _hydrate_document(document: dict, *, sections: bool = False, include_chunks: bool = False) -> dict:
    """Voeg de velden toe die het SPA-type verwacht (user_id, source_url, json_ld)."""

    payload = dict(document)
    payload["user_id"] = 1
    payload.setdefault("source_url", None)
    payload.setdefault("json_ld", None)
    if sections:
        section_rows = models.list_sections(document["id"])
        if include_chunks:
            for section in section_rows:
                section["chunks"] = models.list_chunks_for_section(section["id"])
        payload["sections"] = section_rows
    return payload


def _hydrate_section(section: dict, *, with_chunks: bool = False) -> dict:
    payload = dict(section)
    if with_chunks:
        payload["chunks"] = models.list_chunks_for_section(section["id"])
    return payload


def _document_or_404(document_id: int) -> dict:
    document = models.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document niet gevonden")
    return document


def _section_or_404(section_id: int) -> dict:
    section = models.get_section(section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Sectie niet gevonden")
    return section


# ---- auth -------------------------------------------------------------------


@router.post("/login")
def login(body: LoginRequest) -> dict:
    if not verify_credentials(body.email, body.password):
        raise HTTPException(status_code=422, detail="Deze inloggegevens kloppen niet.")
    record = issue_token()
    return {"token": record.token, "user": admin_user_payload()}


@router.post("/logout", response_model=MessageResponse)
def logout(record: TokenRecord = Depends(require_embedder_user)) -> dict:
    revoke_token(record.token)
    return {"message": "Logged out successfully"}


@router.get("/me")
def me(_: TokenRecord = Depends(require_embedder_user)) -> dict:
    return admin_user_payload()


# ---- documents --------------------------------------------------------------


@router.get("/documents")
def list_documents(_: TokenRecord = Depends(require_embedder_user)) -> dict:
    docs = models.list_documents()
    return {"documents": [_hydrate_document(doc) for doc in docs]}


@router.post("/documents", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    category: Optional[str] = Form(default=None),
    version_tag: Optional[str] = Form(default=None),
    content_date: Optional[str] = Form(default=None),
    language: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    _: TokenRecord = Depends(require_embedder_user),
) -> dict:
    mime_type = file.content_type or ""
    if mime_type not in _ALLOWED_MIMES:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Bestandstype niet ondersteund",
                "allowed_types": ["PDF", "DOCX", "CSV", "XML", "TXT", "MD"],
            },
        )

    raw = await file.read()
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Bestand groter dan 50MB")

    original_name = file.filename or "document"
    extension = Path(original_name).suffix.lstrip(".").lower() or "bin"
    stored_filename = f"{uuid.uuid4().hex}_{int(time.time())}.{extension}"
    target_path = _upload_dir() / stored_filename
    target_path.write_bytes(raw)

    title_value = (title or Path(original_name).stem).strip() or Path(original_name).stem
    base_doc_id = slugify(title_value, fallback="document")
    doc_id = models.reserve_unique_doc_id(base_doc_id)

    document_payload = {
        "doc_id": doc_id,
        "title": title_value,
        "description": (description or None),
        "category": (category or None),
        "filename": stored_filename,
        "original_filename": original_name,
        "file_size": len(raw),
        "mime_type": mime_type,
        "version_tag": (version_tag or None),
        "content_date": _coerce_content_date(content_date) or _today_iso_date(),
        "language": (language or None),
        "status": "uploaded",
        "processing_stage": processing.STAGE_UPLOADED,
        "processing_progress": 0,
    }
    document = models.create_document(document_payload)

    needs_mapping = processing.requires_mapping(document)
    mappable_fields: dict[str, str] = {}
    if needs_mapping:
        try:
            mappable_fields = processing.get_mappable_fields(document, _upload_dir())
        except Exception:
            logger.exception("Kon mappable fields niet bepalen voor document %s", document["id"])

    return {
        "document": _hydrate_document(document),
        "requires_mapping": needs_mapping,
        "mappable_fields": mappable_fields,
    }


@router.get("/documents/{document_id}")
def get_document(
    document_id: int, _: TokenRecord = Depends(require_embedder_user)
) -> dict:
    document = _document_or_404(document_id)
    return {"document": _hydrate_document(document, sections=True, include_chunks=True)}


@router.patch("/documents/{document_id}")
def update_document(
    document_id: int,
    body: DocumentUpdate,
    _: TokenRecord = Depends(require_embedder_user),
) -> dict:
    _document_or_404(document_id)
    fields = body.model_dump(exclude_unset=True)
    if "content_date" in fields and fields["content_date"]:
        coerced = _coerce_content_date(fields["content_date"])
        if coerced is None:
            raise HTTPException(status_code=422, detail="Ongeldige content_date")
        fields["content_date"] = coerced
    updated = models.update_document(document_id, fields)
    return {"document": _hydrate_document(updated or {})}


@router.post("/documents/{document_id}/mapping")
def save_mapping(
    document_id: int,
    body: MappingRequest,
    _: TokenRecord = Depends(require_embedder_user),
) -> dict:
    _document_or_404(document_id)
    updated = models.update_document_metadata(document_id, {"mapping": body.mapping})
    return {"document": _hydrate_document(updated or {})}


@router.post("/documents/{document_id}/process")
def process_document_route(
    document_id: int, _: TokenRecord = Depends(require_embedder_user)
) -> dict:
    document = _document_or_404(document_id)

    if document.get("status") == "formatted":
        return {"message": "Document is al verwerkt", "document": _hydrate_document(document)}

    stage = document.get("processing_stage")
    if processing.is_processing_stage(stage):
        return {"message": "Document wordt al verwerkt", "document": _hydrate_document(document)}

    options: dict[str, Any] = {}
    metadata = document.get("metadata") or {}
    if isinstance(metadata, dict) and metadata.get("mapping"):
        options["mapping"] = metadata["mapping"]

    models.update_document(
        document_id,
        {
            "status": "processing",
            "processing_stage": processing.STAGE_QUEUED,
            "processing_progress": 5,
        },
    )

    try:
        updated = processing.process_document(document_id, options, _upload_dir())
    except Exception as exc:
        logger.exception("Verwerking faalde voor document %s", document_id)
        raise HTTPException(
            status_code=500,
            detail={"message": "Verwerking mislukt", "error": str(exc)},
        )

    return {
        "message": "Document succesvol verwerkt",
        "document": _hydrate_document(updated),
    }


@router.get("/documents/{document_id}/status")
def document_status_route(
    document_id: int, _: TokenRecord = Depends(require_embedder_user)
) -> dict:
    document = _document_or_404(document_id)
    metadata = document.get("metadata") or {}
    error_msg = metadata.get("error") if isinstance(metadata, dict) else None
    stage = document.get("processing_stage")
    return {
        "status": document.get("status"),
        "processing_stage": stage,
        "processing_stage_label": processing.stage_label(stage),
        "processing_progress": document.get("processing_progress", 0),
        "is_processing": processing.is_processing_stage(stage),
        "is_ready": processing.is_ready_stage(stage),
        "has_failed": processing.is_failed_stage(stage),
        "error": error_msg,
    }


@router.delete("/documents/{document_id}")
def delete_document_route(
    document_id: int, _: TokenRecord = Depends(require_embedder_user)
) -> dict:
    document = _document_or_404(document_id)
    processing.delete_upload_for(document, _upload_dir())
    models.delete_document(document_id)
    return {"message": "Document verwijderd"}


# ---- library ----------------------------------------------------------------


@router.get("/library/tree")
def library_tree(_: TokenRecord = Depends(require_embedder_user)) -> dict:
    docs = models.list_documents()
    tree = []
    for doc in docs:
        sections = models.list_sections(doc["id"])
        tree.append(
            {
                "id": doc["id"],
                "doc_id": doc["doc_id"],
                "title": doc["title"],
                "category": doc.get("category"),
                "status": doc.get("status"),
                "position": doc.get("position", 0),
                "type": "document",
                "children": [
                    {
                        "id": section["id"],
                        "title": section["title"],
                        "slug": section["slug"],
                        "type": "section",
                        "document_id": doc["id"],
                    }
                    for section in sections
                ],
            }
        )
    return {"tree": tree}


@router.get("/library/search")
def library_search(
    query: str = "",
    category: Optional[str] = None,
    _: TokenRecord = Depends(require_embedder_user),
) -> dict:
    if not query or len(query) < 2 or len(query) > 100:
        raise HTTPException(status_code=422, detail="Query moet 2-100 tekens zijn")

    pattern = f"%{query}%"
    sql = (
        "SELECT s.id, s.document_id, s.title, s.slug, "
        "d.doc_id, d.title AS document_title, d.category "
        "FROM document_sections s JOIN documents d ON s.document_id = d.id "
        "WHERE (s.title LIKE ? OR s.text LIKE ?)"
    )
    params: list[Any] = [pattern, pattern]
    if category:
        sql += " AND d.category = ?"
        params.append(category)
    sql += " LIMIT 50"

    from .db import get_connection
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        sections = [
            {
                "id": row["id"],
                "document_id": row["document_id"],
                "title": row["title"],
                "slug": row["slug"],
                "document": {
                    "id": row["document_id"],
                    "doc_id": row["doc_id"],
                    "title": row["document_title"],
                    "category": row["category"],
                },
            }
            for row in rows
        ]
    return {"sections": sections}


@router.get("/library/documents/{document_id}")
def library_document(
    document_id: int, _: TokenRecord = Depends(require_embedder_user)
) -> dict:
    document = _document_or_404(document_id)
    sections = models.list_sections(document_id)
    chunks_map: dict[int, list[dict]] = {}
    for section in sections:
        section["chunks"] = models.list_chunks_for_section(section["id"])
        chunks_map[section["id"]] = section["chunks"]
    json_ld = jsonld.serialize_document(
        document, sections=sections, chunks_by_section_id=chunks_map, include_chunks=False
    )
    hydrated = _hydrate_document(document)
    hydrated["sections"] = sections
    hydrated["json_ld"] = json_ld
    return {"document": hydrated, "json_ld": json_ld}


@router.patch("/library/documents/{document_id}")
def library_update_document(
    document_id: int,
    body: LibraryDocumentUpdate,
    _: TokenRecord = Depends(require_embedder_user),
) -> dict:
    _document_or_404(document_id)
    fields = body.model_dump(exclude_unset=True)
    updated = models.update_document(document_id, fields)
    return {"document": _hydrate_document(updated or {})}


@router.get("/library/sections/{section_id}")
def library_section(
    section_id: int, _: TokenRecord = Depends(require_embedder_user)
) -> dict:
    section = _section_or_404(section_id)
    document = _document_or_404(section["document_id"])
    chunks = models.list_chunks_for_section(section_id)
    section_with_chunks = dict(section)
    section_with_chunks["chunks"] = chunks
    json_ld = jsonld.serialize_section(
        section, document, chunks=chunks, include_chunks=True
    )
    return {"section": section_with_chunks, "json_ld": json_ld}


@router.patch("/library/sections/{section_id}")
def library_update_section(
    section_id: int,
    body: SectionUpdate,
    _: TokenRecord = Depends(require_embedder_user),
) -> dict:
    section = _section_or_404(section_id)
    fields = body.model_dump(exclude_unset=True)
    updated = models.update_section(section_id, fields)
    if updated and (fields.get("text") is not None):
        _rehash_chunks_for_section(updated)
    return {"section": _hydrate_section(updated or section)}


def _rehash_chunks_for_section(section: dict) -> None:
    """Als de section-tekst is gewijzigd, markeren we de chunks van die sectie
    als dirty zodat de eerstvolgende sync ze opnieuw embedt. We laten de
    chunk-text zelf intact — die wordt pas opnieuw uitgerekend bij de volgende
    ``/documents/{id}/process`` call."""

    chunks = models.list_chunks_for_section(section["id"])
    if not chunks:
        return
    # Forceer re-sync door last_synced_hash leeg te zetten via een no-op update
    # die de updated_at bumpt; eenvoudige aanpak houdt dit kort.
    from .db import get_connection
    with get_connection() as conn:
        conn.execute(
            "UPDATE document_chunks SET last_synced_hash = NULL WHERE section_id = ?",
            (section["id"],),
        )
        conn.commit()


# ---- priorities -------------------------------------------------------------


@router.get("/priorities")
def priorities_index(_: TokenRecord = Depends(require_embedder_user)) -> dict:
    docs = models.list_documents(only_status="formatted", order="category, priority, title")
    grouped: dict[str, list[dict]] = {}
    for doc in docs:
        cat = doc.get("category") or "Geen categorie"
        grouped.setdefault(cat, []).append(_hydrate_document(doc))
    return {"categories": grouped}


@router.patch("/priorities/{document_id}")
def priorities_update(
    document_id: int,
    body: PriorityUpdate,
    _: TokenRecord = Depends(require_embedder_user),
) -> dict:
    _document_or_404(document_id)
    updated = models.update_document(document_id, {"priority": body.priority})
    return {"document": _hydrate_document(updated or {})}


@router.post("/priorities/bulk")
def priorities_bulk(
    body: PriorityBulkRequest, _: TokenRecord = Depends(require_embedder_user)
) -> dict:
    for item in body.priorities:
        if models.get_document(item.id) is None:
            raise HTTPException(status_code=422, detail=f"Document {item.id} bestaat niet")
    for item in body.priorities:
        models.update_document(item.id, {"priority": item.priority})
    return {"message": "Prioriteiten bijgewerkt"}


# ---- insights (alleen read-only deel) ---------------------------------------


@router.get("/insights/stats")
def insights_stats(_: TokenRecord = Depends(require_embedder_user)) -> dict:
    total_documents = models.count_documents()
    processed_documents = models.count_documents(status="formatted")
    failed_documents = models.count_documents(status="failed")
    processing_documents = models.count_documents(status="processing")
    total_sections = models.count_sections()
    total_chunks = models.count_chunks()

    # estimated_words: som van word_count-velden in chunk-metadata (anders nul)
    total_words = 0
    for doc in models.list_documents():
        for chunk in models.list_chunks(doc["id"]):
            metadata = chunk.get("metadata") or {}
            if isinstance(metadata, dict) and metadata.get("word_count"):
                total_words += int(metadata["word_count"])

    categories = models.categories_with_counts()
    recent = [_hydrate_document(doc) for doc in models.recent_documents()]

    return {
        "stats": {
            "total_documents": total_documents,
            "processed_documents": processed_documents,
            "failed_documents": failed_documents,
            "processing_documents": processing_documents,
            "total_sections": total_sections,
            "total_chunks": total_chunks,
            "estimated_words": total_words,
        },
        "categories": categories,
        "recent_documents": recent,
    }


@router.get("/insights/categories")
def insights_categories(_: TokenRecord = Depends(require_embedder_user)) -> dict:
    from .db import get_connection

    sql = (
        "SELECT category, COUNT(*) AS document_count "
        "FROM documents "
        "WHERE category IS NOT NULL AND category != '' AND status = 'formatted' "
        "GROUP BY category"
    )
    results: list[dict] = []
    with get_connection() as conn:
        category_rows = conn.execute(sql).fetchall()
        for row in category_rows:
            cat_docs = conn.execute(
                "SELECT id FROM documents WHERE category = ?",
                (row["category"],),
            ).fetchall()
            doc_ids = [r["id"] for r in cat_docs]
            section_count = 0
            chunk_count = 0
            if doc_ids:
                placeholders = ",".join("?" for _ in doc_ids)
                section_count = (
                    conn.execute(
                        f"SELECT COUNT(*) FROM document_sections WHERE document_id IN ({placeholders})",
                        doc_ids,
                    ).fetchone()[0]
                )
                chunk_count = (
                    conn.execute(
                        f"SELECT COUNT(*) FROM document_chunks WHERE document_id IN ({placeholders})",
                        doc_ids,
                    ).fetchone()[0]
                )
            results.append(
                {
                    "category": row["category"],
                    "document_count": int(row["document_count"]),
                    "section_count": int(section_count),
                    "chunk_count": int(chunk_count),
                }
            )
    return {"categories": results}


@router.get("/insights/versions")
def insights_versions(_: TokenRecord = Depends(require_embedder_user)) -> dict:
    return {"versions": models.versions_with_counts()}


# ---- kennisbank sync (in-process) -------------------------------------------


@router.post("/kennisbank/push")
def kennisbank_push(_: TokenRecord = Depends(require_embedder_user)) -> dict:
    from . import sync as embedder_sync

    try:
        result = embedder_sync.sync_changed_chunks_to_qdrant()
    except Exception as exc:
        logger.exception("Sync naar device mislukt")
        raise HTTPException(
            status_code=500,
            detail={"message": "Synchronisatie naar device mislukt.", "error": str(exc)},
        ) from exc

    return {
        "message": "Kennisbank gesynchroniseerd met device.",
        "last_pushed_at": datetime.now(timezone.utc).isoformat(),
        "device_response": result,
    }
