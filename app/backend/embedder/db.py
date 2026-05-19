"""SQLite-backend voor de embedder.

Eén bestand op ``devices_db/embedder.db``. Schema is bewust plat en handmatig
beheerd (geen Alembic) — de Laravel-migraties zijn samengevoegd tot één
``CREATE TABLE`` per relatie. Foreign keys staan aan.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.backend.settings import settings


_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    filename TEXT,
    original_filename TEXT,
    file_size INTEGER,
    mime_type TEXT,
    version_tag TEXT,
    content_date TEXT,
    language TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    position INTEGER NOT NULL DEFAULT 0,
    processing_stage TEXT,
    processing_progress INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    parsed_at TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_priority_position ON documents(priority, position);

CREATE TABLE IF NOT EXISTS document_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 0,
    text TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sections_document_id ON document_sections(document_id);

CREATE TABLE IF NOT EXISTS document_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES document_sections(id) ON DELETE SET NULL,
    chunk_id TEXT NOT NULL UNIQUE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    token_count INTEGER,
    content_hash TEXT NOT NULL,
    last_synced_hash TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_section_id ON document_chunks(section_id);
"""


_lock = threading.Lock()
_initialized = False


def _db_path() -> Path:
    path = settings.embedder_db_path
    if path is None:
        # Fallback — should normally come from settings.
        path = Path(__file__).resolve().parents[3] / "devices_db" / "embedder.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _ensure_schema(conn: sqlite3.Connection) -> None:
    global _initialized
    if _initialized:
        return
    conn.executescript(_SCHEMA)
    conn.commit()
    _initialized = True


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Geef een SQLite-connectie met row_factory en FK's aan.

    Niet draadveilig om dezelfde connectie te delen tussen requests, dus we
    openen er één per call. Voor single-tenant LAN-gebruik is dit ruim genoeg.
    """

    path = _db_path()
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with _lock:
            _ensure_schema(conn)
        yield conn
    finally:
        conn.close()
