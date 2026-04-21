from __future__ import annotations

from typing import Optional

from ..settings import settings
from .base import LLMBackend
from .lemonade import LemonadeBackend
from .ollama import OllamaBackend

_cached_backend: Optional[LLMBackend] = None
_cached_provider: Optional[str] = None


def _instantiate(provider: str) -> LLMBackend:
    if provider == "lemonade":
        return LemonadeBackend()
    return OllamaBackend()


def get_backend() -> LLMBackend:
    global _cached_backend, _cached_provider
    provider = settings.llm_provider
    if _cached_backend is None or _cached_provider != provider:
        _cached_backend = _instantiate(provider)
        _cached_provider = provider
    return _cached_backend


def invalidate_backend_cache() -> None:
    global _cached_backend, _cached_provider
    _cached_backend = None
    _cached_provider = None
