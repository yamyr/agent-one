"""Typed Pydantic contexts for agent protocol — replaces flat context dicts."""

from enum import Enum

from pydantic import BaseModel


# ── Resource & Agent Type Enums ──


class ResourceType(str, Enum):
    """All collectible resource types in the simulation."""

    basalt_vein = "basalt_vein"
    ice = "ice"
    water = "water"
    gas = "gas"


class AgentType(str, Enum):
    """Agent role types in the simulation."""

    rover = "rover"
    drone = "drone"
    station = "station"
    hauler = "hauler"


# ── Core Models ──


class AgentMission(BaseModel):
    objective: str
    plan: list[str] = []


class InventoryItem(BaseModel):
    type: str
    grade: str = "unknown"
    quantity: int = 0
    refined: bool = False


class GroundItem(BaseModel):
    type: str
    quantity: int = 0
    position: list[int]
    dropped_by: str
    tick: int


class StoneInfo(BaseModel):
    position: list[int]
    type: str
    grade: str = "unknown"
    quantity: int = 0
    analyzed: bool = False


class IceDepositInfo(BaseModel):
    position: list[int]
    quantity: int = 0


class StructureInfo(BaseModel):
    type: str
    category: str
    position: list[int]
    explored: bool = False
    active: bool = False
    upgrade_level: int = 1
    description: str = ""


class ObstacleInfo(BaseModel):
    """An environmental obstacle visible to the agent."""

    position: list[int]
    kind: str  # "mountain" or "geyser"
    state: str = "idle"  # mountains: always "idle"; geysers: "idle" | "warning" | "erupting"


class PendingCommand(BaseModel):
    """A command queued for an agent by the Host (e.g. recall, assign_mission)."""

    name: str
    payload: dict = {}
    id: str = ""


# ── Resource System Models ──


class IceDeposit(BaseModel):
    """An ice deposit available for gathering in the world."""

    position: list[int]
    quantity: int = 1
    gathered: bool = False


class GasPlantInfo(BaseModel):
    position: list[int]
    gas_stored: int = 0
    max_gas: int = 100
    built_by: str = ""


class StationUpgrades(BaseModel):
    """Upgrades applied to the station/base by delivering resources."""

    charge_bonus: float = 0.0  # added to base CHARGE_RATE
    upgrade_count: int = 0


class UpgradeInfo(BaseModel):
    """Info about a single available base upgrade."""

    name: str
    level: int = 0
    max_level: int = 1
    cost_water: int = 0
    cost_gas: int = 0
    description: str = ""


class ResourceStorage(BaseModel):
    """Global resource storage at the station."""

    water: int = 0
    gas: int = 0
    basalt_delivered: int = 0


class StationResources(BaseModel):
    water: int = 0
    gas: int = 0
    parts: list[str] = []


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
    station_water: int = 0
    station_gas: int = 0
    water_collected: int = 0
    gas_collected: int = 0


class RoverComputed(BaseModel):
    """Derived fields for decision-making."""

    unvisited_dirs: list[str] = []
    stone_line: str = "none"
    stone_here: StoneInfo | None = None
    visible_stones: list[str] = []
    visible_ice_deposits: list[str] = []
    pending_commands: list[PendingCommand] = []
    visible_structures: list[str] = []
    nearby_obstacles: list[ObstacleInfo] = []


class RoverContext(BaseModel):
    agent: RoverAgentState
    world: RoverWorldView
    computed: RoverComputed


# ── Station Context ──


class RoverSummary(BaseModel):
    id: str
    agent_type: str = "rover"
    position: list[int]
    battery: float
    mission: AgentMission
    visited_count: int = 0


class StationContext(BaseModel):
    grid_w: int
    grid_h: int
    rovers: list[RoverSummary]
    stones: list[StoneInfo]
    memory: list[str] = []
    tick: int = 0
    mission_status: str = "in_progress"
    collected_quantity: int = 0
    target_quantity: int = 100
    water_collected: int = 0
    gas_collected: int = 0
    station_resources: StationResources | None = None


# ── Hauler Context ──


class HaulerAgentState(BaseModel):
    """Hauler's own internal state."""

    position: list[int]
    battery: float
    mission: AgentMission
    inventory: list[InventoryItem] = []
    memory: list[str] = []
    tasks: list[str] = []
    visited: list[list[int]] = []
    visited_count: int = 0


class HaulerWorldView(BaseModel):
    """World info visible to the hauler."""

    grid_w: int
    grid_h: int
    station_position: list[int]
    target_type: str = "basalt_vein"
    target_quantity: int = 100
    collected_quantity: int = 0


class HaulerComputed(BaseModel):
    """Derived fields for hauler decision-making."""

    distance_to_station: int = 0
    station_direction: str = "here"
    inventory_capacity: int = 6
    visible_ground_items: list[GroundItem] = []


class HaulerContext(BaseModel):
    agent: HaulerAgentState
    world: HaulerWorldView
    computed: HaulerComputed
