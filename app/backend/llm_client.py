"""
LLM client abstraction layer.

Provides a unified interface for different LLM inference backends
(Ollama, FastFlowLM). The active backend is selected via the
INFERENCE_BACKEND environment variable.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, AsyncIterator, Optional, Sequence

if TYPE_CHECKING:
    from .settings import Settings

THINKING_TAG_RE = re.compile(r"<think>(.*?)</think>", re.IGNORECASE | re.DOTALL)

THINKING_MODEL_MARKERS = (
    "qwen3",
    "qwen 3",
    "qwen3.5",
    "deepseek-r1",
    "deepseek_r1",
    "deepseek-v3.1",
    "gpt-oss",
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    """Unified response from any LLM backend."""
    message: str
    thinking: str = ""


@dataclass
class StreamToken:
    """A single token/chunk from a streaming response."""
    token: str = ""
    thinking: str = ""
    done: bool = False


@dataclass
class ModelPullProgress:
    """Progress update from a model pull operation."""
    status: str = ""
    progress: int = 0
    completed: int = 0
    total: int = 0
    done: bool = False


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class LLMBackendError(Exception):
    """Raised when the LLM backend is unreachable or returns an error."""

    def __init__(self, message: str, backend: str, is_timeout: bool = False):
        self.backend = backend
        self.is_timeout = is_timeout
        super().__init__(message)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def model_supports_thinking(model: str) -> bool:
    """Return True if the model name suggests it supports thinking/reasoning."""
    normalized = (model or "").strip().lower()
    return any(marker in normalized for marker in THINKING_MODEL_MARKERS)


def split_thinking_tags(
    response_text: Optional[str],
    thinking_text: Optional[str] = None,
) -> tuple[str, str]:
    """Extract <think>…</think> blocks from response text.

    Returns ``(thinking, response)`` with inline think tags removed from
    the response and merged with any explicit *thinking_text*.
    """
    response = (response_text or "").strip()
    thinking_parts = [
        part.strip()
        for part in [(thinking_text or "").strip()]
        if part.strip()
    ]
    if response:
        inline_thinking = [
            match.strip()
            for match in THINKING_TAG_RE.findall(response)
            if match.strip()
        ]
        if inline_thinking:
            thinking_parts.extend(inline_thinking)
            response = THINKING_TAG_RE.sub("", response).strip()
    seen: set[str] = set()
    ordered: list[str] = []
    for part in thinking_parts:
        if part and part not in seen:
            seen.add(part)
            ordered.append(part)
    return ("\n\n".join(ordered).strip(), response)


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class LLMClient(ABC):
    """Abstract interface for LLM inference backends."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        images: Optional[Sequence[str]] = None,
        thinking: Optional[bool] = None,
        options: Optional[dict] = None,
    ) -> LLMResponse:
        """Non-streaming text generation."""

    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        *,
        images: Optional[Sequence[str]] = None,
        thinking: Optional[bool] = None,
    ) -> AsyncIterator[StreamToken]:
        """Streaming text generation yielding tokens."""

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List locally available model tags."""

    @abstractmethod
    async def pull_model(self, model: str) -> AsyncIterator[ModelPullProgress]:
        """Pull/download a model, yielding progress updates."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the backend is reachable and ready."""

    @abstractmethod
    async def switch_model(self, model: str) -> None:
        """Switch to a different model.

        For Ollama this only pulls the model if needed.
        For FLM this restarts ``flm serve`` with the new model tag.
        """

    @property
    @abstractmethod
    def current_model(self) -> str:
        """Currently active model tag."""

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Human-readable backend name (e.g. 'Ollama', 'FastFlowLM')."""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_llm_client(settings: "Settings") -> LLMClient:
    """Instantiate the configured LLM backend client."""
    backend = settings.inference_backend.lower()
    if backend == "flm":
        from .flm_client import FLMClient
        return FLMClient(settings)
    from .ollama_client import OllamaClient
    return OllamaClient(settings)
