from __future__ import annotations

import os
from typing import Dict, List, Tuple

from qdrant_client.models import ScoredPoint

from .contacts_repo import _get_qdrant_client
from .kennisbank_sync import KNOWLEDGE_COLLECTION, _knowledge_embedded_path
from .rag.embedder import embed_text


class KnowledgeRepository:
    """Lightweight helper around the kennisbank Qdrant collection."""

    def __init__(self) -> None:
        self.collection = os.getenv("QDRANT_KNOWLEDGE_COLLECTION", KNOWLEDGE_COLLECTION)
        self._embedded_path = _knowledge_embedded_path()

    def search_chunks(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.25,
    ) -> List[Tuple[Dict, float]]:
        if not query.strip():
            return []

        try:
            vector = list(embed_text(query).vector)
        except Exception:
            return []

        with _get_qdrant_client(self._embedded_path) as client:
            try:
                response = client.query_points(
                    collection_name=self.collection,
                    query=vector,
                    limit=limit,
                    with_payload=True,
                )
                results = response.points if hasattr(response, 'points') else []
            except Exception:
                return []

        hits: List[Tuple[Dict, float]] = []
        for point in results or []:
            score = float(point.score or 0.0)
            if score < score_threshold:
                continue
            payload = dict(point.payload or {})
            hits.append((payload, score))
        return hits
