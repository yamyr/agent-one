Here’s the **updated full spec Markdown** including **probabilistic goals, drone-assisted mapping, and LLM-driven agentic reasoning**:

---

# Autonomous Multi-Agent Mars Mission Simulation (LLM-Powered, Probabilistic Goals)

A sandbox-style multi-robot simulation with **emergent behavior**, partially supervised by a base/control center.
Humans mainly **choose missions and observe**, with optional strategic intervention.

---

## 1. System Architecture

```
+--------------------+
|   Base / Control   |   <-- assigns missions, sets policies, monitors health, optional approvals
+--------------------+
        |
        v
+--------------------+       +--------------------+       +--------------------+
|      Rover(s)      |       |       Drone(s)     |       |  Science Station(s)|
+--------------------+       +--------------------+       +--------------------+
| LLM Decision Loop  |       | LLM Decision Loop  |       | LLM Decision Loop  |
| Goal Evaluator     |       | Goal Evaluator     |       | Goal Evaluator     |
| Task Scheduler     |       | Task Scheduler     |       | Task Scheduler     |
| World Interface    |       | World Interface    |       | World Interface    |
| Action Emitter     |       | Action Emitter     |       | Action Emitter     |
+--------------------+       +--------------------+       +--------------------+
```

* **Base / Control Center:** assigns missions, monitors agent events, optionally approves high-risk tasks
* **Agents:** autonomous, **LLM-powered**, probabilistic reasoning, execute tasks, interact via Actions
* **World:** shared simulation state with terrain, hazards, storm, agent positions, rocks, etc.

---

## 2. World Model

### 2.1 World State Structure

```json
{
  "time": "T+0230",
  "environment": {
    "storm_level": 2,
    "visibility": 0.85,
    "temperature": -35
  },
  "terrain": {
    "hazard_zones": ["Z12","Z14"],
    "rock_positions": ["R-101","R-102","R-103"],
    "rock_types": { "R-101": "core", "R-102": "basalt", "R-103": "core" }
  },
  "agents": {
    "rover-1": {"position": "Z10","battery": 0.78,"mobility": 0.9},
    "drone-1": {"position": "Z08","battery": 0.65},
    "station-1": {"position": "Base","power": 0.85}
  }
}
```

### 2.2 Robot–World Interface

| Robot   | Read                                                | Write / Affect                                  |
| ------- | --------------------------------------------------- | ----------------------------------------------- |
| Rover   | Terrain, hazards, battery, storm, drone scans       | Move, Drill, Carry sample                       |
| Drone   | Terrain, hazard map, storm, rock probabilistic data | Scan, Map safe routes, Relay signals            |
| Station | Storm data, agent telemetry, power levels           | Allocate power, Suggest tasks, Broadcast events |

* External events (storm, terrain shifts) update world asynchronously
* Drone scans provide **probabilistic data**, not the exact rock type

---

## 3. Missions, Goals, Tasks

### 3.1 Mission Example

```json
{
  "mission_id": "M-01",
  "name": "Crater Survey Alpha",
  "status": "ACTIVE",
  "goals": [
    {"goal_id": "G-01","description":"Collect core sample from crater floor"},
    {"goal_id": "G-02","description":"Maintain rover mobility > 60%"},
    {"goal_id": "G-03","description":"Map storm progression"}
  ]
}
```

---

### 3.2 Probabilistic Goal Structure

```json
{
  "goal_id": "G-01",
  "description": "Collect core sample",
  "status": "PENDING",
  "confidence": 0.0,     // probability that goal is satisfied
  "threshold": 0.9        // considered satisfied if confidence >= 0.9
}
```

* `confidence` is updated dynamically as rover samples candidate rocks
* Goal is **partially satisfied** before reaching threshold

---

### 3.3 Tasks

```json
{
  "task_id": "T-01",
  "goal_id": "G-01",
  "type": "DrillSample",
  "state": "PENDING",
  "risk_score": 0.35
}
```

* Tasks map to **tool calls**
* Stream progress (start → update → end)
* Tasks may emit **Actions** to other agents or base

---

## 4. Event System

### 4.1 Event Categories

| Category    | Name            | Description                |
| ----------- | --------------- | -------------------------- |
| Environment | StormIncrease   | Storm level increases      |
| Environment | TerrainShift    | Hazard zones appear        |
| Agent       | BatteryLow      | Battery below threshold    |
| Agent       | MobilityReduced | Rover mobility degraded    |
| Agent       | TaskFailed      | Task failed                |
| Human       | InjectChaos     | Manual disruption injected |

### 4.2 Actions (Agent-to-Agent Communication)

| Action Name               | Trigger                 | Target         |
| ------------------------- | ----------------------- | -------------- |
| MechanicalAnomalyDetected | Rover sensor anomaly    | Drone, Station |
| SafeRouteIdentified       | Drone maps safe path    | Rover          |
| PowerBudgetWarning        | Station low power       | Rover, Drone   |
| TaskCompleted             | Task ends               | Base           |
| EmergencyModeActivated    | Critical goal violation | All            |

Coordinator routes Actions; agents **do not call each other directly**.

---

## 5. LLM-Powered Agent Loop (with Probabilistic Reasoning)

At each tick (or on relevant events):

### 5.1 Observe World

* Read world state slice (terrain, hazards, agent positions, battery/power, storm level)
* Read **probabilistic data** from drone scans

### 5.2 Evaluate Goals (LLM)

* LLM interprets state, evaluates goal health, and proposes **tasks**
* Includes **probabilistic reasoning**: which rock to sample for `Collect core sample` goal

**Example prompt:**

```
You are Rover-1. Current goal: Collect core sample.
Probabilistic map from drone:
- Z12: 70% chance core sample
- Z13: 20% chance core sample
- Z14: 0% chance core sample

Storm in 3 ticks, battery: 0.6
Propose next action, risk assessment, and alternatives.
```

**Example LLM output:**

```json
{
  "proposed_task": "MoveTo(Z12) -> DrillSample(R-101)",
  "expected_confidence_increase": 0.7,
  "risk_score": 0.3,
  "alternative": "MoveTo(Z13) if Z12 blocked"
}
```

---

### 5.3 Select & Execute Task

* Combine LLM recommendation with policy & resource constraints
* Execute via **tool calls**, updating world and goal confidence

**Tool Examples:**

| Task                   | Tool Call                        |
| ---------------------- | -------------------------------- |
| MoveTo(Z12)            | `move_agent("Z12")`              |
| DrillSample(R-101)     | `drill_sample("R-101")`          |
| ScanTerrain(Z12-Z14)   | `scan_area("Z12-Z14")`           |
| AllocatePower(rover-1) | `allocate_power("rover-1", 0.1)` |

* Stream **start → progress → completion**

---

### 5.4 Update Goal Confidence

```python
# Pseudo-code
sampled = world.get_rock_at(rover.position)
prob = drone_scan.get_probability(rover.position)
if sampled.type == "core":
    goal.confidence = min(1.0, goal.confidence + prob)
else:
    goal.confidence = max(0.0, goal.confidence - 0.5)
```

* Goal considered **satisfied** if `confidence >= threshold`

---

### 5.5 Emit Actions

* Notify other agents or base of relevant events:

  * SafeRouteIdentified
  * MechanicalAnomalyDetected
  * TaskCompleted

---

## 6. Base / Control Center

* Assigns missions and policies
* Observes agent events and streaming reasoning
* Approves high-risk tasks if required
* Receives final goal confidence and mission outcome

---

## 7. Human Interaction

* Passive: select missions, set policies
* Optional: inject chaos, approve/cancel high-risk tasks, adjust autonomy mode
* Watch live streaming of LLM reasoning, probabilistic goal updates, and task execution

---

## 8. Demo Timeline (5-Minute)

| Time | Event / Action                                       | Agents / Base                  |
| ---- | ---------------------------------------------------- | ------------------------------ |
| 0:00 | Mission Assigned                                     | Base → All                     |
| 0:15 | Drone scans crater, emits probabilistic map          | Drone → Rover                  |
| 0:20 | Rover LLM proposes MoveTo(Z12) -> DrillSample(R-101) | Rover                          |
| 0:25 | Rover executes MoveTo(Z12), streams progress         | Rover                          |
| 0:45 | StormIncrease(Level2)                                | World → all agents             |
| 1:00 | Rover drills rock, goal confidence updates (0.7)     | Rover                          |
| 1:15 | Rover evaluates alternatives due to storm            | Rover LLM                      |
| 1:30 | Drone identifies safe route if Z12 blocked           | Drone → Rover                  |
| 2:00 | Station reallocates power to rover                   | Station                        |
| 2:30 | Human optionally approves high-risk movement         | Base → Rover                   |
| 3:00 | TerrainShift event                                   | World → all agents             |
| 3:15 | Rover selects alternate rock, executes DrillSample   | Rover                          |
| 4:00 | Drone continues mapping, streams updates             | Drone                          |
| 4:30 | Rover reaches confidence threshold → goal satisfied  | Rover                          |
| 5:00 | Mission complete, final goal confidence reported     | Base & agents emit final state |

---

## 9. Message / Protocol Schema

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

* Coordinator routes messages declaratively
* Agents subscribe to relevant events only

---

## 10. Emergent Simulation Characteristics

* **LLM-driven probabilistic reasoning** generates emergent coordination
* Agents dynamically adapt to storm, hazards, and incomplete information
* Cascading failures, risk trade-offs, and alternative task planning
* Human interventions optional but visually dramatic
* Streaming of LLM reasoning, tasks, drone scans, and goal confidence is engaging

---

This spec now explicitly integrates:

* LLM reasoning loops for task selection and goal evaluation
* Probabilistic goal satisfaction (drone provides partial info, rover decides)
* Agentic outputs driving tool calls and action emissions
* Dynamic, emergent mission flow for live demo

---

If you want, I can also **draw a diagram of this probabilistic drone → rover → station LLM flow**, showing live reasoning, tool calls, and goal confidence updates — it would make the demo logic visually clear for the judges.


