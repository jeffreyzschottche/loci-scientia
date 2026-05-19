"""Kennisbank Qdrant-helpers + sync-state file.

Voorheen hostte deze module de volledige JSON-LD importer die ZIP-bundles van
de externe Laravel-embedder ontving. Sinds de Aitje Embedding Application
in-process draait (zie ``app.backend.embedder``) schrijft die rechtstreeks
naar Qdrant — alle JSON-walking, hashing op disk en SQLite-cache spul is weg.

Wat overblijft zijn de paar constanten en helpers die zowel
``app.backend.embedder.sync`` als de device-route ``/api/v1/kennisbank/sync-state``
gebruiken: de collection-naam, het Qdrant-pad, de chunk-id → UUID conversie
en het sync-state JSON-bestand dat het network-page leest.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from .qdrant_utils import QDRANT_LOCAL_DIR


logger = logging.getLogger(__name__)


_PROJECT_ROOT = Path(__file__).resolve().parents[2]

KNOWLEDGE_COLLECTION = os.getenv("QDRANT_KNOWLEDGE_COLLECTION", "kennisbank")
SYNC_STATE_FILE = _PROJECT_ROOT / "devices_db" / "kennisbank_sync_state.json"


def _chunk_id_to_qdrant_id(chunk_id: str) -> str:
    """Map een ``doc#section#index`` chunk-id naar een UUID die Qdrant accepteert."""

    digest = hashlib.md5(chunk_id.encode("utf-8")).hexdigest()
    return (
        f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-"
        f"{digest[16:20]}-{digest[20:32]}"
    )


def _knowledge_embedded_path() -> Path:
    """Lokaal pad waar de embedded Qdrant-client de kennisbank-collectie bewaart."""

    custom = os.getenv("QDRANT_KNOWLEDGE_EMBEDDED_PATH")
    if custom:
        return Path(custom).expanduser()
    return QDRANT_LOCAL_DIR / "kennisbank_db"


def read_sync_state() -> dict:
    if not SYNC_STATE_FILE.exists():
        return {}
    try:
        return json.loads(SYNC_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_sync_state(payload: dict) -> None:
    """Persist de laatste sync-result + timestamp zodat de network-page hem leest."""

    try:
        SYNC_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        merged = {
            "synced_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        SYNC_STATE_FILE.write_text(
            json.dumps(merged, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:  # pragma: no cover
        logger.warning("Kon sync-state niet wegschrijven: %s", exc)
