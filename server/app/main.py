import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from rich.logging import RichHandler

from .agent import MockRoverAgent, RoverAgent
from .broadcast import broadcaster
from .config import settings
from .db import init_db, close_db
from .views import router as views_router
from .world import execute_action, get_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)

logger = logging.getLogger(__name__)


async def agent_loop(agent, interval):
    """Run an agent every `interval` seconds, broadcast events."""
    while True:
        try:
            turn = await asyncio.to_thread(agent.run_turn)
            events = []

            if turn["thinking"]:
                events.append({
                    "source": agent.agent_id,
                    "type": "event",
                    "name": "thinking",
                    "payload": {"text": turn["thinking"]},
                })

            if turn["action"]:
                result = execute_action(
                    agent.agent_id,
                    turn["action"]["name"],
                    turn["action"]["params"],
                )
                if result["ok"]:
                    events.append({
                        "source": agent.agent_id,
                        "type": "action",
                        "name": turn["action"]["name"],
                        "payload": result,
                    })
                    ground = result.get("ground")
                    if ground and ground["stone"]:
                        events.append({
                            "source": agent.agent_id,
                            "type": "event",
                            "name": "check",
                            "payload": ground,
                        })

            for event in events:
                await broadcaster.send(event)
            await broadcaster.send({
                "source": "world",
                "type": "event",
                "name": "state",
                "payload": get_snapshot(),
            })
        except Exception:
            logger.exception("Agent loop error (%s)", agent.agent_id)
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app):
    init_db()
    mock_task = asyncio.create_task(agent_loop(MockRoverAgent(), interval=10))
    mistral_task = asyncio.create_task(agent_loop(RoverAgent(), interval=20))
    yield
    mock_task.cancel()
    mistral_task.cancel()
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


# Serve Vue static files (must be after all API routes)
_ui_dir = Path(__file__).resolve().parent.parent / "ui_dist"
if _ui_dir.is_dir():
    app.mount("/", StaticFiles(directory=_ui_dir, html=True), name="ui")
