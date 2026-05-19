"""SQLite-toegangslaag voor documents / sections / chunks.

Hand-rolled SQL met de stdlib ``sqlite3``; ORM-loos. Alle functies geven dicts
terug (geen dataclasses) — dat sluit aan op hoe de routes en JSON-LD
serializers ze gebruiken. JSON-velden (``metadata``) worden in/uit gehydrateerd.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from .db import get_connection


# ---- helpers ----------------------------------------------------------------


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _dump_json(value: Optional[dict]) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _load_json(value: Optional[str]) -> Optional[dict]:
    if value is None or value == "":
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _row_to_document(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["metadata"] = _load_json(data.get("metadata"))
    return data


def _row_to_section(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["metadata"] = _load_json(data.get("metadata"))
    return data


def _row_to_chunk(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["metadata"] = _load_json(data.get("metadata"))
    return data


# ---- documents --------------------------------------------------------------


_DOCUMENT_COLUMNS = (
    "id", "doc_id", "title", "description", "category", "status",
    "filename", "original_filename", "file_size", "mime_type",
    "version_tag", "content_date", "language",
    "priority", "position", "processing_stage", "processing_progress",
    "chunk_count", "parsed_at", "metadata",
    "created_at", "updated_at",
)


def doc_id_exists(doc_id: str, exclude_id: Optional[int] = None) -> bool:
    with get_connection() as conn:
        if exclude_id is None:
            row = conn.execute(
                "SELECT 1 FROM documents WHERE doc_id = ? LIMIT 1", (doc_id,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT 1 FROM documents WHERE doc_id = ? AND id != ? LIMIT 1",
                (doc_id, exclude_id),
            ).fetchone()
        return row is not None


def reserve_unique_doc_id(base: str) -> str:
    candidate = base or "document"
    if not doc_id_exists(candidate):
        return candidate
    counter = 1
    while True:
        candidate = f"{base}-{counter}"
        if not doc_id_exists(candidate):
            return candidate
        counter += 1


def create_document(payload: dict) -> dict:
    now = _utcnow_iso()
    columns = [
        "doc_id", "title", "description", "category", "status",
        "filename", "original_filename", "file_size", "mime_type",
        "version_tag", "content_date", "language",
        "priority", "position", "processing_stage", "processing_progress",
        "chunk_count", "parsed_at", "metadata",
        "created_at", "updated_at",
    ]
    values = [
        payload.get("doc_id"),
        payload.get("title"),
        payload.get("description"),
        payload.get("category"),
        payload.get("status", "uploaded"),
        payload.get("filename"),
        payload.get("original_filename"),
        payload.get("file_size"),
        payload.get("mime_type"),
        payload.get("version_tag"),
        payload.get("content_date"),
        payload.get("language"),
        int(payload.get("priority", 0)),
        int(payload.get("position", 0)),
        payload.get("processing_stage", "uploaded"),
        int(payload.get("processing_progress", 0)),
        int(payload.get("chunk_count", 0)),
        payload.get("parsed_at"),
        _dump_json(payload.get("metadata")),
        now,
        now,
    ]
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO documents ({', '.join(columns)}) VALUES ({placeholders})"
    with get_connection() as conn:
        cursor = conn.execute(sql, values)
        conn.commit()
        new_id = cursor.lastrowid
    return get_document(new_id)  # type: ignore[return-value]


def get_document(document_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
        return _row_to_document(row) if row else None


def get_document_by_doc_id(doc_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE doc_id = ?", (doc_id,)
        ).fetchone()
        return _row_to_document(row) if row else None


def list_documents(
    *,
    only_status: Optional[str] = None,
    order: str = "position, created_at DESC",
) -> list[dict]:
    sql = "SELECT * FROM documents"
    params: list[Any] = []
    if only_status is not None:
        sql += " WHERE status = ?"
        params.append(only_status)
    sql += f" ORDER BY {order}"
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_document(r) for r in rows]


def update_document(document_id: int, fields: dict) -> Optional[dict]:
    if not fields:
        return get_document(document_id)

    payload = dict(fields)
    if "metadata" in payload:
        payload["metadata"] = _dump_json(payload["metadata"])
    payload["updated_at"] = _utcnow_iso()

    columns = list(payload.keys())
    assignments = ", ".join(f"{col} = ?" for col in columns)
    values = [payload[col] for col in columns] + [document_id]
    sql = f"UPDATE documents SET {assignments} WHERE id = ?"

    with get_connection() as conn:
        conn.execute(sql, values)
        conn.commit()
    return get_document(document_id)


def update_document_metadata(document_id: int, patch: dict) -> Optional[dict]:
    """Merge ``patch`` into the document's metadata JSON (shallow)."""

    document = get_document(document_id)
    if not document:
        return None
    existing = document.get("metadata") or {}
    if not isinstance(existing, dict):
        existing = {}
    existing.update(patch)
    return update_document(document_id, {"metadata": existing})


def delete_document(document_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()


# ---- sections ---------------------------------------------------------------


def list_sections(document_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM document_sections WHERE document_id = ? ORDER BY order_index",
            (document_id,),
        ).fetchall()
        return [_row_to_section(r) for r in rows]


def get_section(section_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM document_sections WHERE id = ?", (section_id,)
        ).fetchone()
        return _row_to_section(row) if row else None


def create_section(payload: dict) -> dict:
    now = _utcnow_iso()
    sql = (
        "INSERT INTO document_sections "
        "(document_id, title, slug, order_index, text, metadata, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
    values = (
        payload["document_id"],
        payload["title"],
        payload["slug"],
        int(payload.get("order_index", 0)),
        payload.get("text", ""),
        _dump_json(payload.get("metadata")),
        now,
        now,
    )
    with get_connection() as conn:
        cursor = conn.execute(sql, values)
        conn.commit()
        return get_section(cursor.lastrowid) or {}


def update_section(section_id: int, fields: dict) -> Optional[dict]:
    if not fields:
        return get_section(section_id)

    payload = dict(fields)
    if "metadata" in payload:
        payload["metadata"] = _dump_json(payload["metadata"])
    payload["updated_at"] = _utcnow_iso()

    columns = list(payload.keys())
    assignments = ", ".join(f"{col} = ?" for col in columns)
    values = [payload[col] for col in columns] + [section_id]
    sql = f"UPDATE document_sections SET {assignments} WHERE id = ?"

    with get_connection() as conn:
        conn.execute(sql, values)
        conn.commit()
    return get_section(section_id)


def delete_sections_for_document(document_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM document_sections WHERE document_id = ?",
            (document_id,),
        )
        conn.commit()


# ---- chunks -----------------------------------------------------------------


def list_chunks(document_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM document_chunks WHERE document_id = ? ORDER BY chunk_index",
            (document_id,),
        ).fetchall()
        return [_row_to_chunk(r) for r in rows]


def list_chunks_for_section(section_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM document_chunks WHERE section_id = ? ORDER BY chunk_index",
            (section_id,),
        ).fetchall()
        return [_row_to_chunk(r) for r in rows]


def list_chunks_for_documents(document_ids: Iterable[int]) -> list[dict]:
    ids = list(document_ids)
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    sql = (
        f"SELECT * FROM document_chunks WHERE document_id IN ({placeholders}) "
        f"ORDER BY document_id, chunk_index"
    )
    with get_connection() as conn:
        rows = conn.execute(sql, ids).fetchall()
        return [_row_to_chunk(r) for r in rows]


def create_chunk(payload: dict) -> dict:
    now = _utcnow_iso()
    sql = (
        "INSERT INTO document_chunks "
        "(document_id, section_id, chunk_id, chunk_index, text, token_count, "
        "content_hash, last_synced_hash, metadata, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    values = (
        payload["document_id"],
        payload.get("section_id"),
        payload["chunk_id"],
        int(payload["chunk_index"]),
        payload["text"],
        payload.get("token_count"),
        payload["content_hash"],
        payload.get("last_synced_hash"),
        _dump_json(payload.get("metadata")),
        now,
        now,
    )
    with get_connection() as conn:
        cursor = conn.execute(sql, values)
        conn.commit()
        new_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM document_chunks WHERE id = ?", (new_id,)
        ).fetchone()
        return _row_to_chunk(row) if row else {}


def delete_chunks_for_document(document_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM document_chunks WHERE document_id = ?",
            (document_id,),
        )
        conn.commit()


def mark_chunks_synced(chunk_ids: Iterable[str]) -> None:
    """Zet ``last_synced_hash`` op de huidige ``content_hash`` voor de gegeven chunks."""

    ids = list(chunk_ids)
    if not ids:
        return
    placeholders = ",".join("?" for _ in ids)
    sql = (
        f"UPDATE document_chunks SET last_synced_hash = content_hash, "
        f"updated_at = ? WHERE chunk_id IN ({placeholders})"
    )
    params: list[Any] = [_utcnow_iso()] + ids
    with get_connection() as conn:
        conn.execute(sql, params)
        conn.commit()


# ---- counts -----------------------------------------------------------------


def count_documents(status: Optional[str] = None) -> int:
    sql = "SELECT COUNT(*) FROM documents"
    params: list[Any] = []
    if status is not None:
        sql += " WHERE status = ?"
        params.append(status)
    with get_connection() as conn:
        row = conn.execute(sql, params).fetchone()
        return int(row[0]) if row else 0


def count_sections() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM document_sections").fetchone()
        return int(row[0]) if row else 0


def count_chunks() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()
        return int(row[0]) if row else 0


def categories_with_counts() -> dict[str, int]:
    sql = (
        "SELECT category, COUNT(*) FROM documents "
        "WHERE category IS NOT NULL AND category != '' "
        "GROUP BY category"
    )
    with get_connection() as conn:
        rows = conn.execute(sql).fetchall()
        return {row[0]: int(row[1]) for row in rows}


def versions_with_counts() -> list[dict]:
    sql = (
        "SELECT version_tag, COUNT(*) AS document_count FROM documents "
        "WHERE version_tag IS NOT NULL AND version_tag != '' "
        "GROUP BY version_tag ORDER BY version_tag DESC"
    )
    with get_connection() as conn:
        rows = conn.execute(sql).fetchall()
        return [
            {"version_tag": row[0], "document_count": int(row[1])} for row in rows
        ]


def recent_documents(limit: int = 5) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, doc_id, title, status, updated_at FROM documents "
            "ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---- bulk operations for sync ----------------------------------------------


def chunks_needing_sync() -> list[dict]:
    """Chunks waarvan ``content_hash`` afwijkt van ``last_synced_hash``."""

    sql = (
        "SELECT * FROM document_chunks "
        "WHERE last_synced_hash IS NULL OR last_synced_hash != content_hash "
        "ORDER BY document_id, chunk_index"
    )
    with get_connection() as conn:
        rows = conn.execute(sql).fetchall()
        return [_row_to_chunk(r) for r in rows]


def all_chunk_ids() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT chunk_id FROM document_chunks"
        ).fetchall()
        return [row[0] for row in rows]
