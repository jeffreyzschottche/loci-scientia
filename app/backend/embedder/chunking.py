"""Chunker + ID-generator + hasher.

Direct port van ``app/embedder/backend/app/Support/Chunking/*`` (PHP).

Chunk-ID's en content-hashes moeten byte-voor-byte gelijk zijn aan wat de
Laravel-versie produceerde, anders verschijnen na de port duplicate punten in
Qdrant. Vandaar dezelfde format-strings en dezelfde SHA-256-input.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from typing import Optional


# ---- defaults uit config/embedding.php (PHP) --------------------------------
_DEFAULT_CHUNK_TOKENS = 150
_DEFAULT_CHUNK_OVERLAP_TOKENS = 80
_DEFAULT_TOKENS_PER_WORD = 1.3


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _env_float(key: str, default: float, *, minimum: float = 0.0) -> float:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > minimum else default


def _chunk_tokens() -> int:
    return _env_int("EMBEDDING_CHUNK_TOKENS", _DEFAULT_CHUNK_TOKENS)


def _chunk_overlap_tokens() -> int:
    return _env_int("EMBEDDING_CHUNK_OVERLAP_TOKENS", _DEFAULT_CHUNK_OVERLAP_TOKENS)


def _tokens_per_word() -> float:
    return _env_float(
        "EMBEDDING_TOKENS_PER_WORD", _DEFAULT_TOKENS_PER_WORD, minimum=0.1
    )


# ---- chunker -----------------------------------------------------------------


@dataclass
class Chunk:
    text: str
    token_count: int
    word_count: int
    char_start: int
    char_end: int


_NON_WHITESPACE_RE = re.compile(r"\S+", re.UNICODE)
_WORD_RE = re.compile(r"\w+", re.UNICODE)


def estimate_token_count(text: str) -> int:
    words = max(1, len(_WORD_RE.findall(text)))
    return int(math.ceil(words * _tokens_per_word()))


def chunk_text(
    text: str,
    target_tokens: Optional[int] = None,
    overlap_tokens: Optional[int] = None,
) -> list[Chunk]:
    """Splits ``text`` op woordgrens met overlap.

    Geeft per chunk char-offsets terug (Python codepoint-indices). De
    ``processing``-laag matcht deze offsets met page-ranges uit de parser om
    chunks naar pagina-nummers te mappen.
    """

    target = target_tokens if target_tokens is not None else _chunk_tokens()
    overlap = overlap_tokens if overlap_tokens is not None else _chunk_overlap_tokens()
    tokens_per_word = _tokens_per_word()

    matches = list(_NON_WHITESPACE_RE.finditer(text))
    if not matches:
        return []

    target_words = max(1, int(target / tokens_per_word))
    overlap_words = max(0, int(overlap / tokens_per_word))

    chunks: list[Chunk] = []
    total = len(matches)
    start = 0

    while start < total:
        end = min(total, start + target_words)
        slice_ = matches[start:end]
        if not slice_:
            break

        char_start = slice_[0].start()
        char_end = slice_[-1].end()
        chunk_str = " ".join(m.group(0) for m in slice_).strip()
        if not chunk_str:
            break

        word_count = len(slice_)
        token_estimate = estimate_token_count(chunk_str)

        chunks.append(
            Chunk(
                text=chunk_str,
                token_count=min(token_estimate, target),
                word_count=word_count,
                char_start=char_start,
                char_end=char_end,
            )
        )

        if end >= total:
            break

        start = max(end - overlap_words, 0)
        if start >= total:
            break

    return chunks


# ---- chunk-id ---------------------------------------------------------------


def make_chunk_id(doc_id: str, section_slug: str, chunk_index: int) -> str:
    """Zelfde format als ``ChunkIdGenerator::generate`` (``%s#%s#%04d``)."""

    return f"{doc_id}#{section_slug}#{chunk_index:04d}"


_CHUNK_ID_RE = re.compile(r"^(.+)#(.+)#(\d{4})$")


def parse_chunk_id(chunk_id: str) -> Optional[dict]:
    match = _CHUNK_ID_RE.match(chunk_id)
    if not match:
        return None
    return {
        "doc_id": match.group(1),
        "section_slug": match.group(2),
        "chunk_index": int(match.group(3)),
    }


# ---- hashing ----------------------------------------------------------------


def hash_chunk(text: str) -> str:
    """Format: ``sha256:<hex>``. Strip's whitespace zoals de PHP-versie."""

    digest = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def hash_chunk_with_context(title: str, section: str, text: str) -> str:
    payload = f"{title}|{section}|{text}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return f"sha256:{digest}"
