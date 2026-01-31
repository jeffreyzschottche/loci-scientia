"""Synchroniseer de kennisbank repo en embed JSON-LD exports naar Qdrant + SQLite."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from qdrant_client.models import Distance, PointStruct, VectorParams

from .contacts_repo import QDRANT_LOCAL_DIR, _get_qdrant_client
from .rag.embedder import embed_text

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
KENNISBANK_REPO_DIR = _PROJECT_ROOT / "kennisbank_repo"
KNOWLEDGE_BASE_DIRNAME = "knowledge_base"
KNOWLEDGE_MODEL_FILE = "model.json"
KNOWLEDGE_COLLECTION = os.getenv("QDRANT_KNOWLEDGE_COLLECTION", "kennisbank")
KNOWLEDGE_SQLITE_CACHE = _PROJECT_ROOT / "kennisbank_cache.db"
SYNC_STATE_FILE = KENNISBANK_REPO_DIR / ".sync_state.json"


@dataclass
class DocumentRecord:
    doc_id: str
    title: str
    category: Optional[str]
    version: Optional[str]
    content_date: Optional[str]
    metadata: Dict


@dataclass
class ChunkRecord:
    chunk_id: str
    doc_id: str
    text: str
    position: int
    section: Optional[str]
    metadata: Dict


def _git_repo_url() -> str:
    url = os.getenv("KENNISBANK_GIT_REPO", "").strip().strip("'\"")
    if not url:
        raise RuntimeError("KENNISBANK_GIT_REPO niet ingesteld in .env")
    return url


def _git_branch() -> str:
    return os.getenv("KENNISBANK_GIT_BRANCH", "main").strip().strip("'\"")


def _git_token() -> str:
    return os.getenv("KENNISBANK_GIT_TOKEN", "").strip().strip("'\"")


def _authenticated_url() -> str:
    url = _git_repo_url()
    token = _git_token()
    if not token or token == "ghp_xxxxxxxxxxxxx":
        raise RuntimeError("KENNISBANK_GIT_TOKEN niet correct ingesteld in .env")

    if "://" in url:
        scheme, rest = url.split("://", 1)
        return f"{scheme}://{token}@{rest}"
    return url


def _knowledge_embedded_path() -> Path:
    custom = os.getenv("QDRANT_KNOWLEDGE_EMBEDDED_PATH")
    if custom:
        return Path(custom).expanduser()
    return QDRANT_LOCAL_DIR / "kennisbank_db"


def _strip_prefix(value: str, prefix: str) -> str:
    if value.startswith(prefix):
        return value[len(prefix):]
    return value


def _load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_documents(doc_dir: Path) -> Dict[str, DocumentRecord]:
    documents: Dict[str, DocumentRecord] = {}
    if not doc_dir.exists():
        return documents

    for path in doc_dir.glob("*.json"):
        try:
            data = _load_json(path)
        except json.JSONDecodeError as exc:
            logger.warning("Kon document json niet lezen (%s): %s", path.name, exc)
            continue
        doc_id = _strip_prefix(str(data.get("@id", "")).strip(), "doc:")
        if not doc_id:
            continue
        documents[doc_id] = DocumentRecord(
            doc_id=doc_id,
            title=str(data.get("name") or doc_id),
            category=data.get("articleSection"),
            version=data.get("version"),
            content_date=data.get("datePublished"),
            metadata={
                "source_url": data.get("url"),
                "priority": data.get("position"),
                "description": data.get("description"),
            },
        )
    return documents


def _load_chunks(chunk_dir: Path, documents: Dict[str, DocumentRecord]) -> List[ChunkRecord]:
    chunks: List[ChunkRecord] = []
    if not chunk_dir.exists():
        return chunks

    for path in chunk_dir.glob("*.json"):
        try:
            data = _load_json(path)
        except json.JSONDecodeError as exc:
            logger.warning("Kon chunk json niet lezen (%s): %s", path.name, exc)
            continue
        doc_ref = str(data.get("document") or "")
        doc_id = _strip_prefix(doc_ref, "doc:")
        if not doc_id:
            # Probeer van bestandsnaam af te leiden
            doc_id = path.stem
        for entry in data.get("itemListElement", []):
            item = entry.get("item", {})
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            raw_chunk_id = str(item.get("@id") or "")
            chunk_id = _strip_prefix(raw_chunk_id, "chunk:") or f"{doc_id}-{entry.get('position', 0)}"
            section_ref = item.get("isPartOf", {}).get("@id") if isinstance(item.get("isPartOf"), dict) else None
            section_id = _strip_prefix(section_ref or "", "sec:")
            metadata = {
                "wordCount": item.get("wordCount"),
                "tokenCount": item.get("tokenCount"),
                "contentDate": item.get("contentDate"),
                "embedding": item.get("embedding"),
            }
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    text=text,
                    position=int(entry.get("position") or item.get("position") or 0),
                    section=section_id or None,
                    metadata=metadata,
                )
            )
    return chunks


def _load_model_metadata(base_dir: Path) -> Dict:
    model_path = base_dir / KNOWLEDGE_MODEL_FILE
    if not model_path.exists():
        return {}
    try:
        return _load_json(model_path)
    except json.JSONDecodeError:
        return {}


def git_pull() -> dict:
    branch = _git_branch()
    auth_url = _authenticated_url()

    KENNISBANK_REPO_DIR.mkdir(parents=True, exist_ok=True)

    if not (KENNISBANK_REPO_DIR / ".git").exists():
        result = subprocess.run(
            ["git", "clone", "--branch", branch, auth_url, str(KENNISBANK_REPO_DIR)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git clone mislukt: {result.stderr}")
        return {"action": "cloned", "branch": branch}

    subprocess.run(
        ["git", "remote", "set-url", "origin", auth_url],
        cwd=str(KENNISBANK_REPO_DIR),
        capture_output=True,
    )
    result = subprocess.run(
        ["git", "pull", "origin", branch],
        cwd=str(KENNISBANK_REPO_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git pull mislukt: {result.stderr}")
    return {"action": "pulled", "branch": branch}


def _embed_chunks(chunks: Sequence[ChunkRecord]) -> List[Tuple[ChunkRecord, Sequence[float]]]:
    embedded: List[Tuple[ChunkRecord, Sequence[float]]] = []
    for chunk in chunks:
        try:
            vector = embed_text(chunk.text).vector
        except Exception as exc:  # pragma: no cover - fastembed exceptions
            logger.error("Embedding faalde voor chunk %s: %s", chunk.chunk_id, exc)
            continue
        embedded.append((chunk, vector))
    return embedded


def _index_in_qdrant(
    embedded: Sequence[Tuple[ChunkRecord, Sequence[float]]],
    documents: Dict[str, DocumentRecord],
    vector_size: int,
) -> dict:
    if not embedded:
        return {"collection": KNOWLEDGE_COLLECTION, "points": 0, "vector_size": vector_size}

    with _get_qdrant_client(_knowledge_embedded_path()) as client:
        client.recreate_collection(
            collection_name=KNOWLEDGE_COLLECTION,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        points: List[PointStruct] = []
        for chunk, vector in embedded:
            doc = documents.get(chunk.doc_id)
            payload = {
                "doc_id": chunk.doc_id,
                "chunk_id": chunk.chunk_id,
                "position": chunk.position,
                "section": chunk.section,
                "text": chunk.text,
                "metadata": chunk.metadata,
                "document_title": doc.title if doc else chunk.doc_id,
                "document_category": doc.category if doc else None,
                "document_date": doc.content_date if doc else None,
            }
            points.append(
                PointStruct(
                    id=chunk.chunk_id,
                    vector=list(vector),
                    payload=payload,
                )
            )
        client.upsert(collection_name=KNOWLEDGE_COLLECTION, points=points)
    return {"collection": KNOWLEDGE_COLLECTION, "points": len(embedded), "vector_size": vector_size}


def _persist_sqlite_cache(
    documents: Dict[str, DocumentRecord],
    embedded: Sequence[Tuple[ChunkRecord, Sequence[float]]],
) -> dict:
    KNOWLEDGE_SQLITE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(KNOWLEDGE_SQLITE_CACHE))
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            title TEXT,
            category TEXT,
            version TEXT,
            content_date TEXT,
            metadata TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            doc_id TEXT,
            position INTEGER,
            text TEXT,
            metadata TEXT,
            vector TEXT
        )
        """
    )
    cur.execute("DELETE FROM chunks")
    cur.execute("DELETE FROM documents")
    for doc in documents.values():
        cur.execute(
            """
            INSERT OR REPLACE INTO documents(doc_id, title, category, version, content_date, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                doc.doc_id,
                doc.title,
                doc.category,
                doc.version,
                doc.content_date,
                json.dumps(doc.metadata or {}, ensure_ascii=False),
            ),
        )
    for chunk, vector in embedded:
        cur.execute(
            """
            INSERT OR REPLACE INTO chunks(chunk_id, doc_id, position, text, metadata, vector)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                chunk.chunk_id,
                chunk.doc_id,
                chunk.position,
                chunk.text,
                json.dumps(chunk.metadata or {}, ensure_ascii=False),
                json.dumps(list(vector)),
            ),
        )
    conn.commit()
    conn.close()
    return {
        "path": str(KNOWLEDGE_SQLITE_CACHE),
        "documents": len(documents),
        "chunks": len(embedded),
    }


def _write_state_file(payload: Dict) -> None:
    try:
        SYNC_STATE_FILE.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Kon sync-state niet wegschrijven: %s", exc)


def read_sync_state() -> Dict:
    if not SYNC_STATE_FILE.exists():
        return {}
    try:
        return _load_json(SYNC_STATE_FILE)
    except json.JSONDecodeError:
        return {}


def sync_kennisbank() -> dict:
    git_result = git_pull()
    export_base = KENNISBANK_REPO_DIR / KNOWLEDGE_BASE_DIRNAME

    documents = _load_documents(export_base / "documents")
    chunks = _load_chunks(export_base / "chunks", documents)
    if not chunks:
        qdrant_result = {"collection": KNOWLEDGE_COLLECTION, "points": 0, "vector_size": 0}
        sqlite_result = {"path": str(KNOWLEDGE_SQLITE_CACHE), "documents": len(documents), "chunks": 0}
        stats = {
            "document_count": len(documents),
            "chunk_count": 0,
            "message": "Geen chunk-bestanden gevonden in knowledge_base.",
        }
        result = {
            "git": git_result,
            "qdrant": qdrant_result,
            "sqlite": sqlite_result,
            "stats": stats,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_state_file(result)
        return result

    embedded = _embed_chunks(chunks)
    if not embedded:
        raise RuntimeError("Embedding mislukt voor alle chunks; controleer fastembed setup.")

    model_meta = _load_model_metadata(export_base)
    vector_size = int(model_meta.get("vectorDimension") or len(embedded[0][1]))
    qdrant_result = _index_in_qdrant(embedded, documents, vector_size)
    sqlite_result = _persist_sqlite_cache(documents, embedded)

    stats = {
        "document_count": len(documents),
        "chunk_count": len(embedded),
        "model": model_meta or {"model": "unknown", "vectorDimension": vector_size},
    }
    result = {
        "git": git_result,
        "qdrant": qdrant_result,
        "sqlite": sqlite_result,
        "stats": stats,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_state_file(result)
    return result
