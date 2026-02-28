import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from rich.logging import RichHandler

from .broadcast import broadcaster
from .config import settings
from .db import init_db, close_db
from .sim_agent import MockSimAgent
from .views import router as views_router

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)

logger = logging.getLogger(__name__)


async def agent_loop(app: FastAPI, interval: float = 3.0):
    """Run the sim agent every `interval` seconds, broadcast events."""
    agent: MockSimAgent = app.state.sim_agent
    while not agent.is_terminal():
        try:
            step_result, observation = agent.run_turn()
            await broadcaster.send({
                "source": "rover-1",
                "type": "action",
                "name": "step_result",
                "payload": step_result,
            })
            await broadcaster.send({
                "source": "world",
                "type": "event",
                "name": "state",
                "payload": observation,
            })
        except Exception:
            logger.exception("Agent loop error")
        await asyncio.sleep(interval)
    logger.info("Simulation reached terminal state — agent loop stopped.")


@asynccontextmanager
async def lifespan(app):
    try:
        init_db()
    except RuntimeError:
        logger.warning("SurrealDB unavailable — running without database")
    app.state.sim_agent = MockSimAgent(seed=42)
    task = asyncio.create_task(agent_loop(app, interval=3.0))
    yield
    task.cancel()
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
