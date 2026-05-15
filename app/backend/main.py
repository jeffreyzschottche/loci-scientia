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
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.concurrency import run_in_threadpool
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .auth_tokens import BearerTokenStore, TokenRecord
from .apiAsk import (
    ApiLogEntry,
    ParsedDocument,
    build_ollama_generate_payload,
    build_augmented_prompt_with_details,
    collect_prompt_images,
    estimate_prompt_tokens,
    generate_conversation_id,
    generate_request_id,
    handle_ask,
    history_documents_from_parsed,
    invalid_model_output_message,
    is_invalid_model_output,
    log_api_request,
    log_prompt,
    normalize_documents,
    normalize_images,
    normalize_model_response,
    prepare_prompt,
    summarize_history,
)
from .web_search import (
    WebSearchResult,
    WebSearchUnavailable,
    is_configured as web_search_is_configured,
    results_to_payload as web_results_to_payload,
    search as run_web_search,
)
from .chat_history import ChatHistoryStore
from .admin_access import AdminTokenManager
from .devices_repo import DevicesRepository
from .kennisbank_sync import (
    KNOWLEDGE_BASE_DIRNAME,
    import_kennisbank_from_dir,
    read_sync_state,
)
from .knowledge_library import get_library_overview, load_document_detail
from .schemas import (
    BearerTokenResponse,
    ChatCancelRequest,
    ChatRequest,
    ChatResetRequest,
    Device,
    DeviceCreate,
    DevicePatch,
    OllamaModelRequest,
    SignOnRequest,
    SupportTunnelRequest,
    SupportTunnelStatus,
)
from .settings import settings
from .support_tunnel import SupportTunnelError, SupportTunnelManager

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

devices_repo = DevicesRepository()
token_store = BearerTokenStore()
chat_history = ChatHistoryStore(max_items=20)
ollama_switch_lock = asyncio.Lock()
support_tunnel = SupportTunnelManager(env_path=ENV_FILE_PATH)
admin_tokens = AdminTokenManager(
    token_store=token_store,
    admin_usernames=settings.admin_usernames,
)
admin_tokens.ensure()
summary_task: Optional[asyncio.Task] = None
last_prompt_at: Optional[datetime] = None
last_idle_summary_at: Optional[datetime] = None

SUMMARY_POLL_SECONDS = 60
STATS_HISTORY_MAX_SAMPLES = 50
API_STATS_MODE = "interactive_v1"
API_STATS_PATH = Path(__file__).resolve().parents[2] / "devices_db" / "api_stats_snapshot.json"
STATS_HISTORY_PATH = Path(__file__).resolve().parents[2] / "devices_db" / "api_stats_history.json"


class ActiveGeneration:
    def __init__(self, token: str):
        self.token = token
        self.cancelled = False
        self._response = None

    def bind_response(self, response) -> None:
        self._response = response

    async def cancel(self) -> None:
        self.cancelled = True
        if self._response is not None:
            try:
                await self._response.aclose()
            except Exception:
                pass


active_generations: dict[str, ActiveGeneration] = {}


class DevicePresenceTracker:
    def __init__(self, *, timeout_seconds: int = 30):
        self._lock = Lock()
        self._timeout = timedelta(seconds=timeout_seconds)
        self._last_seen: dict[str, datetime] = {}

    def mark(self, device_id: Optional[str]) -> None:
        if not device_id:
            return
        now = datetime.now(timezone.utc)
        with self._lock:
            self._last_seen[str(device_id)] = now
            self._prune_locked(now)

    def snapshot(self) -> dict[str, datetime]:
        now = datetime.now(timezone.utc)
        with self._lock:
            self._prune_locked(now)
            return dict(self._last_seen)

    def is_connected(self, device_id: Optional[str]) -> bool:
        if not device_id:
            return False
        now = datetime.now(timezone.utc)
        with self._lock:
            self._prune_locked(now)
            last_seen = self._last_seen.get(str(device_id))
        return last_seen is not None and (now - last_seen) <= self._timeout

    def _prune_locked(self, now: datetime) -> None:
        expired = [
            device_id
            for device_id, last_seen in self._last_seen.items()
            if (now - last_seen) > self._timeout
        ]
        for device_id in expired:
            self._last_seen.pop(device_id, None)


class ApiStats:
    def __init__(self, state_path: Path):
        self._lock = Lock()
        self._state_path = state_path
        self._day = datetime.now(timezone.utc).date()
        self._requests_today = 0
        self._errors_today = 0
        self._latency_total_ms = 0.0
        self._latency_count = 0
        self._output_tokens_total = 0.0
        self._generation_seconds_total = 0.0
        self._active_ids: set[str] = set()
        self._load_state()

    def _load_state(self) -> None:
        try:
            raw = self._state_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return
        except OSError:
            return
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return
        if not isinstance(payload, dict):
            return
        if payload.get("mode") != API_STATS_MODE:
            return
        day_raw = payload.get("date")
        if isinstance(day_raw, str):
            try:
                self._day = datetime.fromisoformat(day_raw).date()
            except ValueError:
                self._day = datetime.now(timezone.utc).date()
        self._requests_today = int(payload.get("requests_today") or 0)
        self._errors_today = int(payload.get("errors_today") or 0)
        self._latency_total_ms = float(payload.get("latency_total_ms") or 0.0)
        self._latency_count = int(payload.get("latency_count") or 0)
        self._output_tokens_total = float(payload.get("output_tokens_total") or 0.0)
        self._generation_seconds_total = float(payload.get("generation_seconds_total") or 0.0)
        active_ids = payload.get("active_ids") or []
        if isinstance(active_ids, list):
            self._active_ids = {str(item) for item in active_ids if str(item).strip()}

    def _persist_locked(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "mode": API_STATS_MODE,
            "date": self._day.isoformat(),
            "requests_today": self._requests_today,
            "errors_today": self._errors_today,
            "latency_total_ms": round(self._latency_total_ms, 3),
            "latency_count": self._latency_count,
            "output_tokens_total": round(self._output_tokens_total, 3),
            "generation_seconds_total": round(self._generation_seconds_total, 3),
            "active_ids": sorted(self._active_ids),
        }
        tmp = self._state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self._state_path)

    def _rollover(self, now: datetime) -> None:
        today = now.date()
        if today == self._day:
            return
        self._day = today
        self._requests_today = 0
        self._errors_today = 0
        self._latency_total_ms = 0.0
        self._latency_count = 0
        self._output_tokens_total = 0.0
        self._generation_seconds_total = 0.0
        self._active_ids.clear()
        self._persist_locked()

    def begin_interaction(self, token_value: Optional[str]) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            self._rollover(now)
            self._requests_today += 1
            if token_value:
                token_hash = hashlib.sha256(token_value.encode("utf-8")).hexdigest()[:16]
                self._active_ids.add(token_hash)
            self._persist_locked()

    def finish_interaction(
        self,
        duration_ms: float,
        *,
        error: bool = False,
        output_chars: int = 0,
        output_tokens: float | None = None,
        generation_seconds: float | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            self._rollover(now)
            if error:
                self._errors_today += 1
            self._latency_total_ms += duration_ms
            self._latency_count += 1
            estimated_tokens = (
                max(0.0, float(output_tokens))
                if output_tokens is not None
                else max(0.0, float(output_chars) / 4.0)
            )
            duration_seconds = (
                max(0.001, float(generation_seconds))
                if generation_seconds is not None
                else max(0.001, float(duration_ms) / 1000.0)
            )
            if estimated_tokens:
                self._output_tokens_total += estimated_tokens
                self._generation_seconds_total += duration_seconds
            self._persist_locked()
            avg = self._latency_total_ms / self._latency_count if self._latency_count else None
            error_rate = (
                (self._errors_today / self._requests_today) * 100.0
                if self._requests_today
                else 0.0
            )
            tokens_per_second = (
                self._output_tokens_total / self._generation_seconds_total
                if self._generation_seconds_total
                else None
            )
            snapshot = {
                "date": self._day.isoformat(),
                "requests_today": self._requests_today,
                "errors_today": self._errors_today,
                "error_rate": round(error_rate, 1),
                "active_users_today": len(self._active_ids),
                "avg_response_ms": round(avg, 1) if avg is not None else None,
                "tokens_per_second": round(tokens_per_second, 1) if tokens_per_second is not None else None,
            }
        api_stats_history.append(snapshot)

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
            error_rate = (
                (self._errors_today / self._requests_today) * 100.0
                if self._requests_today
                else 0.0
            )
            tokens_per_second = (
                self._output_tokens_total / self._generation_seconds_total
                if self._generation_seconds_total
                else None
            )
            return {
                "date": self._day.isoformat(),
                "requests_today": self._requests_today,
                "errors_today": self._errors_today,
                "error_rate": round(error_rate, 1),
                "active_users_today": len(self._active_ids),
                "avg_response_ms": avg_ms,
                "tokens_per_second": round(tokens_per_second, 1) if tokens_per_second is not None else None,
            }


class ApiStatsHistory:
    def __init__(self, history_path: Path, *, max_samples: int = STATS_HISTORY_MAX_SAMPLES):
        self._lock = Lock()
        self._history_path = history_path
        self._max_samples = max(1, int(max_samples))
        self._samples: list[dict] = self._load()

    def _load(self) -> list[dict]:
        try:
            raw = self._history_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        except OSError:
            return []
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if isinstance(payload, dict) and payload.get("mode") != API_STATS_MODE:
            return []
        items = payload.get("samples") if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            items = []
        normalized: list[dict] = []
        for item in items[-self._max_samples:]:
            if not isinstance(item, dict):
                continue
            timestamp = item.get("timestamp")
            if not isinstance(timestamp, str):
                continue
            normalized.append(
                {
                    "timestamp": timestamp,
                    "requests_today": int(item.get("requests_today") or 0),
                    "errors_today": int(item.get("errors_today") or 0),
                    "error_rate": float(item.get("error_rate") or 0.0),
                    "active_users_today": int(item.get("active_users_today") or 0),
                    "avg_response_ms": int(round(float(item.get("avg_response_ms") or 0))),
                    "tokens_per_second": float(item.get("tokens_per_second") or 0.0),
                }
            )
        return normalized

    def _persist_locked(self) -> None:
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"mode": API_STATS_MODE, "samples": self._samples}
        tmp = self._history_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self._history_path)

    def append(self, snapshot: dict) -> None:
        sample = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "requests_today": int(snapshot.get("requests_today") or 0),
            "errors_today": int(snapshot.get("errors_today") or 0),
            "error_rate": float(snapshot.get("error_rate") or 0.0),
            "active_users_today": int(snapshot.get("active_users_today") or 0),
            "avg_response_ms": int(round(float(snapshot.get("avg_response_ms") or 0))),
            "tokens_per_second": float(snapshot.get("tokens_per_second") or 0.0),
        }
        with self._lock:
            self._samples.append(sample)
            self._samples = self._samples[-self._max_samples:]
            self._persist_locked()

    def snapshot(self) -> dict:
        with self._lock:
            samples = list(self._samples)
        return {
            "max_samples": self._max_samples,
            "samples": samples,
        }


api_stats = ApiStats(API_STATS_PATH)
api_stats_history = ApiStatsHistory(STATS_HISTORY_PATH, max_samples=STATS_HISTORY_MAX_SAMPLES)
device_presence = DevicePresenceTracker(timeout_seconds=30)


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
    device_presence.mark(record.device_id)
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
        "source": None,
        "qdrant": None,
        "sqlite": None,
        "stats": None,
        "synced_at": None,
    }


def _mark_prompt_activity() -> None:
    global last_prompt_at
    last_prompt_at = datetime.now(timezone.utc)


def _history_key(record: TokenRecord, conversation_id: Optional[str]) -> str:
    conversation = (conversation_id or "").strip()
    if not conversation:
        return record.token
    return f"{record.token}:{conversation}"


def _format_prompt_for_history(prompt: str, images_count: int, documents_count: int = 0) -> str:
    clean = (prompt or "").strip()
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
        summary_task = None
    elif summary_task is None or summary_task.done():
        summary_task = asyncio.create_task(_idle_summary_loop())


@app.on_event("shutdown")
async def stop_idle_summary_task() -> None:
    global summary_task
    if summary_task is not None:
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


@app.get("/api/stats/history")
def api_stats_history_snapshot(_: TokenRecord = Depends(require_admin_token)):
    return api_stats_history.snapshot()


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


@app.get("/api/support/tunnel", response_model=SupportTunnelStatus)
def support_tunnel_status(_: TokenRecord = Depends(require_admin_token)):
    return support_tunnel.status().to_response()


@app.post("/api/support/tunnel", response_model=SupportTunnelStatus)
def support_tunnel_action(
    req: SupportTunnelRequest,
    _: TokenRecord = Depends(require_admin_token),
):
    try:
        if req.action == "open":
            state = support_tunnel.open(duration_minutes=req.duration_minutes or 60)
        else:
            state = support_tunnel.close()
    except SupportTunnelError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return state.to_response()


@app.get("/api/v1/kennisbank/sync-state")
def kennisbank_sync_state(_: TokenRecord = Depends(require_admin_token)):
    state = read_sync_state()
    if not state:
        return _empty_sync_state()
    return {**state, "synced": True}


def _unpack_kennisbank_bundle(file_bytes: bytes, dest_dir: Path) -> Path:
    """Pak een knowledge_base export-bundle uit naar een tijdelijke map.

    De bundle is een ZIP geproduceerd door de embedder
    (`Services\\DeviceSyncService::buildBundle`). Hij kan met of zonder
    `knowledge_base/` top-level dir komen — we normaliseren naar een pad
    dat documents/, chunks/, model.json etc bevat.
    """
    import zipfile

    bundle_path = dest_dir / "bundle.zip"
    bundle_path.write_bytes(file_bytes)
    extract_to = dest_dir / "extracted"
    extract_to.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(bundle_path) as zf:
            for name in zf.namelist():
                # Bescherm tegen path traversal / absolute paden.
                normalized = name.replace("\\", "/")
                if normalized.startswith("/") or ".." in Path(normalized).parts:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Onveilig pad in bundle: {name}",
                    )
            zf.extractall(extract_to)
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Bundle is geen geldig ZIP-bestand") from exc

    inner = extract_to / KNOWLEDGE_BASE_DIRNAME
    if inner.is_dir():
        return inner
    if (extract_to / "documents").is_dir() or (extract_to / "model.json").is_file():
        return extract_to
    candidates = [p for p in extract_to.iterdir() if p.is_dir()]
    if len(candidates) == 1 and (candidates[0] / "documents").is_dir():
        return candidates[0]
    raise HTTPException(
        status_code=400,
        detail="Bundle bevat geen herkenbare knowledge_base structuur",
    )


@app.post("/api/v1/kennisbank/import")
async def kennisbank_import_endpoint(
    bundle: UploadFile = File(...),
    _: TokenRecord = Depends(require_admin_token),
):
    """Ontvang een knowledge_base ZIP-bundle van de embedder-app en importeer
    incrementeel naar Qdrant + SQLite. Vervangt de oude git-pull sync."""
    import tempfile

    file_bytes = await bundle.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Lege bundle ontvangen")

    source = {
        "filename": bundle.filename,
        "content_type": bundle.content_type,
        "size_bytes": len(file_bytes),
    }

    def _run() -> dict:
        with tempfile.TemporaryDirectory(prefix="aitje-import-") as tmp:
            tmp_path = Path(tmp)
            export_base = _unpack_kennisbank_bundle(file_bytes, tmp_path)
            return import_kennisbank_from_dir(export_base, source=source)

    try:
        result = await run_in_threadpool(_run)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - onverwachte qdrant/embed fouten
        logger.exception("Kennisbank import faalde: %s", exc)
        raise HTTPException(status_code=500, detail=f"Kennisbank import mislukt: {exc}") from exc
    return {**result, "synced": True}


@app.post("/api/v1/kennisbank/import/stream")
async def kennisbank_import_stream(
    bundle: UploadFile = File(...),
    _: TokenRecord = Depends(require_admin_token),
):
    """Stream SSE progress events terwijl de bundle wordt geïmporteerd."""
    import queue
    import tempfile
    import threading

    file_bytes = await bundle.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Lege bundle ontvangen")

    source = {
        "filename": bundle.filename,
        "content_type": bundle.content_type,
        "size_bytes": len(file_bytes),
    }

    progress_queue: queue.Queue = queue.Queue()
    result_holder: dict = {}
    error_holder: list = []

    def progress_callback(current: int, total: int, message: str):
        progress_queue.put({"progress": current, "total": total, "status": message})

    def run_import():
        try:
            with tempfile.TemporaryDirectory(prefix="aitje-import-") as tmp:
                tmp_path = Path(tmp)
                export_base = _unpack_kennisbank_bundle(file_bytes, tmp_path)
                result = import_kennisbank_from_dir(
                    export_base,
                    source=source,
                    progress_callback=progress_callback,
                )
                result_holder["result"] = result
        except HTTPException as exc:
            error_holder.append(exc.detail)
        except Exception as exc:
            error_holder.append(str(exc))
            logger.exception("Kennisbank import faalde: %s", exc)

    async def event_stream():
        thread = threading.Thread(target=run_import, daemon=True)
        thread.start()
        while thread.is_alive() or not progress_queue.empty():
            try:
                update = progress_queue.get(timeout=0.5)
                yield f"data: {json.dumps(update)}\n\n"
            except queue.Empty:
                continue
        if error_holder:
            yield f"data: {json.dumps({'error': error_holder[0], 'done': True})}\n\n"
            return
        if "result" in result_holder:
            final = {**result_holder["result"], "synced": True, "done": True}
            yield f"data: {json.dumps(final)}\n\n"
        else:
            yield f"data: {json.dumps({'error': 'Onbekende fout', 'done': True})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
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
@app.post("/api/v1/sigon", response_model=BearerTokenResponse, include_in_schema=False)
def api_signon(req: SignOnRequest):
    device = devices_repo.find_by_username(req.user_name)
    if device is None or device.user_name != req.user_name:
        raise HTTPException(status_code=401, detail="Account niet gevonden of geblokkeerd")
    if device.password != req.password:
        raise HTTPException(status_code=401, detail="Onjuiste gebruikersnaam of wachtwoord")
    issued = token_store.issue_token(device.id, device.user_name)
    device_presence.mark(device.id)
    return {"token": issued.token, "expires_at": issued.expires_at}


@app.post("/api/v1/ask")
async def api_ask(req: ChatRequest, record: TokenRecord = Depends(require_token)):
    _mark_prompt_activity()
    started = time.perf_counter()
    api_stats.begin_interaction(record.token)

    try:
        documents = normalize_documents(req.documents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    history_key = _history_key(record, req.conversation_id)

    # Clear history if new_chat flag is set
    if req.new_chat:
        chat_history.clear(history_key)

    history = chat_history.get(history_key)
    web_results: list[WebSearchResult] = []
    web_search_error: Optional[str] = None
    if req.web_search:
        try:
            web_results = await run_web_search(req.prompt)
        except WebSearchUnavailable as exc:
            web_search_error = str(exc)
            logger.warning("Web search unavailable: %s", exc)
    try:
        final_prompt, images = prepare_prompt(
            req, history=history, documents=documents, web_results=web_results
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _ensure_prompt_within_context(final_prompt)
    chat_history.append(
        history_key,
        "user",
        _format_prompt_for_history(req.prompt, len(images), len(documents)),
        images=images,
        documents=history_documents_from_parsed(documents),
    )

    # Generate IDs for tracking
    request_id = generate_request_id()
    conversation_id = req.conversation_id or generate_conversation_id(record.token)

    # Build prompt with details for logging
    final_prompt, context_details = build_augmented_prompt_with_details(
        req.prompt,
        history=history,
        images_count=len(images),
        documents=documents,
        mode=req.mode,
        web_results=web_results,
    )

    # Create API log entry
    log_entry = ApiLogEntry(
        conversation_id=conversation_id,
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        source="api",
        endpoint="/api/v1/ask",
        mode=req.mode,
        thinking_enabled=req.thinking,
        user_name=record.user_name,
        device_id=record.device_id,
        token_prefix=record.token[:8] if record.token else None,
        original_prompt=req.prompt,
        new_chat=req.new_chat,
        history_length=len(history) if history else 0,
        images_count=len(images),
        documents_count=len(documents),
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
        citations=context_details.get("citations", []),
        web_results=web_results,
    )
    if web_search_error and not response.get("web_search_error"):
        response["web_search_error"] = web_search_error
    message = response.get("message", "")

    # Update log entry with response
    log_entry.response_preview = message
    log_api_request(log_entry)

    chat_history.append(history_key, "assistant", message)
    api_stats.finish_interaction(
        (time.perf_counter() - started) * 1000,
        error=bool(web_search_error or response.get("web_search_error")),
        output_chars=len(message),
        output_tokens=float(response["eval_count"]) if isinstance(response.get("eval_count"), (int, float)) else None,
        generation_seconds=(
            float(response["eval_duration"]) / 1_000_000_000
            if isinstance(response.get("eval_duration"), (int, float)) and response.get("eval_duration")
            else None
        ),
    )
    return response


@app.post("/api/v1/ask/reset")
def api_ask_reset(
    req: Optional[ChatResetRequest] = None,
    record: TokenRecord = Depends(require_token),
):
    conversation_id = req.conversation_id if req else None
    chat_history.clear(_history_key(record, conversation_id))
    return {"ok": True}


async def sse_stream_generator(
    req: ChatRequest,
    history: list,
    documents: list[ParsedDocument],
    history_key: str,
    record: TokenRecord,
    request_id: str,
    conversation_id: str,
    generation: ActiveGeneration,
    final_prompt: Optional[str] = None,
    images: Optional[list[str]] = None,
    web_results: Optional[list[WebSearchResult]] = None,
    web_search_error: Optional[str] = None,
):
    """Generate SSE events for queue countdown and token streaming from Ollama."""
    started = time.perf_counter()

    current_images = images if images is not None else normalize_images(req.images)
    prompt_images = collect_prompt_images(history, current_images=current_images)

    # Run web search (if requested but not yet executed) and emit progress events
    if req.web_search and web_results is None:
        if not web_search_is_configured():
            web_search_error = "SearXNG is niet geconfigureerd (zet SEARXNG_URL)."
            yield f"data: {json.dumps({'web_search': {'status': 'unavailable', 'error': web_search_error}})}\n\n"
            web_results = []
        else:
            yield f"data: {json.dumps({'web_search': {'status': 'started', 'query': req.prompt}})}\n\n"
            try:
                web_results = await run_web_search(req.prompt)
            except WebSearchUnavailable as exc:
                web_search_error = str(exc)
                web_results = []
                yield f"data: {json.dumps({'web_search': {'status': 'error', 'error': web_search_error}})}\n\n"
            else:
                payload = {
                    "web_search": {
                        "status": "results",
                        "query": req.prompt,
                        "results": web_results_to_payload(web_results),
                    }
                }
                yield f"data: {json.dumps(payload)}\n\n"
    elif web_results is None:
        web_results = []

    # Build prompt with details for logging (web_results may shift the prompt,
    # so we always rebuild here and ignore any pre-built final_prompt when
    # web search produced extra context).
    logged_prompt, context_details = build_augmented_prompt_with_details(
        req.prompt,
        history=history,
        images_count=len(current_images),
        documents=documents,
        mode=req.mode,
        web_results=web_results,
    )
    if web_results:
        final_prompt = logged_prompt
    else:
        final_prompt = final_prompt or logged_prompt
    log_prompt(final_prompt)

    # Create API log entry
    log_entry = ApiLogEntry(
        conversation_id=conversation_id,
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        source="api",
        endpoint="/api/v1/ask/stream",
        thinking_enabled=req.thinking,
        user_name=record.user_name,
        device_id=record.device_id,
        token_prefix=record.token[:8] if record.token else None,
        original_prompt=req.prompt,
        mode=req.mode,
        new_chat=req.new_chat,
        history_length=len(history) if history else 0,
        images_count=len(current_images),
        documents_count=len(documents),
        context_devices=context_details.get("devices", []),
        context_knowledge=context_details.get("knowledge", []),
        context_documents=context_details.get("documents", []),
        final_prompt_length=len(final_prompt),
    )

    assistant_chunks: list[str] = []
    pending_assistant_chunks: list[str] = []
    thinking_chunks: list[str] = []
    error_message: Optional[str] = None
    mock_response: Optional[str] = None
    assistant_stream_started = False
    eval_count: Optional[float] = None
    eval_duration_seconds: Optional[float] = None

    # Short queue countdown: 2 to 0 with 1 second between each
    for position in range(2, -1, -1):
        if generation.cancelled:
            active_generations.pop(request_id, None)
            return
        event_data = json.dumps({"status": "queued", "position": position})
        yield f"data: {event_data}\n\n"
        await asyncio.sleep(1)

    # Call Ollama API with streaming
    ollama_url = f"{settings.ollama_base_url}/api/generate"
    ollama_payload = build_ollama_generate_payload(
        final_prompt,
        stream=True,
        images=prompt_images,
        thinking=req.thinking,
    )

    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            async with client.stream("POST", ollama_url, json=ollama_payload) as response:
                generation.bind_response(response)
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
                    if generation.cancelled:
                        active_generations.pop(request_id, None)
                        return
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        if "thinking" in data:
                            token = data["thinking"]
                            if token:
                                thinking_chunks.append(token)
                                event_data = json.dumps({"thinking": token, "done": False})
                                yield f"data: {event_data}\n\n"

                        # Ollama sends answer tokens in "response" field
                        if "response" in data:
                            token = data["response"]
                            if token:  # Only send non-empty tokens
                                pending_assistant_chunks.append(token)
                                partial_text = "".join(assistant_chunks + pending_assistant_chunks).strip()
                                if is_invalid_model_output(partial_text):
                                    assistant_chunks = [invalid_model_output_message()]
                                    pending_assistant_chunks = []
                                    break
                                should_flush_pending = assistant_stream_started or len("".join(pending_assistant_chunks)) >= 120 or data.get("done", False)
                                if should_flush_pending:
                                    assistant_stream_started = True
                                    for pending_token in pending_assistant_chunks:
                                        assistant_chunks.append(pending_token)
                                        event_data = json.dumps({"token": pending_token, "done": False})
                                        yield f"data: {event_data}\n\n"
                                    pending_assistant_chunks = []

                        # Check if done
                        if data.get("done", False):
                            if isinstance(data.get("eval_count"), (int, float)):
                                eval_count = float(data["eval_count"])
                            if isinstance(data.get("eval_duration"), (int, float)) and data.get("eval_duration"):
                                eval_duration_seconds = float(data["eval_duration"]) / 1_000_000_000
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
            if generation.cancelled:
                active_generations.pop(request_id, None)
                return
            token = word + " "
            assistant_chunks.append(token)
            event_data = json.dumps({"token": token, "done": False})
            yield f"data: {event_data}\n\n"
            await asyncio.sleep(0.1)

    raw_assistant_text = "".join(assistant_chunks).strip()
    raw_thinking_text = "".join(thinking_chunks).strip()
    thinking_text, assistant_text = normalize_model_response(
        response_text=raw_assistant_text,
        thinking_text=raw_thinking_text,
    )
    if assistant_text:
        chat_history.append(history_key, "assistant", assistant_text)

    # Update log entry with response and write to log
    log_entry.response_preview = assistant_text
    log_entry.error = error_message
    log_api_request(log_entry)

    # Finalize latency before the terminal done event is sent.
    api_stats.finish_interaction(
        (time.perf_counter() - started) * 1000,
        error=bool(error_message),
        output_chars=len(assistant_text),
        output_tokens=eval_count,
        generation_seconds=eval_duration_seconds,
    )
    final_event = {
        "done": True,
        "message": assistant_text,
        "thinking": thinking_text,
        "citations": context_details.get("citations", []),
        "web_results": web_results_to_payload(web_results) if web_results else [],
    }
    if web_search_error:
        final_event["web_search_error"] = web_search_error
    yield f"data: {json.dumps(final_event)}\n\n"
    active_generations.pop(request_id, None)


@app.post("/api/v1/ask/stream")
async def api_ask_stream(req: ChatRequest, record: TokenRecord = Depends(require_token)):
    """Stream SSE response with queue position and token-by-token LLM output."""
    _mark_prompt_activity()
    api_stats.begin_interaction(record.token)

    try:
        documents = normalize_documents(req.documents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    history_key = _history_key(record, req.conversation_id)

    # Clear history if new_chat flag is set
    if req.new_chat:
        chat_history.clear(history_key)

    history = chat_history.get(history_key)
    try:
        final_prompt, images = prepare_prompt(req, history=history, documents=documents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _ensure_prompt_within_context(final_prompt)
    chat_history.append(
        history_key,
        "user",
        _format_prompt_for_history(req.prompt, len(images), len(documents)),
        images=images,
        documents=history_documents_from_parsed(documents),
    )

    # Generate IDs for tracking
    request_id = (req.request_id or generate_request_id()).strip()
    conversation_id = req.conversation_id or generate_conversation_id(record.token)
    generation = ActiveGeneration(record.token)
    active_generations[request_id] = generation

    return StreamingResponse(
        sse_stream_generator(
            req,
            history,
            documents,
            history_key,
            record,
            request_id,
            conversation_id,
            generation,
            final_prompt=final_prompt,
            images=images,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/v1/ask/cancel")
async def api_ask_cancel(req: ChatCancelRequest, record: TokenRecord = Depends(require_token)):
    request_id = req.request_id.strip()
    generation = active_generations.get(request_id)
    if generation is None:
        return {"ok": True, "cancelled": False}
    if generation.token != record.token:
        raise HTTPException(status_code=403, detail="Request hoort niet bij dit token")
    await generation.cancel()
    active_generations.pop(request_id, None)
    return {"ok": True, "cancelled": True}


@app.get("/devices", response_model=list[Device])
def list_devices(_: TokenRecord = Depends(require_admin_token)):
    presence = device_presence.snapshot()
    devices = devices_repo.list_devices()
    for device in devices:
        last_seen = presence.get(device.id)
        device.is_connected = last_seen is not None
        device.last_seen_at = last_seen
    return devices


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


# ---- LAN embedder app (Laravel + Nuxt SPA) ----------------------------------
#
# De Aitje Embedding Application is geïnternaliseerd onder /embedder. De
# Laravel-backend draait lokaal op 127.0.0.1:${EMBEDDER_PORT} (gestart door
# lociscientia.sh) en de Nuxt SPA wordt statisch gegenereerd naar
# app/embedder/frontend/.output/public en gemount op /embedder/. We proxien
# /embedder/api/* naar Laravel zodat alles same-origin op poort 8000 zit.

_EMBEDDER_PROXY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


async def _embedder_proxy(request: Request, full_path: str):
    # Laravel registreert zijn routes onder /embedder/api/* (apiPrefix in
    # bootstrap/app.php). We forwarden het volledige pad zodat de URL die
    # Laravel ziet exact overeenkomt met de URL waarmee signed routes
    # gegenereerd zijn — anders mismatchen email-verify signatures.
    upstream = f"http://127.0.0.1:{settings.embedder_port}/embedder/api/{full_path}"
    body = await request.body()
    forwarded_headers = {
        name: value
        for name, value in request.headers.items()
        if name.lower() not in _EMBEDDER_PROXY_HOP_HEADERS
    }
    forwarded_headers["X-Forwarded-Host"] = request.headers.get(
        "host", forwarded_headers.get("host", "")
    )
    forwarded_headers["X-Forwarded-Proto"] = request.url.scheme
    forwarded_headers["X-Forwarded-Prefix"] = "/embedder"

    try:
        async with httpx.AsyncClient(timeout=settings.embedder_timeout) as client:
            upstream_response = await client.request(
                request.method,
                upstream,
                params=request.query_params,
                content=body,
                headers=forwarded_headers,
            )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=502,
            detail="Embedder-backend (Laravel) niet bereikbaar.",
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Embedder proxy error: {exc}") from exc

    response_headers = {
        name: value
        for name, value in upstream_response.headers.items()
        if name.lower() not in _EMBEDDER_PROXY_HOP_HEADERS
    }
    return StreamingResponse(
        content=iter([upstream_response.content]),
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type"),
    )


@app.api_route(
    "/embedder/api/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def embedder_api_proxy(request: Request, full_path: str):
    return await _embedder_proxy(request, full_path)


# ---- LAN web client (Nuxt SPA) -----------------------------------------------
#
# The Nuxt 3 client is generated to app/webclient/.output/public during
# `lociscientia.sh` startup (or manually with `npm run generate`). FastAPI
# serves it on the same port so phones/laptops on the LAN can just open
# http://aitje-<n>.local:8000/ and log in via /api/v1/signon.
#
# This block must remain at the bottom of the file: the catch-all mount on "/"
# would shadow any later-registered API route.

_SPA_RESERVED_PREFIXES = ("api", "api/", "devices", "devices/", "health", "ws", "fonts/", "sprites/", "embedder", "embedder/")


class _SPAStaticFiles(StaticFiles):
    """StaticFiles that falls back to index.html for unknown SPA routes,
    but never for paths that look like API routes (so a POST-only endpoint
    queried with GET still returns 405/404 instead of an HTML page)."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            normalized = path.lstrip("/")
            if normalized == "" or any(
                normalized == prefix.rstrip("/") or normalized.startswith(prefix)
                for prefix in _SPA_RESERVED_PREFIXES
            ):
                raise
            index_path = Path(self.directory) / "index.html"
            if index_path.is_file():
                return FileResponse(index_path)
            raise


_EMBEDDER_DIST = Path(__file__).resolve().parents[1] / "embedder" / "frontend" / ".output" / "public"
if _EMBEDDER_DIST.is_dir() and (_EMBEDDER_DIST / "index.html").is_file():
    # Reserve geen extra prefixes: alle requests die hier landen zitten al
    # onder /embedder/, en de api-proxy hierboven vangt /embedder/api/* af
    # voordat deze mount aan de beurt is.
    app.mount(
        "/embedder",
        _SPAStaticFiles(directory=str(_EMBEDDER_DIST), html=True),
        name="embedder",
    )
else:
    logger.warning(
        "Embedder build niet gevonden op %s; /embedder SPA niet gemount. "
        "Run `cd app/embedder/frontend && npm install && npm run generate` of start lociscientia.sh.",
        _EMBEDDER_DIST,
    )

_WEBCLIENT_DIST = Path(__file__).resolve().parents[1] / "webclient" / ".output" / "public"
if _WEBCLIENT_DIST.is_dir() and (_WEBCLIENT_DIST / "index.html").is_file():
    app.mount(
        "/",
        _SPAStaticFiles(directory=str(_WEBCLIENT_DIST), html=True),
        name="webclient",
    )
else:
    logger.warning(
        "Webclient build niet gevonden op %s; SPA niet gemount. "
        "Run `cd app/webclient && npm install && npm run generate` of start lociscientia.sh.",
        _WEBCLIENT_DIST,
    )
