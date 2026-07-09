"""WebSocket event stream (spec section 4.5).

Sends recent history on connect, then live events. Pings every 30s so
proxies/clients don't idle-close the socket.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/events")
async def event_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    bus = websocket.app.state.bus
    queue = bus.subscribe_async()
    try:
        # Replay recent history so a freshly opened dashboard is not empty.
        for evt in bus.recent(limit=30):
            await websocket.send_json(evt)
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(event.to_dict())
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping", "payload": {}})
    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe_async(queue)
