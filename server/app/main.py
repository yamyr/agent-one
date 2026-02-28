import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rich.logging import RichHandler

from .agent import MockRoverAgent
from .broadcast import broadcaster
from .db import init_db, close_db
from .views import router as views_router
from .world import get_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)

logger = logging.getLogger(__name__)

TURN_INTERVAL = 10  # seconds between agent turns


async def game_loop():
    """Run the rover agent every TURN_INTERVAL seconds, broadcast events."""
    rover = MockRoverAgent()
    while True:
        try:
            events = await asyncio.to_thread(
                rover.run_turn, "Observe your surroundings and decide your next move.",
            )
            for event in events:
                await broadcaster.send(event)
            await broadcaster.send({
                "source": "world",
                "type": "event",
                "name": "state",
                "payload": get_snapshot(),
            })
        except Exception:
            logger.exception("Game loop error")
        await asyncio.sleep(TURN_INTERVAL)


@asynccontextmanager
async def lifespan(app):
    init_db()
    loop_task = asyncio.create_task(game_loop())
    yield
    loop_task.cancel()
    close_db()


app = FastAPI(
    title="Mars Mission API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4089"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(views_router)


@app.get("/health")
def health():
    return {"status": "ok"}
