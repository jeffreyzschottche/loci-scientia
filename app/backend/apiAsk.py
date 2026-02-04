import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
import httpx

from .contacts_repo import ContactsRepository
from .devices_repo import DevicesRepository
from .knowledge_repository import KnowledgeRepository
from .schemas import ChatMessage, ChatRequest, Contact, Device
from .settings import settings
from .translations import t, get_current_language

logger = logging.getLogger(__name__)

MAX_CONTEXT_ITEMS = 3
MIN_CONTEXT_SCORE = 0.25
KNOWLEDGE_SNIPPET_LENGTH = 999999  # Characters to include from each knowledge chunk
PROMPT_TEMPLATE_PATH = Path(__file__).with_name("prompt.txt")
PROMPT_LOG_PATH = Path(__file__).resolve().parents[2] / "promptlog.log"
API_PROMPT_LOG_PATH = Path(__file__).resolve().parents[2] / "apiprompt.log"


@dataclass
class ApiLogEntry:
    """Structured log entry for API conversations."""
    conversation_id: str
    request_id: str
    timestamp: str
    source: str  # "local" or "api"
    endpoint: str  # "/api/v1/ask" or "/api/v1/ask/stream"
    user_name: Optional[str] = None
    device_id: Optional[str] = None
    token_prefix: Optional[str] = None
    original_prompt: str = ""
    new_chat: bool = False  # True if this request cleared the history
    history_length: int = 0
    images_count: int = 0
    context_contacts: List[Dict[str, Any]] = field(default_factory=list)
    context_devices: List[Dict[str, Any]] = field(default_factory=list)
    context_knowledge: List[Dict[str, Any]] = field(default_factory=list)
    final_prompt_length: int = 0
    response_preview: str = ""
    error: Optional[str] = None


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())[:8]


def generate_conversation_id(token: str) -> str:
    """Generate a conversation ID based on token (first 8 chars of hash)."""
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()[:8]


def log_api_request(entry: ApiLogEntry) -> None:
    """Write structured API log entry to apiprompt.log."""
    try:
        API_PROMPT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        separator = "=" * 80
        new_chat_marker = " [NEW CHAT]" if entry.new_chat else ""
        lines = [
            separator,
            f"[{entry.timestamp}]{new_chat_marker}",
            f"Conversation ID: {entry.conversation_id}",
            f"Request ID:      {entry.request_id}",
            f"Source:          {entry.source}",
            f"Endpoint:        {entry.endpoint}",
            f"User:            {entry.user_name or 'unknown'}",
            f"Device ID:       {entry.device_id or 'unknown'}",
            f"Token:           {entry.token_prefix or 'unknown'}...",
            f"New Chat:        {entry.new_chat}",
            "",
            f"--- Original Prompt ({len(entry.original_prompt)} chars) ---",
            entry.original_prompt[:500] + ("..." if len(entry.original_prompt) > 500 else ""),
            "",
            f"History messages: {entry.history_length}",
            f"Images attached:  {entry.images_count}",
            "",
            "--- Context Found ---",
            f"Contacts ({len(entry.context_contacts)}):",
        ]

        if entry.context_contacts:
            for c in entry.context_contacts:
                lines.append(f"  - {c.get('name', '?')} (score: {c.get('score', 0):.3f})")
        else:
            lines.append("  (none)")

        lines.append(f"Devices ({len(entry.context_devices)}):")
        if entry.context_devices:
            for d in entry.context_devices:
                lines.append(f"  - {d.get('user_name', '?')} / {d.get('device_name', '?')} (score: {d.get('score', 0):.3f})")
        else:
            lines.append("  (none)")

        lines.append(f"Knowledge ({len(entry.context_knowledge)}):")
        if entry.context_knowledge:
            for k in entry.context_knowledge:
                lines.append(f"  - [{k.get('doc_id', '?')}] {k.get('title', '?')} (score: {k.get('score', 0):.3f})")
                lines.append(f"    {k.get('snippet', '')}")
        else:
            lines.append("  (none)")

        lines.extend([
            "",
            f"Final prompt length: {entry.final_prompt_length} chars",
        ])

        if entry.response_preview:
            lines.extend([
                "",
                "--- Response Preview ---",
                entry.response_preview[:300] + ("..." if len(entry.response_preview) > 300 else ""),
            ])

        if entry.error:
            lines.extend([
                "",
                f"--- ERROR ---",
                entry.error,
            ])

        lines.append("")

        with API_PROMPT_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    except OSError as exc:
        logger.warning("Kon API log niet schrijven: %s", exc)


contacts_repo = ContactsRepository()
devices_repo = DevicesRepository()
knowledge_repo = KnowledgeRepository()


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

    knowledge_hits = knowledge_repo.search_chunks(prompt_text, limit=5)
    for payload, score in knowledge_hits:
        text = _flatten_multiline(str(payload.get("text") or ""))
        if not text:
            continue
        title = payload.get("document_title") or payload.get("doc_id") or "doc"
        prefix = f"{title}"
        snippet = text[:KNOWLEDGE_SNIPPET_LENGTH] + ("…" if len(text) > KNOWLEDGE_SNIPPET_LENGTH else "")
        desc = f"{prefix}: {snippet}"
        scored.append(("knowledge", desc, float(score or 0.0)))

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


def _gather_context_with_details(prompt_text: str) -> tuple[list[str], Dict[str, List]]:
    """Gather context lines AND detailed info for logging."""
    scored: list[tuple[str, str, float]] = []
    details: Dict[str, List] = {
        "contacts": [],
        "devices": [],
        "knowledge": [],
    }

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
        details["contacts"].append({
            "name": contact.name,
            "score": float(score or 0.0),
        })

    device_hits = devices_repo.search_devices(prompt_text, limit=5)
    for device, score in device_hits:
        scored.append(
            (
                "device",
                _flatten_multiline(describe_device(device)),
                float(score or 0.0),
            )
        )
        details["devices"].append({
            "user_name": device.user_name,
            "device_name": device.device_name,
            "score": float(score or 0.0),
        })

    knowledge_hits = knowledge_repo.search_chunks(prompt_text, limit=5)
    for payload, score in knowledge_hits:
        text = _flatten_multiline(str(payload.get("text") or ""))
        if not text:
            continue
        title = payload.get("document_title") or payload.get("doc_id") or "doc"
        prefix = f"{title}"
        snippet = text[:KNOWLEDGE_SNIPPET_LENGTH] + ("..." if len(text) > KNOWLEDGE_SNIPPET_LENGTH else "")
        desc = f"{prefix}: {snippet}"
        scored.append(("knowledge", desc, float(score or 0.0)))
        details["knowledge"].append({
            "doc_id": payload.get("doc_id"),
            "title": title,
            "score": float(score or 0.0),
            "snippet": text[:100] + ("..." if len(text) > 100 else ""),
        })

    if not scored:
        return [], details

    scored.sort(key=lambda item: item[2], reverse=True)
    best_score = scored[0][2]
    threshold = max(MIN_CONTEXT_SCORE, best_score * 0.7)
    filtered = [item for item in scored if item[2] >= threshold]
    limited = filtered[:MAX_CONTEXT_ITEMS]
    lines: list[str] = []
    for idx, (kind, desc, score) in enumerate(limited, 1):
        lines.append(f"{idx}. [{kind}] score {score:.3f}: {desc}")
    return lines, details


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


def build_augmented_prompt_with_details(
    user_prompt: str,
    history: Optional[Sequence[ChatMessage]] = None,
    images_count: int = 0,
) -> tuple[str, Dict[str, List]]:
    """Build augmented prompt AND return context details for logging."""
    base_lines: list[str] = []

    history_lines = _format_history_lines(history)
    if history_lines:
        base_lines.append(t("previous_chat"))
        base_lines.extend(history_lines)
        base_lines.append("")

    base_lines.append(f"Huidige vraag: {user_prompt.strip()}")
    if images_count > 0:
        base_lines.append(f"Bijgevoegde afbeeldingen: {images_count}")

    context_lines, context_details = _gather_context_with_details(user_prompt)
    if context_lines:
        base_lines.append("> context:")
        base_lines.extend(context_lines)

    template = _prompt_template()
    if template:
        base_lines.append("")
        base_lines.append(template)

    return "\n".join(base_lines).strip(), context_details


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
) -> dict:
    history_to_use = req.history if history is None else history
    images = normalize_images(req.images)
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
