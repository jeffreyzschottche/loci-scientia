from __future__ import annotations

import logging
import os
from typing import Dict, List, Tuple

from .kennisbank_sync import KNOWLEDGE_COLLECTION, _knowledge_embedded_path
from .qdrant_utils import get_qdrant_client
from .rag.embedder import embed_text

logger = logging.getLogger(__name__)


class KnowledgeRepository:
    """Vector-only retrieval against the kennisbank Qdrant collection."""

    def __init__(self) -> None:
        self.collection = os.getenv("QDRANT_KNOWLEDGE_COLLECTION", KNOWLEDGE_COLLECTION)
        self._embedded_path = _knowledge_embedded_path()

    def search_chunks(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.45,
    ) -> List[Tuple[Dict, float]]:
        if not query.strip():
            return []

        try:
            vector = list(embed_text(query).vector)
        except Exception as exc:
            logger.warning("Embedding query failed: %s", exc)
            return []

        try:
            client_context = get_qdrant_client(self._embedded_path)
        except Exception as exc:
            logger.warning("Opening Qdrant knowledge store failed: %s", exc)
            return []

        try:
            with client_context as client:
                response = client.query_points(
                    collection_name=self.collection,
                    query=vector,
                    limit=limit,
                    with_payload=True,
                    score_threshold=score_threshold,
                )
                results = response.points if hasattr(response, "points") else []
        except Exception as exc:
            logger.warning("Querying Qdrant knowledge store failed: %s", exc)
            return []

        hits: List[Tuple[Dict, float]] = []
        for point in results or []:
            score = float(point.score or 0.0)
            payload = dict(point.payload or {})
            hits.append((payload, score))
        return hits
