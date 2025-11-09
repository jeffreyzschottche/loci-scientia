import asyncio
import json

import websockets


class WSClient:
    def __init__(self, url: str):
        self.url = url
        self._conn = None

    async def _ensure(self):
        if self._conn is None:
            self._conn = await websockets.connect(self.url)

    async def stream_echo(self, prompt: str):
        await self._ensure()
        await self._conn.send(json.dumps({"prompt": prompt}))
        while True:
            message = await self._conn.recv()
            data = json.loads(message)
            if data.get("done"):
                break
            yield data.get("token", "")

    async def close(self):
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
