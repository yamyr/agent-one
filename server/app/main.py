import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from rich.logging import RichHandler

from .agent import (
    RoverMistralLoop,
    DroneMistralLoop,
    HaulerLoop,
    RoverHuggingFaceLoop,
    DroneHuggingFaceLoop,
    StationLoop,
    RoverLargeLoop,
    RoverMediumLoop,
    RoverCodestralLoop,
    RoverMinistralLoop,
    RoverMagistralLoop,
)
from .agents_api import RoverAgentsApiLoop, DroneAgentsApiLoop, StationAgentsApiLoop
from .broadcast import broadcaster
from .config import settings
from .db import init_db, close_db
from .host import Host
from .narrator import Narrator
from .views import router as views_router
from .voice import VoiceCommandProcessor, SUPPORTED_AUDIO_TYPES
from .presets import apply_preset, list_presets, PRESETS
from .world import reset_world, WORLD, set_agent_model
from .training import collector as training_collector
from .events import timeline as event_timeline, DEMO_TIMELINE

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)

logger = logging.getLogger(__name__)

narrator = Narrator(broadcast_fn=broadcaster.send)
_reset_lock = asyncio.Lock()
host = Host(narrator=narrator)
voice_processor = VoiceCommandProcessor()

AGENT_MAP = {
    "rover-mistral": lambda: RoverMistralLoop(
        agent_id="rover-mistral", interval=settings.llm_turn_interval_seconds
    ),
    "rover-2": lambda: RoverHuggingFaceLoop(
        agent_id="rover-2", interval=settings.llm_turn_interval_seconds
    ),
    "drone-mistral": lambda: DroneMistralLoop(interval=settings.drone_turn_interval_seconds),
    "hauler-mistral": lambda: HaulerLoop(
        agent_id="hauler-mistral", interval=settings.llm_turn_interval_seconds
    ),
    "rover-huggingface": lambda: RoverHuggingFaceLoop(
        agent_id="rover-huggingface", interval=settings.llm_turn_interval_seconds
    ),
    "drone-huggingface": lambda: DroneHuggingFaceLoop(
        interval=settings.drone_turn_interval_seconds
    ),
    "station-loop": lambda: StationLoop(interval=20.0),
    "rover-large": lambda: RoverLargeLoop(
        agent_id="rover-large", interval=settings.llm_turn_interval_seconds
    ),
    "rover-medium": lambda: RoverMediumLoop(
        agent_id="rover-medium", interval=settings.llm_turn_interval_seconds
    ),
    "rover-codestral": lambda: RoverCodestralLoop(
        agent_id="rover-codestral", interval=settings.llm_turn_interval_seconds
    ),
    "rover-ministral": lambda: RoverMinistralLoop(
        agent_id="rover-ministral", interval=settings.llm_turn_interval_seconds
    ),
    "rover-magistral": lambda: RoverMagistralLoop(
        agent_id="rover-magistral", interval=settings.llm_turn_interval_seconds
    ),
    "rover-agents-api": lambda: RoverAgentsApiLoop(
        agent_id="rover-agents-api", interval=settings.llm_turn_interval_seconds
    ),
    "drone-agents-api": lambda: DroneAgentsApiLoop(interval=settings.drone_turn_interval_seconds),
    "station-agents-api": lambda: StationAgentsApiLoop(interval=20.0),
}


def _register_agents():
    """Construct and register agents from settings.active_agents."""
    # Station model — set here so it survives reset_world()
    set_agent_model("station", host._station.model)
    active = [a.strip() for a in settings.active_agents.split(",") if a.strip()]

    # If backend is agents_api, swap default chat_completions agents for agents_api equivalents
    if settings.agent_backend == "agents_api":
        swap_map = {
            "rover-mistral": "rover-agents-api",
            "drone-mistral": "drone-agents-api",
            "station-loop": "station-agents-api",
        }
        active = [swap_map.get(a, a) for a in active]

    for name in active:
        factory = AGENT_MAP.get(name)
        if factory:
            host.register(factory())
        else:
            logging.getLogger(__name__).warning("Unknown agent in ACTIVE_AGENTS: %s", name)


def _register_agents_with_preset(preset_name: str | None = None):
    """Apply preset overrides to active_agents before registering.

    If the preset specifies an active_agents list, temporarily override
    settings.active_agents for agent registration.
    """
    original_agents = settings.active_agents
    if preset_name and preset_name in PRESETS:
        preset = PRESETS[preset_name]
        if preset.get("active_agents"):
            settings.active_agents = preset["active_agents"]
    try:
        _register_agents()
    finally:
        settings.active_agents = original_agents


@asynccontextmanager
async def lifespan(app):
    init_db()
    training_collector._ensure_dir()
    # Apply startup preset if configured
    if settings.preset != "default":
        apply_preset(settings.preset, WORLD)
        logger.info("Applying startup preset: %s", settings.preset)
        _register_agents_with_preset(settings.preset)
    else:
        _register_agents()
    # Load scripted event timeline from config
    if settings.event_script:
        count = event_timeline.load_from_file(settings.event_script)
        logger.info("Loaded %d scripted events from %s", count, settings.event_script)
    await host.start()
    yield
    host.stop()
    close_db()


app = FastAPI(
    title="Mars Mission API",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(views_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/simulation/pause")
def pause_simulation():
    host.paused = True
    return {"paused": True}


@app.post("/simulation/resume")
def resume_simulation():
    host.paused = False
    return {"paused": False}


@app.get("/simulation/status")
def simulation_status():
    return {"paused": host.paused}


@app.post("/simulation/reset")
async def reset_simulation():
    async with _reset_lock:
        host.stop()
        reset_world()
        narrator.reset()
        _register_agents()
        await host.start()
    return {"reset": True}


# ── Preset endpoints ────────────────────────────────────────────────────────


@app.get("/api/presets")
def get_presets():
    """List all available simulation presets."""
    return list_presets()


@app.post("/api/presets/{name}/apply")
async def apply_preset_endpoint(name: str):
    """Apply a simulation preset: reset world, apply overrides, restart agents."""
    if name not in PRESETS:
        raise HTTPException(status_code=404, detail=f"Unknown preset: {name!r}")
    async with _reset_lock:
        host.stop()
        reset_world()
        apply_preset(name, WORLD)
        narrator.reset()
        _register_agents_with_preset(name)
        await host.start()
    return {"ok": True, "preset": name}


# ── Timeline endpoints ──────────────────────────────────────────────────────


@app.get("/api/timeline")
def get_timeline():
    return event_timeline.get_status()


@app.post("/api/timeline/load")
def load_timeline(body: dict):
    events = body.get("events", [])
    if not isinstance(events, list):
        raise HTTPException(status_code=400, detail="'events' must be a list")
    count = event_timeline.load(events)
    return {"ok": True, "loaded": count}


@app.post("/api/timeline/load-demo")
def load_demo_timeline():
    count = event_timeline.load(DEMO_TIMELINE)
    return {"ok": True, "loaded": count}


@app.post("/api/timeline/clear")
def clear_timeline():
    event_timeline.clear()
    return {"ok": True}


@app.post("/api/timeline/reset")
def reset_timeline():
    event_timeline.reset()
    return {"ok": True}


@app.post("/narration/toggle")
def toggle_narration():
    narrator.enabled = not narrator.enabled
    return {"enabled": narrator.enabled}


@app.get("/narration/status")
def narration_status():
    return {"enabled": narrator.enabled}


@app.post("/mission/abort")
async def abort_mission(reason: str = "Manual abort from mission control"):
    return await host.abort_mission(reason)


@app.post("/rover/{rover_id}/recall")
async def recall_rover(rover_id: str):
    return await host.recall_rover(rover_id)


@app.post("/api/confirm")
async def confirm_action(body: dict):
    """Accept human confirmation response for a pending rover action."""
    from .protocol import make_message

    request_id = body.get("request_id")
    confirmed = body.get("confirmed")

    if request_id is None or confirmed is None:
        return {"ok": False, "error": "Missing required fields: request_id, confirmed"}

    resolved = host.resolve_confirm(request_id, bool(confirmed))
    if not resolved:
        return {"ok": False, "error": "No pending confirmation with this request_id"}

    # Broadcast confirm_response event so UI can dismiss modal
    msg = make_message(
        source="human",
        type="command",
        name="confirm_response",
        payload={"request_id": request_id, "confirmed": bool(confirmed)},
    )
    await broadcaster.send(msg.to_dict())

    return {"ok": True, "request_id": request_id, "confirmed": bool(confirmed)}


# ── Voice command endpoint ──────────────────────────────────────────────────


@app.post("/api/voice-command")
async def voice_command(audio: UploadFile):
    """Accept audio upload, transcribe via Voxtral, parse command, and route."""
    from .protocol import make_message

    # Validate content type
    content_type = audio.content_type or ""
    if content_type and content_type not in SUPPORTED_AUDIO_TYPES:
        return {
            "ok": False,
            "error": f"Unsupported audio format: {content_type}. "
            f"Supported: {', '.join(sorted(SUPPORTED_AUDIO_TYPES))}",
        }

    # Read audio bytes
    audio_bytes = await audio.read()
    if not audio_bytes:
        return {"ok": False, "error": "Empty audio file"}

    # Process: transcribe + parse command
    try:
        result = await voice_processor.process(
            audio_bytes=audio_bytes,
            filename=audio.filename or "audio.wav",
        )
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception:
        logger.exception("Voice command processing failed")
        return {"ok": False, "error": "Voice command processing failed"}

    # Broadcast the voice command event to all WebSocket clients
    msg = make_message(
        source="human",
        type="command",
        name="voice_command",
        payload={
            "transcript": result["transcript"],
            "command": result["command"],
            "params": result["params"],
            "confidence": result["confidence"],
        },
    )
    await broadcaster.send(msg.to_dict())

    # Route recognized commands through the Host
    command = result["command"]
    params = result["params"]

    if command == "recall_rover":
        rover_id = params.get("rover_id", "rover-mistral")
        action_result = await host.recall_rover(rover_id)
        result["action_result"] = action_result
    elif command == "abort_mission":
        reason = params.get("reason", "Voice command abort")
        action_result = await host.abort_mission(reason)
        result["action_result"] = action_result
    elif command == "pause_simulation":
        host.paused = True
        result["action_result"] = {"ok": True, "paused": True}
    elif command == "resume_simulation":
        host.paused = False
        result["action_result"] = {"ok": True, "paused": False}

    return {"ok": True, **result}


# Serve Vue static files (must be after all API routes)
_ui_dir = Path(__file__).resolve().parent.parent / "ui_dist"
if _ui_dir.is_dir():
    _index_html = _ui_dir / "index.html"

    # Pre-index every servable file at startup so the request handler
    # never builds a filesystem path from user input.
    _static_files: dict[str, Path] = {}
    for child in _ui_dir.rglob("*"):
        if child.is_file() and child.name != "index.html":
            rel = child.relative_to(_ui_dir).as_posix()
            _static_files[rel] = child

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        asset = _static_files.get(path)
        if asset is not None:
            return FileResponse(asset)
        return FileResponse(_index_html)
