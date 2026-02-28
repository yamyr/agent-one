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
from .world import execute_action, get_snapshot, reset_world, WORLD, charge_rover, next_tick
from .narrator import Narrator

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)

logger = logging.getLogger(__name__)


station = StationAgent()
simulation_paused = False
_agent_tasks = []
narrator = Narrator(broadcast_fn=broadcaster.send)


async def _trigger_station(event):
    """Feed an event to the station agent and broadcast its response."""
    try:
        station_events = await asyncio.to_thread(station.handle_event, event)
        for se in station_events:
            se["tick"] = WORLD["tick"]
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
            tick = next_tick()
            events = []

            if turn["thinking"]:
                events.append(
                    {
                        "source": agent.agent_id,
                        "type": "event",
                        "name": "thinking",
                        "tick": tick,
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
                            "tick": tick,
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
                                "tick": tick,
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
                                "tick": tick,
                                "payload": mission_event,
                            }
                        )

            for event in events:
                await broadcaster.send(event)
                await narrator.feed(event)
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
                    charge_event = {
                        "source": "station",
                        "type": "action",
                        "name": "charge_rover",
                        "payload": charge_result,
                    }
                    await broadcaster.send(charge_event)
                    await narrator.feed(charge_event)

            # Trigger station on stone-found events
            for event in events:
                if event["name"] == "check":
                    await _trigger_station(event)

        except Exception:
            logger.exception("Agent loop error (%s)", agent.agent_id)
        await asyncio.sleep(interval)


async def _station_startup():
    """Run station mission definition in background."""
    try:
        station_events = await asyncio.to_thread(station.define_mission)
        for event in station_events:
            event["tick"] = WORLD["tick"]
            await broadcaster.send(event)
            await narrator.feed(event)
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


async def _start_simulation():
    """Start station mission definition and agent loops."""
    global simulation_paused
    simulation_paused = False

    narrator.reset()
    narrator.start()
    _agent_tasks.append(asyncio.create_task(_station_startup()))

    active = [a.strip() for a in settings.active_agents.split(",") if a.strip()]
    agent_map = {
        "rover-mock": lambda: MockRoverAgent(),
        "rover-mistral": lambda: RoverAgent(),
    }
    interval_map = {
        "rover-mock": settings.agent_turn_interval_seconds,
        "rover-mistral": settings.llm_turn_interval_seconds,
    }
    for name in active:
        factory = agent_map.get(name)
        if factory:
            interval = interval_map.get(name, settings.agent_turn_interval_seconds)
            _agent_tasks.append(asyncio.create_task(agent_loop(factory(), interval=interval)))
            logger.info("Started agent loop: %s (interval=%.1fs)", name, interval)
        else:
            logger.warning("Unknown agent in ACTIVE_AGENTS: %s", name)


def _stop_simulation():
    """Cancel all running agent loops and narrator."""
    narrator.stop()
    for task in _agent_tasks:
        task.cancel()
    _agent_tasks.clear()



@asynccontextmanager
async def lifespan(app):
    init_db()
    await _start_simulation()
    yield
    _stop_simulation()
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


@app.post("/simulation/reset")
async def reset_simulation():
    _stop_simulation()
    reset_world()
    narrator.reset()
    await _start_simulation()
    return {"reset": True}



@app.post("/narration/toggle")
def toggle_narration():
    narrator.enabled = not narrator.enabled
    return {"enabled": narrator.enabled}


@app.get("/narration/status")
def narration_status():
    return {"enabled": narrator.enabled}


# Serve Vue static files (must be after all API routes)
_ui_dir = Path(__file__).resolve().parent.parent / "ui_dist"
if _ui_dir.is_dir():
    app.mount("/", StaticFiles(directory=_ui_dir, html=True), name="ui")
