import logging
import math
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional, Sequence
import httpx

from .contacts_repo import ContactsRepository
from .devices_repo import DevicesRepository
from .schemas import ChatMessage, ChatRequest, Contact, Device
from .settings import settings
from .translations import t, get_current_language

logger = logging.getLogger(__name__)

MAX_CONTEXT_ITEMS = 3
MIN_CONTEXT_SCORE = 0.35
PROMPT_TEMPLATE_PATH = Path(__file__).with_name("prompt.txt")
PROMPT_LOG_PATH = Path(__file__).resolve().parents[2] / "promptlog.log"
_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


contacts_repo = ContactsRepository()
devices_repo = DevicesRepository()


def describe_contact(contact: Contact) -> str:
    company = f" ({contact.company})" if contact.company else ""
    location_bits = [
        contact.location_label or "",
        contact.location_street or "",
        contact.location_city or "",
        contact.location_region or "",
        contact.location_country or "",
    ]
    location_text = ", ".join(bit for bit in location_bits if bit)
    if not location_text and contact.location_context:
        location_text = contact.location_context
    coords = ""
    if contact.location_lat is not None and contact.location_lon is not None:
        coords = f"{contact.location_lat:.5f}, {contact.location_lon:.5f}"
    lines = [
        f"{contact.name}{company}",
        f"  ✉ {contact.email}" if contact.email else "",
        f"  ☎ {contact.phone}" if contact.phone else "",
        f"  ❝ {contact.notes}" if contact.notes else "",
        f"  📍 {location_text}" if location_text else "",
        f"     ({coords})" if coords else "",
    ]
    return "\n".join(line for line in lines if line)


def describe_device(device: Device) -> str:
    lines = [
        f"{device.user_name} ({device.device_name})",
        f"  ✉ {device.email}" if device.email else "",
        f"  ☎ {device.phone}" if device.phone else "",
    ]
    return "\n".join(line for line in lines if line)


def _flatten_multiline(text: str) -> str:
    return " ".join(line.strip() for line in text.splitlines() if line.strip())


def _gather_context_lines(prompt_text: str) -> list[str]:
    scored: list[tuple[str, str, float]] = []
    contact_hits = contacts_repo.search_contacts(prompt_text, limit=5)
    if not contact_hits and hasattr(contacts_repo, "keyword_search_contacts"):
        contact_hits = contacts_repo.keyword_search_contacts(prompt_text, limit=5)
    for contact, score in contact_hits:
        scored.append(
            (
                "contact",
                _flatten_multiline(describe_contact(contact)),
                float(score or 0.0),
            )
        )

    device_hits = devices_repo.search_devices(prompt_text, limit=5)
    for device, score in device_hits:
        scored.append(
            (
                "device",
                _flatten_multiline(describe_device(device)),
                float(score or 0.0),
            )
        )

    if not scored:
        return []

    scored.sort(key=lambda item: item[2], reverse=True)
    best_score = scored[0][2]
    threshold = max(MIN_CONTEXT_SCORE, best_score * 0.7)
    filtered = [item for item in scored if item[2] >= threshold]
    limited = filtered[:MAX_CONTEXT_ITEMS]
    lines: list[str] = []
    for idx, (kind, desc, score) in enumerate(limited, 1):
        lines.append(f"{idx}. [{kind}] score {score:.3f}: {desc}")
    return lines


def _prompt_template() -> str:
    """Get the prompt template - NOT cached to allow language changes."""
    try:
        template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8").strip()
        # If file exists but we're in English mode, use English template
        if get_current_language() == "en":
            return t("prompt_default_template")
        return template
    except FileNotFoundError:
        return t("prompt_default_template")


def _format_history_lines(history: Optional[Sequence[ChatMessage]]) -> list[str]:
    if not history:
        return []
    lines: list[str] = []
    for idx, message in enumerate(history, 1):
        role = (message.role or "").lower()
        if role == "assistant":
            speaker = t("speaker_assistant")
        elif role == "system":
            speaker = t("speaker_system")
        else:
            speaker = t("speaker_user")
        content = _flatten_multiline(message.content or "")
        if not content:
            continue
        lines.append(f"{idx}. {speaker}: {content}")
    return lines


def build_augmented_prompt(
    user_prompt: str,
    history: Optional[Sequence[ChatMessage]] = None,
    images_count: int = 0,
) -> str:
    base_lines: list[str] = []

    history_lines = _format_history_lines(history)
    if history_lines:
        base_lines.append(t("previous_chat"))
        base_lines.extend(history_lines)
        base_lines.append("")

    base_lines.append(f"Huidige vraag: {user_prompt.strip()}")
    if images_count > 0:
        base_lines.append(f"Bijgevoegde afbeeldingen: {images_count}")
    context_lines = _gather_context_lines(user_prompt)
    if context_lines:
        base_lines.append("> context:")
        base_lines.extend(context_lines)
    template = _prompt_template()
    if template:
        base_lines.append("")
        base_lines.append(template)
    return "\n".join(base_lines).strip()


def prepare_prompt(
    req: ChatRequest,
    history: Optional[Sequence[ChatMessage]] = None,
) -> tuple[str, list[str]]:
    history_to_use = req.history if history is None else history
    images = normalize_images(req.images)
    final_prompt = build_augmented_prompt(
        req.prompt,
        history_to_use,
        images_count=len(images),
    )
    return final_prompt, images


def estimate_prompt_tokens(text: str) -> int:
    if not text:
        return 0
    wordish = len(_TOKEN_PATTERN.findall(text))
    char_est = math.ceil(len(text) / 4)
    byte_est = math.ceil(len(text.encode("utf-8")) / 4)
    # Heuristic: use the largest estimate to avoid undercounting.
    return max(wordish, char_est, byte_est)


def log_prompt(final_prompt: str) -> None:
    try:
        PROMPT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with PROMPT_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"[{datetime.utcnow().isoformat()}Z]\n{final_prompt}\n\n")
    except OSError:
        pass


def _build_summary_prompt(
    history_lines: Sequence[str],
    existing_summary: Optional[str] = None,
) -> str:
    lines: list[str] = [
        t("summary_instruction_1"),
        t("summary_instruction_2"),
        t("summary_instruction_3"),
        t("summary_instruction_4"),
        "",
    ]
    if existing_summary:
        lines.append(t("existing_summary"))
        lines.append(existing_summary.strip())
        lines.append("")
    lines.append(t("new_messages"))
    lines.extend(history_lines)
    return "\n".join(lines).strip()


def _fallback_summary(existing_summary: Optional[str], history_lines: Sequence[str]) -> str:
    combined = []
    if existing_summary:
        combined.append(existing_summary.strip())
    combined.append(" ".join(history_lines))
    text = " ".join(part for part in combined if part)
    return text[:1200].rstrip()


async def summarize_history(
    history: Optional[Sequence[ChatMessage]] = None,
    existing_summary: Optional[str] = None,
) -> str:
    history_lines = _format_history_lines(history)
    if not history_lines:
        return (existing_summary or "").strip()
    prompt = _build_summary_prompt(history_lines, existing_summary)
    try:
        summary = await _call_ollama(prompt, options={"num_predict": 256})
    except Exception as exc:  # pragma: no cover - netwerkfout
        logger.warning("%s %s", t("summary_failed"), exc)
        summary = _fallback_summary(existing_summary, history_lines)
    return (summary or "").strip()


def normalize_images(images: Optional[Sequence[str]]) -> list[str]:
    if not images:
        return []
    normalized: list[str] = []
    for item in images:
        if not item:
            continue
        data = item.strip()
        if not data:
            continue
        if data.startswith("data:"):
            _, _, b64 = data.partition("base64,")
            if not b64:
                continue
            data = b64.strip()
        normalized.append(data)
    return normalized


async def _call_ollama(
    prompt: str,
    options: Optional[dict] = None,
    images: Optional[Sequence[str]] = None,
) -> str:
    ollama_url = f"{settings.ollama_base_url}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }
    if images:
        payload["images"] = list(images)
    max_context = settings.ollama_max_context.get(settings.ollama_model)
    if isinstance(max_context, int) and max_context > 0:
        payload["options"] = {"num_ctx": max_context}
    if options:
        if "options" in payload:
            payload["options"].update(options)
        else:
            payload["options"] = dict(options)
    async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
        response = await client.post(ollama_url, json=payload)
        response.raise_for_status()
        data = response.json()
        return (data.get("response") or "").strip()


def _fallback_response(original_prompt: str) -> str:
    return (
        f"{t('ollama_not_available')} "
        f"{t('ollama_no_response', url=settings.ollama_base_url, model=settings.ollama_model)} "
        f"'{original_prompt}'. "
        f"{t('ollama_check_service')}"
    )


async def handle_ask(
    req: ChatRequest,
    history: Optional[Sequence[ChatMessage]] = None,
    final_prompt: Optional[str] = None,
    images: Optional[Sequence[str]] = None,
) -> dict:
    history_to_use = req.history if history is None else history
    if images is None:
        images = normalize_images(req.images)
    if final_prompt is None:
        final_prompt = build_augmented_prompt(
            req.prompt,
            history_to_use,
            images_count=len(images),
        )
    log_prompt(final_prompt)
    try:
        message = await _call_ollama(final_prompt, images=images)
    except Exception as exc:  # pragma: no cover - netwerkfout
        logger.warning(
            "Kan niet verbinden met Ollama (url=%s, model=%s): %s",
            settings.ollama_base_url,
            settings.ollama_model,
            exc,
        )
        message = _fallback_response(req.prompt)
    if not message:
        message = t("no_response_generated")
    return {"message": message}
