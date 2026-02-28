import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rich.logging import RichHandler

from .broadcast import broadcaster
from .db import init_db, close_db
from .views import router as views_router

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)


async def game_loop():
    """Temporary game loop — sends a ping every second to all connected clients."""
    while True:
        await broadcaster.send({
            "source": "world",
            "type": "event",
            "name": "ping",
            "payload": {"ts": time.time()},
        })
        await asyncio.sleep(1)


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
