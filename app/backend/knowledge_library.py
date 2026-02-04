from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from .kennisbank_sync import (
    KENNISBANK_REPO_DIR,
    KNOWLEDGE_BASE_DIRNAME,
    KNOWLEDGE_SQLITE_CACHE,
)


def _knowledge_base_root() -> Path:
    return KENNISBANK_REPO_DIR / KNOWLEDGE_BASE_DIRNAME


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _strip_doc_prefix(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip()
    if value.startswith("doc:"):
        return value[4:]
    return value


def _load_sqlite_documents() -> List[Dict[str, Any]]:
    if not KNOWLEDGE_SQLITE_CACHE.exists():
        return []

    conn = sqlite3.connect(str(KNOWLEDGE_SQLITE_CACHE))
    conn.row_factory = sqlite3.Row
    try:
        doc_rows = conn.execute(
            """
            SELECT doc_id, title, category, version, content_date, metadata
            FROM documents
            ORDER BY COALESCE(category, ''), title
            """
        ).fetchall()
        chunk_rows = conn.execute(
            "SELECT doc_id, COUNT(*) as chunk_count FROM chunks GROUP BY doc_id"
        ).fetchall()
    finally:
        conn.close()

    chunk_map = {row["doc_id"]: int(row["chunk_count"] or 0) for row in chunk_rows}
    documents: List[Dict[str, Any]] = []
    for row in doc_rows:
        metadata = {}
        raw_meta = row["metadata"]
        if raw_meta:
            try:
                metadata = json.loads(raw_meta)
            except json.JSONDecodeError:
                metadata = {}
        documents.append(
            {
                "doc_id": row["doc_id"],
                "title": row["title"],
                "category": row["category"],
                "version": row["version"],
                "content_date": row["content_date"],
                "chunk_count": chunk_map.get(row["doc_id"], 0),
                "priority": metadata.get("priority"),
                "source_url": metadata.get("source_url"),
                "description": metadata.get("description"),
            }
        )
    return documents


def _load_document_relations() -> Dict[str, List[Dict[str, Any]]]:
    relations_dir = _knowledge_base_root() / "relations"
    rel_file = relations_dir / "documents.json"
    if not rel_file.exists():
        return {}

    try:
        data = _read_json(rel_file)
    except json.JSONDecodeError:
        return {}

    relations: Dict[str, List[Dict[str, Any]]] = {}
    entries = data if isinstance(data, list) else data.get("relations", [])
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        source = _strip_doc_prefix(entry.get("source"))
        target = _strip_doc_prefix(entry.get("target"))
        if not source or not target:
            continue
        relations.setdefault(source, []).append(
            {
                "target": target,
                "relationship": entry.get("linkRelationship"),
                "description": entry.get("description"),
            }
        )
    return relations


def get_library_overview() -> Dict[str, Any]:
    documents = _load_sqlite_documents()
    relations = _load_document_relations()

    categories: Dict[str, Dict[str, Any]] = {}
    for doc in documents:
        cat = doc.get("category") or "uncategorized"
        bucket = categories.setdefault(
            cat,
            {
                "category": cat,
                "document_count": 0,
            },
        )
        bucket["document_count"] += 1

    return {
        "documents": documents,
        "categories": list(categories.values()),
        "relations": relations,
    }


def load_document_detail(doc_id: str) -> Dict[str, Any]:
    base = _knowledge_base_root() / "documents"
    if not doc_id:
        raise FileNotFoundError("Document id ontbreekt")
    if not base.exists():
        raise FileNotFoundError("Knowledge base documenten ontbreken")

    normalized = doc_id.strip().lower()
    for path in base.glob("*.json"):
        try:
            data = _read_json(path)
        except json.JSONDecodeError:
            continue
        identifier = _strip_doc_prefix(
            str(data.get("@id") or data.get("identifier") or "")
        ).lower()
        if identifier == normalized:
            return data

    raise FileNotFoundError(f"Document {doc_id} niet gevonden")
