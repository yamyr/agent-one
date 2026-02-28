import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .translations import get_all_translations, get_supported_languages, set_translation

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/mission/status")
def mission_status():
    """Placeholder endpoint — returns current mission state."""
    return {"status": "idle", "mission": None}


@router.get("/translations/{language}")
def get_translations(language: str):
    """Get all translations for a specific language."""
    return get_all_translations(language)


@router.get("/translations/languages")
def get_languages():
    """Get list of supported languages."""
    return {"languages": get_supported_languages()}


@router.post("/translations/{language}/{key}")
def update_translation(language: str, key: str, value: str):
    """Update a specific translation."""
    set_translation(language, key, value)
    return {"success": True, "language": language, "key": key, "value": value}


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
