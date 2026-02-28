import json
import logging

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from .broadcast import broadcaster

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/mission/status")
def mission_status(request: Request):
    """Return current mission state from the sim agent."""
    agent = request.app.state.sim_agent
    obs = agent.get_observation()
    return {
        "status": obs.get("status", "idle"),
        "mission": obs.get("mission"),
        "tick": obs.get("tick", 0),
    }


@router.websocket("/ws")
async def websocket_stream(ws: WebSocket):
    """WebSocket endpoint for streaming simulation events to the UI."""
    await broadcaster.connect(ws)
    try:
        # Send current state immediately so the frontend renders on connect
        agent = ws.app.state.sim_agent
        obs = agent.get_observation()
        await ws.send_text(json.dumps({
            "source": "world",
            "type": "event",
            "name": "state",
            "payload": obs,
        }))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        broadcaster.disconnect(ws)
