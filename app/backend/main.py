import asyncio
import json

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .apiAsk import handle_ask
from .contacts_repo import ContactsRepository
from .devices_repo import DevicesRepository
from .schemas import (
    ApiRouteCreate,
    ChatRequest,
    Contact,
    ContactCreate,
    Device,
    DeviceCreate,
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
    return handle_ask(req)


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


@app.get("/devices", response_model=list[Device])
def list_devices():
    return devices_repo.list_devices()


@app.post("/devices", response_model=Device)
def create_device(data: DeviceCreate):
    try:
        return devices_repo.create_device(data)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
