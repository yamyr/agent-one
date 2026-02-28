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
from .station import StationAgent
from .views import router as views_router
from .world import execute_action, get_snapshot, WORLD, charge_rover

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)

logger = logging.getLogger(__name__)


station = StationAgent()
simulation_paused = False


async def _trigger_station(event):
    """Feed an event to the station agent and broadcast its response."""
    try:
        station_events = await asyncio.to_thread(station.handle_event, event)
        for se in station_events:
            await broadcaster.send(se)
        await broadcaster.send(
            {
                "source": "world",
                "type": "event",
                "name": "state",
                "payload": get_snapshot(),
            }
        )
    except Exception:
        logger.exception("Station trigger error")


async def agent_loop(agent, interval):
    """Run an agent every `interval` seconds, broadcast events."""
    while True:
        # Stop if mission is terminal
        mission_status = WORLD["mission"]["status"]
        if mission_status in ("success", "failed"):
            logger.info("Agent loop stopped (%s): mission %s", agent.agent_id, mission_status)
            return

        if simulation_paused:
            await asyncio.sleep(interval)
            continue

        try:
            turn = await asyncio.to_thread(agent.run_turn)
            events = []

            if turn["thinking"]:
                events.append(
                    {
                        "source": agent.agent_id,
                        "type": "event",
                        "name": "thinking",
                        "payload": {"text": turn["thinking"]},
                    }
                )

            if turn["action"]:
                result = execute_action(
                    agent.agent_id,
                    turn["action"]["name"],
                    turn["action"]["params"],
                )
                if result["ok"]:
                    events.append(
                        {
                            "source": agent.agent_id,
                            "type": "action",
                            "name": turn["action"]["name"],
                            "payload": result,
                        }
                    )
                    ground = result.get("ground")
                    if ground and ground["stone"]:
                        events.append(
                            {
                                "source": agent.agent_id,
                                "type": "event",
                                "name": "check",
                                "payload": ground,
                            }
                        )
                    mission_event = result.get("mission")
                    if mission_event:
                        events.append(
                            {
                                "source": "world",
                                "type": "event",
                                "name": "mission_" + mission_event["status"],
                                "payload": mission_event,
                            }
                        )

            for event in events:
                await broadcaster.send(event)
            await broadcaster.send(
                {
                    "source": "world",
                    "type": "event",
                    "name": "state",
                    "payload": get_snapshot(),
                }
            )

            # Auto-charge rover when it arrives at station
            rover = WORLD["agents"].get(agent.agent_id)
            station_agent = WORLD["agents"].get("station")
            if (
                rover
                and station_agent
                and rover["position"] == station_agent["position"]
                and rover["battery"] < 1.0
            ):
                charge_result = charge_rover(agent.agent_id)
                if charge_result["ok"]:
                    await broadcaster.send(
                        {
                            "source": "station",
                            "type": "action",
                            "name": "charge_rover",
                            "payload": charge_result,
                        }
                    )

            # Trigger station on stone-found events
            for event in events:
                if event["name"] == "check":
                    await _trigger_station(event)

        except Exception:
            logger.exception("Agent loop error (%s)", agent.agent_id)
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app):
    init_db()

    # Station defines initial missions at startup
    try:
        station_events = await asyncio.to_thread(station.define_mission)
        for event in station_events:
            await broadcaster.send(event)
        await broadcaster.send(
            {
                "source": "world",
                "type": "event",
                "name": "state",
                "payload": get_snapshot(),
            }
        )
    except Exception:
        logger.exception("Station startup failed")

    mock_task = asyncio.create_task(agent_loop(MockRoverAgent(), interval=2))
    mistral_task = asyncio.create_task(agent_loop(RoverAgent(), interval=2))
    yield
    mock_task.cancel()
    mistral_task.cancel()
    close_db()


app = FastAPI(
    title="Mars Mission API",
    version="0.1.0",  # x-release-please-version
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
    global simulation_paused
    simulation_paused = True
    return {"paused": True}


@app.post("/simulation/resume")
def resume_simulation():
    global simulation_paused
    simulation_paused = False
    return {"paused": False}


@app.get("/simulation/status")
def simulation_status():
    return {"paused": simulation_paused}


# Serve Vue static files (must be after all API routes)
_ui_dir = Path(__file__).resolve().parent.parent / "ui_dist"
if _ui_dir.is_dir():
    app.mount("/", StaticFiles(directory=_ui_dir, html=True), name="ui")
