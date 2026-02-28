"""Dynamic world event engine — injects environmental events into the simulation."""

import random
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class WorldEvent:
    name: str
    description: str
    tick: int
    duration: int
    effects: dict = field(default_factory=dict)
    active: bool = True


class EventEngine:
    """Generates and manages dynamic world events."""

    def __init__(self):
        self.active_events: list[WorldEvent] = []
        self.event_history: list[WorldEvent] = []
        self.next_event_tick: int = 15
        self.event_interval_range: tuple = (10, 25)

    def tick(self, current_tick: int, world: dict) -> list[WorldEvent]:
        """Called every tick. Returns newly triggered events."""
        new_events = []
        for ev in self.active_events:
            if ev.duration > 0 and current_tick >= ev.tick + ev.duration:
                ev.active = False
                self.event_history.append(ev)
        self.active_events = [e for e in self.active_events if e.active]
        if current_tick >= self.next_event_tick:
            event = self._generate_event(current_tick, world)
            if event:
                self.active_events.append(event)
                new_events.append(event)
                logger.info("World event: %s at tick %d", event.name, current_tick)
            self.next_event_tick = current_tick + random.randint(*self.event_interval_range)
        return new_events

    def _generate_event(self, tick: int, world: dict) -> WorldEvent | None:
        event_types = [self._dust_storm, self._solar_flare, self._seismic_reading, self._comm_interference]
        weights = [3, 2, 3, 2]
        generator = random.choices(event_types, weights=weights, k=1)[0]
        return generator(tick, world)

    def _dust_storm(self, tick: int, world: dict) -> WorldEvent:
        return WorldEvent(
            name="dust_storm",
            description="A dust storm has reduced visibility. Rover reveal radius halved.",
            tick=tick, duration=random.randint(5, 12),
            effects={"rover_reveal_modifier": 0.5, "drone_reveal_modifier": 0.7},
        )

    def _solar_flare(self, tick: int, world: dict) -> WorldEvent:
        return WorldEvent(
            name="solar_flare",
            description="Solar flare detected! Solar panels charge faster but movement costs increase.",
            tick=tick, duration=random.randint(4, 8),
            effects={"solar_boost": 1.5, "move_cost_modifier": 1.3},
        )

    def _seismic_reading(self, tick: int, world: dict) -> WorldEvent | None:
        agents = world.get("agents", {})
        rover = agents.get("rover-mistral")
        if not rover:
            return None
        rx, ry = rover["position"]
        dx, dy = random.randint(-8, 8), random.randint(-8, 8)
        vein_pos = [rx + dx, ry + dy]
        return WorldEvent(
            name="seismic_reading",
            description=f"Seismic sensors detected a mineral signature at ({vein_pos[0]}, {vein_pos[1]})!",
            tick=tick, duration=0,
            effects={"reveal_vein": vein_pos, "vein_grade": "high"},
        )

    def _comm_interference(self, tick: int, world: dict) -> WorldEvent:
        return WorldEvent(
            name="comm_interference",
            description="Communication interference detected. Radio transmissions cost more energy.",
            tick=tick, duration=random.randint(3, 7),
            effects={"notify_cost_modifier": 2.0},
        )

    def get_active_effects(self) -> dict:
        merged = {}
        for ev in self.active_events:
            for key, val in ev.effects.items():
                if key in merged and isinstance(val, (int, float)):
                    merged[key] = merged[key] * val
                else:
                    merged[key] = val
        return merged

    def get_active_descriptions(self) -> list[str]:
        return [e.description for e in self.active_events if e.active]

    def get_active_events_data(self) -> list[dict]:
        return [
            {"name": e.name, "description": e.description, "tick": e.tick,
             "duration": e.duration, "effects": e.effects}
            for e in self.active_events if e.active
        ]

    def reset(self):
        self.active_events.clear()
        self.event_history.clear()
        self.next_event_tick = 15


event_engine = EventEngine()
