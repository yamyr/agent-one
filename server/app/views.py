import logging
from typing import Any
import re

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from surrealdb import Surreal

from .broadcast import broadcaster
from .db import get_db
from .i18n import DEFAULT_TRANSLATIONS, SUPPORTED_LOCALES, resolve_locale

logger = logging.getLogger(__name__)
router = APIRouter()


I18N_TABLE = "i18n_entry"

def _entry_id(key: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", key)


def _safe_db_seed(db: Surreal) -> None:
    for key, translations in DEFAULT_TRANSLATIONS.items():
        try:
            db.query(
                "UPSERT type::thing($table, $key) CONTENT $translations;",
                {"table": I18N_TABLE, "key": _entry_id(key), "translations": {"key": key, "translations": translations}},
            )
        except Exception:
            # Fall back to create if UPSERT not available
            try:
                db.create(f"{I18N_TABLE}:{_entry_id(key)}", {"key": key, "translations": translations})
            except Exception:
                continue


def _load_entries(db: Surreal) -> list[dict[str, Any]]:
    try:
        data = db.select(I18N_TABLE)
        if isinstance(data, list):
            return data
    except Exception:
        pass

    try:
        result = db.query(f"SELECT key, translations FROM {I18N_TABLE};")
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and "result" in item and isinstance(item["result"], list):
                    return item["result"]
    except Exception:
        pass

    return []


@router.get("/mission/status")
def mission_status():
    """Placeholder endpoint — returns current mission state."""
    return {"status": "idle", "mission": None}


@router.get("/i18n/translations")
def i18n_translations(locale: str | None = None, db: Surreal = Depends(get_db)):
    _safe_db_seed(db)
    selected = resolve_locale(locale)
    entries = _load_entries(db)

    resolved: dict[str, str] = {}
    for entry in entries:
        key = entry.get("key")
        translations = entry.get("translations") or {}
        if not key:
            continue
        resolved[key] = translations.get(selected) or translations.get("en-US") or key

    # Ensure at least defaults are present
    for key, translations in DEFAULT_TRANSLATIONS.items():
        resolved.setdefault(key, translations.get(selected) or translations.get("en-US") or key)

    return {
        "locale": selected,
        "fallback": "en-US",
        "locales": SUPPORTED_LOCALES,
        "translations": resolved,
    }


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
