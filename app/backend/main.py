import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock

import httpx
from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.concurrency import run_in_threadpool
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .auth_tokens import BearerTokenStore, TokenRecord
from .apiAsk import (
    ApiLogEntry,
    ParsedDocument,
    build_augmented_prompt_with_details,
    generate_conversation_id,
    generate_request_id,
    handle_ask,
    log_api_request,
    log_prompt,
    normalize_documents,
    normalize_images,
    prepare_prompt,
    summarize_history,
)
from .chat_history import ChatHistoryStore
from .admin_access import AdminTokenManager
from .contacts_repo import ContactsRepository
from .devices_repo import DevicesRepository
from .kennisbank_sync import read_sync_state, sync_kennisbank
from .knowledge_library import get_library_overview, load_document_detail
from .schemas import (
    BearerTokenResponse,
    ChatRequest,
    Contact,
    ContactCreate,
    ContactPatch,
    Device,
    DeviceCreate,
    DevicePatch,
    OllamaModelRequest,
    SignOnRequest,
    SupportAccessRequest,
    SupportAccessStatus,
)
from .settings import settings
from .support_access import SupportAccessError, SupportAccessManager

logger = logging.getLogger(__name__)
ENV_FILE_PATH = Path(
    os.environ.get(
        "AITJE_ENV_PATH",
        Path(__file__).resolve().parents[2] / ".env",
    )
).expanduser().resolve()

app = FastAPI(title="AITJE Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.offline_assets_dir and settings.offline_assets_dir.exists():
    fonts_dir = settings.offline_assets_dir / "fonts"
    sprites_dir = settings.offline_assets_dir / "sprites"
    if fonts_dir.exists():
        app.mount("/fonts", StaticFiles(directory=str(fonts_dir)), name="fonts")
    if sprites_dir.exists():
        app.mount("/sprites", StaticFiles(directory=str(sprites_dir)), name="sprites")

contacts_repo = ContactsRepository()
devices_repo = DevicesRepository()
token_store = BearerTokenStore()
chat_history = ChatHistoryStore(max_items=20)
ollama_switch_lock = asyncio.Lock()
support_access = SupportAccessManager()
admin_tokens = AdminTokenManager(
    token_store=token_store,
    admin_usernames=settings.admin_usernames,
)
admin_tokens.ensure()
summary_task: Optional[asyncio.Task] = None
last_prompt_at: Optional[datetime] = None
last_idle_summary_at: Optional[datetime] = None

SUMMARY_POLL_SECONDS = 60


class ApiStats:
    def __init__(self):
        self._lock = Lock()
        self._day = datetime.now(timezone.utc).date()
        self._requests_today = 0
        self._latency_total_ms = 0.0
        self._latency_count = 0
        self._active_ids: set[str] = set()

    def _rollover(self, now: datetime) -> None:
        today = now.date()
        if today == self._day:
            return
        self._day = today
        self._requests_today = 0
        self._latency_total_ms = 0.0
        self._latency_count = 0
        self._active_ids.clear()

    def record(self, path: str, auth_header: Optional[str], duration_ms: float) -> None:
        if not path.startswith("/api/v1/"):
            return
        now = datetime.now(timezone.utc)
        token_value = None
        if auth_header:
            scheme, _, value = auth_header.partition(" ")
            if scheme.lower() == "bearer" and value.strip():
                token_value = value.strip()
            else:
                token_value = auth_header.strip()
        with self._lock:
            self._rollover(now)
            self._requests_today += 1
            self._latency_total_ms += duration_ms
            self._latency_count += 1
            if token_value:
                token_hash = hashlib.sha256(token_value.encode("utf-8")).hexdigest()[:16]
                self._active_ids.add(token_hash)

    def snapshot(self) -> dict:
        now = datetime.now(timezone.utc)
        with self._lock:
            self._rollover(now)
            avg = (
                self._latency_total_ms / self._latency_count
                if self._latency_count
                else None
            )
            avg_ms = round(avg, 1) if avg is not None else None
            return {
                "date": self._day.isoformat(),
                "requests_today": self._requests_today,
                "active_users_today": len(self._active_ids),
                "avg_response_ms": avg_ms,
            }


api_stats = ApiStats()


def _extract_bearer_token(auth_header: Optional[str]) -> str:
    if not auth_header:
        raise HTTPException(status_code=401, detail="Bearer token vereist")
    scheme, _, value = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        raise HTTPException(status_code=401, detail="Ongeldig Authorization-headerformaat")
    return value.strip()


def require_token(authorization: Optional[str] = Header(default=None)) -> TokenRecord:
    token_value = _extract_bearer_token(authorization)
    record = token_store.validate(token_value)
    if record is None:
        raise HTTPException(status_code=401, detail="Bearer token ongeldig of verlopen")
    return record


def require_admin_token(record: TokenRecord = Depends(require_token)) -> TokenRecord:
    if (
        record.user_name not in settings.admin_usernames
        or record.device_id != admin_tokens.admin_device_id
    ):
        raise HTTPException(status_code=403, detail="Admin token vereist")
    return record


def _empty_sync_state() -> dict:
    return {
        "synced": False,
        "git": None,
        "qdrant": None,
        "sqlite": None,
        "stats": None,
        "synced_at": None,
    }


@app.middleware("http")
async def collect_api_stats(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        try:
            api_stats.record(
                request.url.path,
                request.headers.get("authorization"),
                duration_ms,
            )
        except Exception:  # pragma: no cover - best effort
            pass


def _mark_prompt_activity() -> None:
    global last_prompt_at
    last_prompt_at = datetime.now(timezone.utc)


def _format_prompt_for_history(prompt: str, images_count: int, documents_count: int = 0) -> str:
    clean = (prompt or "").strip()
    if not clean:
        return clean
    tags: list[str] = []
    if images_count > 0:
        tags.append(f"Afbeeldingen: {images_count}")
    if documents_count > 0:
        tags.append(f"Documenten: {documents_count}")
    if tags:
        return f"{clean}\n[{'; '.join(tags)}]"
    return clean


def _ensure_prompt_within_context(final_prompt: str) -> None:
    max_context = settings.ollama_max_context.get(settings.ollama_model)
    if not isinstance(max_context, int) or max_context <= 0:
        return
    estimated_tokens = estimate_prompt_tokens(final_prompt)
    if estimated_tokens > max_context:
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Context limit reached. Start a new session or delete some context from this prompt."
                ),
                "estimated_tokens": estimated_tokens,
                "max_context": max_context,
            },
        )


async def _run_summary_cycle() -> None:
    snapshots = chat_history.snapshot_pending()
    for snapshot in snapshots:
        try:
            summary = await summarize_history(
                snapshot.messages,
                existing_summary=snapshot.summary,
            )
        except Exception as exc:  # pragma: no cover - onverwachte fout
            logger.warning("Samenvatting maken faalde voor sessie %s: %s", snapshot.key, exc)
            continue
        if not summary:
            continue
        chat_history.apply_summary(
            snapshot.key,
            summary,
            snapshot.updated_at,
            snapshot.summarized_at,
        )


async def _maybe_run_idle_summary() -> None:
    global last_idle_summary_at
    if settings.chat_summary_idle_minutes <= 0:
        return
    if last_prompt_at is None:
        return
    idle_for = datetime.now(timezone.utc) - last_prompt_at
    if idle_for < timedelta(minutes=settings.chat_summary_idle_minutes):
        return
    if last_idle_summary_at and last_idle_summary_at >= last_prompt_at:
        return
    await _run_summary_cycle()
    last_idle_summary_at = datetime.now(timezone.utc)


async def _idle_summary_loop() -> None:
    if settings.chat_summary_idle_minutes <= 0:
        return
    while True:
        await _maybe_run_idle_summary()
        await asyncio.sleep(SUMMARY_POLL_SECONDS)


@app.on_event("startup")
async def start_idle_summary_task() -> None:
    global summary_task
    if settings.chat_summary_idle_minutes <= 0:
        return
    if summary_task is None or summary_task.done():
        summary_task = asyncio.create_task(_idle_summary_loop())


@app.on_event("shutdown")
async def stop_idle_summary_task() -> None:
    global summary_task
    if summary_task is None:
        return
    summary_task.cancel()
    try:
        await summary_task
    except asyncio.CancelledError:
        pass


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/stats")
def api_stats_snapshot(_: TokenRecord = Depends(require_admin_token)):
    return api_stats.snapshot()


async def _pull_ollama_model(model: str) -> None:
    success = False
    async for data in _stream_ollama_pull(model):
        if data.get("status") == "success":
            success = True
            break
    if not success:
        raise HTTPException(status_code=502, detail="Ollama pull beeindigd zonder succes-status")


async def _stream_ollama_pull(model: str):
    ollama_url = f"{settings.ollama_base_url}/api/pull"
    payload = {"name": model}

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", ollama_url, json=payload) as response:
                if response.status_code >= 400:
                    error_body = await response.aread()
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            f"Ollama pull faalde ({response.status_code}): "
                            f"{error_body.decode('utf-8', errors='replace').strip()}"
                        ),
                    )

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    yield data
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ollama pull faalde: {exc}") from exc


def _persist_ollama_model(model: str) -> None:
    if not ENV_FILE_PATH.exists():
        raise HTTPException(status_code=500, detail=f".env niet gevonden: {ENV_FILE_PATH}")
    try:
        content = ENV_FILE_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f".env lezen faalde: {exc}") from exc

    lines = content.splitlines(keepends=True)
    updated = False
    for idx, line in enumerate(lines):
        if line.startswith("OLLAMA_MODEL="):
            lines[idx] = f"OLLAMA_MODEL={model}\n"
            updated = True
            break
    if not updated:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] = lines[-1] + "\n"
        lines.append(f"OLLAMA_MODEL={model}\n")

    try:
        ENV_FILE_PATH.write_text("".join(lines), encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f".env schrijven faalde: {exc}") from exc


@app.get("/api/v1/ollama/models")
def list_ollama_models(_: TokenRecord = Depends(require_admin_token)):
    return {"current": settings.ollama_model, "available": settings.ollama_models}


@app.post("/api/v1/ollama/model")
async def set_ollama_model(req: OllamaModelRequest, _: TokenRecord = Depends(require_admin_token)):
    model = req.model.strip()
    if not model:
        raise HTTPException(status_code=400, detail="model ontbreekt")
    if model not in settings.ollama_models:
        raise HTTPException(status_code=400, detail="model niet toegestaan")

    async with ollama_switch_lock:
        if model != settings.ollama_model:
            await _pull_ollama_model(model)
            _persist_ollama_model(model)
            settings.ollama_model = model

    return {"current": settings.ollama_model}


@app.post("/api/v1/ollama/model/stream")
async def set_ollama_model_stream(
    req: OllamaModelRequest,
    _: TokenRecord = Depends(require_admin_token),
):
    model = req.model.strip()
    if not model:
        raise HTTPException(status_code=400, detail="model ontbreekt")
    if model not in settings.ollama_models:
        raise HTTPException(status_code=400, detail="model niet toegestaan")

    async def event_stream():
        async with ollama_switch_lock:
            if model == settings.ollama_model:
                payload = json.dumps(
                    {"progress": 100, "status": "Model is al actief", "done": True, "current": model}
                )
                yield f"data: {payload}\n\n"
                return

            progress = 0
            status = "Pull starten..."
            payload = json.dumps({"progress": progress, "status": status})
            yield f"data: {payload}\n\n"

            try:
                async for data in _stream_ollama_pull(model):
                    status = data.get("status") or status
                    completed = data.get("completed")
                    total = data.get("total")
                    if isinstance(completed, (int, float)) and isinstance(total, (int, float)) and total:
                        progress = min(100, int(completed * 100 / total))
                    payload = json.dumps({"progress": progress, "status": status})
                    yield f"data: {payload}\n\n"
                    if data.get("status") == "success":
                        break
            except HTTPException as exc:
                payload = json.dumps({"error": exc.detail, "done": True})
                yield f"data: {payload}\n\n"
                return

            try:
                _persist_ollama_model(model)
            except HTTPException as exc:
                payload = json.dumps({"error": exc.detail, "done": True})
                yield f"data: {payload}\n\n"
                return
            settings.ollama_model = model
            payload = json.dumps(
                {"progress": 100, "status": "Model actief", "done": True, "current": model}
            )
            yield f"data: {payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/v1/support/ssh", response_model=SupportAccessStatus)
def support_access_status(_: TokenRecord = Depends(require_admin_token)):
    return support_access.status().to_response()


@app.post("/api/v1/support/ssh/enable", response_model=SupportAccessStatus)
def support_access_enable(
    req: SupportAccessRequest,
    record: TokenRecord = Depends(require_admin_token),
):
    try:
        state = support_access.enable(
            duration_minutes=req.duration_minutes,
            public_key=req.public_key,
            ticket=req.ticket,
            requested_by=record.user_name,
        )
    except SupportAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return state.to_response()


@app.post("/api/v1/support/ssh/disable", response_model=SupportAccessStatus)
def support_access_disable(
    record: TokenRecord = Depends(require_admin_token),
):
    try:
        state = support_access.disable(
            requested_by=record.user_name,
            reason="manual",
            force=False,
        )
    except SupportAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return state.to_response()


@app.get("/api/v1/kennisbank/sync-state")
def kennisbank_sync_state(_: TokenRecord = Depends(require_admin_token)):
    state = read_sync_state()
    if not state:
        return _empty_sync_state()
    return {**state, "synced": True}


@app.post("/api/v1/kennisbank/sync")
async def kennisbank_sync_endpoint(_: TokenRecord = Depends(require_admin_token)):
    try:
        result = await run_in_threadpool(sync_kennisbank)
    except Exception as exc:  # pragma: no cover - onverwachte git/qdrant fouten
        logger.exception("Kennisbank sync faalde: %s", exc)
        raise HTTPException(status_code=500, detail=f"Kennisbank sync mislukt: {exc}") from exc
    return {**result, "synced": True}


@app.post("/api/v1/kennisbank/sync/stream")
async def kennisbank_sync_stream(_: TokenRecord = Depends(require_admin_token)):
    """Stream SSE progress updates tijdens kennisbank sync."""
    import queue
    import threading

    progress_queue: queue.Queue = queue.Queue()
    result_holder: dict = {}
    error_holder: list = []

    def progress_callback(current: int, total: int, message: str):
        progress_queue.put({"progress": current, "total": total, "status": message})

    def run_sync():
        try:
            result = sync_kennisbank(progress_callback=progress_callback)
            result_holder["result"] = result
        except Exception as exc:
            error_holder.append(str(exc))
            logger.exception("Kennisbank sync faalde: %s", exc)

    async def event_stream():
        # Start sync in background thread
        thread = threading.Thread(target=run_sync, daemon=True)
        thread.start()

        # Stream progress updates
        while thread.is_alive() or not progress_queue.empty():
            try:
                update = progress_queue.get(timeout=0.5)
                payload = json.dumps(update)
                yield f"data: {payload}\n\n"
            except queue.Empty:
                continue

        # Check for errors
        if error_holder:
            payload = json.dumps({"error": error_holder[0], "done": True})
            yield f"data: {payload}\n\n"
            return

        # Send final result
        if "result" in result_holder:
            final = {**result_holder["result"], "synced": True, "done": True}
            payload = json.dumps(final)
            yield f"data: {payload}\n\n"
        else:
            payload = json.dumps({"error": "Onbekende fout", "done": True})
            yield f"data: {payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/v1/kennisbank/library")
def kennisbank_library(_: TokenRecord = Depends(require_admin_token)):
    return get_library_overview()


@app.get("/api/v1/kennisbank/library/documents/{doc_id}")
def kennisbank_document_detail(doc_id: str, _: TokenRecord = Depends(require_admin_token)):
    try:
        document = load_document_detail(doc_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document niet gevonden") from None
    return {"document": document}


@app.post("/api/v1/signon", response_model=BearerTokenResponse)
def api_signon(req: SignOnRequest):
    device = devices_repo.find_by_username(req.user_name)
    if device is None or device.user_name != req.user_name:
        raise HTTPException(status_code=401, detail="Account niet gevonden of geblokkeerd")
    if device.password != req.password:
        raise HTTPException(status_code=401, detail="Onjuiste gebruikersnaam of wachtwoord")
    issued = token_store.issue_token(device.id, device.user_name)
    return {"token": issued.token, "expires_at": issued.expires_at}


@app.post("/api/v1/ask")
async def api_ask(req: ChatRequest, record: TokenRecord = Depends(require_token)):
    _mark_prompt_activity()

    try:
        documents = normalize_documents(req.documents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Clear history if new_chat flag is set
    if req.new_chat:
        chat_history.clear(record.token)

    history = chat_history.get(record.token)
    final_prompt, images, current_images = prepare_prompt(req, history=history)
    _ensure_prompt_within_context(final_prompt)
    chat_history.append(
        record.token,
        "user",
        _format_prompt_for_history(req.prompt, len(images), len(documents)),
    )

    # Generate IDs for tracking
    request_id = generate_request_id()
    conversation_id = generate_conversation_id(record.token)

    # Build prompt with details for logging
    final_prompt, context_details = build_augmented_prompt_with_details(
        req.prompt,
        history,
        images_count=len(images),
        documents=documents,
    )

    # Create API log entry
    log_entry = ApiLogEntry(
        conversation_id=conversation_id,
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        source="api",
        endpoint="/api/v1/ask",
        user_name=record.user_name,
        device_id=record.device_id,
        token_prefix=record.token[:8] if record.token else None,
        original_prompt=req.prompt,
        new_chat=req.new_chat,
        history_length=len(history) if history else 0,
        images_count=len(images),
        documents_count=len(documents),
        context_contacts=context_details.get("contacts", []),
        context_devices=context_details.get("devices", []),
        context_knowledge=context_details.get("knowledge", []),
        context_documents=context_details.get("documents", []),
        final_prompt_length=len(final_prompt),
    )

    response = await handle_ask(
        req,
        history=history,
        documents=documents,
        final_prompt_override=final_prompt,
    )
    message = response.get("message", "")

    # Update log entry with response
    log_entry.response_preview = message
    log_api_request(log_entry)

    chat_history.append(record.token, "assistant", message)
    return response


@app.post("/api/v1/ask/reset")
def api_ask_reset(record: TokenRecord = Depends(require_token)):
    chat_history.clear(record.token)
    return {"ok": True}


async def sse_stream_generator(
    req: ChatRequest,
    history: list,
    documents: list[ParsedDocument],
    history_key: str,
    final_prompt: Optional[str] = None,
    images: Optional[list[str]] = None,
):
    """Generate SSE events for queue countdown and token streaming from Ollama."""

    images = normalize_images(req.images)

    # Build prompt with details for logging
    final_prompt, context_details = build_augmented_prompt_with_details(
        req.prompt,
        history,
        images_count=len(images),
        documents=documents,
    )
    log_prompt(final_prompt)

    # Create API log entry
    log_entry = ApiLogEntry(
        conversation_id=conversation_id,
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        source="api",
        endpoint="/api/v1/ask/stream",
        user_name=record.user_name,
        device_id=record.device_id,
        token_prefix=record.token[:8] if record.token else None,
        original_prompt=req.prompt,
        mode=req.mode,
        new_chat=req.new_chat,
        history_length=len(history) if history else 0,
        images_count=len(images),
        documents_count=len(documents),
        context_contacts=context_details.get("contacts", []),
        context_devices=context_details.get("devices", []),
        context_knowledge=context_details.get("knowledge", []),
        context_documents=context_details.get("documents", []),
        final_prompt_length=len(final_prompt),
    )

    assistant_chunks: list[str] = []
    error_message: Optional[str] = None
    mock_response: Optional[str] = None

    # Short queue countdown: 2 to 0 with 1 second between each
    for position in range(2, -1, -1):
        event_data = json.dumps({"status": "queued", "position": position})
        yield f"data: {event_data}\n\n"
        await asyncio.sleep(1)

    # Call Ollama API with streaming
    ollama_url = f"{settings.ollama_base_url}/api/generate"
    ollama_payload = {
        "model": settings.ollama_model,
        "prompt": final_prompt,
        "stream": True,
    }
    if images:
        ollama_payload["images"] = list(images)
    max_context = settings.ollama_max_context.get(settings.ollama_model)
    if isinstance(max_context, int) and max_context > 0:
        ollama_payload["options"] = {"num_ctx": max_context}

    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            async with client.stream("POST", ollama_url, json=ollama_payload) as response:
                if response.status_code >= 400:
                    # Lees fouttekst voor logging zodat we weten waarom de fallback triggert.
                    error_body = await response.aread()
                    error_message = f"Ollama status {response.status_code}: {error_body.decode('utf-8', errors='replace').strip()}"
                    logger.warning(
                        "Ollama gaf status %s voor model '%s' via %s: %s",
                        response.status_code,
                        settings.ollama_model,
                        ollama_url,
                        error_body.decode("utf-8", errors="replace").strip(),
                    )
                    response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        # Ollama sends token in "response" field
                        if "response" in data:
                            token = data["response"]
                            if token:  # Only send non-empty tokens
                                assistant_chunks.append(token)
                                event_data = json.dumps({"token": token, "done": False})
                                yield f"data: {event_data}\n\n"

                        # Check if done
                        if data.get("done", False):
                            break

                    except json.JSONDecodeError:
                        continue

    except httpx.TimeoutException as exc:
        error_message = f"Ollama timeout after {settings.ollama_timeout:g}s: {exc!r}"
        logger.warning(
            "Timeout bij Ollama (timeout=%ss, url=%s, model=%s): %r",
            settings.ollama_timeout,
            ollama_url,
            settings.ollama_model,
            exc,
        )
        mock_response = (
            "[Ollama reageert te langzaam - Mock response] "
            f"Geen antwoord binnen {settings.ollama_timeout:g}s van {ollama_url} "
            f"met model '{settings.ollama_model}'. Je vroeg: '{req.prompt}'. "
            "Dit gebeurt vaak bij een koude start of model-lading; probeer het opnieuw."
        )
    except httpx.RequestError as exc:
        # Fallback to mock response if Ollama is not available
        error_message = f"Ollama connection failed: {exc}"
        logger.warning(
            "Kan niet verbinden met Ollama (url=%s, model=%s): %s",
            ollama_url,
            settings.ollama_model,
            exc,
        )
        mock_response = (
            "[Ollama niet beschikbaar - Mock response] "
            f"Kon geen antwoord krijgen van Ollama op {ollama_url} met model '{settings.ollama_model}'. "
            f"Je vroeg: '{req.prompt}'. Controleer of de Ollama-service draait en bereikbaar is."
        )
    except Exception as exc:
        error_message = f"Ollama onverwachte fout: {exc!r}"
        logger.warning(
            "Onverwachte Ollama fout (url=%s, model=%s): %r",
            ollama_url,
            settings.ollama_model,
            exc,
        )
        mock_response = (
            "[Ollama fout - Mock response] "
            f"Er ging iets mis bij {ollama_url} met model '{settings.ollama_model}'. "
            f"Je vroeg: '{req.prompt}'. Controleer de backend- en Ollama-logs."
        )

    if mock_response:
        # Stream the mock response word by word
        words = mock_response.split()
        for word in words:
            token = word + " "
            assistant_chunks.append(token)
            event_data = json.dumps({"token": token, "done": False})
            yield f"data: {event_data}\n\n"
            await asyncio.sleep(0.1)

    assistant_text = "".join(assistant_chunks).strip()
    if assistant_text:
        chat_history.append(history_key, "assistant", assistant_text)

    # Update log entry with response and write to log
    log_entry.response_preview = assistant_text
    log_entry.error = error_message
    log_api_request(log_entry)

    # Send final done event
    event_data = json.dumps({"done": True})
    yield f"data: {event_data}\n\n"


@app.post("/api/v1/ask/stream")
async def api_ask_stream(req: ChatRequest, record: TokenRecord = Depends(require_token)):
    """Stream SSE response with queue position and token-by-token LLM output."""
    _mark_prompt_activity()

    try:
        documents = normalize_documents(req.documents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Clear history if new_chat flag is set
    if req.new_chat:
        chat_history.clear(record.token)

    history = chat_history.get(record.token)
    final_prompt, images, current_images = prepare_prompt(req, history=history)
    _ensure_prompt_within_context(final_prompt)
    chat_history.append(
        record.token,
        "user",
        _format_prompt_for_history(req.prompt, len(images), len(documents)),
    )

    # Generate IDs for tracking
    request_id = generate_request_id()
    conversation_id = generate_conversation_id(record.token)

    return StreamingResponse(
        sse_stream_generator(req, history, documents, record.token, record, request_id, conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/contacts", response_model=list[Contact])
def list_contacts():
    return contacts_repo.list_contacts()


@app.post("/contacts", response_model=Contact)
def create_contact(data: ContactCreate):
    try:
        return contacts_repo.create_contact(data)
    except Exception as exc:  # pragma: no cover - simple error surface
        # Log de volledige traceback zodat we fouten in Qdrant of
        # het opslagpad kunnen debuggen.
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.patch("/contacts/{contact_id}", response_model=Contact)
def patch_contact(contact_id: str, patch: ContactPatch):
    try:
        return contacts_repo.update_contact(contact_id, patch)
    except ValueError:
        raise HTTPException(status_code=404, detail="contact not found")
    except Exception as exc:  # pragma: no cover
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/contacts/{contact_id}")
def delete_contact(contact_id: str):
    try:
        contacts_repo.delete_contact(contact_id)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "ok"}


@app.get("/devices", response_model=list[Device])
def list_devices(_: TokenRecord = Depends(require_admin_token)):
    return devices_repo.list_devices()


@app.post("/devices", response_model=Device)
def create_device(
    data: DeviceCreate,
    _: TokenRecord = Depends(require_admin_token),
):
    try:
        return devices_repo.create_device(data)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.patch("/devices/{device_id}", response_model=Device)
def patch_device(
    device_id: str,
    patch: DevicePatch,
    _: TokenRecord = Depends(require_admin_token),
):
    try:
        return devices_repo.update_device(device_id, patch)
    except ValueError:
        raise HTTPException(status_code=404, detail="device not found")
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/devices/{device_id}")
def delete_device(
    device_id: str,
    _: TokenRecord = Depends(require_admin_token),
):
    try:
        devices_repo.delete_device(device_id)
        token_store.revoke_for_device(device_id)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "ok"}


@app.websocket(settings.ws_path)
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            payload = await ws.receive_text()
            try:
                data = json.loads(payload)
                prompt = data.get("prompt", "")
            except json.JSONDecodeError:
                prompt = payload
            message = f"Echo: {prompt}"
            for ch in message:
                await ws.send_json({"token": ch, "done": False})
                await asyncio.sleep(0.005)
            await ws.send_json({"done": True})
    except WebSocketDisconnect:
        return
