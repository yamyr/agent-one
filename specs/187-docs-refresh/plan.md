# Feature 187: Implementation Plan

## Phase 1: SPEC.md Refresh

### 1.1 Update Architecture Section
- [x] Add narrator, training pipeline, voice command to diagram
- [x] Document Host as message router
- [x] Add hauler agent to agent list

### 1.2 Update World Model Section
- [x] Add ice deposits, gas geysers, gas plants to world state
- [x] Add abandoned structures and obstacles (mountains, geysers)
- [x] Update world state JSON structure
- [x] Document resource economy (ice -> water, geyser -> gas)

### 1.3 Update Agents and Tools Section
- [x] Add all rover tools (notify_peer, gather_ice, recycle_ice, build_gas_plant, collect_gas, upgrade_base, investigate_structure, use_refinery, drop_item, request_confirm, harvest_ice, upgrade_building)
- [x] Add hauler agent section with tools (move, load_cargo, unload_cargo, pickup, deliver)
- [x] Update station tools (recall_agent, allocate_power)
- [x] Update drone tools

### 1.4 Add New Feature Sections
- [x] Storm system (lifecycle, battery multipliers, move failures)
- [x] AI Narration (dual narrator, ElevenLabs TTS, streaming)
- [x] Goal confidence tracking (update logic, threshold, UI)
- [x] Human-in-the-loop (request_confirm, confirm endpoint, timeout)
- [x] Peer messaging (notify_peer tool)
- [x] Agents API backend (switchable backend, conversation threads)
- [x] Training data pipeline (SurrealDB tables, JSONL export)
- [x] Upgrade system (base upgrades, building upgrades)
- [x] Voice command (Voxtral transcription, command parsing)

### 1.5 Update Configuration Section
- [x] Document all Settings fields from config.py

## Phase 2: README.md Refresh

### 2.1 Update Architecture
- [x] Update diagram with narrator, hauler, voice, training
- [x] Update key features list

### 2.2 Update Agent Descriptions
- [x] Document hauler capabilities
- [x] Document new rover tools
- [x] Document station power allocation, recall

### 2.3 Update Configuration
- [x] Add all environment variables from config.py
- [x] Document agent_backend, agents_api_persist_threads
- [x] Document training_data_enabled, etc.

### 2.4 Add API Endpoints Section
- [x] List all REST and WebSocket endpoints

### 2.5 Update Project Structure
- [x] Add new files (agents_api.py, host.py, models.py, etc.)

## Phase 3: Finalize

- [x] Update Changelog.md
- [x] Commit changes
