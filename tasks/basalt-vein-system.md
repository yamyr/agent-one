# Basalt Vein System

## Overview
Replace the binary stone system (core/basalt) with a vein-based mineral system. Every vein contains basalt with a grade that determines quantity and rarity.

## Vein Grade Design

| Grade | Min Qty | Max Qty | Weight | Approx Probability |
|-------|---------|---------|--------|-------------------|
| low | 10 | 50 | 200 | ~71.2% |
| medium | 51 | 150 | 60 | ~21.4% |
| high | 151 | 350 | 16 | ~5.7% |
| rich | 351 | 700 | 4 | ~1.4% |
| pristine | 701 | 1000 | 1 | ~0.36% |

Rarity follows exponential decay: `weight = 200 * e^(-1.3 * grade_index)`

## Data Structure

```python
# Before (old)
stone = {
    "position": [x, y],
    "type": "unknown",        # "unknown" | "core" | "basalt"
    "_true_type": "core",     # hidden
    "extracted": False,
    "analyzed": False,
}

# After (new)
vein = {
    "position": [x, y],
    "type": "unknown",           # "unknown" -> "basalt_vein" after analyze
    "_true_type": "basalt_vein", # always basalt_vein now
    "grade": "unknown",          # "unknown" -> grade after analyze
    "_true_grade": "rich",       # hidden until analyzed
    "quantity": 0,               # 0 until analyzed, then revealed
    "_true_quantity": 523,       # hidden until analyzed
    "extracted": False,
    "analyzed": False,
}
```

## Mission System

```python
# Before
mission = {"target_type": "core", "target_count": 1, "collected_count": 0}

# After
mission = {"target_type": "basalt_vein", "target_quantity": 100, "collected_quantity": 0}
```

Rover inventory: `[{"type": "basalt_vein", "grade": "high", "quantity": 237}]`
Mission success: `sum(stone.quantity for delivered stones) >= target_quantity`

## Tasks

### Server (world.py)
- [x] Replace STONE_TYPES, TARGET_STONE_TYPE constants with VEIN_GRADES, VEIN_CONFIG
- [x] Update `_ensure_chunk()` to generate veins with weighted grade selection
- [x] Update `_execute_analyze()` to reveal grade + quantity
- [x] Update `_execute_dig()` for veins
- [x] Update `_execute_pickup()` for veins with quantity
- [x] Update `check_mission_status()` for quantity-based success
- [x] Update `get_snapshot()` to strip hidden vein fields
- [x] Update concentration map to boost around high-grade veins
- [x] Update task planning (`update_tasks`) for vein priorities
- [x] Update agent system prompts

### UI
- [x] Add vein grade colors to constants.js
- [x] Update WorldMap.vue stone rendering (size/color by grade)
- [x] Update AgentDetailModal.vue inventory display
- [x] Update MissionBar.vue for quantity-based progress

### Tests
- [x] Update TestStones for vein generation
- [x] Update TestAnalyze for grade/quantity reveal
- [x] Update TestDig for veins
- [x] Update TestPickup for quantity inventory
- [x] Update TestMissionStatus for quantity-based success
- [x] Update TestSnapshot for hidden field stripping
- [x] Add TestVeinGradeDistribution for exponential rarity
