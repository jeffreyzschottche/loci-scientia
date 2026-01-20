import asyncio
import json
import logging
import os
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .auth_tokens import BearerTokenStore, TokenRecord
from .apiAsk import build_augmented_prompt, handle_ask, log_prompt
from .chat_history import ChatHistoryStore
from .admin_access import AdminTokenManager
from .contacts_repo import ContactsRepository
from .devices_repo import DevicesRepository
from .schemas import (
    ApiRouteCreate,
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
from .store import Store
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

store = Store()
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


@app.get("/health")
def health():
    return {"status": "ok"}


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


@app.get("/routes")
def list_routes(_: TokenRecord = Depends(require_admin_token)):
    return [route.model_dump() for route in store.list()]


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


@app.post("/routes")
def create_route(
    data: ApiRouteCreate,
    _: TokenRecord = Depends(require_admin_token),
):
    return store.create(data).model_dump()


@app.patch("/routes/{rid}")
def update_route(
    rid: str,
    patch: dict,
    _: TokenRecord = Depends(require_admin_token),
):
    if rid not in store.routes:
        raise HTTPException(status_code=404, detail="not found")
    return store.update(rid, patch).model_dump()


@app.delete("/routes/{rid}")
def delete_route(rid: str, _: TokenRecord = Depends(require_admin_token)):
    store.delete(rid)
    return {"ok": True}


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
    history = chat_history.get(record.token)
    chat_history.append(record.token, "user", req.prompt)
    response = await handle_ask(req, history=history)
    chat_history.append(record.token, "assistant", response.get("message", ""))
    return response


@app.post("/api/v1/ask/reset")
def api_ask_reset(record: TokenRecord = Depends(require_token)):
    chat_history.clear(record.token)
    return {"ok": True}


async def sse_stream_generator(req: ChatRequest, history: list, history_key: str):
    """Generate SSE events for queue countdown and token streaming from Ollama."""

    final_prompt = build_augmented_prompt(req.prompt, history)
    log_prompt(final_prompt)
    assistant_chunks: list[str] = []

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
    max_context = settings.ollama_max_context.get(settings.ollama_model)
    if isinstance(max_context, int) and max_context > 0:
        ollama_payload["options"] = {"num_ctx": max_context}

    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            async with client.stream("POST", ollama_url, json=ollama_payload) as response:
                if response.status_code >= 400:
                    # Lees fouttekst voor logging zodat we weten waarom de fallback triggert.
                    error_body = await response.aread()
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

    except Exception as exc:
        # Fallback to mock response if Ollama is not available
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

    # Send final done event
    event_data = json.dumps({"done": True})
    yield f"data: {event_data}\n\n"


@app.post("/api/v1/ask/stream")
async def api_ask_stream(req: ChatRequest, record: TokenRecord = Depends(require_token)):
    """Stream SSE response with queue position and token-by-token LLM output."""
    history = chat_history.get(record.token)
    chat_history.append(record.token, "user", req.prompt)
    return StreamingResponse(
        sse_stream_generator(req, history, record.token),
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
