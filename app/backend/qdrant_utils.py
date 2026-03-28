import os
import threading
from contextlib import contextmanager, nullcontext
from functools import lru_cache
from pathlib import Path
from typing import Iterator, Optional

from qdrant_client import QdrantClient

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
QDRANT_LOCAL_DIR = _PROJECT_ROOT / "qdrant_storage"
QDRANT_LOCAL_DIR.mkdir(parents=True, exist_ok=True)

_QDRANT_EMBED_LOCK = threading.Lock()


@contextmanager
def _embedded_client_context(path: Path) -> Iterator[QdrantClient]:
    with _QDRANT_EMBED_LOCK:
        client = QdrantClient(path=str(path))
        try:
            yield client
        finally:
            client.close()


@lru_cache(maxsize=None)
def _cached_remote_client(host: str, port: int, api_key: Optional[str]) -> QdrantClient:
    return QdrantClient(host=host, port=port, api_key=api_key or None)


def get_qdrant_client(embedded_path: Optional[Path] = None):
    host = os.getenv("QDRANT_HOST")
    if not host:
        db_path = embedded_path or (QDRANT_LOCAL_DIR / "default_db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return _embedded_client_context(db_path)

    port = int(os.getenv("QDRANT_PORT", "6333"))
    api_key = os.getenv("QDRANT_API_KEY") or None
    return nullcontext(_cached_remote_client(host, port, api_key))
