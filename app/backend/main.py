import asyncio
import json

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .schemas import ApiRouteCreate, ChatRequest
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


@app.post("/chat")
async def chat(req: ChatRequest):
    return {"text": f"Echo: {req.prompt}"}


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
