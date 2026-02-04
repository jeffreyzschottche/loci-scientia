"""Synchroniseer de kennisbank repo en embed JSON-LD exports naar Qdrant + SQLite.

Incrementele sync: alleen gewijzigde chunks worden opnieuw geëmbed.
Content hashes worden bijgehouden om wijzigingen te detecteren.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

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
CHUNK_HASHES_FILE = _PROJECT_ROOT / ".kennisbank_chunk_hashes.json"


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

    def content_hash(self) -> str:
        """Bereken een hash van de chunk content voor change detection."""
        content = f"{self.doc_id}|{self.text}|{self.position}|{self.section or ''}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def qdrant_id(self) -> str:
        """Genereer een geldige UUID voor Qdrant gebaseerd op chunk_id."""
        # Qdrant vereist UUIDs als point IDs, dus we hashen de chunk_id naar een UUID
        hash_bytes = hashlib.md5(self.chunk_id.encode("utf-8")).hexdigest()
        # Format als UUID: 8-4-4-4-12
        return f"{hash_bytes[:8]}-{hash_bytes[8:12]}-{hash_bytes[12:16]}-{hash_bytes[16:20]}-{hash_bytes[20:32]}"


def _load_chunk_hashes() -> Dict[str, str]:
    """Laad opgeslagen chunk hashes van de vorige sync."""
    if not CHUNK_HASHES_FILE.exists():
        return {}
    try:
        return json.loads(CHUNK_HASHES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_chunk_hashes(hashes: Dict[str, str]) -> None:
    """Sla chunk hashes op voor de volgende sync."""
    try:
        CHUNK_HASHES_FILE.write_text(
            json.dumps(hashes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Kon chunk hashes niet opslaan: %s", exc)


def _chunk_id_to_qdrant_id(chunk_id: str) -> str:
    """Converteer een chunk_id naar een geldige Qdrant UUID."""
    hash_bytes = hashlib.md5(chunk_id.encode("utf-8")).hexdigest()
    return f"{hash_bytes[:8]}-{hash_bytes[8:12]}-{hash_bytes[12:16]}-{hash_bytes[16:20]}-{hash_bytes[20:32]}"


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


def _embed_chunks(
    chunks: Sequence[ChunkRecord],
    progress_callback: Optional[callable] = None,
) -> List[Tuple[ChunkRecord, Sequence[float]]]:
    embedded: List[Tuple[ChunkRecord, Sequence[float]]] = []
    total = len(chunks)
    for idx, chunk in enumerate(chunks):
        if progress_callback:
            progress_callback(idx, total, f"Embedding chunk {idx + 1}/{total}")
        try:
            vector = embed_text(chunk.text).vector
        except Exception as exc:  # pragma: no cover - fastembed exceptions
            logger.error("Embedding faalde voor chunk %s: %s", chunk.chunk_id, exc)
            continue
        embedded.append((chunk, vector))
    return embedded


def _ensure_collection(client, vector_size: int) -> None:
    """Zorg dat de collection bestaat, maak aan indien nodig."""
    try:
        info = client.get_collection(KNOWLEDGE_COLLECTION)
        # Check vector size match
        vectors = info.config.params.vectors
        if isinstance(vectors, VectorParams):
            current_size = vectors.size
        elif isinstance(vectors, dict):
            first = next(iter(vectors.values()), None)
            current_size = first.size if isinstance(first, VectorParams) else None
        else:
            current_size = None

        if current_size != vector_size:
            logger.info("Vector size mismatch (%s vs %s), recreating collection", current_size, vector_size)
            client.recreate_collection(
                collection_name=KNOWLEDGE_COLLECTION,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
    except Exception:
        # Collection bestaat niet, maak aan
        client.recreate_collection(
            collection_name=KNOWLEDGE_COLLECTION,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def _index_in_qdrant(
    embedded: Sequence[Tuple[ChunkRecord, Sequence[float]]],
    documents: Dict[str, DocumentRecord],
    vector_size: int,
    chunks_to_delete: Set[str],
) -> dict:
    """Index chunks in Qdrant met incrementele updates.

    - Upsert nieuwe/gewijzigde chunks
    - Delete verwijderde chunks
    - Behoudt ongewijzigde chunks
    """
    with _get_qdrant_client(_knowledge_embedded_path()) as client:
        _ensure_collection(client, vector_size)

        # Delete verwijderde chunks (converteer chunk_ids naar qdrant UUIDs)
        if chunks_to_delete:
            try:
                qdrant_ids_to_delete = [_chunk_id_to_qdrant_id(cid) for cid in chunks_to_delete]
                client.delete(
                    collection_name=KNOWLEDGE_COLLECTION,
                    points_selector=qdrant_ids_to_delete,
                )
                logger.info("Verwijderd %d chunks uit Qdrant", len(chunks_to_delete))
            except Exception as exc:
                logger.warning("Kon chunks niet verwijderen: %s", exc)

        # Upsert nieuwe/gewijzigde chunks
        if embedded:
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
                        id=chunk.qdrant_id(),  # Gebruik UUID in plaats van raw chunk_id
                        vector=list(vector),
                        payload=payload,
                    )
                )
            client.upsert(collection_name=KNOWLEDGE_COLLECTION, points=points)

        # Haal totaal aantal punten op
        try:
            info = client.get_collection(KNOWLEDGE_COLLECTION)
            total_points = info.points_count or 0
        except Exception:
            total_points = len(embedded)

    return {
        "collection": KNOWLEDGE_COLLECTION,
        "points": total_points,
        "upserted": len(embedded),
        "deleted": len(chunks_to_delete),
        "vector_size": vector_size,
    }


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


def _determine_changes(
    chunks: List[ChunkRecord],
    old_hashes: Dict[str, str],
) -> Tuple[List[ChunkRecord], Set[str], Dict[str, str]]:
    """Bepaal welke chunks gewijzigd, nieuw of verwijderd zijn.

    Returns:
        - chunks_to_embed: chunks die nieuw of gewijzigd zijn
        - chunks_to_delete: chunk_ids die verwijderd moeten worden
        - new_hashes: nieuwe hash mapping voor alle huidige chunks
    """
    new_hashes: Dict[str, str] = {}
    current_chunk_ids: Set[str] = set()
    chunks_to_embed: List[ChunkRecord] = []

    for chunk in chunks:
        chunk_id = chunk.chunk_id
        content_hash = chunk.content_hash()
        new_hashes[chunk_id] = content_hash
        current_chunk_ids.add(chunk_id)

        old_hash = old_hashes.get(chunk_id)
        if old_hash != content_hash:
            # Chunk is nieuw of gewijzigd
            chunks_to_embed.append(chunk)

    # Chunks die verwijderd zijn (waren in old_hashes, niet in current)
    chunks_to_delete = set(old_hashes.keys()) - current_chunk_ids

    return chunks_to_embed, chunks_to_delete, new_hashes


def sync_kennisbank(progress_callback: Optional[callable] = None) -> dict:
    """Synchroniseer kennisbank met incrementele embedding.

    - Git pull de laatste wijzigingen
    - Detecteer welke chunks gewijzigd zijn via content hashes
    - Embed alleen nieuwe/gewijzigde chunks
    - Verwijder verwijderde chunks uit Qdrant
    - Behoud ongewijzigde chunks (geen re-embedding)

    Args:
        progress_callback: Optional callback(current, total, message) voor progress updates
    """
    if progress_callback:
        progress_callback(0, 100, "Git pull starten...")

    git_result = git_pull()

    if progress_callback:
        progress_callback(5, 100, "Documenten laden...")

    export_base = KENNISBANK_REPO_DIR / KNOWLEDGE_BASE_DIRNAME

    documents = _load_documents(export_base / "documents")
    chunks = _load_chunks(export_base / "chunks", documents)

    # Laad vorige chunk hashes
    old_hashes = _load_chunk_hashes()

    if not chunks:
        # Geen chunks, verwijder alles
        chunks_to_delete = set(old_hashes.keys())
        qdrant_result = {
            "collection": KNOWLEDGE_COLLECTION,
            "points": 0,
            "upserted": 0,
            "deleted": len(chunks_to_delete),
            "vector_size": 0,
        }
        sqlite_result = {"path": str(KNOWLEDGE_SQLITE_CACHE), "documents": len(documents), "chunks": 0}
        stats = {
            "document_count": len(documents),
            "chunk_count": 0,
            "message": "Geen chunk-bestanden gevonden in knowledge_base.",
        }
        # Clear hashes
        _save_chunk_hashes({})
        result = {
            "git": git_result,
            "qdrant": qdrant_result,
            "sqlite": sqlite_result,
            "stats": stats,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_state_file(result)
        return result

    # Bepaal wijzigingen
    if progress_callback:
        progress_callback(10, 100, "Wijzigingen detecteren...")

    chunks_to_embed, chunks_to_delete, new_hashes = _determine_changes(chunks, old_hashes)

    logger.info(
        "Kennisbank sync: %d totaal, %d te embedden, %d te verwijderen, %d ongewijzigd",
        len(chunks),
        len(chunks_to_embed),
        len(chunks_to_delete),
        len(chunks) - len(chunks_to_embed),
    )

    # Bepaal vector size
    model_meta = _load_model_metadata(export_base)
    vector_size = int(model_meta.get("vectorDimension") or 768)

    # Embed alleen gewijzigde chunks
    if chunks_to_embed:
        def embed_progress(idx, total, msg):
            # Scale embedding progress from 15% to 85%
            pct = 15 + int((idx / max(total, 1)) * 70)
            if progress_callback:
                progress_callback(pct, 100, f"Embedding {idx + 1}/{total} chunks...")

        embedded = _embed_chunks(chunks_to_embed, progress_callback=embed_progress)
        if not embedded and chunks_to_embed:
            raise RuntimeError("Embedding mislukt voor alle chunks; controleer fastembed setup.")
        # Update vector size from actual embedding if available
        if embedded:
            vector_size = len(embedded[0][1])
    else:
        embedded = []
        if progress_callback:
            progress_callback(85, 100, "Geen nieuwe chunks te embedden")

    # Index in Qdrant (incrementeel)
    if progress_callback:
        progress_callback(88, 100, "Indexeren in Qdrant...")

    qdrant_result = _index_in_qdrant(embedded, documents, vector_size, chunks_to_delete)

    # SQLite cache bijwerken - we moeten alle chunks hebben voor de cache
    # Haal vectors van bestaande chunks uit Qdrant indien nodig
    if progress_callback:
        progress_callback(92, 100, "SQLite cache bijwerken...")

    all_embedded = _get_all_embedded_chunks(chunks, embedded, old_hashes)
    sqlite_result = _persist_sqlite_cache(documents, all_embedded)

    # Sla nieuwe hashes op
    if progress_callback:
        progress_callback(98, 100, "Afronden...")

    _save_chunk_hashes(new_hashes)

    stats = {
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "embedded_count": len(embedded),
        "unchanged_count": len(chunks) - len(chunks_to_embed),
        "deleted_count": len(chunks_to_delete),
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

    if progress_callback:
        progress_callback(100, 100, "Sync voltooid!")

    return result


def _get_all_embedded_chunks(
    all_chunks: List[ChunkRecord],
    newly_embedded: List[Tuple[ChunkRecord, Sequence[float]]],
    old_hashes: Dict[str, str],
) -> List[Tuple[ChunkRecord, Sequence[float]]]:
    """Combineer nieuw geëmbedde chunks met bestaande vectors uit SQLite cache."""
    # Maak lookup van nieuw geëmbedde chunks
    newly_embedded_map = {chunk.chunk_id: vector for chunk, vector in newly_embedded}

    # Laad bestaande vectors uit SQLite cache
    existing_vectors = _load_vectors_from_cache()

    result: List[Tuple[ChunkRecord, Sequence[float]]] = []
    for chunk in all_chunks:
        if chunk.chunk_id in newly_embedded_map:
            # Nieuw geëmbed
            result.append((chunk, newly_embedded_map[chunk.chunk_id]))
        elif chunk.chunk_id in existing_vectors:
            # Bestaande vector uit cache
            result.append((chunk, existing_vectors[chunk.chunk_id]))
        else:
            # Chunk bestaat maar geen vector - moet geëmbed worden
            # Dit kan gebeuren bij eerste run of corrupte cache
            try:
                vector = embed_text(chunk.text).vector
                result.append((chunk, vector))
            except Exception as exc:
                logger.error("Embedding faalde voor chunk %s: %s", chunk.chunk_id, exc)
    return result


def _load_vectors_from_cache() -> Dict[str, Sequence[float]]:
    """Laad vectors uit SQLite cache."""
    vectors: Dict[str, Sequence[float]] = {}
    if not KNOWLEDGE_SQLITE_CACHE.exists():
        return vectors
    try:
        conn = sqlite3.connect(str(KNOWLEDGE_SQLITE_CACHE))
        cur = conn.cursor()
        cur.execute("SELECT chunk_id, vector FROM chunks WHERE vector IS NOT NULL")
        for row in cur.fetchall():
            chunk_id, vector_json = row
            if vector_json:
                try:
                    vectors[chunk_id] = json.loads(vector_json)
                except json.JSONDecodeError:
                    pass
        conn.close()
    except Exception as exc:
        logger.warning("Kon vectors niet laden uit cache: %s", exc)
    return vectors
