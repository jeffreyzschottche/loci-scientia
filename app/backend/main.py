import asyncio
import json
import logging
import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .apiAsk import build_augmented_prompt, handle_ask, log_prompt
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

logger = logging.getLogger(__name__)

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
    return await handle_ask(req)


async def sse_stream_generator(req: ChatRequest):
    """Generate SSE events for queue countdown and token streaming from Ollama."""

    final_prompt = build_augmented_prompt(req.prompt)
    log_prompt(final_prompt)

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
