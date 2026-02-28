"""CLI tool for RAG knowledge base management.

Usage:
    python -m app.rag_setup generate-knowledge   # Generate Mars knowledge document
    python -m app.rag_setup init-db               # Initialize SurrealDB tables + embed chunks
    python -m app.rag_setup upload-library         # Upload to Mistral Libraries API
"""

import sys
import time
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"
KNOWLEDGE_PATH = DATA_DIR / "mars_knowledge.md"


def generate_knowledge():
    """Generate the Mars knowledge document from world model constants and flavor text."""
    from .world import (
        VEIN_GRADES,
        VEIN_WEIGHTS,
        VEIN_QUANTITY_RANGES,
        FUEL_CAPACITY_ROVER,
        FUEL_CAPACITY_DRONE,
        BATTERY_COST_MOVE,
        BATTERY_COST_MOVE_DRONE,
        BATTERY_COST_DIG,
        BATTERY_COST_PICKUP,
        BATTERY_COST_ANALYZE,
        BATTERY_COST_ANALYZE_GROUND,
        BATTERY_COST_SCAN,
        RETURN_TO_BASE_THRESHOLD,
        ROVER_REVEAL_RADIUS,
        DRONE_REVEAL_RADIUS,
        MAX_MOVE_DISTANCE,
        MAX_MOVE_DISTANCE_DRONE,
        MEMORY_MAX,
        SOLAR_BATTERY_CAPACITY,
        TARGET_QUANTITY,
    )

    # Build grade details
    grade_lines = []
    for grade, weight, (qty_min, qty_max) in zip(
        VEIN_GRADES, VEIN_WEIGHTS, [VEIN_QUANTITY_RANGES[g] for g in VEIN_GRADES]
    ):
        rarity = (
            "common"
            if weight > 50
            else "uncommon"
            if weight > 10
            else "rare"
            if weight > 3
            else "very rare"
            if weight > 1
            else "extremely rare"
        )
        grade_lines.append(
            f"- **{grade.capitalize()}**: {qty_min}-{qty_max} basalt units, {rarity} (weight {weight})"
        )

    doc = f"""# Mars Mission Knowledge Base

Generated from simulation world model constants and Mars geological research.

## Terrain and Surface Conditions

Mars surface terrain in the mission zone consists of an infinite procedurally-generated grid.
Each chunk of terrain ({16}x{16} tiles) is generated with deterministic seeding for consistency.
The terrain features regolith plains, scattered basalt vein deposits, and occasional crater formations.

Key terrain facts:
- The mission grid extends infinitely in all directions from the station at origin
- Terrain chunks are generated on-demand as agents explore new areas
- Surface composition varies: some areas have higher mineral concentration than others
- Crater rims and volcanic basalt flows tend to concentrate valuable mineral deposits
- Rocky outcrops near ancient lava tubes may contain pristine basalt formations

## Geology and Mineral Deposits

Mars basalt veins form through ancient volcanic activity. Magma intrusions created mineral-rich
deposits that cooled into basalt formations of varying purity and size.

Geological principles relevant to prospecting:
- Basalt veins are distributed stochastically across the terrain with ~1.5% probability per tile
- Higher-grade veins correlate with proximity to deep geological structures
- Concentration gradients follow Manhattan distance: signal strength = 1 - (distance / effective_radius)
- Higher-grade veins have larger effective detection radii (10 + 2 per grade level)
- Veins near each other may indicate a geological hotspot worth thorough exploration
- Core deposits (30% chance) produce the strongest concentration signals

## Vein Classification and Grades

Basalt veins are classified by grade, which determines their basalt yield and rarity:

{chr(10).join(grade_lines)}

Vein grades follow exponential rarity: weight ≈ 200 × e^(-1.3 × grade_index).
This means pristine veins are approximately 200× rarer than low-grade veins.

All veins start as "unknown" until analyzed. The analysis workflow is:
1. Encounter unknown vein → 2. Analyze to reveal grade and quantity → 3. Dig to extract → 4. Pick up into inventory

## Concentration Gradients and Prospecting

Ground concentration readings (0.0-1.0) indicate proximity to basalt vein deposits:
- 0.0: No veins detected within sensor range
- 0.1-0.3: Weak signal — veins may exist 8-10 tiles away
- 0.3-0.5: Moderate signal — veins likely within 5-7 tiles
- 0.5-0.7: Strong signal — high-grade veins within 3-5 tiles
- 0.7-0.9: Very strong signal — pristine or rich deposits within 1-3 tiles
- 1.0: Directly on top of a vein deposit

Concentration formula: concentration = max(0, 1 - manhattan_distance / effective_radius)
- Effective radius varies by vein grade: 10 (low) to 18 (pristine)
- Always follow increasing concentration gradients to locate high-value deposits
- Multiple high readings in an area suggest a geological hotspot

## Battery and Fuel Management

Battery is the critical resource constraining all agent operations:

**Rover** (fuel capacity: {FUEL_CAPACITY_ROVER} units):
- Move: 1 fuel unit/tile (~{BATTERY_COST_MOVE:.2%} battery per tile), max {MAX_MOVE_DISTANCE} tiles per move
- Analyze vein: {int(BATTERY_COST_ANALYZE * FUEL_CAPACITY_ROVER)} fuel units (~{BATTERY_COST_ANALYZE:.2%} battery)
- Analyze ground: {int(BATTERY_COST_ANALYZE_GROUND * FUEL_CAPACITY_ROVER)} fuel units (~{BATTERY_COST_ANALYZE_GROUND:.2%} battery)
- Dig: {int(BATTERY_COST_DIG * FUEL_CAPACITY_ROVER)} fuel units (~{BATTERY_COST_DIG:.2%} battery)
- Pickup: {int(BATTERY_COST_PICKUP * FUEL_CAPACITY_ROVER)} fuel units (~{BATTERY_COST_PICKUP:.2%} battery)
- Reveal radius: {ROVER_REVEAL_RADIUS} tiles around position

**Drone** (fuel capacity: {FUEL_CAPACITY_DRONE} units):
- Move: 1 fuel unit/tile (~{BATTERY_COST_MOVE_DRONE:.2%} battery per tile), max {MAX_MOVE_DISTANCE_DRONE} tiles per move
- Scan: {int(BATTERY_COST_SCAN * FUEL_CAPACITY_DRONE)} fuel units (~{BATTERY_COST_SCAN:.2%} battery)
- Reveal radius: {DRONE_REVEAL_RADIUS} tiles around position

**Return-to-base threshold**: {RETURN_TO_BASE_THRESHOLD:.0%} — agents must return to station when battery drops to this level.
Solar panels provide {SOLAR_BATTERY_CAPACITY:.0%} emergency recharge each.

## Exploration Strategy

Effective exploration follows these principles:
- **Systematic coverage**: Prefer unvisited tiles over backtracking
- **Concentration-guided navigation**: Move toward increasing concentration readings
- **Drone-first scouting**: The drone's scan reveals concentration patterns over a {DRONE_REVEAL_RADIUS}-tile radius, guiding rover exploration
- **Hotspot prioritization**: Areas with readings above 0.5 warrant thorough investigation
- **Diminishing returns**: After scanning an area, move at least {DRONE_REVEAL_RADIUS} tiles before scanning again
- **Agent memory**: Agents retain {MEMORY_MAX} recent actions in sliding memory; RAG extends recall beyond this window
- **Battery awareness**: Always maintain sufficient battery to return to station; the distance-based cost plus {6:.0%} safety margin

## Storm and Hazard Protocols

Mars surface operations face periodic environmental hazards:
- **Dust storms**: Reduce visibility and sensor accuracy; concentration readings become less reliable
- **Solar interference**: Can temporarily reduce solar panel charging efficiency
- **Communication delays**: Brief signal interruptions between agents and station
- **Temperature extremes**: Night-side operations consume slightly more battery for thermal management

During storm conditions:
- Reduce exploration range to stay closer to station
- Rely more on recent memory than new sensor readings
- The drone should prioritize returning to safe altitude/station
- Concentration readings during storms should be considered less accurate

## Mission Procedures and Workflow

The complete mission workflow for basalt collection:

1. **Scout phase**: Drone scans the terrain in expanding patterns from station
2. **Identify targets**: Locate high-concentration areas (>0.5 reading)
3. **Navigate**: Rover moves toward identified hotspots using concentration gradient
4. **Discover**: When rover encounters an unknown vein, analyze it
5. **Evaluate**: Check vein grade — prioritize high/rich/pristine over low/medium
6. **Extract**: Dig to extract the analyzed vein
7. **Collect**: Pick up the extracted vein into inventory
8. **Deliver**: Return to station with collected basalt when inventory is significant or battery is low
9. **Repeat**: Continue until mission target of {TARGET_QUANTITY} basalt units is delivered

**Key decision points**:
- Skip low-grade veins if battery allows further exploration (unless target is nearly met)
- Return early with partial load if battery is approaching {RETURN_TO_BASE_THRESHOLD:.0%}
- Coordinate with drone scan data to minimize wasted exploration moves
"""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_PATH.write_text(doc)
    print(f"Generated Mars knowledge document: {KNOWLEDGE_PATH}")
    print(f"Sections: 8, approximate size: {len(doc)} chars")


def init_db():
    """Initialize SurrealDB tables and load knowledge chunks."""
    from .rag import init_knowledge_table, init_memory_table, load_knowledge_chunks

    print("Initializing RAG tables in SurrealDB...")
    init_knowledge_table()
    init_memory_table()
    print("Tables created.")

    if not KNOWLEDGE_PATH.exists():
        print("Knowledge document not found, generating...")
        generate_knowledge()

    print("Embedding and storing knowledge chunks...")
    load_knowledge_chunks()
    print("Knowledge chunks loaded.")


def upload_library():
    """Upload knowledge document to Mistral Libraries API."""
    from .rag import _get_mistral_client

    if not KNOWLEDGE_PATH.exists():
        print(f"Knowledge document not found at {KNOWLEDGE_PATH}")
        print("Run 'generate-knowledge' first.")
        return

    client = _get_mistral_client()

    print("Creating Mistral library 'mars-mission-kb'...")
    library = client.beta.libraries.create(name="mars-mission-kb")
    library_id = library.id
    print(f"Library created: {library_id}")

    print(f"Uploading {KNOWLEDGE_PATH.name}...")
    with open(KNOWLEDGE_PATH, "rb") as f:
        doc = client.beta.libraries.documents.upload(
            library_id=library_id,
            file={"file_name": KNOWLEDGE_PATH.name, "content": f},
        )
    print(f"Document uploaded: {doc.id}")

    # Poll for processing completion
    print("Waiting for processing...", end="", flush=True)
    for _ in range(60):
        status = client.beta.libraries.documents.retrieve(library_id=library_id, document_id=doc.id)
        if hasattr(status, "processing_status") and status.processing_status == "Completed":
            print(" done!")
            break
        print(".", end="", flush=True)
        time.sleep(2)
    else:
        print(" timeout (may still be processing)")

    print(f"\nLibrary ID: {library_id}")
    print("Save this ID for future reference.")


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m app.rag_setup <command>")
        print("Commands: generate-knowledge, init-db, upload-library")
        sys.exit(1)

    command = sys.argv[1]
    if command == "generate-knowledge":
        generate_knowledge()
    elif command == "init-db":
        init_db()
    elif command == "upload-library":
        upload_library()
    else:
        print(f"Unknown command: {command}")
        print("Commands: generate-knowledge, init-db, upload-library")
        sys.exit(1)


if __name__ == "__main__":
    main()
