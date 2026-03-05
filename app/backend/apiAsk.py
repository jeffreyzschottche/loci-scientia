import base64
import binascii
import io
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
from .schemas import ChatMessage, ChatRequest, Contact, Device, PromptDocument
from .settings import settings
from .translations import t, get_current_language

logger = logging.getLogger(__name__)

MAX_CONTEXT_ITEMS = 3
MIN_CONTEXT_SCORE = 0.25
KNOWLEDGE_SNIPPET_LENGTH = 999999  # Characters to include from each knowledge chunk
PROMPT_TEMPLATE_PATH = Path(__file__).with_name("prompt.txt")
PROMPT_LOG_PATH = Path(__file__).resolve().parents[2] / "promptlog.log"
API_PROMPT_LOG_PATH = Path(__file__).resolve().parents[2] / "apiprompt.log"
MAX_DOCUMENTS_PER_REQUEST = 4
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_TOTAL_DOCUMENT_BYTES = 20 * 1024 * 1024
MAX_DOCUMENT_CHARS = 40_000
MAX_TOTAL_DOCUMENT_CHARS = 120_000


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
    documents_count: int = 0
    context_contacts: List[Dict[str, Any]] = field(default_factory=list)
    context_devices: List[Dict[str, Any]] = field(default_factory=list)
    context_knowledge: List[Dict[str, Any]] = field(default_factory=list)
    context_documents: List[Dict[str, Any]] = field(default_factory=list)
    final_prompt_length: int = 0
    response_preview: str = ""
    error: Optional[str] = None


@dataclass
class ParsedDocument:
    filename: str
    file_type: str
    text: str
    source_bytes: int
    truncated: bool = False


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
            f"Documents:        {entry.documents_count}",
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

        lines.append(f"Documents ({len(entry.context_documents)}):")
        if entry.context_documents:
            for d in entry.context_documents:
                lines.append(
                    f"  - {d.get('filename', '?')} [{d.get('file_type', '?')}] "
                    f"{d.get('chars', 0)} chars / {d.get('bytes', 0)} bytes"
                )
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


def _clean_document_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines())


def _strip_data_url(value: str) -> str:
    raw = (value or "").strip()
    if not raw.startswith("data:"):
        return raw
    _, _, b64 = raw.partition("base64,")
    return b64.strip() if b64 else ""


def _detect_document_type(document: PromptDocument) -> str:
    file_name = (document.filename or "").strip().lower()
    if "." in file_name:
        ext = file_name.rsplit(".", 1)[-1]
        if ext in {"pdf", "docx", "xls", "xlsx", "txt"}:
            return ext
    content_type = (document.content_type or "").strip().lower()
    type_map = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/msword": "docx",
        "application/vnd.ms-excel": "xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "text/plain": "txt",
    }
    for key, value in type_map.items():
        if key in content_type:
            return value
    return ""


def _decode_base64_document(document: PromptDocument) -> bytes:
    raw = _strip_data_url(document.data)
    if not raw:
        raise ValueError(f"Document '{document.filename}' has no base64 payload.")
    try:
        return base64.b64decode(raw, validate=True)
    except binascii.Error as exc:
        raise ValueError(f"Document '{document.filename}' contains invalid base64 data.") from exc


def _extract_pdf_text(source: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - dependency absence
        raise ValueError("PDF parsing requires 'pypdf'. Install backend dependencies first.") from exc

    reader = PdfReader(io.BytesIO(source))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _extract_docx_text(source: bytes) -> str:
    try:
        from docx import Document
    except Exception as exc:  # pragma: no cover - dependency absence
        raise ValueError("DOCX parsing requires 'python-docx'. Install backend dependencies first.") from exc

    document = Document(io.BytesIO(source))
    parts: list[str] = []
    for paragraph in document.paragraphs:
        if paragraph.text:
            parts.append(paragraph.text)
    for table in document.tables:
        for row in table.rows:
            cells = [str(cell.text).strip() for cell in row.cells if str(cell.text).strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def _extract_xlsx_text(source: bytes) -> str:
    try:
        from openpyxl import load_workbook
    except Exception as exc:  # pragma: no cover - dependency absence
        raise ValueError("XLSX parsing requires 'openpyxl'. Install backend dependencies first.") from exc

    workbook = load_workbook(filename=io.BytesIO(source), read_only=True, data_only=True)
    parts: list[str] = []
    for sheet in workbook.worksheets:
        parts.append(f"Sheet: {sheet.title}")
        for row in sheet.iter_rows(values_only=True):
            cells = [str(cell).strip() for cell in row if cell not in (None, "")]
            if cells:
                parts.append(" | ".join(cells))
    workbook.close()
    return "\n".join(parts)


def _extract_xls_text(source: bytes) -> str:
    try:
        import xlrd
    except Exception as exc:  # pragma: no cover - dependency absence
        raise ValueError("XLS parsing requires 'xlrd'. Install backend dependencies first.") from exc

    workbook = xlrd.open_workbook(file_contents=source, on_demand=True)
    parts: list[str] = []
    for sheet in workbook.sheets():
        parts.append(f"Sheet: {sheet.name}")
        for row_idx in range(sheet.nrows):
            cells: list[str] = []
            for value in sheet.row_values(row_idx):
                cell_text = str(value).strip()
                if cell_text:
                    cells.append(cell_text)
            if cells:
                parts.append(" | ".join(cells))
    workbook.release_resources()
    return "\n".join(parts)


def _extract_txt_text(source: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            return source.decode(encoding)
        except UnicodeDecodeError:
            continue
    return source.decode("utf-8", errors="replace")


def _extract_document_text(file_type: str, source: bytes) -> str:
    if file_type == "pdf":
        return _extract_pdf_text(source)
    if file_type == "docx":
        return _extract_docx_text(source)
    if file_type == "xlsx":
        return _extract_xlsx_text(source)
    if file_type == "xls":
        return _extract_xls_text(source)
    if file_type == "txt":
        return _extract_txt_text(source)
    raise ValueError(f"Unsupported document type: {file_type}")


def normalize_documents(documents: Optional[Sequence[PromptDocument]]) -> list[ParsedDocument]:
    if not documents:
        return []
    if len(documents) > MAX_DOCUMENTS_PER_REQUEST:
        raise ValueError(
            f"Too many documents in one request ({len(documents)}). "
            f"Maximum allowed is {MAX_DOCUMENTS_PER_REQUEST}."
        )

    parsed_documents: list[ParsedDocument] = []
    total_bytes = 0
    total_chars = 0

    for index, document in enumerate(documents, 1):
        filename = (document.filename or "").strip() or f"document-{index}"
        file_type = _detect_document_type(document)
        if not file_type:
            raise ValueError(
                f"Document '{filename}' is not supported. Allowed: pdf, docx, xls, xlsx, txt."
            )

        source = _decode_base64_document(document)
        source_bytes = len(source)
        if source_bytes > MAX_DOCUMENT_BYTES:
            raise ValueError(
                f"Document '{filename}' is too large ({source_bytes} bytes). "
                f"Maximum per document is {MAX_DOCUMENT_BYTES} bytes."
            )

        total_bytes += source_bytes
        if total_bytes > MAX_TOTAL_DOCUMENT_BYTES:
            raise ValueError(
                f"Total document payload is too large ({total_bytes} bytes). "
                f"Maximum per request is {MAX_TOTAL_DOCUMENT_BYTES} bytes."
            )

        extracted = _clean_document_text(_extract_document_text(file_type, source)).strip()
        if not extracted:
            continue

        truncated = False
        if len(extracted) > MAX_DOCUMENT_CHARS:
            extracted = extracted[:MAX_DOCUMENT_CHARS]
            truncated = True

        remaining_chars = MAX_TOTAL_DOCUMENT_CHARS - total_chars
        if remaining_chars <= 0:
            break
        if len(extracted) > remaining_chars:
            extracted = extracted[:remaining_chars]
            truncated = True

        total_chars += len(extracted)
        parsed_documents.append(
            ParsedDocument(
                filename=filename,
                file_type=file_type,
                text=extracted,
                source_bytes=source_bytes,
                truncated=truncated,
            )
        )

    return parsed_documents


def _format_document_context_lines(documents: Optional[Sequence[ParsedDocument]]) -> list[str]:
    if not documents:
        return []
    lines: list[str] = []
    for index, document in enumerate(documents, 1):
        lines.append(f"{index}. [{document.file_type}] {document.filename}")
        lines.append(document.text)
    return lines


def _document_details(documents: Optional[Sequence[ParsedDocument]]) -> List[Dict[str, Any]]:
    if not documents:
        return []
    details: List[Dict[str, Any]] = []
    for document in documents:
        details.append(
            {
                "filename": document.filename,
                "file_type": document.file_type,
                "bytes": document.source_bytes,
                "chars": len(document.text),
                "truncated": document.truncated,
            }
        )
    return details


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
    documents: Optional[Sequence[ParsedDocument]] = None,
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
    document_lines = _format_document_context_lines(documents)
    if document_lines:
        base_lines.append("> document context:")
        base_lines.extend(document_lines)
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
    documents: Optional[Sequence[ParsedDocument]] = None,
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
    document_lines = _format_document_context_lines(documents)
    if document_lines:
        base_lines.append("> document context:")
        base_lines.extend(document_lines)

    context_lines, context_details = _gather_context_with_details(user_prompt)
    context_details["documents"] = _document_details(documents)
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


def _fallback_timeout_response(original_prompt: str) -> str:
    timeout_seconds = f"{settings.ollama_timeout:g}"
    return (
        "[Ollama reageert te langzaam] "
        f"Geen antwoord ontvangen binnen {timeout_seconds}s van "
        f"{settings.ollama_base_url} met model '{settings.ollama_model}'. "
        f"Je vroeg: '{original_prompt}'. "
        "Dit gebeurt vaak bij een koude start of het laden van een groot model; probeer het opnieuw."
    )


async def handle_ask(
    req: ChatRequest,
    history: Optional[Sequence[ChatMessage]] = None,
    documents: Optional[Sequence[ParsedDocument]] = None,
    final_prompt_override: Optional[str] = None,
) -> dict:
    history_to_use = req.history if history is None else history
    images = normalize_images(req.images)
    final_prompt = final_prompt_override or build_augmented_prompt(
        req.prompt,
        history_to_use,
        images_count=len(images),
        documents=documents,
    )
    log_prompt(final_prompt)
    try:
        message = await _call_ollama(final_prompt, images=images)
    except httpx.TimeoutException as exc:  # pragma: no cover - netwerkfout
        logger.warning(
            "Timeout bij Ollama (timeout=%ss, url=%s, model=%s): %r",
            settings.ollama_timeout,
            settings.ollama_base_url,
            settings.ollama_model,
            exc,
        )
        message = _fallback_timeout_response(req.prompt)
    except httpx.RequestError as exc:  # pragma: no cover - netwerkfout
        logger.warning(
            "Kan niet verbinden met Ollama (url=%s, model=%s): %s",
            settings.ollama_base_url,
            settings.ollama_model,
            exc,
        )
        message = _fallback_response(req.prompt)
    except Exception as exc:  # pragma: no cover - netwerkfout
        logger.warning(
            "Onverwachte Ollama fout (url=%s, model=%s): %r",
            settings.ollama_base_url,
            settings.ollama_model,
            exc,
        )
        message = _fallback_response(req.prompt)
    if not message:
        message = t("no_response_generated")
    return {"message": message}
