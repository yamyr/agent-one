"""Typed Pydantic contexts for agent protocol — replaces flat context dicts."""

from pydantic import BaseModel


class AgentMission(BaseModel):
    objective: str
    plan: list[str] = []


class InventoryItem(BaseModel):
    type: str
    grade: str = "unknown"
    quantity: int = 0


class StoneInfo(BaseModel):
    position: list[int]
    type: str
    grade: str = "unknown"
    quantity: int = 0
    analyzed: bool = False


class StructureInfo(BaseModel):
    type: str
    category: str
    position: list[int]
    explored: bool = False
    active: bool = False
    description: str = ""


# ── Rover Context (3 clear sections) ──


class RoverAgentState(BaseModel):
    """Rover's own internal state."""

    position: list[int]
    battery: float
    mission: AgentMission
    inventory: list[InventoryItem] = []
    memory: list[str] = []
    tasks: list[str] = []
    visited: list[list[int]] = []
    visited_count: int = 0


class RoverWorldView(BaseModel):
    """World info visible to the rover (not agent state)."""

    grid_w: int
    grid_h: int
    station_position: list[int]
    target_type: str = "basalt_vein"
    target_quantity: int = 100
    collected_quantity: int = 0


class PendingCommand(BaseModel):
    """A command queued for an agent by the Host (e.g. recall, assign_mission)."""

    name: str
    payload: dict = {}
    id: str = ""


class RoverComputed(BaseModel):
    """Derived fields for decision-making."""

    unvisited_dirs: list[str] = []
    stone_line: str = "none"
    stone_here: StoneInfo | None = None
    visible_stones: list[str] = []
    pending_commands: list[PendingCommand] = []
    visible_structures: list[str] = []


class RoverContext(BaseModel):
    agent: RoverAgentState
    world: RoverWorldView
    computed: RoverComputed


# ── Station Context ──


class RoverSummary(BaseModel):
    id: str
    position: list[int]
    battery: float
    mission: AgentMission
    visited_count: int = 0


class StationContext(BaseModel):
    grid_w: int
    grid_h: int
    rovers: list[RoverSummary]
    stones: list[StoneInfo]
