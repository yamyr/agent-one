"""Core deterministic simulation engine for Station + Rover world."""
from __future__ import annotations

from typing import Literal

from . import errors
from .models import (
    Action,
    Observation,
    SimEvent,
    StepResult,
    Stone,
    WorldState,
    clone_world,
    world_to_dict,
)
from .world_factory import in_bounds, reveal_within_radius

MOVE_COST = 1
DIG_COST = 3
PICKUP_COST = 1


class SimulationEngine:
    """Applies validated actions and advances world state in deterministic ticks."""

    def __init__(self, world: WorldState, step_limit: int = 400):
        self._world = clone_world(world)
        self._step_limit = step_limit

    def get_world_state(self) -> WorldState:
        return clone_world(self._world)

    def get_world_state_dict(self) -> dict[str, object]:
        return world_to_dict(self._world)

    def is_terminal(self) -> bool:
        return self._world.status in ("success", "failed")

    def get_observation(self, observer: Literal["rover", "station"]) -> Observation:
        if observer not in ("rover", "station"):
            raise ValueError(f"Unknown observer: {observer}")

        rover = self._world.rover
        station = self._world.station

        known_cells = []
        for x, y in sorted(rover.revealed_cells):
            cell = self._world.grid.cells[y][x]
            stone_payload: dict[str, object] | None = None
            if cell.stone is not None:
                stone_payload = {
                    "kind": cell.stone.kind,
                    "extracted": cell.stone.extracted,
                }
            known_cells.append(
                {
                    "coord": [x, y],
                    "terrain": cell.terrain,
                    "dug": cell.dug,
                    "stone": stone_payload,
                }
            )

        return Observation(
            observer=observer,
            tick=self._world.tick,
            status=self._world.status,
            mission={
                "target_kind": self._world.mission.target_kind,
                "target_count": self._world.mission.target_count,
                "collected_count": self._world.mission.collected_count,
            },
            rover={
                "id": rover.id,
                "position": [rover.position[0], rover.position[1]],
                "battery": rover.battery,
                "battery_max": rover.battery_max,
                "battery_pct": rover.battery / rover.battery_max,
                "distance_to_station": self._distance_to_station(),
                "inventory_count": len(rover.inventory),
            },
            station={
                "id": station.id,
                "position": [station.position[0], station.position[1]],
                "charge_rate": station.charge_rate,
            },
            known_cells=known_cells,
        )

    def get_legal_actions(self) -> list[Action]:
        if self.is_terminal():
            return []

        rover = self._world.rover
        legal: list[Action] = [{"kind": "wait"}]

        x, y = rover.position
        if rover.battery >= MOVE_COST:
            candidates = ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
            for nx, ny in candidates:
                if in_bounds((nx, ny), self._world.grid):
                    legal.append({"kind": "move", "to": (nx, ny)})

        cell = self._world.grid.cells[y][x]
        if rover.battery >= DIG_COST and not cell.dug:
            legal.append({"kind": "dig"})
        if (
            rover.battery >= PICKUP_COST
            and cell.stone is not None
            and cell.stone.extracted
        ):
            legal.append({"kind": "pickup"})
        if rover.position == self._world.station.position and rover.battery < rover.battery_max:
            legal.append({"kind": "charge"})

        return legal

    def step(self, action: dict[str, object]) -> StepResult:
        normalized, error_event = self._normalize_action(action)
        if error_event is not None:
            return StepResult(
                tick=self._world.tick,
                accepted=False,
                action=action,
                events=[error_event],
                state_delta={},
                terminal_status=self._terminal_status(),
            )

        assert normalized is not None

        if self.is_terminal():
            return StepResult(
                tick=self._world.tick,
                accepted=False,
                action=normalized,
                events=[SimEvent(name=errors.TERMINAL_WORLD)],
                state_delta={},
                terminal_status=self._terminal_status(),
            )

        accepted, events = self._apply_action(normalized)
        if not accepted:
            return StepResult(
                tick=self._world.tick,
                accepted=False,
                action=normalized,
                events=events,
                state_delta={},
                terminal_status=self._terminal_status(),
            )

        if self._world.status == "idle":
            self._world.status = "running"

        self._world.tick += 1
        self._update_mission_collected_count()
        self._apply_terminal_rules(events)

        state_delta = {
            "tick": self._world.tick,
            "status": self._world.status,
            "mission": {"collected_count": self._world.mission.collected_count},
            "rover": {
                "position": [self._world.rover.position[0], self._world.rover.position[1]],
                "battery": self._world.rover.battery,
                "battery_pct": self._world.rover.battery / self._world.rover.battery_max,
                "distance_to_station": self._distance_to_station(),
                "inventory_count": len(self._world.rover.inventory),
            },
        }
        return StepResult(
            tick=self._world.tick,
            accepted=True,
            action=normalized,
            events=events,
            state_delta=state_delta,
            terminal_status=self._terminal_status(),
        )

    def _terminal_status(self) -> Literal["running", "success", "failed"]:
        if self._world.status == "success":
            return "success"
        if self._world.status == "failed":
            return "failed"
        return "running"

    def _normalize_action(
        self,
        action: dict[str, object],
    ) -> tuple[Action | None, SimEvent | None]:
        kind = action.get("kind")
        if kind not in ("move", "dig", "pickup", "charge", "wait"):
            return None, SimEvent(
                name=errors.INVALID_PRECONDITION,
                payload={"reason": "unknown_kind"},
            )

        if kind == "move":
            coord = action.get("to")
            if not isinstance(coord, (list, tuple)) or len(coord) != 2:
                return None, SimEvent(
                    name=errors.INVALID_PRECONDITION,
                    payload={"reason": "move_requires_to"},
                )
            x, y = coord
            if not isinstance(x, int) or not isinstance(y, int):
                return None, SimEvent(
                    name=errors.INVALID_PRECONDITION,
                    payload={"reason": "move_to_must_be_int"},
                )
            return {"kind": "move", "to": (x, y)}, None

        return {"kind": kind}, None

    def _apply_action(self, action: Action) -> tuple[bool, list[SimEvent]]:
        rover = self._world.rover
        x, y = rover.position
        cell = self._world.grid.cells[y][x]

        kind = action["kind"]
        events: list[SimEvent] = [SimEvent(name="action_executed", payload={"kind": kind})]

        if kind == "wait":
            return True, events

        if kind == "move":
            if rover.battery < MOVE_COST:
                return False, [SimEvent(name=errors.INVALID_NO_ENERGY)]
            target = action["to"]
            if not in_bounds(target, self._world.grid):
                return False, [SimEvent(name=errors.INVALID_OUT_OF_BOUNDS)]
            if self._manhattan(rover.position, target) != 1:
                return False, [SimEvent(name=errors.INVALID_NON_ADJACENT_MOVE)]

            rover.position = target
            rover.battery -= MOVE_COST
            reveal_within_radius(rover, self._world.grid, radius=2)
            events.append(
                SimEvent(
                    name="rover_moved",
                    payload={
                        "to": [target[0], target[1]],
                        "battery": rover.battery,
                    },
                )
            )
            return True, events

        if kind == "dig":
            if rover.battery < DIG_COST:
                return False, [SimEvent(name=errors.INVALID_NO_ENERGY)]
            if cell.dug:
                return False, [
                    SimEvent(
                        name=errors.INVALID_PRECONDITION,
                        payload={"reason": "already_dug"},
                    )
                ]

            rover.battery -= DIG_COST
            cell.dug = True
            rover.dug_cells.add(rover.position)
            events.append(
                SimEvent(
                    name="cell_dug",
                    payload={"at": [x, y], "battery": rover.battery},
                )
            )
            if cell.stone is not None and not cell.stone.extracted:
                cell.stone.extracted = True
                events.append(
                    SimEvent(
                        name="stone_extracted",
                        payload={"at": [x, y], "kind": cell.stone.kind},
                    )
                )
            return True, events

        if kind == "pickup":
            if rover.battery < PICKUP_COST:
                return False, [SimEvent(name=errors.INVALID_NO_ENERGY)]
            if cell.stone is None or not cell.stone.extracted:
                return False, [
                    SimEvent(
                        name=errors.INVALID_PRECONDITION,
                        payload={"reason": "no_extracted_stone"},
                    )
                ]

            rover.battery -= PICKUP_COST
            rover.inventory.append(Stone(kind=cell.stone.kind, extracted=True))
            picked_kind = cell.stone.kind
            cell.stone = None
            events.append(
                SimEvent(
                    name="stone_picked",
                    payload={
                        "at": [x, y],
                        "kind": picked_kind,
                        "inventory_count": len(rover.inventory),
                        "battery": rover.battery,
                    },
                )
            )
            return True, events

        if kind == "charge":
            if rover.position != self._world.station.position:
                return False, [
                    SimEvent(
                        name=errors.INVALID_PRECONDITION,
                        payload={"reason": "not_at_station"},
                    )
                ]
            if rover.battery >= rover.battery_max:
                return False, [
                    SimEvent(
                        name=errors.INVALID_PRECONDITION,
                        payload={"reason": "battery_full"},
                    )
                ]

            rover.battery = min(
                rover.battery_max,
                rover.battery + self._world.station.charge_rate,
            )
            events.append(SimEvent(name="battery_charged", payload={"battery": rover.battery}))
            return True, events

        return False, [
            SimEvent(
                name=errors.INVALID_PRECONDITION,
                payload={"reason": "unknown_kind"},
            )
        ]

    def _update_mission_collected_count(self) -> None:
        target_kind = self._world.mission.target_kind
        self._world.mission.collected_count = sum(
            1 for stone in self._world.rover.inventory if stone.kind == target_kind
        )

    def _apply_terminal_rules(self, events: list[SimEvent]) -> None:
        rover = self._world.rover
        mission = self._world.mission

        if mission.collected_count >= mission.target_count:
            self._world.status = "success"
            events.append(SimEvent(name="mission_success", payload={"tick": self._world.tick}))
            return

        if rover.battery == 0 and rover.position != self._world.station.position:
            self._world.status = "failed"
            events.append(
                SimEvent(name="mission_failed", payload={"reason": "battery_depleted"})
            )
            return

        if self._world.tick >= self._step_limit:
            self._world.status = "failed"
            events.append(SimEvent(name="mission_failed", payload={"reason": "timeout"}))
            return

        if self._world.status not in ("success", "failed"):
            self._world.status = "running"

    def _distance_to_station(self) -> int:
        return self._manhattan(self._world.rover.position, self._world.station.position)

    @staticmethod
    def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
