from __future__ import annotations

import base64
import binascii
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


def _detect_image_mime(raw: bytes) -> str:
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if raw.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if raw.startswith(b"GIF87a") or raw.startswith(b"GIF89a"):
        return "image/gif"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


def _to_data_url(image_b64: str) -> str:
    value = (image_b64 or "").strip()
    if value.startswith("data:"):
        return value
    try:
        raw = base64.b64decode(value, validate=False)
    except binascii.Error:
        raw = b""
    mime = _detect_image_mime(raw) if raw else "image/png"
    return f"data:{mime};base64,{value}"


def _build_user_content(prompt: str, images: Optional[Sequence[str]]) -> Any:
    if not images or not settings.lemonade_vision_enabled:
        return prompt
    parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image in images:
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": _to_data_url(image)},
            }
        )
    return parts


def _active_model() -> str:
    return settings.lemonade_model or ""


def _build_chat_payload(
    prompt: str,
    *,
    stream: bool,
    images: Optional[Sequence[str]] = None,
    options: Optional[dict] = None,
) -> dict[str, Any]:
    model = _active_model()
    if not model:
        raise LLMUnavailable("LEMONADE_MODEL is niet ingesteld.")
    payload: dict[str, Any] = {
        "model": model,
        "stream": stream,
        "messages": [
            {"role": "user", "content": _build_user_content(prompt, images)},
        ],
    }
    max_context = settings.lemonade_max_context.get(model)
    if isinstance(max_context, int) and max_context > 0:
        payload["max_tokens"] = max_context
    if options:
        for key, value in options.items():
            if key == "num_predict":
                payload["max_tokens"] = int(value)
            elif key == "num_ctx":
                # Lemonade exposes context as max_tokens via OpenAI contract.
                payload.setdefault("max_tokens", int(value))
            else:
                payload[key] = value
    return payload


def _extract_delta(chunk: dict[str, Any]) -> tuple[str, str, bool]:
    choices = chunk.get("choices") or []
    if not choices:
        return "", "", False
    choice = choices[0] or {}
    delta = choice.get("delta") or {}
    token = delta.get("content") or ""
    thinking = (
        delta.get("reasoning_content")
        or delta.get("reasoning")
        or ""
    )
    finish_reason = choice.get("finish_reason")
    done = bool(finish_reason)
    return token, thinking, done


class LemonadeBackend:
    name = "lemonade"

    @property
    def current_model(self) -> str:
        return _active_model()

    def list_models(self) -> dict[str, Any]:
        current = _active_model()
        available = list(settings.lemonade_models)
        # Best effort: vraag Lemonade om z'n geladen modellen op te halen als dat lukt;
        # faalt dit, dan vallen we terug op de .env-lijst.
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{settings.lemonade_base_url}/api/v1/models")
                if response.status_code < 400:
                    data = response.json()
                    items = data.get("data") if isinstance(data, dict) else None
                    if isinstance(items, list):
                        discovered = [
                            str(item.get("id")).strip()
                            for item in items
                            if isinstance(item, dict) and item.get("id")
                        ]
                        for name in discovered:
                            if name and name not in available:
                                available.append(name)
        except httpx.HTTPError:
            pass
        return {"current": current, "available": available}

    def supports_thinking(self, model: Optional[str] = None) -> bool:
        # Lemonade stuurt reasoning-velden alleen als het model ze produceert;
        # dat detecteren we runtime in _extract_delta, dus geen whitelist nodig.
        return True

    async def generate(
        self,
        prompt: str,
        *,
        options: Optional[dict] = None,
        images: Optional[Sequence[str]] = None,
        thinking: Optional[bool] = None,
    ) -> LLMGenerateResult:
        url = f"{settings.lemonade_base_url}/api/v1/chat/completions"
        payload = _build_chat_payload(prompt, stream=False, images=images, options=options)
        async with httpx.AsyncClient(timeout=settings.lemonade_timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        choices = data.get("choices") or []
        message_text = ""
        reasoning_text = ""
        if choices:
            message = choices[0].get("message") or {}
            message_text = str(message.get("content") or "")
            reasoning_text = str(
                message.get("reasoning_content") or message.get("reasoning") or ""
            )
        thinking_text, assistant_text = _split_response_parts(
            response_text=message_text,
            thinking_text=reasoning_text,
        )
        return LLMGenerateResult(message=assistant_text, thinking=thinking_text)

    async def stream(
        self,
        prompt: str,
        *,
        images: Optional[Sequence[str]] = None,
        thinking: Optional[bool] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        url = f"{settings.lemonade_base_url}/api/v1/chat/completions"
        payload = _build_chat_payload(prompt, stream=True, images=images)
        async with httpx.AsyncClient(timeout=settings.lemonade_timeout) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code >= 400:
                    body = (await response.aread()).decode("utf-8", errors="replace").strip()
                    raise LLMUnavailable(f"Lemonade status {response.status_code}: {body}")
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if not line.startswith("data:"):
                        continue
                    payload_text = line[len("data:"):].strip()
                    if not payload_text or payload_text == "[DONE]":
                        if payload_text == "[DONE]":
                            yield LLMStreamChunk(done=True)
                            break
                        continue
                    try:
                        data = json.loads(payload_text)
                    except json.JSONDecodeError:
                        continue
                    token, thinking_token, done = _extract_delta(data)
                    if token or thinking_token or done:
                        yield LLMStreamChunk(
                            token=token,
                            thinking=thinking_token,
                            done=done,
                        )
                    if done:
                        break

    async def pull_model(self, model: str) -> AsyncIterator[LLMPullEvent]:
        url = f"{settings.lemonade_base_url}/api/v1/pull"
        payload = {"model_name": model}
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code >= 400:
                        body = (await response.aread()).decode("utf-8", errors="replace").strip()
                        yield LLMPullEvent(
                            status=f"Lemonade pull faalde ({response.status_code}): {body}",
                            done=True,
                            error=body or f"HTTP {response.status_code}",
                        )
                        return
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        stripped = line.strip()
                        if stripped.startswith("data:"):
                            stripped = stripped[len("data:"):].strip()
                        if not stripped or stripped == "[DONE]":
                            if stripped == "[DONE]":
                                yield LLMPullEvent(status="success", progress=100, done=True)
                                return
                            continue
                        try:
                            data = json.loads(stripped)
                        except json.JSONDecodeError:
                            continue
                        status = str(data.get("status") or "")
                        completed = data.get("completed") or data.get("downloaded")
                        total = data.get("total")
                        progress: Optional[int] = None
                        if (
                            isinstance(completed, (int, float))
                            and isinstance(total, (int, float))
                            and total
                        ):
                            progress = min(100, int(completed * 100 / total))
                        elif isinstance(data.get("progress"), (int, float)):
                            progress = max(0, min(100, int(data["progress"])))
                        done = status in {"success", "done", "completed"} or bool(data.get("done"))
                        yield LLMPullEvent(status=status or "", progress=progress, done=done)
                        if done:
                            return
                    # Stream eindigde zonder expliciete success; beschouw als voltooid.
                    yield LLMPullEvent(status="success", progress=100, done=True)
        except httpx.HTTPError as exc:
            yield LLMPullEvent(
                status=f"Lemonade pull faalde: {exc}",
                done=True,
                error=str(exc),
            )

    def persist_model(self, model: str) -> None:
        persist_env_var("LEMONADE_MODEL", model)

    def apply_model(self, model: str) -> None:
        settings.lemonade_model = model
        if model and model not in settings.lemonade_models:
            settings.lemonade_models.insert(0, model)
