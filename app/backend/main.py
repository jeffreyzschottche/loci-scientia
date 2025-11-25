import asyncio
import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .apiAsk import describe_contact, describe_device, handle_ask
from .contacts_repo import ContactsRepository
from .devices_repo import DevicesRepository
from .schemas import (
    ApiRouteCreate,
    ChatRequest,
    Contact,
    ContactCreate,
    ContactPatch,
    Device,
    DeviceCreate,
    DevicePatch,
)
from .settings import settings
from .store import Store

app = FastAPI(title="Loci Backend")
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

MAX_CONTEXT_ITEMS = 3
MIN_CONTEXT_SCORE = 0.35
PROMPT_TEMPLATE_PATH = Path(__file__).with_name("prompt.txt")
PROMPT_LOG_PATH = Path(__file__).resolve().parents[2] / "promptlog.log"


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


@lru_cache(maxsize=1)
def _prompt_template() -> str:
    try:
        return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return (
            "Je bent de Loci Scientia assistent. Gebruik context waar mogelijk, "
            "maar verzin niets als er geen relevante context beschikbaar is. "
            "Leg je antwoord duidelijk uit en antwoord in het Nederlands."
        )


def build_augmented_prompt(user_prompt: str) -> str:
    base_lines = [f"User Prompt: {user_prompt.strip()}"]
    context_lines = _gather_context_lines(user_prompt)
    if context_lines:
        base_lines.append("> context:")
        base_lines.extend(context_lines)
    template = _prompt_template()
    if template:
        base_lines.append("")
        base_lines.append(template)
    return "\n".join(base_lines).strip()


def _log_prompt(final_prompt: str) -> None:
    try:
        PROMPT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with PROMPT_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"[{datetime.utcnow().isoformat()}Z]\n{final_prompt}\n\n")
    except OSError:
        # Logging failures should not break the request flow.
        pass


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/routes")
def list_routes():
    return [route.model_dump() for route in store.list()]


@app.post("/routes")
def create_route(data: ApiRouteCreate):
    return store.create(data).model_dump()


@app.patch("/routes/{rid}")
def update_route(rid: str, patch: dict):
    if rid not in store.routes:
        raise HTTPException(status_code=404, detail="not found")
    return store.update(rid, patch).model_dump()


@app.delete("/routes/{rid}")
def delete_route(rid: str):
    store.delete(rid)
    return {"ok": True}


@app.post("/api/v1/ask")
async def api_ask(req: ChatRequest):
    return handle_ask(req)


async def sse_stream_generator(req: ChatRequest):
    """Generate SSE events for queue countdown and token streaming from Ollama."""

    final_prompt = build_augmented_prompt(req.prompt)
    _log_prompt(final_prompt)

    # Short queue countdown: 2 to 0 with 1 second between each
    for position in range(2, -1, -1):
        event_data = json.dumps({"status": "queued", "position": position})
        yield f"data: {event_data}\n\n"
        await asyncio.sleep(1)

    # Call Ollama API with streaming
    ollama_url = "http://localhost:11434/api/generate"
    ollama_payload = {
        "model": "gemma3:4b",
        "prompt": final_prompt,
        "stream": True,
    }

    ollama_available = False

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", ollama_url, json=ollama_payload) as response:
                response.raise_for_status()
                ollama_available = True

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        # Ollama sends token in "response" field
                        if "response" in data:
                            token = data["response"]
                            if token:  # Only send non-empty tokens
                                event_data = json.dumps({"token": token, "done": False})
                                yield f"data: {event_data}\n\n"

                        # Check if done
                        if data.get("done", False):
                            break

                    except json.JSONDecodeError:
                        continue

    except (httpx.HTTPError, httpx.ConnectError) as exc:
        # Fallback to mock response if Ollama is not available
        mock_response = f"[Ollama niet beschikbaar - Mock response] Je vroeg: '{req.prompt}'. Dit is een test response omdat Ollama niet draait. Installeer Ollama via: https://ollama.com"

        # Stream the mock response word by word
        words = mock_response.split()
        for word in words:
            token = word + " "
            event_data = json.dumps({"token": token, "done": False})
            yield f"data: {event_data}\n\n"
            await asyncio.sleep(0.1)

    # Send final done event
    event_data = json.dumps({"done": True})
    yield f"data: {event_data}\n\n"


@app.post("/api/v1/ask/stream")
async def api_ask_stream(req: ChatRequest):
    """Stream SSE response with queue position and token-by-token LLM output."""
    return StreamingResponse(
        sse_stream_generator(req),
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
def list_devices():
    return devices_repo.list_devices()


@app.post("/devices", response_model=Device)
def create_device(data: DeviceCreate):
    try:
        return devices_repo.create_device(data)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.patch("/devices/{device_id}", response_model=Device)
def patch_device(device_id: str, patch: DevicePatch):
    try:
        return devices_repo.update_device(device_id, patch)
    except ValueError:
        raise HTTPException(status_code=404, detail="device not found")
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/devices/{device_id}")
def delete_device(device_id: str):
    try:
        devices_repo.delete_device(device_id)
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
