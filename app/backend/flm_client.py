"""
FastFlowLM (FLM) client implementation.

Uses the OpenAI-compatible API exposed by FLM on port 52625.
Model management (pull, list, serve) is done via the ``flm`` CLI
because FLM does not expose management endpoints over HTTP.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import TYPE_CHECKING, AsyncIterator, Optional, Sequence

import httpx
from openai import AsyncOpenAI

from .llm_client import (
    LLMBackendError,
    LLMClient,
    LLMResponse,
    ModelPullProgress,
    StreamToken,
    split_thinking_tags,
)

if TYPE_CHECKING:
    from .settings import Settings

logger = logging.getLogger(__name__)


class FLMClient(LLMClient):
    """LLM client backed by a local FastFlowLM server (NPU inference)."""

    def __init__(self, settings: "Settings") -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            base_url=settings.flm_base_url,
            api_key=settings.flm_api_key,
        )
        self._serve_process: Optional[asyncio.subprocess.Process] = None

    # -- internal helpers ---------------------------------------------------

    def _build_messages(
        self,
        prompt: str,
        images: Optional[Sequence[str]] = None,
    ) -> list[dict]:
        """Convert a prompt string (+ optional images) to OpenAI messages format."""
        if not images:
            return [{"role": "user", "content": prompt}]
        content: list[dict] = [{"type": "text", "text": prompt}]
        for img_b64 in images:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
            })
        return [{"role": "user", "content": content}]

    # -- LLMClient interface ------------------------------------------------

    async def generate(
        self,
        prompt: str,
        *,
        images: Optional[Sequence[str]] = None,
        thinking: Optional[bool] = None,
        options: Optional[dict] = None,
    ) -> LLMResponse:
        messages = self._build_messages(prompt, images)
        model = self._settings.flm_model

        extra_kwargs: dict = {}
        if options and "num_predict" in options:
            extra_kwargs["max_tokens"] = options["num_predict"]

        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                stream=False,
                timeout=self._settings.flm_timeout,
                **extra_kwargs,
            )
            raw_text = response.choices[0].message.content or ""
            thinking_text, message = split_thinking_tags(raw_text)
            return LLMResponse(message=message, thinking=thinking_text)
        except Exception as exc:
            is_timeout = "timeout" in str(exc).lower()
            raise LLMBackendError(
                f"FastFlowLM fout: {exc}",
                backend="flm",
                is_timeout=is_timeout,
            ) from exc

    async def stream_generate(
        self,
        prompt: str,
        *,
        images: Optional[Sequence[str]] = None,
        thinking: Optional[bool] = None,
    ) -> AsyncIterator[StreamToken]:
        messages = self._build_messages(prompt, images)
        model = self._settings.flm_model

        try:
            stream = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                timeout=self._settings.flm_timeout,
            )
            # Track <think> state for inline parsing during streaming
            in_think = False
            think_buffer = ""

            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue
                content = delta.content or ""
                if not content:
                    # Check for finish_reason
                    finish = chunk.choices[0].finish_reason if chunk.choices else None
                    if finish:
                        yield StreamToken(done=True)
                        return
                    continue

                # Handle inline <think> tags in streamed content
                # Buffer content to detect tag boundaries
                token = ""
                thinking_token = ""

                if in_think:
                    # We're inside a <think> block
                    if "</think>" in content:
                        parts = content.split("</think>", 1)
                        think_buffer += parts[0]
                        thinking_token = think_buffer
                        think_buffer = ""
                        in_think = False
                        # Remainder after </think> is regular content
                        if parts[1]:
                            token = parts[1]
                    else:
                        think_buffer += content
                        thinking_token = content
                elif "<think>" in content:
                    parts = content.split("<think>", 1)
                    if parts[0]:
                        token = parts[0]
                    in_think = True
                    think_buffer = parts[1] if len(parts) > 1 else ""
                    if think_buffer:
                        thinking_token = think_buffer
                        think_buffer = ""
                else:
                    token = content

                if token or thinking_token:
                    yield StreamToken(token=token, thinking=thinking_token, done=False)

            # End of stream
            yield StreamToken(done=True)

        except Exception as exc:
            is_timeout = "timeout" in str(exc).lower()
            raise LLMBackendError(
                f"FastFlowLM streaming fout: {exc}",
                backend="flm",
                is_timeout=is_timeout,
            ) from exc

    async def list_models(self) -> list[str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "flm", "list",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            lines = stdout.decode("utf-8", errors="replace").strip().splitlines()
            # flm list output: skip header line, parse model tags
            models = []
            for line in lines[1:]:  # Skip header
                parts = line.split()
                if parts:
                    models.append(parts[0])
            return models
        except Exception as exc:
            logger.warning("flm list mislukt: %s", exc)
            return []

    async def pull_model(self, model: str) -> AsyncIterator[ModelPullProgress]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "flm", "pull", model,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                # Parse progress from flm pull output
                # Typical output lines contain status/progress info
                yield ModelPullProgress(status=text, progress=0)

            await proc.wait()
            if proc.returncode == 0:
                yield ModelPullProgress(status="success", progress=100, done=True)
            else:
                raise LLMBackendError(
                    f"flm pull mislukt met exit code {proc.returncode}",
                    backend="flm",
                )
        except LLMBackendError:
            raise
        except Exception as exc:
            raise LLMBackendError(
                f"flm pull mislukt: {exc}",
                backend="flm",
            ) from exc

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self._settings.flm_base_url}/models")
                return response.status_code < 400
        except Exception:
            return False

    async def switch_model(self, model: str) -> None:
        """Switch FLM to serve a different model.

        This requires stopping the current ``flm serve`` process and
        starting a new one with the requested model tag.
        """
        # First pull the model if needed
        async for p in self.pull_model(model):
            if p.done:
                break

        # Try to stop existing flm serve via systemctl first
        try:
            proc = await asyncio.create_subprocess_exec(
                "systemctl", "--user", "restart", "aitje-flm",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except Exception:
            # If systemctl fails, try killing and restarting manually
            if self._serve_process and self._serve_process.returncode is None:
                try:
                    self._serve_process.send_signal(signal.SIGTERM)
                    await asyncio.wait_for(self._serve_process.wait(), timeout=10)
                except Exception:
                    self._serve_process.kill()

            self._serve_process = await asyncio.create_subprocess_exec(
                "flm", "serve", model,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

        # Wait for health check to pass
        for _ in range(30):
            await asyncio.sleep(1)
            if await self.health_check():
                return
        raise LLMBackendError(
            f"FLM kwam niet op na model switch naar '{model}'",
            backend="flm",
        )

    @property
    def current_model(self) -> str:
        return self._settings.flm_model

    @property
    def backend_name(self) -> str:
        return "FastFlowLM"
