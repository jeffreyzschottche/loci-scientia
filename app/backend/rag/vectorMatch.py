"""Placeholder vector matching logic."""

from dataclasses import dataclass

from .embedder import EmbeddingResult


@dataclass
class MatchResult:
    """Simple result object so we can plug in a real vector store later."""

    embedding: EmbeddingResult
    preview: str
    similarity: float


def find_best_match(embedding: EmbeddingResult) -> MatchResult:
    """Pretend to run cosine similarity and return the original text."""

    preview = embedding.preview
    return MatchResult(embedding=embedding, preview=preview, similarity=1.0)
