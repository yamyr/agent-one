import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .broadcast import broadcaster

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/mission/status")
def mission_status():
    """Placeholder endpoint — returns current mission state."""
    return {"status": "idle", "mission": None}


@router.websocket("/ws")
async def websocket_stream(ws: WebSocket):
    """WebSocket endpoint for streaming simulation events to the UI."""
    await broadcaster.connect(ws)
    try:
        while True:
            # keep connection alive; we don't expect input from client
            await ws.receive_text()
    except WebSocketDisconnect:
        broadcaster.disconnect(ws)
