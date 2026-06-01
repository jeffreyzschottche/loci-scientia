from __future__ import annotations

import logging
import os
import re
from typing import Dict, List, Tuple

from .kennisbank_sync import KNOWLEDGE_COLLECTION, _knowledge_embedded_path
from .qdrant_utils import get_qdrant_client
from .rag.embedder import embed_text

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
_STOPWORDS = {
    "aan",
    "als",
    "bij",
    "dat",
    "de",
    "een",
    "en",
    "er",
    "had",
    "heeft",
    "het",
    "hoeveel",
    "in",
    "is",
    "met",
    "naar",
    "op",
    "over",
    "te",
    "van",
    "voor",
    "wat",
    "welke",
}


class KnowledgeRepository:
    """Vector-only retrieval against the kennisbank Qdrant collection."""

    def __init__(self) -> None:
        self.collection = os.getenv("QDRANT_KNOWLEDGE_COLLECTION", KNOWLEDGE_COLLECTION)
        self._embedded_path = _knowledge_embedded_path()

    def search_chunks(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.35,
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
                keyword_results = self._keyword_hits(
                    client,
                    query,
                    limit=limit,
                    score_threshold=score_threshold,
                )
        except Exception as exc:
            logger.warning("Querying Qdrant knowledge store failed: %s", exc)
            return []

        merged: dict[str, Tuple[Dict, float]] = {}
        for point in results or []:
            score = float(point.score or 0.0)
            payload = dict(point.payload or {})
            key = str(payload.get("chunk_id") or point.id)
            merged[key] = (payload, score)

        for payload, score in keyword_results:
            key = str(payload.get("chunk_id") or "")
            existing = merged.get(key)
            if existing is None or score > existing[1]:
                merged[key] = (payload, score)

        return sorted(merged.values(), key=lambda item: item[1], reverse=True)[:limit]

    def _keyword_hits(
        self,
        client,
        query: str,
        limit: int,
        score_threshold: float,
    ) -> List[Tuple[Dict, float]]:
        query_tokens = list(dict.fromkeys(_content_tokens(query)))
        if not query_tokens:
            return []

        query_phrase = " ".join(query_tokens)
        min_matches = min(2, len(query_tokens))
        hits: list[tuple[Dict, float]] = []
        next_offset = None
        while True:
            points, next_offset = client.scroll(
                collection_name=self.collection,
                limit=512,
                with_payload=True,
                with_vectors=False,
                offset=next_offset,
            )
            for point in points:
                payload = dict(point.payload or {})
                haystack = " ".join(
                    str(payload.get(field) or "")
                    for field in (
                        "document_title",
                        "doc_id",
                        "document_category",
                        "section",
                        "text",
                    )
                ).lower()
                haystack_tokens = set(_content_tokens(haystack))
                if not haystack_tokens:
                    continue
                matched = sum(1 for token in query_tokens if token in haystack_tokens)
                has_exact_phrase = bool(query_phrase and query_phrase in haystack)
                if matched < min_matches and not has_exact_phrase:
                    continue
                match_ratio = matched / max(len(query_tokens), 1)
                if len(query_tokens) >= 3 and match_ratio < 0.40 and not has_exact_phrase:
                    continue
                score = 0.35 + min(0.45, match_ratio * 0.45)
                if has_exact_phrase:
                    score += 0.2
                score = min(score, 0.98)
                if score < score_threshold:
                    continue
                hits.append((payload, score))
            if not next_offset:
                break

        return sorted(hits, key=lambda item: item[1], reverse=True)[:limit]


def _content_tokens(value: str) -> list[str]:
    return [
        token
        for token in (match.group(0).lower() for match in _TOKEN_RE.finditer(value))
        if len(token) >= 3 and token not in _STOPWORDS
    ]
