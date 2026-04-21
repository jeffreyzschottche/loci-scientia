from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional, Protocol, Sequence


class LLMUnavailable(RuntimeError):
    """Raised when the active LLM backend cannot serve a request."""


@dataclass
class LLMGenerateResult:
    message: str
    thinking: str = ""


@dataclass
class LLMStreamChunk:
    """Normalized streaming chunk produced by every backend."""

    token: str = ""
    thinking: str = ""
    done: bool = False


@dataclass
class LLMPullEvent:
    status: str = ""
    progress: Optional[int] = None  # 0..100 or None if unknown
    done: bool = False
    error: Optional[str] = None


class LLMBackend(Protocol):
    """Uniform contract for Ollama, Lemonade, and any future local LLM runners."""

    name: str

    @property
    def current_model(self) -> str: ...

    def list_models(self) -> dict[str, Any]:
        """Return ``{"current": str, "available": [str, ...]}``."""

    def supports_thinking(self, model: Optional[str] = None) -> bool: ...

    async def generate(
        self,
        prompt: str,
        *,
        options: Optional[dict] = None,
        images: Optional[Sequence[str]] = None,
        thinking: Optional[bool] = None,
    ) -> LLMGenerateResult: ...

    async def stream(
        self,
        prompt: str,
        *,
        images: Optional[Sequence[str]] = None,
        thinking: Optional[bool] = None,
    ) -> AsyncIterator[LLMStreamChunk]: ...

    async def pull_model(self, model: str) -> AsyncIterator[LLMPullEvent]: ...

    def persist_model(self, model: str) -> None:
        """Persist the selected model into .env so it survives restarts."""

    def apply_model(self, model: str) -> None:
        """Update in-memory settings to reflect the active model."""
