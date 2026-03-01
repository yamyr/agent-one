"""Mars dust storm system — periodic storms that affect rover operations.

Storms follow a lifecycle: scheduled -> warning -> active -> ended.
During active storms, rovers experience increased battery drain and
probabilistic move failures. Drones are unaffected by move failures.

All functions take the world dict as a parameter to stay decoupled
from the global WORLD singleton.
"""

import logging
import random

logger = logging.getLogger(__name__)

# -- Storm constants --

STORM_MIN_INTERVAL = 30
STORM_MAX_INTERVAL = 80
STORM_WARNING_TICKS = 5
STORM_MIN_DURATION = 10
STORM_MAX_DURATION = 30
STORM_MAX_BATTERY_MULT = 2.5
STORM_MAX_MOVE_FAIL = 0.15
STORM_VISIBILITY_REDUCTION = 0.4


def make_storm_state():
    """Return a fresh storm state dict for embedding in the world."""
    return {
        "phase": "clear",
        "next_storm_tick": 0,
        "active_start": 0,
        "active_end": 0,
        "intensity": 0.0,
        "warning_start": 0,
    }


def schedule_next_storm(world):
    """Pick a random future tick for the next storm warning."""
    tick = world["tick"]
    delay = random.randint(STORM_MIN_INTERVAL, STORM_MAX_INTERVAL)
    storm = world.setdefault("storm", make_storm_state())
    storm["next_storm_tick"] = tick + delay
    storm["phase"] = "clear"
    storm["intensity"] = 0.0
    logger.info("Next storm scheduled at tick %d (current %d)", tick + delay, tick)


def check_storm_tick(world):
    """Advance storm lifecycle. Returns a list of storm events to broadcast."""
    storm = world.get("storm")
    if storm is None:
        storm = make_storm_state()
        world["storm"] = storm
        schedule_next_storm(world)
        return []

    tick = world["tick"]
    events = []

    if storm["phase"] == "clear":
        if tick >= storm["next_storm_tick"]:
            storm["phase"] = "warning"
            storm["warning_start"] = tick
            duration = random.randint(STORM_MIN_DURATION, STORM_MAX_DURATION)
            storm["active_start"] = tick + STORM_WARNING_TICKS
            storm["active_end"] = tick + STORM_WARNING_TICKS + duration
            storm["intensity"] = 0.0
            events.append(
                {
                    "name": "storm_warning",
                    "payload": {
                        "message": "Dust storm approaching! ETA %d ticks." % STORM_WARNING_TICKS,
                        "active_start": storm["active_start"],
                        "active_end": storm["active_end"],
                    },
                }
            )
            logger.info(
                "Storm warning at tick %d, active %d-%d",
                tick,
                storm["active_start"],
                storm["active_end"],
            )

    elif storm["phase"] == "warning":
        if tick >= storm["active_start"]:
            storm["phase"] = "active"
            storm["intensity"] = 0.3
            events.append(
                {
                    "name": "storm_started",
                    "payload": {
                        "message": "Dust storm has arrived!",
                        "duration": storm["active_end"] - storm["active_start"],
                        "intensity": storm["intensity"],
                    },
                }
            )
            logger.info("Storm active at tick %d", tick)

    elif storm["phase"] == "active":
        if tick >= storm["active_end"]:
            storm["phase"] = "clear"
            storm["intensity"] = 0.0
            events.append(
                {
                    "name": "storm_ended",
                    "payload": {"message": "Dust storm has passed."},
                }
            )
            schedule_next_storm(world)
            logger.info("Storm ended at tick %d", tick)
        else:
            total = storm["active_end"] - storm["active_start"]
            elapsed = tick - storm["active_start"]
            mid = total / 2
            if elapsed <= mid:
                storm["intensity"] = min(1.0, 0.3 + 0.7 * (elapsed / mid))
            else:
                remaining = total - elapsed
                storm["intensity"] = max(0.1, 0.3 + 0.7 * (remaining / mid))

    return events


def get_battery_multiplier(world):
    """Return battery cost multiplier based on current storm intensity."""
    storm = world.get("storm")
    if storm is None or storm["phase"] != "active":
        return 1.0
    return 1.0 + (STORM_MAX_BATTERY_MULT - 1.0) * storm["intensity"]


def should_move_fail(world):
    """Return True if a rover move should fail due to storm conditions."""
    storm = world.get("storm")
    if storm is None or storm["phase"] != "active":
        return False
    fail_chance = STORM_MAX_MOVE_FAIL * storm["intensity"]
    return random.random() < fail_chance


def get_storm_info(world):
    """Return storm info dict suitable for snapshots and agent context."""
    storm = world.get("storm")
    if storm is None:
        return {"phase": "clear", "intensity": 0.0}
    return {
        "phase": storm["phase"],
        "intensity": round(storm["intensity"], 2),
        "battery_multiplier": round(get_battery_multiplier(world), 2),
        "move_fail_chance": round(
            STORM_MAX_MOVE_FAIL * storm["intensity"] if storm["phase"] == "active" else 0.0,
            3,
        ),
    }
