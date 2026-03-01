"""Pydantic models for training data logging — structured records for agent replay and fine-tuning."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Session ──


class SessionConfig(BaseModel):
    """Simulation configuration captured at session start."""

    world_seed: str = ""
    active_agents: list[str] = []
    llm_turn_interval: float = 3.0
    target_quantity: int = 300
    grid_w: int = 20
    grid_h: int = 20
    fuel_capacity_rover: int = 350
    fuel_capacity_drone: int = 250


class SessionResult(BaseModel):
    """Final outcome of a simulation session."""

    total_ticks: int = 0
    basalt_collected: int = 0
    basalt_delivered: int = 0
    duration_seconds: float = 0.0


class TrainingSession(BaseModel):
    """One simulation run — top-level record linking all training data."""

    started_at: datetime = Field(default_factory=_utcnow)
    ended_at: datetime | None = None
    status: str = "running"  # running | success | failed | aborted
    config: SessionConfig = Field(default_factory=SessionConfig)
    result: SessionResult | None = None
    tags: list[str] = []


# ── Turn (core training row) ──


class TurnWorldSnapshot(BaseModel):
    """Structured world state visible to the agent at decision time."""

    agent_position: list[int] = [0, 0]
    agent_battery: float = 1.0
    agent_inventory: list[dict[str, Any]] = []
    agent_memory: list[str] = []
    agent_tasks: list[str] = []
    visible_stones: list[str] = []
    mission_status: str = "running"
    collected_quantity: int = 0
    target_quantity: int = 300
    distance_to_station: int = 0


class TrainingTurn(BaseModel):
    """One agent decision cycle — the core training record.

    Maps context (input) → action (output) → result (outcome).
    """

    session_id: str = ""
    tick: int = 0
    agent_id: str = ""
    agent_type: str = ""  # rover | drone | station
    timestamp: datetime = Field(default_factory=_utcnow)

    # INPUT: what the agent saw
    context: str = ""  # full LLM prompt text
    world_snapshot: TurnWorldSnapshot = Field(default_factory=TurnWorldSnapshot)

    # OUTPUT: what the agent decided
    thinking: str | None = None
    action_name: str = ""
    action_params: dict[str, Any] = {}

    # OUTCOME: what happened
    action_result: dict[str, Any] = {}
    action_ok: bool = False
    battery_before: float = 1.0
    battery_after: float = 1.0
    position_before: list[int] = [0, 0]
    position_after: list[int] = [0, 0]

    # META
    model: str = ""
    is_fallback: bool = False
    llm_duration_ms: int | None = None


# ── Event ──


class TrainingEvent(BaseModel):
    """Significant world or mission event for session replay."""

    session_id: str = ""
    tick: int = 0
    timestamp: datetime = Field(default_factory=_utcnow)
    source: str = ""
    event_type: str = ""  # thinking | action | command | mission_success | charge | etc.
    event_name: str = ""
    payload: dict[str, Any] = {}


# ── World Snapshot ──


class TrainingWorldSnapshot(BaseModel):
    """Periodic full world state capture for session replay."""

    session_id: str = ""
    tick: int = 0
    timestamp: datetime = Field(default_factory=_utcnow)
    world_state: dict[str, Any] = {}
