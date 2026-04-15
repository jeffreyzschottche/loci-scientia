from __future__ import annotations

import logging
import os
import re
import sqlite3
from typing import Dict, List, Tuple

from .kennisbank_sync import KNOWLEDGE_COLLECTION, KNOWLEDGE_SQLITE_CACHE, _knowledge_embedded_path
from .qdrant_utils import get_qdrant_client
from .rag.embedder import embed_text

_QUERY_TOKEN_PATTERN = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ][0-9A-Za-zÀ-ÖØ-öø-ÿ_-]*")
_QUERY_STOPWORDS = {
    "aan", "al", "als", "bij", "dan", "dat", "de", "den", "der", "dit", "door", "een", "en",
    "er", "haar", "heb", "heeft", "hem", "het", "hier", "hoe", "hun", "ik", "in", "info",
    "informatie", "is", "je",
    "kan", "me", "meer", "met", "mij", "mijn", "naar", "niet", "nu", "of", "om", "ons", "ook",
    "over", "te", "tot", "uit", "van", "vertel", "voor", "wat", "we", "wel", "wie", "wil",
    "wordt", "ze", "zelf", "zich", "zijn", "zo", "zou", "allemaal", "product", "producten",
}

logger = logging.getLogger(__name__)


class KnowledgeRepository:
    """Lightweight helper around the kennisbank Qdrant collection."""

    def __init__(self) -> None:
        self.collection = os.getenv("QDRANT_KNOWLEDGE_COLLECTION", KNOWLEDGE_COLLECTION)
        self._embedded_path = _knowledge_embedded_path()
        self._sqlite_cache = KNOWLEDGE_SQLITE_CACHE

    def _query_terms(self, query: str) -> List[str]:
        terms: List[str] = []
        for raw in _QUERY_TOKEN_PATTERN.findall((query or "").lower()):
            token = raw.strip("_-")
            if token.isdigit():
                continue
            if token.endswith("s") and len(token) > 4:
                token = token[:-1]
            if len(token) < 3 or token in _QUERY_STOPWORDS:
                continue
            if token not in terms:
                terms.append(token)
        return terms

    def _vector_hits(self, query: str, limit: int, score_threshold: float) -> List[Tuple[Dict, float]]:
        try:
            vector = list(embed_text(query).vector)
        except Exception:
            return []

        try:
            client_context = get_qdrant_client(self._embedded_path)
        except Exception as exc:
            logger.warning("Opening Qdrant knowledge store failed: %s", exc)
            return []

        try:
            with client_context as client:
                try:
                    response = client.query_points(
                        collection_name=self.collection,
                        query=vector,
                        limit=limit,
                        with_payload=True,
                    )
                    results = response.points if hasattr(response, "points") else []
                except Exception:
                    return []
        except Exception as exc:
            logger.warning("Querying Qdrant knowledge store failed: %s", exc)
            return []

        hits: List[Tuple[Dict, float]] = []
        for point in results or []:
            score = float(point.score or 0.0)
            if score < score_threshold:
                continue
            payload = dict(point.payload or {})
            hits.append((payload, score))
        return hits

    def _lexical_hits(self, query: str, limit: int) -> List[Tuple[Dict, float]]:
        terms = self._query_terms(query)
        if not terms or not self._sqlite_cache.exists():
            return []

        where_clauses = ["lower(c.text) LIKE ?"] * len(terms)
        params = [f"%{term}%" for term in terms]
        sql = f"""
            SELECT
                c.chunk_id,
                c.doc_id,
                c.position,
                c.text,
                d.title,
                d.category,
                d.content_date
            FROM chunks c
            LEFT JOIN documents d ON d.doc_id = c.doc_id
            WHERE {" AND ".join(where_clauses)}
            ORDER BY c.position ASC
            LIMIT ?
        """
        params.append(limit)

        conn = sqlite3.connect(str(self._sqlite_cache))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.Error:
            return []
        finally:
            conn.close()

        hits: List[Tuple[Dict, float]] = []
        for row in rows:
            payload = {
                "doc_id": row["doc_id"],
                "chunk_id": row["chunk_id"],
                "position": row["position"],
                "section": None,
                "text": row["text"],
                "document_title": row["title"] or row["doc_id"],
                "document_category": row["category"],
                "document_date": row["content_date"],
            }
            score = 1.0 + (len(terms) * 0.05)
            hits.append((payload, score))
        return hits

    def search_chunks(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.25,
    ) -> List[Tuple[Dict, float]]:
        if not query.strip():
            return []

        merged: Dict[str, Tuple[Dict, float]] = {}
        for payload, score in self._lexical_hits(query, limit=limit):
            key = str(payload.get("chunk_id") or payload.get("doc_id") or id(payload))
            merged[key] = (payload, score)

        for payload, score in self._vector_hits(query, limit=limit, score_threshold=score_threshold):
            key = str(payload.get("chunk_id") or payload.get("doc_id") or id(payload))
            existing = merged.get(key)
            if existing is None or score > existing[1]:
                merged[key] = (payload, score)

        hits = sorted(merged.values(), key=lambda item: item[1], reverse=True)
        return hits[:limit]
