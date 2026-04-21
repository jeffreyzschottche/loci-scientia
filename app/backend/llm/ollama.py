from __future__ import annotations

import json
import logging
import re
from typing import Any, AsyncIterator, Optional, Sequence

import httpx

from ..settings import settings
from ._env import persist_env_var
from .base import LLMGenerateResult, LLMPullEvent, LLMStreamChunk, LLMUnavailable

logger = logging.getLogger(__name__)

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


def _supports_thinking(model: str) -> bool:
    normalized = (model or "").strip().lower()
    return any(marker in normalized for marker in THINKING_MODEL_MARKERS)


def _split_response_parts(
    response_text: Optional[str],
    thinking_text: Optional[str] = None,
) -> tuple[str, str]:
    response = (response_text or "").strip()
    thinking_parts = [part.strip() for part in [(thinking_text or "").strip()] if part.strip()]
    if response:
        inline_thinking = [match.strip() for match in THINKING_TAG_RE.findall(response) if match.strip()]
        if inline_thinking:
            thinking_parts.extend(inline_thinking)
            response = THINKING_TAG_RE.sub("", response).strip()
    seen: set[str] = set()
    ordered_thinking: list[str] = []
    for part in thinking_parts:
        if part and part not in seen:
            seen.add(part)
            ordered_thinking.append(part)
    return ("\n\n".join(ordered_thinking).strip(), response)


def _build_generate_payload(
    prompt: str,
    *,
    stream: bool,
    images: Optional[Sequence[str]] = None,
    thinking: Optional[bool] = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": stream,
    }
    if images:
        payload["images"] = list(images)
    max_context = settings.ollama_max_context.get(settings.ollama_model)
    if isinstance(max_context, int) and max_context > 0:
        payload["options"] = {"num_ctx": max_context}
    if _supports_thinking(settings.ollama_model):
        payload["think"] = True if thinking is None else bool(thinking)
    return payload


class OllamaBackend:
    name = "ollama"

    @property
    def current_model(self) -> str:
        return settings.ollama_model

    def list_models(self) -> dict[str, Any]:
        return {"current": settings.ollama_model, "available": list(settings.ollama_models)}

    def supports_thinking(self, model: Optional[str] = None) -> bool:
        return _supports_thinking(model or settings.ollama_model)

    async def generate(
        self,
        prompt: str,
        *,
        options: Optional[dict] = None,
        images: Optional[Sequence[str]] = None,
        thinking: Optional[bool] = None,
    ) -> LLMGenerateResult:
        url = f"{settings.ollama_base_url}/api/generate"
        payload = _build_generate_payload(prompt, stream=False, images=images, thinking=thinking)
        if options:
            payload.setdefault("options", {}).update(options)
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        thinking_text, message = _split_response_parts(
            response_text=data.get("response"),
            thinking_text=data.get("thinking"),
        )
        return LLMGenerateResult(message=message, thinking=thinking_text)

    async def stream(
        self,
        prompt: str,
        *,
        images: Optional[Sequence[str]] = None,
        thinking: Optional[bool] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        url = f"{settings.ollama_base_url}/api/generate"
        payload = _build_generate_payload(prompt, stream=True, images=images, thinking=thinking)
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code >= 400:
                    body = (await response.aread()).decode("utf-8", errors="replace").strip()
                    raise LLMUnavailable(f"Ollama status {response.status_code}: {body}")
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    thinking_token = data.get("thinking") or ""
                    token = data.get("response") or ""
                    done = bool(data.get("done"))
                    if thinking_token or token or done:
                        yield LLMStreamChunk(
                            token=token,
                            thinking=thinking_token,
                            done=done,
                        )
                    if done:
                        break

    async def pull_model(self, model: str) -> AsyncIterator[LLMPullEvent]:
        url = f"{settings.ollama_base_url}/api/pull"
        payload = {"name": model}
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code >= 400:
                        body = (await response.aread()).decode("utf-8", errors="replace").strip()
                        yield LLMPullEvent(
                            status=f"Ollama pull faalde ({response.status_code}): {body}",
                            done=True,
                            error=body or f"HTTP {response.status_code}",
                        )
                        return
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        status = data.get("status") or ""
                        completed = data.get("completed")
                        total = data.get("total")
                        progress: Optional[int] = None
                        if isinstance(completed, (int, float)) and isinstance(total, (int, float)) and total:
                            progress = min(100, int(completed * 100 / total))
                        done = status == "success"
                        yield LLMPullEvent(status=status, progress=progress, done=done)
                        if done:
                            break
        except httpx.HTTPError as exc:
            yield LLMPullEvent(
                status=f"Ollama pull faalde: {exc}",
                done=True,
                error=str(exc),
            )

    def persist_model(self, model: str) -> None:
        persist_env_var("OLLAMA_MODEL", model)

    def apply_model(self, model: str) -> None:
        settings.ollama_model = model
