"""Eenvoudige, offline embedding via hashing van tokens/teksten."""
from dataclasses import dataclass
from math import sqrt
from typing import Sequence

import hashlib

VECTOR_SIZE = 64


@dataclass(frozen=True)
class EmbeddingResult:
    text: str
    vector: Sequence[float]

    @property
    def dimension(self) -> int:
        return len(self.vector)


def _stable_hash(value: str) -> int:
    """Bepaal een reproduceerbare hash zonder afhankelijkheid van hash randomization."""
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def _normalize(vector: Sequence[float]) -> list[float]:
    norm = sqrt(sum(value * value for value in vector))
    if norm <= 0:
        return [0.0] * len(vector)
    return [value / norm for value in vector]


def _tokenize(text: str) -> list[str]:
    cleaned = "".join(ch if ch.isalnum() else " " for ch in text.lower())
    return [token for token in cleaned.split() if token]


def _add_ngrams(vector: list[float], text: str, weight: float, n: int) -> None:
    for i in range(len(text) - n + 1):
        ngram = text[i : i + n]
        if " " in ngram:
            continue
        idx = _stable_hash(ngram) % VECTOR_SIZE
        vector[idx] += weight


def embed_text(text: str) -> EmbeddingResult:
    vector = [0.0] * VECTOR_SIZE
    tokens = _tokenize(text)

    for token in tokens:
        idx = _stable_hash(token) % VECTOR_SIZE
        vector[idx] += 1.0

    joined = " ".join(tokens)
    _add_ngrams(vector, joined, weight=0.5, n=3)
    _add_ngrams(vector, joined, weight=0.2, n=4)

    normalized = _normalize(vector)
    return EmbeddingResult(text=text, vector=normalized)
