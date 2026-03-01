# Agent One: System Specification

Multi-agent LLM-powered Mars mission simulation. Three autonomous agents (Rover, Drone, Station) collaborate on a procedurally generated Mars surface, coordinated by a central Coordinator. Each agent runs its own Mistral LLM reasoning loop to observe, decide, and act.

---

## 1. Architecture

```
+--------------------+
|   Base / Control   |   <-- human operator: assigns missions, monitors, optional intervention
+--------------------+
        |
        v
+--------------------+       +--------------------+       +--------------------+
|   rover-mistral    |       |   drone-mistral    |       |      station       |
+--------------------+       +--------------------+       +--------------------+
| LLM Decision Loop  |       | LLM Decision Loop  |       | LLM Decision Loop  |
| Tool Executor      |       | Tool Executor      |       | Charge / Allocate  |
| World Interface    |       | World Interface    |       | Mission Manager    |
+--------------------+       +--------------------+       +--------------------+
```

- **Coordinator**: Spawns agent tasks, injects world state into prompts, routes messages between agents, handles timed events. Agents communicate through the Coordinator, never directly.
- **Agents**: `rover-mistral`, `drone-mistral`, `station`. Each runs an observe, reason (LLM), act, update loop.
- **World Model**: Python dict holding the chunk-based grid, stones, agent positions/battery, and simulation state. Updated by tool call results and external events.
- **Broadcaster**: Singleton for WebSocket fan-out to connected UI clients.

---

## 2. World Model

### 2.1 Chunk-Based Infinite Grid

The world is an infinite 2D grid divided into chunks. Each chunk is `CHUNK_SIZE x CHUNK_SIZE` (16x16) tiles. Chunks generate procedurally with deterministic seeds as agents explore.

- Positions are `(x, y)` integer coordinates (no zone IDs)
- The origin chunk at `(0, 0)` is guaranteed to contain at least one basalt vein
- World bounds expand dynamically as agents move into unexplored areas
- No predefined map edges; the world grows with exploration

### 2.2 Fog-of-War

Agents reveal tiles within their visibility radius:

| Agent | Reveal Radius |
|-------|---------------|
| Rover | 3 tiles       |
| Drone | 6 tiles       |

Unexplored tiles remain hidden until an agent moves close enough. Previously revealed tiles stay visible.

### 2.3 Stones and Veins

Stones are basalt veins embedded in the terrain. Each vein has a grade that determines its value:

| Grade    | Rarity       |
|----------|--------------|
| low      | Common       |
| medium   | Uncommon     |
| high     | Rare         |
| rich     | Very rare    |
| pristine | Extremely rare |

Rarity follows an exponential distribution. Veins start with `"unknown"` type and grade until analyzed by the rover.

### 2.4 World State Structure

```json
{
  "tick": 42,
  "agents": {
    "rover-mistral": { "position": [3, 5], "battery": 0.78, "inventory": [] },
    "drone-mistral": { "position": [8, -2], "battery": 0.65 },
    "station":       { "position": [0, 0] }
  },
  "revealed_tiles": { "(3,5)": { "terrain": "sand", "vein": null }, "..." : "..." },
  "stones": [
    { "position": [4, 6], "type": "unknown", "grade": "unknown" }
  ]
}
```

---

## 3. Agents and Tools

### 3.1 Rover (`rover-mistral`)

Primary ground agent. Moves across the surface, digs veins, analyzes samples, manages solar panels.

| Tool                  | Description                                    | Cost        |
|-----------------------|------------------------------------------------|-------------|
| `move`                | Move in direction (north/south/east/west), optional distance (max 3) | 1 fuel/tile |
| `dig`                 | Extract vein at current position               | 6 fuel      |
| `analyze`             | Reveal true grade/type of vein at position     | 3 fuel      |
| `deploy_solar_panel`  | Deploy emergency solar panel at position       | -           |
| `use_solar_battery`   | Consume deployed solar panel for battery       | -           |
| `notify`              | Send message to other agents via coordinator   | -           |

- Fuel capacity: 350 units
- Battery stored as 0.0 to 1.0 fraction
- Inventory: max 3 veins carried at once
- Solar panels: 0.25 capacity each, max 2 deployed

### 3.2 Drone (`drone-mistral`)

Aerial scout. Covers large areas quickly with wider visibility.

| Tool     | Description                                | Cost        |
|----------|--------------------------------------------|-------------|
| `move`   | Move in direction + distance (max 6 tiles) | 1 fuel/tile |
| `scan`   | Area scan around drone position (radius 6) | 2 fuel      |
| `notify` | Send message to other agents               | -           |

- Fuel capacity: 250 units

### 3.3 Station (`station`)

Fixed at position `(0, 0)`. Manages power, charges agents, assigns missions.

| Action         | Description                              |
|----------------|------------------------------------------|
| `charge_rover` | Charge rover battery (+20% per cycle)    |
| `charge_drone` | Charge drone battery (+20% per cycle)    |
| Mission assign | Assign missions to agents                |
| Mission abort  | Cancel active missions                   |
| Power alerts   | Broadcast power allocation warnings      |

---

## 4. Mission System

### 4.1 Primary Mission

Collect 100 units of basalt and deliver to station at `(0, 0)`.

### 4.2 Mission Flow

1. Station assigns mission to rover
2. Drone scouts terrain, revealing veins through scan
3. Rover moves to veins, analyzes them, digs high-grade samples
4. Rover carries samples back to station (max 3 per trip)
5. Repeat until 100 units collected

### 4.3 Probabilistic Goal Structure

```json
{
  "goal_id": "G-01",
  "description": "Collect basalt samples",
  "confidence": 0.0,
  "threshold": 0.9
}
```

`confidence` updates dynamically as the rover collects and delivers samples. Goal is satisfied when `confidence >= threshold`.

---

## 5. Agent Loop

Each tick, every agent runs this cycle:

### 5.1 Observe

Read world state slice: position, battery level, nearby revealed tiles, visible stones, other agent positions.

### 5.2 Reason (LLM)

Mistral API call with the agent's system prompt, current observations, and available tools. The LLM evaluates state and proposes an action via tool call.

Example prompt context:

```
You are rover-mistral. Position: (3, 5). Battery: 0.72.
Nearby tiles: sand at (3,6), basalt vein (unknown grade) at (4,5).
Inventory: 1/3 slots used.
Mission: collect 100 basalt units, 34 delivered so far.
```

### 5.3 Execute

Tool call result mutates world state. Move updates position. Dig adds vein to inventory. Analyze reveals grade.

### 5.4 Record

Memory updated. Events broadcast to all connected WebSocket clients via the Broadcaster singleton.

---

## 6. Event System

### 6.1 Event Categories

| Category    | Examples                               |
|-------------|----------------------------------------|
| Agent       | BatteryLow, VeinDiscovered, DigSuccess |
| Mission     | MissionAssigned, DeliveryComplete       |
| World       | ChunkGenerated, BoundsExpanded          |
| Human       | ManualIntervention                      |

### 6.2 Agent-to-Agent Communication

Agents use `notify` to send messages through the Coordinator. Typical patterns:

- Drone notifies rover of discovered veins
- Station alerts agents about low power
- Rover reports delivery completion

The Coordinator routes all messages. Agents never call each other directly.

---

## 7. Message Protocol

```json
{
  "id": "uuid",
  "ts": 1738472912,
  "source": "rover|drone|station|base|human|world",
  "type": "event|action|command|tool|stream",
  "name": "EventOrActionName",
  "payload": {},
  "correlation_id": "optional"
}
```

- Coordinator routes messages declaratively
- Agents subscribe to relevant events only
- All messages broadcast to UI via WebSocket

---

## 8. AI Narration

Mistral LLM generates narrative commentary on simulation events in real time. The narration engine watches the event stream and produces human-readable descriptions of agent actions, discoveries, and mission progress.

- Text narration generated by Mistral API
- Optional voice narration via ElevenLabs TTS
- Streaming delivery via WebSocket `narration_chunk` events
- Configurable minimum interval between narrations

---

## 9. Demo Timeline (5-Minute)

| Time | Event                                                    | Agents          |
|------|----------------------------------------------------------|-----------------|
| 0:00 | Mission assigned: collect 100 basalt units               | Station -> All  |
| 0:15 | Drone takes off, scans area around origin                | drone-mistral   |
| 0:30 | Drone discovers veins at (4, 5) and (6, 3)              | drone-mistral   |
| 0:45 | Rover moves toward nearest vein, analyzes it             | rover-mistral   |
| 1:00 | Rover digs high-grade basalt, adds to inventory          | rover-mistral   |
| 1:30 | Drone expands search radius, finds more veins            | drone-mistral   |
| 2:00 | Rover battery drops below 30%, heads back to station     | rover-mistral   |
| 2:30 | Station charges rover, rover delivers samples            | station, rover  |
| 3:00 | Rover deploys solar panel as backup power                | rover-mistral   |
| 3:30 | Second exploration run, drone guides rover to rich veins | Both            |
| 4:00 | Narration describes mission progress                     | Narration       |
| 4:30 | Rover completes final delivery                           | rover-mistral   |
| 5:00 | Mission target reached, confidence threshold met         | All             |

---

## 10. Emergent Simulation Characteristics

- LLM-driven decision making produces non-deterministic, adaptive behavior
- Agents respond to changing conditions: battery constraints force return trips, new vein discoveries redirect exploration paths
- Drone-rover cooperation emerges naturally from shared world state and notify messages
- Fog-of-war creates genuine exploration, not just pathfinding on a known map
- Procedural generation means every simulation run produces a different terrain layout
- Solar panel deployment adds resource management tension
- Streaming LLM reasoning and narration makes the simulation watchable and engaging
