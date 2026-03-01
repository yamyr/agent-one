import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from rich.logging import RichHandler

from .agent import RoverMistralLoop, DroneMistralLoop
from .broadcast import broadcaster
from .config import settings
from .db import init_db, close_db
from .host import Host
from .narrator import Narrator
from .views import router as views_router
from .world import reset_world, set_agent_model
from .voice import VoiceCommander

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)

logger = logging.getLogger(__name__)

narrator = Narrator(broadcast_fn=broadcaster.send)
host = Host(narrator=narrator)
voice_commander = VoiceCommander(host=host)

AGENT_MAP = {
    "rover-mistral": lambda: RoverMistralLoop(
        agent_id="rover-mistral", interval=settings.llm_turn_interval_seconds
    ),
    "rover-2": lambda: RoverMistralLoop(
        agent_id="rover-2", interval=settings.llm_turn_interval_seconds
    ),
    "drone-mistral": lambda: DroneMistralLoop(interval=2.0),
}


def _register_agents():
    """Construct and register agents from settings.active_agents."""
    # Station model — set here so it survives reset_world()
    set_agent_model("station", host._station.model)
    active = [a.strip() for a in settings.active_agents.split(",") if a.strip()]
    for name in active:
        factory = AGENT_MAP.get(name)
        if factory:
            host.register(factory())
        else:
            logging.getLogger(__name__).warning("Unknown agent in ACTIVE_AGENTS: %s", name)


@asynccontextmanager
async def lifespan(app):
    init_db()
    _register_agents()
    await host.start()
    yield
    host.stop()
    close_db()


app = FastAPI(
    title="Mars Mission API",
    version="0.1.0",
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
    host.stop()
    reset_world()
    narrator.reset()
    _register_agents()
    await host.start()
    return {"reset": True}


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


@app.post("/voice/command")
async def voice_command(audio: UploadFile):
    """Accept audio upload, transcribe via Voxtral, route command to agents."""
    audio_bytes = await audio.read()
    return await voice_commander.handle_voice_command(audio_bytes, audio.filename or "audio.webm")


# Serve Vue static files (must be after all API routes)
_ui_dir = Path(__file__).resolve().parent.parent / "ui_dist"
if _ui_dir.is_dir():
    app.mount("/", StaticFiles(directory=_ui_dir, html=True), name="ui")
