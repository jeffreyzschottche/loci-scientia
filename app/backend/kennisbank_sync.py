"""Kennisbank sync: git pull + laad SQLite embeddings in Qdrant."""

import json
import os
import sqlite3
import subprocess
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
KENNISBANK_REPO_DIR = _PROJECT_ROOT / "kennisbank_repo"
KENNISBANK_SQLITE_FILE = "kennisbank.db"
KENNISBANK_COLLECTION = "kennisbank"
VECTOR_SIZE = 768  # mpnet-base-v2 dimensie

_EMBED_LOCK = threading.Lock()


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
    """Bouw een URL met token voor git clone/pull."""
    url = _git_repo_url()
    token = _git_token()
    if not token or token == "ghp_xxxxxxxxxxxxx":
        raise RuntimeError("KENNISBANK_GIT_TOKEN niet correct ingesteld in .env")

    # https://github.com/user/repo.git -> https://TOKEN@github.com/user/repo.git
    if "://" in url:
        scheme, rest = url.split("://", 1)
        return f"{scheme}://{token}@{rest}"
    return url


def _qdrant_embedded_path() -> Path:
    return _PROJECT_ROOT / "qdrant_storage" / "kennisbank_db"


@contextmanager
def _qdrant_client() -> Iterator[QdrantClient]:
    """Geeft een embedded Qdrant client voor de kennisbank collection."""
    host = os.getenv("QDRANT_HOST")
    if host:
        port = int(os.getenv("QDRANT_PORT", "6333"))
        api_key = os.getenv("QDRANT_API_KEY") or None
        client = QdrantClient(host=host, port=port, api_key=api_key)
        try:
            yield client
        finally:
            pass
    else:
        db_path = _qdrant_embedded_path()
        db_path.mkdir(parents=True, exist_ok=True)
        with _EMBED_LOCK:
            client = QdrantClient(path=str(db_path))
            try:
                yield client
            finally:
                client.close()


def git_pull() -> dict:
    """Clone of pull de kennisbank git repo."""
    branch = _git_branch()
    auth_url = _authenticated_url()

    if not KENNISBANK_REPO_DIR.exists():
        result = subprocess.run(
            ["git", "clone", "--branch", branch, auth_url, str(KENNISBANK_REPO_DIR)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git clone mislukt: {result.stderr}")
        return {"action": "cloned", "branch": branch}
    else:
        # Set remote URL met token en pull
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


def load_sqlite_to_qdrant() -> dict:
    """Lees de SQLite kennisbank en laad embeddings in Qdrant."""
    sqlite_path = KENNISBANK_REPO_DIR / KENNISBANK_SQLITE_FILE

    if not sqlite_path.exists():
        return {"loaded": 0, "message": "Geen kennisbank.db gevonden in de repo"}

    # Lees SQLite
    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row

    documents = conn.execute("SELECT * FROM documents").fetchall()
    embeddings = conn.execute("SELECT * FROM embeddings ORDER BY document_id, chunk_index").fetchall()
    conn.close()

    if not embeddings:
        return {"loaded": 0, "message": "Geen embeddings in kennisbank.db"}

    # Laad in Qdrant
    with _qdrant_client() as client:
        # Verwijder bestaande collection en maak opnieuw
        collections = [c.name for c in client.get_collections().collections]
        if KENNISBANK_COLLECTION in collections:
            client.delete_collection(KENNISBANK_COLLECTION)

        client.create_collection(
            collection_name=KENNISBANK_COLLECTION,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )

        # Maak een lookup van document filenames
        doc_lookup = {row["id"]: row["original_filename"] for row in documents}

        # Batch upsert
        points = []
        for emb in embeddings:
            vector = json.loads(emb["vector"])
            points.append(
                PointStruct(
                    id=emb["id"],
                    vector=vector,
                    payload={
                        "document_id": emb["document_id"],
                        "document_name": doc_lookup.get(emb["document_id"], "onbekend"),
                        "chunk_index": emb["chunk_index"],
                        "text": emb["text_content"],
                    },
                )
            )

        # Upsert in batches van 100
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            client.upsert(
                collection_name=KENNISBANK_COLLECTION,
                points=batch,
            )

    return {
        "loaded": len(points),
        "documents": len(documents),
        "message": f"{len(points)} embeddings geladen uit {len(documents)} documenten",
    }


def sync_kennisbank() -> dict:
    """Volledige sync: git pull + laad in Qdrant."""
    git_result = git_pull()
    load_result = load_sqlite_to_qdrant()

    return {
        "git": git_result,
        "qdrant": load_result,
    }
