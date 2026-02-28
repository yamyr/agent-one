"""World creation utilities for deterministic simulation initialization."""
from __future__ import annotations

import random

from .models import (
    Cell,
    Coord,
    GridState,
    MissionState,
    RoverState,
    StationState,
    Stone,
    WorldState,
)


class WorldFactory:
    """Creates seeded world states with guaranteed mission feasibility."""

    def __init__(
        self,
        width: int = 12,
        height: int = 12,
        target_count: int = 2,
        common_stones: int = 10,
    ):
        self.width = width
        self.height = height
        self.target_count = target_count
        self.common_stones = common_stones

    def create(self, seed: int | None = None) -> WorldState:
        rng = random.Random(seed)

        grid = GridState(
            width=self.width,
            height=self.height,
            cells=[[Cell() for _ in range(self.width)] for _ in range(self.height)],
        )

        station = StationState(position=(0, 0))
        rover = RoverState(position=station.position)

        available = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if (x, y) != station.position
        ]
        rng.shuffle(available)

        precious_positions = available[: self.target_count]
        common_end = self.target_count + min(
            self.common_stones,
            len(available) - self.target_count,
        )
        common_positions = available[self.target_count:common_end]

        for x, y in precious_positions:
            grid.cells[y][x].stone = Stone(kind="precious")

        for x, y in common_positions:
            if grid.cells[y][x].stone is None:
                grid.cells[y][x].stone = Stone(kind="common")

        reveal_within_radius(rover, grid, radius=2)

        mission = MissionState(
            target_kind="precious",
            target_count=self.target_count,
            collected_count=0,
        )
        return WorldState(
            tick=0,
            status="idle",
            mission=mission,
            grid=grid,
            station=station,
            rover=rover,
        )


def reveal_within_radius(rover: RoverState, grid: GridState, radius: int) -> None:
    x0, y0 = rover.position
    for y in range(grid.height):
        for x in range(grid.width):
            if abs(x - x0) + abs(y - y0) <= radius:
                rover.revealed_cells.add((x, y))


def in_bounds(coord: Coord, grid: GridState) -> bool:
    x, y = coord
    return 0 <= x < grid.width and 0 <= y < grid.height
