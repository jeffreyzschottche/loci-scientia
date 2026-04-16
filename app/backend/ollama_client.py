"""
Ollama LLM client implementation.

Wraps the Ollama REST API (``/api/generate``, ``/api/tags``, ``/api/pull``)
using httpx for async HTTP.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, AsyncIterator, Optional, Sequence

import httpx

from .llm_client import (
    LLMBackendError,
    LLMClient,
    LLMResponse,
    ModelPullProgress,
    StreamToken,
    model_supports_thinking,
    split_thinking_tags,
)

if TYPE_CHECKING:
    from .settings import Settings

logger = logging.getLogger(__name__)


class OllamaClient(LLMClient):
    """LLM client backed by a local Ollama server."""

    def __init__(self, settings: "Settings") -> None:
        self._settings = settings

    # -- internal helpers ---------------------------------------------------

    def _build_generate_payload(
        self,
        prompt: str,
        *,
        stream: bool,
        images: Optional[Sequence[str]] = None,
        thinking: Optional[bool] = None,
    ) -> dict:
        payload: dict = {
            "model": self._settings.ollama_model,
            "prompt": prompt,
            "stream": stream,
        }
        if images:
            payload["images"] = list(images)
        max_context = self._settings.ollama_max_context.get(
            self._settings.ollama_model
        )
        if isinstance(max_context, int) and max_context > 0:
            payload["options"] = {"num_ctx": max_context}
        if model_supports_thinking(self._settings.ollama_model):
            payload["think"] = True if thinking is None else bool(thinking)
        return payload

    # -- LLMClient interface ------------------------------------------------

    async def generate(
        self,
        prompt: str,
        *,
        images: Optional[Sequence[str]] = None,
        thinking: Optional[bool] = None,
        options: Optional[dict] = None,
    ) -> LLMResponse:
        url = f"{self._settings.ollama_base_url}/api/generate"
        payload = self._build_generate_payload(
            prompt, stream=False, images=images, thinking=thinking,
        )
        if options:
            if "options" in payload:
                payload["options"].update(options)
            else:
                payload["options"] = dict(options)
        try:
            async with httpx.AsyncClient(timeout=self._settings.ollama_timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                thinking_text, message = split_thinking_tags(
                    response_text=data.get("response"),
                    thinking_text=data.get("thinking"),
                )
                return LLMResponse(message=message, thinking=thinking_text)
        except httpx.TimeoutException as exc:
            raise LLMBackendError(
                f"Ollama timeout na {self._settings.ollama_timeout:g}s: {exc}",
                backend="ollama",
                is_timeout=True,
            ) from exc
        except httpx.RequestError as exc:
            raise LLMBackendError(
                f"Ollama verbinding mislukt: {exc}",
                backend="ollama",
            ) from exc

    async def stream_generate(
        self,
        prompt: str,
        *,
        images: Optional[Sequence[str]] = None,
        thinking: Optional[bool] = None,
    ) -> AsyncIterator[StreamToken]:
        url = f"{self._settings.ollama_base_url}/api/generate"
        payload = self._build_generate_payload(
            prompt, stream=True, images=images, thinking=thinking,
        )
        try:
            async with httpx.AsyncClient(timeout=self._settings.ollama_timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code >= 400:
                        error_body = await response.aread()
                        raise LLMBackendError(
                            f"Ollama status {response.status_code}: "
                            f"{error_body.decode('utf-8', errors='replace').strip()}",
                            backend="ollama",
                        )
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        token = ""
                        thinking_token = ""

                        if "thinking" in data and data["thinking"]:
                            thinking_token = data["thinking"]
                        if "response" in data and data["response"]:
                            token = data["response"]

                        done = data.get("done", False)

                        if token or thinking_token or done:
                            yield StreamToken(
                                token=token,
                                thinking=thinking_token,
                                done=done,
                            )
                        if done:
                            return
        except httpx.TimeoutException as exc:
            raise LLMBackendError(
                f"Ollama streaming timeout na {self._settings.ollama_timeout:g}s: {exc}",
                backend="ollama",
                is_timeout=True,
            ) from exc
        except httpx.RequestError as exc:
            raise LLMBackendError(
                f"Ollama verbinding mislukt: {exc}",
                backend="ollama",
            ) from exc

    async def list_models(self) -> list[str]:
        url = f"{self._settings.ollama_base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as exc:
            logger.warning("Ollama list_models mislukt: %s", exc)
            return []

    async def pull_model(self, model: str) -> AsyncIterator[ModelPullProgress]:
        url = f"{self._settings.ollama_base_url}/api/pull"
        payload = {"name": model}
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code >= 400:
                        error_body = await response.aread()
                        raise LLMBackendError(
                            f"Ollama pull mislukt ({response.status_code}): "
                            f"{error_body.decode('utf-8', errors='replace').strip()}",
                            backend="ollama",
                        )
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        status = data.get("status", "")
                        completed = data.get("completed", 0) or 0
                        total = data.get("total", 0) or 0
                        progress = (
                            min(100, int(completed * 100 / total))
                            if isinstance(completed, (int, float))
                            and isinstance(total, (int, float))
                            and total
                            else 0
                        )
                        is_done = status == "success"
                        yield ModelPullProgress(
                            status=status,
                            progress=progress,
                            completed=int(completed),
                            total=int(total),
                            done=is_done,
                        )
                        if is_done:
                            return
        except httpx.HTTPError as exc:
            raise LLMBackendError(
                f"Ollama pull mislukt: {exc}",
                backend="ollama",
            ) from exc

    async def health_check(self) -> bool:
        url = f"{self._settings.ollama_base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(url)
                return response.status_code < 400
        except Exception:
            return False

    async def switch_model(self, model: str) -> None:
        """For Ollama, switching means pulling the model if needed."""
        success = False
        async for progress in self.pull_model(model):
            if progress.done:
                success = True
                break
        if not success:
            raise LLMBackendError(
                "Ollama pull beeindigd zonder succes-status",
                backend="ollama",
            )

    @property
    def current_model(self) -> str:
        return self._settings.ollama_model

    @property
    def backend_name(self) -> str:
        return "Ollama"
