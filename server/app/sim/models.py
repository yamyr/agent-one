"""Simulation domain models for the Station + Rover world engine."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Literal, TypedDict

Coord = tuple[int, int]
StoneKind = Literal["precious", "common"]
WorldStatus = Literal["idle", "running", "success", "failed"]


@dataclass(slots=True)
class Stone:
    kind: StoneKind
    extracted: bool = False


@dataclass(slots=True)
class Cell:
    terrain: str = "plain"
    dug: bool = False
    stone: Stone | None = None


@dataclass(slots=True)
class GridState:
    width: int
    height: int
    cells: list[list[Cell]]


@dataclass(slots=True)
class MissionState:
    target_kind: StoneKind = "precious"
    target_count: int = 2
    collected_count: int = 0


@dataclass(slots=True)
class StationState:
    id: str = "station-1"
    position: Coord = (0, 0)
    charge_rate: int = 10


@dataclass(slots=True)
class RoverState:
    id: str = "rover-1"
    position: Coord = (0, 0)
    battery: int = 100
    battery_max: int = 100
    inventory: list[Stone] = field(default_factory=list)
    revealed_cells: set[Coord] = field(default_factory=set)
    dug_cells: set[Coord] = field(default_factory=set)


@dataclass(slots=True)
class WorldState:
    tick: int
    status: WorldStatus
    mission: MissionState
    grid: GridState
    station: StationState
    rover: RoverState


class MoveAction(TypedDict):
    kind: Literal["move"]
    to: tuple[int, int]


class DigAction(TypedDict):
    kind: Literal["dig"]


class PickupAction(TypedDict):
    kind: Literal["pickup"]


class ChargeAction(TypedDict):
    kind: Literal["charge"]


class WaitAction(TypedDict):
    kind: Literal["wait"]


Action = MoveAction | DigAction | PickupAction | ChargeAction | WaitAction


@dataclass(slots=True)
class SimEvent:
    name: str
    payload: dict[str, object] = field(default_factory=dict)


TerminalStatus = Literal["running", "success", "failed"]


@dataclass(slots=True)
class StepResult:
    tick: int
    accepted: bool
    action: dict[str, object]
    events: list[SimEvent]
    state_delta: dict[str, object]
    terminal_status: TerminalStatus


@dataclass(slots=True)
class Observation:
    observer: Literal["rover", "station"]
    tick: int
    status: WorldStatus
    mission: dict[str, object]
    rover: dict[str, object]
    station: dict[str, object]
    known_cells: list[dict[str, object]]


# Serialization helpers for stable snapshots in tests and integrations.
def stone_to_dict(stone: Stone) -> dict[str, object]:
    return {"kind": stone.kind, "extracted": stone.extracted}


def cell_to_dict(cell: Cell) -> dict[str, object]:
    payload: dict[str, object] = {"terrain": cell.terrain, "dug": cell.dug}
    if cell.stone is None:
        payload["stone"] = None
    else:
        payload["stone"] = stone_to_dict(cell.stone)
    return payload


def world_to_dict(world: WorldState) -> dict[str, object]:
    return {
        "tick": world.tick,
        "status": world.status,
        "mission": {
            "target_kind": world.mission.target_kind,
            "target_count": world.mission.target_count,
            "collected_count": world.mission.collected_count,
        },
        "grid": {
            "width": world.grid.width,
            "height": world.grid.height,
            "cells": [[cell_to_dict(cell) for cell in row] for row in world.grid.cells],
        },
        "station": {
            "id": world.station.id,
            "position": [world.station.position[0], world.station.position[1]],
            "charge_rate": world.station.charge_rate,
        },
        "rover": {
            "id": world.rover.id,
            "position": [world.rover.position[0], world.rover.position[1]],
            "battery": world.rover.battery,
            "battery_max": world.rover.battery_max,
            "inventory": [stone_to_dict(stone) for stone in world.rover.inventory],
            "revealed_cells": [[x, y] for x, y in sorted(world.rover.revealed_cells)],
            "dug_cells": [[x, y] for x, y in sorted(world.rover.dug_cells)],
        },
    }


def clone_world(world: WorldState) -> WorldState:
    """Return a deep copy of world state."""
    return deepcopy(world)
