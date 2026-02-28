# Mars Mission Knowledge Base

Generated from simulation world model constants and Mars geological research.

## Terrain and Surface Conditions

Mars surface terrain in the mission zone consists of an infinite procedurally-generated grid.
Each chunk of terrain (16x16 tiles) is generated with deterministic seeding for consistency.
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

- **Low**: 10-50 basalt units, common (weight 200)
- **Medium**: 51-150 basalt units, common (weight 60)
- **High**: 151-350 basalt units, uncommon (weight 16)
- **Rich**: 351-700 basalt units, rare (weight 4)
- **Pristine**: 701-1000 basalt units, extremely rare (weight 1)

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

**Rover** (fuel capacity: 350 units):
- Move: 1 fuel unit/tile (~0.29% battery per tile), max 3 tiles per move
- Analyze vein: 3 fuel units (~0.86% battery)
- Analyze ground: 3 fuel units (~0.86% battery)
- Dig: 6 fuel units (~1.71% battery)
- Pickup: 2 fuel units (~0.57% battery)
- Reveal radius: 3 tiles around position

**Drone** (fuel capacity: 250 units):
- Move: 1 fuel unit/tile (~0.40% battery per tile), max 6 tiles per move
- Scan: 2 fuel units (~0.80% battery)
- Reveal radius: 6 tiles around position

**Return-to-base**: Agents must maintain sufficient battery to return to station based on distance.
Solar panels provide 25% emergency recharge each.

## Exploration Strategy

Effective exploration follows these principles:
- **Systematic coverage**: Prefer unvisited tiles over backtracking
- **Concentration-guided navigation**: Move toward increasing concentration readings
- **Drone-first scouting**: The drone's scan reveals concentration patterns over a 6-tile radius, guiding rover exploration
- **Hotspot prioritization**: Areas with readings above 0.5 warrant thorough investigation
- **Diminishing returns**: After scanning an area, move at least 6 tiles before scanning again
- **Agent memory**: Agents retain 8 recent actions in sliding memory; RAG extends recall beyond this window
- **Battery awareness**: Always maintain sufficient battery to return to station; the distance-based cost plus 600% safety margin

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
9. **Repeat**: Continue until mission target of 100 basalt units is delivered

**Key decision points**:
- Skip low-grade veins if battery allows further exploration (unless target is nearly met)
- Return early with partial load if battery is running low
- Coordinate with drone scan data to minimize wasted exploration moves
