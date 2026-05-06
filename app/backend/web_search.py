"""SearXNG web search client.

Calls a self-hosted SearXNG instance with JSON output enabled and returns a
trimmed list of results suitable for prompt augmentation and UI display.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Optional

import httpx

from .settings import settings

logger = logging.getLogger(__name__)

MAX_SNIPPET_CHARS = 320
MAX_TITLE_CHARS = 200


@dataclass
class WebSearchResult:
    title: str
    url: str
    snippet: str
    engine: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class WebSearchUnavailable(RuntimeError):
    """Raised when SearXNG is not configured or not reachable."""


def is_configured() -> bool:
    return bool(settings.searxng_url)


def _trim(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _parse_results(payload: dict[str, Any], limit: int) -> list[WebSearchResult]:
    items = payload.get("results") or []
    results: list[WebSearchResult] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        title = _trim(str(item.get("title") or url), MAX_TITLE_CHARS)
        snippet = _trim(str(item.get("content") or ""), MAX_SNIPPET_CHARS)
        engine = str(item.get("engine") or "").strip()
        results.append(WebSearchResult(title=title, url=url, snippet=snippet, engine=engine))
        if len(results) >= limit:
            break
    return results


async def search(
    query: str,
    *,
    limit: Optional[int] = None,
    language: Optional[str] = None,
) -> list[WebSearchResult]:
    if not is_configured():
        raise WebSearchUnavailable("SEARXNG_URL is not configured")
    query = (query or "").strip()
    if not query:
        return []

    max_results = limit or settings.searxng_max_results
    params = {
        "q": query,
        "format": "json",
        "language": language or settings.searxng_language,
        "safesearch": settings.searxng_safesearch,
    }
    url = f"{settings.searxng_url}/search"
    headers = {"Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=settings.searxng_timeout) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        logger.warning("SearXNG request failed (url=%s): %s", url, exc)
        raise WebSearchUnavailable(str(exc)) from exc
    except ValueError as exc:
        logger.warning("SearXNG returned invalid JSON: %s", exc)
        raise WebSearchUnavailable("invalid SearXNG response") from exc

    if not isinstance(payload, dict):
        raise WebSearchUnavailable("unexpected SearXNG payload shape")
    return _parse_results(payload, max_results)


def format_results_for_prompt(results: list[WebSearchResult]) -> list[str]:
    if not results:
        return []
    lines: list[str] = ["> web search:"]
    for idx, item in enumerate(results, 1):
        snippet = item.snippet or "(geen samenvatting)"
        lines.append(f"{idx}. {item.title} — {item.url}")
        lines.append(f"   {snippet}")
    return lines


def results_to_payload(results: list[WebSearchResult]) -> list[dict[str, Any]]:
    return [item.to_dict() for item in results]
