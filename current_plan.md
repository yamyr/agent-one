Plan: Grid Redesign, Hidden Stone Types, Concentration System & Clustered Placement

**Status: ✅ COMPLETE** — All 5 steps implemented and verified (128 tests passing).

 Context

 The Mars rover simulation currently has three limitations:
 1. Grid uses screen coordinates (0,0 = top-left, north = Y-1) — unintuitive for a map
 2. Stone types are immediately visible, removing discovery gameplay
 3. Stones are placed uniformly at random — no geological realism or strategic exploration

 This plan introduces: math-convention coordinates, hidden stone types requiring chemical analysis, a ground concentration system for smart navigation, and clustered precious-stone placement via preferential attachment.

 Branch

 Create feature/geology-and-grid-redesign from main.

 ---
 Step 1: Clustered Stone Placement + Concentration Map

 File: server/app/world.py

 - Add constants: BATTERY_COST_ANALYZE = 0.03, BATTERY_COST_ANALYZE_GROUND = 0.03
 - Rewrite _generate_stones():
   - Place guaranteed core stone randomly (phase 1)
   - For subsequent stones: core stones (30% chance) placed via weighted sampling biased toward existing cores — weight = sum(1/(1 + manhattan_dist)) per existing core position (preferential attachment)
   - Basalt stones placed uniformly random
   - All stones spawn with schema: {"position": [x,y], "type": "unknown", "_true_type": "core"|"basalt", "extracted": False, "analyzed": False}
   - Return (stones, core_positions) tuple
 - Add _compute_concentration_map(core_positions):
   - For each grid cell, compute sum(exp(-d^2 / sigma^2)) where d = manhattan distance to each core position, sigma = 4.0
   - Normalize so max = 1.0
   - Returns dict[(x,y)] -> float
 - Update WORLD init: _stones, _core_positions = _generate_stones(), add "concentration_map": _compute_concentration_map(_core_positions)

 Step 2: Hidden Stone Types + analyze Action

 File: server/app/world.py

 - check_ground() — no change needed, already returns stone["type"] which is now "unknown"
 - Add _execute_analyze(agent_id, agent): costs BATTERY_COST_ANALYZE, reveals stone["type"] = stone["_true_type"], sets stone["analyzed"] = True
 - Gate dig/pickup behind analyze: _execute_dig() and _execute_pickup() must reject if stone["analyzed"] == False with error "Stone not yet analyzed (analyze first)"
 - Wire "analyze" into execute_action() with memory recording
 - Update update_tasks(): add branch — if stone at tile is unanalyzed, task = "Analyze unknown stone at current tile". Priority: analyze > dig > pickup. Also prefer unknown stones over known basalt when navigating.
 - Update get_snapshot(): strip _true_type from stones before broadcasting (prevent UI leaking hidden info)
 - Update rover tools lists in WORLD: add analyze and analyze_ground entries

 File: server/app/agent.py

 - Add ANALYZE_TOOL definition (function schema for LLM)
 - Update _build_context(): show "unknown (needs analyze)" for unanalyzed stones at current tile
 - Update run_turn() tool dispatch: accept "analyze" and "analyze_ground" names
 - Update MockRoverAgent.run_turn(): add analyze step before dig when stone is unanalyzed
 - Update LLM system prompt: explain analyze workflow and hidden types

 File: ui/src/constants.js

 - Add 'unknown': '#4a4a6a' to STONE_COLORS

 File: ui/src/components/AgentDetailModal.vue

 - Add .inv-stone.unknown CSS class

 Step 3: Ground Concentration Analysis + analyze_ground Action

 File: server/app/world.py

 - Add _execute_analyze_ground(agent_id, agent): manual action, costs BATTERY_COST_ANALYZE_GROUND (3%). Reads WORLD["concentration_map"][(x,y)], stores reading in agent["ground_readings"]
 - Wire "analyze_ground" into execute_action() with memory recording
 - Update get_snapshot(): serialize concentration_map tuple keys to "x,y" strings for JSON

 File: server/app/agent.py

 - Add ANALYZE_GROUND_TOOL definition
 - Add to ROVER_TOOLS list
 - Update _build_context(): show past concentration readings in Environment section
 - Update LLM system prompt: explain concentration meaning and exploration strategy

 Step 4: Flip Coordinate System

 File: server/app/world.py

 - DIRECTIONS: "north": (0, +1), "south": (0, -1) (swap from current)
 - _direction_hint(): dy > 0 → "north", dy < 0 → "south" (swap)

 File: server/app/agent.py

 - LLM prompt: "North = Y increases, South = Y decreases", "HIGHER Y → move NORTH"
 - MockRoverAgent: "north" if dy > 0 else "south" (swap)

 File: ui/src/components/WorldMap.vue

 - All Y pixel coords get inverted: replace position[1] * TILE_SIZE with (GRID_SIZE - 1 - position[1]) * TILE_SIZE in:
   - agentTransform() (line 60)
   - Stone :y (line 80)
   - Stone :transform rotate center (line 84)
   - Grid tile :y (line 73)

 Step 5: Update Tests

 File: server/tests/test_world.py

 - Import new symbols: charge_rover, BATTERY_COST_ANALYZE, BATTERY_COST_ANALYZE_GROUND
 - Update TestStones: check _true_type instead of type for core guarantee; update shape test for new schema fields
 - Update TestCheckGround: use new stone schema in fixtures (type: "unknown", _true_type, analyzed)
 - Add TestAnalyze class: success, reveals type, battery drain, no-stone error, already-analyzed error, unknown agent
 - Add TestAnalyzeGround class: returns concentration, battery drain, stores reading, no-battery error
 - Update TestDirectionHint: swap north/south assertions for flipped Y-axis
 - Update test_execute_move_all_directions: swap north/south expected outcomes
 - Update test_move_records_stone_found: expect "unknown" in memory (not "core")
 - Update test_charge_records_memory: use charge_rover() (already done from previous work)
 - Update mission tests: stone fixtures need _true_type and analyzed: True where type must match

 ---
 Files Modified (summary)

 ┌────────────────────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────┐
 │                  File                  │                                          Changes                                          │
 ├────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
 │ server/app/world.py                    │ Stone generation, concentration map, analyze actions, coordinate flip, snapshot filtering │
 ├────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
 │ server/app/agent.py                    │ New tools, prompt updates, mock rover analyze step, coordinate flip                       │
 ├────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
 │ server/app/station.py                  │ No changes needed (reads stone["type"] which is correct)                                  │
 ├────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
 │ server/app/main.py                     │ No changes needed                                                                         │
 ├────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
 │ server/tests/test_world.py             │ New test classes, updated fixtures and assertions                                         │
 ├────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
 │ ui/src/constants.js                    │ Add unknown stone color                                                                   │
 ├────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
 │ ui/src/components/WorldMap.vue         │ Y-axis inversion for all pixel coordinates                                                │
 ├────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤
 │ ui/src/components/AgentDetailModal.vue │ Add .inv-stone.unknown CSS                                                                │
 └────────────────────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────┘

 Verification

 1. Run python -m pytest tests/test_world.py -v — all tests pass
 2. Start server (./run) + UI (npm run dev) — simulation runs
 3. Verify on the map: (0,0) renders at bottom-left, north moves upward
 4. Verify stones render as grey-blue diamonds (unknown) until analyzed
 5. Verify rover analyzes stones before digging
 6. Check event log for concentration readings
 7. Restart a few times to confirm stone clustering (cores should cluster visually)