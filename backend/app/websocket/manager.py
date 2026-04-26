import asyncio
import json
import logging
from datetime import datetime
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self.active.append(ws)
        logger.info("WS connected. Total: %d", len(self.active))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self.active = [c for c in self.active if c is not ws]
        logger.info("WS disconnected. Total: %d", len(self.active))

    async def broadcast(self, event: str, data: dict) -> None:
        if not self.active:
            return
        message = json.dumps({
            "event": event,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })
        dead: list[WebSocket] = []
        async with self._lock:
            targets = list(self.active)
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

    async def send_personal(self, ws: WebSocket, event: str, data: dict) -> None:
        try:
            await ws.send_text(json.dumps({
                "event": event,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }))
        except Exception as e:
            logger.warning("Failed to send personal WS message: %s", e)


ws_manager = ConnectionManager()
