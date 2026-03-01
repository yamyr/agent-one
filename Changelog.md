# Changelog

## [Unreleased]

### Added
- **Agent Memory & Learning (Feature F)**: Persistent strategic memory system where agents periodically summarize exploration memories into strategic insights via LLM
  - `summarize_memories()` generates summary prompts from agent memories (triggers when >= 6 memories)
  - `record_strategic_insight()` stores insights with sliding window (capped at 5)
  - Strategic insights injected into rover and drone `_build_context()` for LLM reasoning
  - Auto-summarization every 20 ticks via `mistral-small-latest`
  - Insight events broadcast via WebSocket with 💡 icon and gold styling
  - Strategic Insights section in Agent Detail Modal
  - 9 unit tests for all memory functions

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Live Inter-Agent Communication (Feature A)**: Drone scan intel wired into rover LLM context, inter-agent message relay system, auto-relay of high-concentration scans.
- `world.py`: `AGENT_MESSAGES`, `send_agent_message()`, `get_unread_messages()`, `get_drone_intel_for_rover()`
- `agent.py`: Rover context injects drone intel hotspots and incoming messages; DroneLoop auto-relays scans
- UI: `intel_relay` event rendering, message badge on agent panes
- 10 new inter-agent communication tests

* **station-loop:** Station Reactive Intelligence (Feature E) — periodic LLM evaluation of field events with reactive coordination
* **station-loop:** `StationLoop` BaseAgent subclass with 20s evaluation interval and event buffering (max 50)
* **station:** `StationAgent.evaluate_situation()` method for periodic LLM-based field assessment
* **models:** `StationContext` extended with `tick`, `mission_status`, `collected_quantity`, `target_quantity`
* **host:** interesting field events (dig, scan, notify, etc.) automatically routed to station loop
* **tests:** 18 new tests (7 station + 11 host integration)
* **voice:** add `/api/voice-command` endpoint — accepts audio uploads, transcribes via Mistral Voxtral, parses structured commands (recall_rover, abort_mission, pause/resume, etc.) via LLM, routes through Host, and broadcasts events via WebSocket
* **voice:** new `VoiceCommandProcessor` class with lazy Mistral client, Mars domain context bias terms, and JSON command extraction
* **voice:** add `voice_transcription_model` and `voice_command_model` settings to `config.py`
* **deps:** add `python-multipart>=0.0.9` for `UploadFile` support
* **tests:** 32 comprehensive tests for voice module (transcription, command parsing, pipeline, endpoint)
* **fine-tuning:** world-data fine-tuning pipeline — captures all LLM interactions (rover, drone, station, narrator) as JSONL training data for Mistral fine-tuning
* **fine-tuning:** `TrainingDataCollector` singleton records system prompts, user messages, assistant responses with tool_calls across simulation generations
* **fine-tuning:** `FineTuningManager` wraps Mistral SDK for file upload, job creation/monitoring/cancellation, and model activation
* **fine-tuning:** 7 REST endpoints for fine-tuning lifecycle management (`/fine-tuning/status`, `/fine-tuning/data`, `/fine-tuning/jobs` CRUD, `/fine-tuning/jobs/{id}/activate`)
* **fine-tuning:** model switching support — activate fine-tuned models at runtime for agents and narrator
* **world:** `generation_id` tracking across simulation resets for multi-generation training data
* **config:** 4 new settings: `training_data_enabled`, `training_data_dir`, `fine_tuned_agent_model`, `fine_tuned_narration_model`

### Fixed

* **ci:** apply ruff format to 7 unformatted files (agent.py, main.py, station.py, world.py, test_narrator.py, test_station.py, test_world.py) to fix server-lint CI failure

## [0.2.0](https://github.com/mhack-agent-one/agent-one/compare/v0.1.0...v0.2.0) (2026-02-28)


### Features

* **ui:** add communication visualization on map — animated SVG lines between agents on comm events (intel relay, command, alert, notify) with 3s fade-out and traveling pulse dots
* add ABORT mission feature. ([05015a6](https://github.com/mhack-agent-one/agent-one/commit/05015a674767facad137062ebdaf487702844e6f))
* add drone scout agent with aerial scanning capability ([1c1ab77](https://github.com/mhack-agent-one/agent-one/commit/1c1ab77788c9a147a96496ec35636f98a4adc7f5))
* add ElevenLabs AI narration for real-time Mars mission commentary ([1b4d19a](https://github.com/mhack-agent-one/agent-one/commit/1b4d19a6723b7f7c32437117027ef141ea4eb5d0))
* add event-driven station agent that assigns missions to rovers and reacts to field ([be23868](https://github.com/mhack-agent-one/agent-one/commit/be238685b05c7d917da75843845077fc7286cb86))
* add GitHub -&gt; Discord webhook notifications for PR and main push events ([7809d92](https://github.com/mhack-agent-one/agent-one/commit/7809d923930e198cb4a09d465759005a56d1f4aa))
* add GitHub Actions CI/CD pipeline with lint, test, and build verification ([#2](https://github.com/mhack-agent-one/agent-one/issues/2)) ([651f13c](https://github.com/mhack-agent-one/agent-one/commit/651f13c759ac1789eee72a5df7626e0d7004071f))
* add rover dig/pickup tools, agent short-term memory, richer LLM context, and system ([d153f31](https://github.com/mhack-agent-one/agent-one/commit/d153f312fca2cb927d0e74b38fbef481d5ef70e3))
* add rover dig/pickup/charge actions, fog-of-war reveal, mission tracking, and UI ([a9201cb](https://github.com/mhack-agent-one/agent-one/commit/a9201cb43367babcc87ad60c1d9bafcbec0bb6fb))
* add rover LLM fallback, split turn intervals, install Spec Kit ([43811be](https://github.com/mhack-agent-one/agent-one/commit/43811be909d7db3079267a4a12a1cbce96fc5087))
* add solar panels, remove mock rover, probability-based stones, mission return logic ([527283d](https://github.com/mhack-agent-one/agent-one/commit/527283d51ba5803e3c5547ea78438506d149ab09))
* add stones, rover visited memory, auto ground-check, and sync docs with world state ([dd7021e](https://github.com/mhack-agent-one/agent-one/commit/dd7021e327f913a379a4a3e94216884d805b9ea8))
* add task system, coordinate hints, pause/resume, and 2s agent loop for reliable rover ([51c821e](https://github.com/mhack-agent-one/agent-one/commit/51c821e297969fe802abe9157d21588f0374fad5))
* add world reset button, seed config, and simulation lifecycle management ([eadad7f](https://github.com/mhack-agent-one/agent-one/commit/eadad7f19201630785cac7d088420bc8afc5f039))
* **agent:** upgrade RoverAgent to magistral-medium and convert MockRoverAgent to LLM-powered ([#3](https://github.com/mhack-agent-one/agent-one/issues/3)) ([2e8a262](https://github.com/mhack-agent-one/agent-one/commit/2e8a262a4da02acf75e42050916d4fcfd00c0adb))
* always-on text narration with streaming ([51a70f2](https://github.com/mhack-agent-one/agent-one/commit/51a70f2b0a80c8e4f97cb8e06e01b1c2222b093f))
* always-on text narration with streaming, voice as opt-in toggle ([e354982](https://github.com/mhack-agent-one/agent-one/commit/e354982fed122205be4ff2e4fffb80e880d47734))
* **battery:** rebalance fuel system — 1 unit/tile, capacity 350/250, 67% return threshold ([865b6cf](https://github.com/mhack-agent-one/agent-one/commit/865b6cf21ed485b2eea633d6dcd72b1f0d07bab5))
* **battery:** rebalance fuel system — 1 unit/tile, capacity 350/250, 67% return threshold ([9979144](https://github.com/mhack-agent-one/agent-one/commit/997914410b21d43c77562e30095f73ec76c3fb67))
* chunk-based infinite grid with lazy procedural generation ([f227c57](https://github.com/mhack-agent-one/agent-one/commit/f227c57919bb7e8bda9c9fdc0fd65bf2f76c9d0e))
* **ci:** add automated release versioning and management ([#6](https://github.com/mhack-agent-one/agent-one/issues/6)) ([9cb1606](https://github.com/mhack-agent-one/agent-one/commit/9cb16062304977de970c22e2d2eaf9a02b3f2f71))
* disable station-rover communication — rovers explore autonomously ([71df09a](https://github.com/mhack-agent-one/agent-one/commit/71df09a23a573b622c53d50c6bed58acae83bec8))
* dual-narrator dialogue system (Commander Rex + Dr. Nova) ([422a5ce](https://github.com/mhack-agent-one/agent-one/commit/422a5ceba6b61db0407b79dd0a9b1d5462ecae4e))
* Dual-narrator dialogue system (Commander Rex + Dr. Nova) ([5ebfd2a](https://github.com/mhack-agent-one/agent-one/commit/5ebfd2a89fd9e00f4510bc31aaa0be60fe11b862))
* ElevenLabs AI narration for Mars mission ([8265871](https://github.com/mhack-agent-one/agent-one/commit/8265871009e5b28f38cbb749c19fb99b1ea0045c))
* entity selector UI + battery safety return-to-base ([651d81c](https://github.com/mhack-agent-one/agent-one/commit/651d81c8614febbd5463888af5a9b16476dab136))
* geology redesign — hidden stone types, clustered placement, concentration map, coordinate flip ([11d33f2](https://github.com/mhack-agent-one/agent-one/commit/11d33f2ba262880acec1d74edf358ea96aa30ce0))
* GitHub -&gt; Discord webhook notifications ([fd66b81](https://github.com/mhack-agent-one/agent-one/commit/fd66b817ddbf71c68b808406f12e01b25276072a))
* infinite grid, drone scout, entity selector & battery safety ([ec35dcc](https://github.com/mhack-agent-one/agent-one/commit/ec35dcc56c6315a7758e68282d988bf749a2be96))
* multi-tile movement, larger fog radius, guaranteed core stones, and visible stone ([6e63457](https://github.com/mhack-agent-one/agent-one/commit/6e6345750b28bcc3f921521e2b22d418d72e38be))
* **rag:** add RAG-enhanced agent intelligence system ([#51](https://github.com/mhack-agent-one/agent-one/issues/51)) ([c10522d](https://github.com/mhack-agent-one/agent-one/commit/c10522d901294d2e20b68766d9251c203c884322))
* remove mock rover, enforce mission return, chronological logs ([595608c](https://github.com/mhack-agent-one/agent-one/commit/595608c9558465365d035bcd81a4b8f1884420b3))
* rover LLM fallback, split turn intervals, install Spec Kit ([cc297b3](https://github.com/mhack-agent-one/agent-one/commit/cc297b3972f3ba22351f7a19cfe6ee8bc1afef10))
* rovers start at station (0,0) and explore from there ([d7bc217](https://github.com/mhack-agent-one/agent-one/commit/d7bc2179a9971f1fd41711e21e2f22b60b2c3aae))
* show LLM model name in agent pane header from single source of truth ([5648c90](https://github.com/mhack-agent-one/agent-one/commit/5648c90ea1c3a243eada1718cfc045dbbc39d474))
* simplify rover actions — station-only charging and delivery-based success ([77526be](https://github.com/mhack-agent-one/agent-one/commit/77526be3b64e22001b6a9b3a43bb9d2898b5a61d))
* simplify rover actions — station-only charging, auto-scan, and delivery-based mission success ([89fab68](https://github.com/mhack-agent-one/agent-one/commit/89fab6813350b3fafcd77e075c500d0e95009c2a))
* **ui:** add BatteryBar component and mission progress bar ([#32](https://github.com/mhack-agent-one/agent-one/issues/32)) ([f3bb21a](https://github.com/mhack-agent-one/agent-one/commit/f3bb21adffba408d65da535c407ce2a8c8cc4a01))
* **ui:** add concentration heatmap to WorldMap tiles ([#34](https://github.com/mhack-agent-one/agent-one/issues/34)) ([70abfe9](https://github.com/mhack-agent-one/agent-one/commit/70abfe95cd3c0b3e03c0013835e3fb37a6a4515f))
* **ui:** add fading movement trails for agents on WorldMap ([#42](https://github.com/mhack-agent-one/agent-one/issues/42)) ([2df0717](https://github.com/mhack-agent-one/agent-one/commit/2df0717266b163d5e27e2a169a1f863055496c5f))
* **ui:** add fog-of-war gradient overlay on WorldMap ([#43](https://github.com/mhack-agent-one/agent-one/issues/43)) ([091cb6e](https://github.com/mhack-agent-one/agent-one/commit/091cb6e8f25d8152467ab3e63de3e4222ca29c57))
* **ui:** add hover tooltips for agents, veins, and solar panels on WorldMap ([#46](https://github.com/mhack-agent-one/agent-one/issues/46)) ([0eed99f](https://github.com/mhack-agent-one/agent-one/commit/0eed99f7e9b9c07a8629edfc26eb516b3835eebf))
* **ui:** add keyboard shortcuts for simulation control ([#41](https://github.com/mhack-agent-one/agent-one/issues/41)) ([427b31d](https://github.com/mhack-agent-one/agent-one/commit/427b31d0bdc33d13459877e2be299d3253af48fe))
* **ui:** add loading skeletons for core components (R3P6) ([#56](https://github.com/mhack-agent-one/agent-one/issues/56)) ([d1c5f19](https://github.com/mhack-agent-one/agent-one/commit/d1c5f19528b6d41462c85502469959fd504e1595))
* **ui:** add MiniMap vein indicators using VEIN_COLORS ([#47](https://github.com/mhack-agent-one/agent-one/issues/47)) ([1e5166d](https://github.com/mhack-agent-one/agent-one/commit/1e5166d4f06360710f69520b6700f81359f7b8aa))
* **ui:** add red dashed circle showing rover visibility radius ([b95ce73](https://github.com/mhack-agent-one/agent-one/commit/b95ce736640edb97dff507f351277ddf65789eb0))
* **ui:** add responsive layout for tablet and mobile ([#36](https://github.com/mhack-agent-one/agent-one/issues/36)) ([b60e11c](https://github.com/mhack-agent-one/agent-one/commit/b60e11cd9d51c66f8b4f1912ec71ed0ec226e370))
* **ui:** add StatsBar with tick counter, tiles revealed, and collection stats ([#44](https://github.com/mhack-agent-one/agent-one/issues/44)) ([4a377dd](https://github.com/mhack-agent-one/agent-one/commit/4a377dd03f882bdaf7991465bf0a8a1efb8de6f6))
* **ui:** add toast notification system for critical simulation events ([#45](https://github.com/mhack-agent-one/agent-one/issues/45)) ([fc5d330](https://github.com/mhack-agent-one/agent-one/commit/fc5d3306d1a934dbe65d9f2e1a70330aa884eb3a))
* **ui:** add toggleable MiniMap legend (R3P3) ([#53](https://github.com/mhack-agent-one/agent-one/issues/53)) ([6921c1f](https://github.com/mhack-agent-one/agent-one/commit/6921c1fa79592f0a09148bfe867901f503bf403a))
* **ui:** add Vue transitions to modal, event log, and narration player ([#40](https://github.com/mhack-agent-one/agent-one/issues/40)) ([fc252b7](https://github.com/mhack-agent-one/agent-one/commit/fc252b70f4b5032fc293d62f165e498bdd0c4373))
* **ui:** add WorldMap zoom controls with mouse wheel support ([#48](https://github.com/mhack-agent-one/agent-one/issues/48)) ([7cde65e](https://github.com/mhack-agent-one/agent-one/commit/7cde65e0a67c4d99a0551f5f4272401dc51740a7))
* **ui:** extract CSS design tokens — replace hardcoded colors with custom properties ([#30](https://github.com/mhack-agent-one/agent-one/issues/30)) ([64fbd65](https://github.com/mhack-agent-one/agent-one/commit/64fbd6587e9e00e9a23352de290d40f0f913fb14))
* **ui:** finalize color token cleanup and add EventLog event-name color coding ([#49](https://github.com/mhack-agent-one/agent-one/issues/49)) ([9f068c3](https://github.com/mhack-agent-one/agent-one/commit/9f068c3ccd7b378fd08faf885630c961b3e87be2))
* **ui:** fix zoom tile scaling + EventLog virtual scrolling (round 3 phase 2) ([9e7647f](https://github.com/mhack-agent-one/agent-one/commit/9e7647f2355858cbc8c31b3d74ad3a3d481cfe61))
* **ui:** implement persisted preferences (R3P7) and help overlay (R3P8) ([#58](https://github.com/mhack-agent-one/agent-one/issues/58)) ([54090cf](https://github.com/mhack-agent-one/agent-one/commit/54090cf9da0aeb54867962a40499e00b75636182))
* **ui:** implement toast deduplication (R3P5) ([#55](https://github.com/mhack-agent-one/agent-one/issues/55)) ([efa8b7f](https://github.com/mhack-agent-one/agent-one/commit/efa8b7f4328b97c7418c242f3c235be6dd8c47e4))
* **ui:** integrate UnoCSS with Vite plugin and custom theme ([#39](https://github.com/mhack-agent-one/agent-one/issues/39)) ([d67b6bf](https://github.com/mhack-agent-one/agent-one/commit/d67b6bf29d6cbd488912194f1e96bb08c5e8c530))
* **ui:** refine camera inertia with adaptive lerp (R3P4) ([#54](https://github.com/mhack-agent-one/agent-one/issues/54)) ([491d88d](https://github.com/mhack-agent-one/agent-one/commit/491d88dedcd429824874ef168fef2629501e4d10))
* **ui:** round 3 phase 1 accessibility baseline improvements ([#50](https://github.com/mhack-agent-one/agent-one/issues/50)) ([7732a9c](https://github.com/mhack-agent-one/agent-one/commit/7732a9c0e41a49eb6e8dda9101c199b2461d80e8))
* **ui:** smart event log formatting — replace raw JSON with human-readable summaries ([#37](https://github.com/mhack-agent-one/agent-one/issues/37)) ([fdbb410](https://github.com/mhack-agent-one/agent-one/commit/fdbb41025b5a9f22fab4586d5db8702aa8b9b7e3))
* **ui:** smooth camera interpolation via requestAnimationFrame ([#38](https://github.com/mhack-agent-one/agent-one/issues/38)) ([1a9a564](https://github.com/mhack-agent-one/agent-one/commit/1a9a56438c510842cb3d4cfed7299a33d4c49bfa))
* **ui:** toast rate-limiting, count badges, EventLog skeleton (R3 remaining) ([#59](https://github.com/mhack-agent-one/agent-one/issues/59)) ([64e0af7](https://github.com/mhack-agent-one/agent-one/commit/64e0af70c274ab9452f340253ee16116ae820efc))
* **ui:** upgrade font to JetBrains Mono ([#31](https://github.com/mhack-agent-one/agent-one/issues/31)) ([637cc91](https://github.com/mhack-agent-one/agent-one/commit/637cc91f7c9d8e009c4b16bf7af37aa57da0c53b))
* **ui:** use per-rover color for visibility radius circle ([f71304c](https://github.com/mhack-agent-one/agent-one/commit/f71304c9856567b72c80763607b9f9bd3334552b))
* **ui:** wire persisted preferences into WorldMap and MapLegend ([#60](https://github.com/mhack-agent-one/agent-one/issues/60)) ([24a92a1](https://github.com/mhack-agent-one/agent-one/commit/24a92a135496ce131914e555b0a0d0ae53293cd3))
* **ui:** zoom tile scaling + EventLog virtual scrolling ([4e723b7](https://github.com/mhack-agent-one/agent-one/commit/4e723b7f062247299b039c250fe4c8650a64f943))
* upgrade TTS to ElevenLabs v3 with audio emotion tags ([c61dcfe](https://github.com/mhack-agent-one/agent-one/commit/c61dcfe66ee1028350a6920038f6261fdcd27beb))
* viewport camera with pan, auto-follow, and minimap ([d022215](https://github.com/mhack-agent-one/agent-one/commit/d022215748890b5f2d7eb3000d281ff71987b7c0))
* **world:** basalt vein grade system ([1ffddf6](https://github.com/mhack-agent-one/agent-one/commit/1ffddf6de152b679bf29167a894aa371840f2fda))
* **world:** replace binary stone system with basalt vein grade system ([259507f](https://github.com/mhack-agent-one/agent-one/commit/259507ff4a8ff3affb80faba69985b6ee33d91ca))


### Bug Fixes

* **ci:** add retry with backoff for Discord webhook rate limits (429) ([fc92edb](https://github.com/mhack-agent-one/agent-one/commit/fc92edb8925f0fd48350dd100f8eae27ccab5d93))
* **ci:** Discord webhook retry on 429 rate limits ([c0e9bf5](https://github.com/mhack-agent-one/agent-one/commit/c0e9bf509c83b29a8e17302deb02a18911f10a41))
* **ci:** remove unused imports and update tests for infinite grid ([51cbfd4](https://github.com/mhack-agent-one/agent-one/commit/51cbfd482853d2e6b884eb1f593acd3c5b6ceb3d))
* collected_quantity should only count delivered basalt, not in-transit inventory ([56e825b](https://github.com/mhack-agent-one/agent-one/commit/56e825b67f47d0714bf019d052c374f6ecb8555f))
* disable all narration (text + voice) when NARRATION_ENABLED is false ([450ba82](https://github.com/mhack-agent-one/agent-one/commit/450ba82ac76a016bf854f5c4e6b2631372056c8b))
* Discord webhook workflow secrets access ([b28db61](https://github.com/mhack-agent-one/agent-one/commit/b28db615043fdb6462816df00c1e1ce35fe765fc))
* include all three agents in default active_agents config ([6402ee0](https://github.com/mhack-agent-one/agent-one/commit/6402ee03dfbd26898b46ed93c14d1f83cf8a7da9))
* keep inventory info out of task list so UI always shows actionable goal first ([56018d2](https://github.com/mhack-agent-one/agent-one/commit/56018d25522d3266a28a9c6182d2cf86d677763c))
* make narration opt-in and gracefully skip missing ElevenLabs key ([f6834c7](https://github.com/mhack-agent-one/agent-one/commit/f6834c7550e91e382f92b130352f4914c97c5567))
* narration opt-in, reduce interval, graceful ElevenLabs fallback ([61d5457](https://github.com/mhack-agent-one/agent-one/commit/61d54571961c352fcf834178652328e11a0f059a))
* prevent rover movement at zero battery ([6abe9cd](https://github.com/mhack-agent-one/agent-one/commit/6abe9cdf4ef0f4df987ba6d05c404f459eb8c125))
* **release:** map pyproject version path for release-please ([#8](https://github.com/mhack-agent-one/agent-one/issues/8)) ([cd291e6](https://github.com/mhack-agent-one/agent-one/commit/cd291e6a8a71d9099b803a45446a5f6df2bb4cec))
* remove secrets from job-level if conditions in Discord workflow ([969ea99](https://github.com/mhack-agent-one/agent-one/commit/969ea9973cef98bf37620d632765229a89e56754))
* remove unused imports/variables to fix server-lint CI ([#64](https://github.com/mhack-agent-one/agent-one/issues/64)) ([72724c3](https://github.com/mhack-agent-one/agent-one/commit/72724c35be0718f1bedc4a16160c8f7ef8863e07))
* resolve 10 ruff lint errors failing CI ([96bf54f](https://github.com/mhack-agent-one/agent-one/commit/96bf54f3945a010e80ae1b8321fb84e144283cd0))
* resolve 10 ruff lint errors failing CI ([450c179](https://github.com/mhack-agent-one/agent-one/commit/450c179cd3135a5a588206465ee25c36df800e11))
* resolve merge conflicts with main, fix coordinate-flipped test assertions ([51e1a2a](https://github.com/mhack-agent-one/agent-one/commit/51e1a2a7fecd0adca40286a3d2c597ee2f45924a))
* rover tasks only reference stones discovered through exploration, not pre-revealed at ([378df08](https://github.com/mhack-agent-one/agent-one/commit/378df08cbe63e9a835563251f7c67e6a4ccaad0f))
* ruff format narrator.py, update test for opt-in default ([465b736](https://github.com/mhack-agent-one/agent-one/commit/465b736da92f21c9000a4f63492cd44e0bb9fa44))
* show inventory quantities before battery in agent pane for better at-a-glance status ([25cf925](https://github.com/mhack-agent-one/agent-one/commit/25cf92500ef2ffb74040f7116f0d4b311acbc471))
* **ui:** broken map — undefined variable in WorldMap.vue ([b0c70ea](https://github.com/mhack-agent-one/agent-one/commit/b0c70ea6129128e93bb0ee8fa9c4b168681e1d8e))
* **ui:** broken map — undefined variable reference in WorldMap.vue ([1810d1d](https://github.com/mhack-agent-one/agent-one/commit/1810d1d5d7cb9082fe39067b24becf4734141562))
* **ui:** make tile count dynamic based on zoom level ([73375bc](https://github.com/mhack-agent-one/agent-one/commit/73375bc6759fac751a84a820cf0361c30de8cada))
* **ui:** move EventLog below map instead of below sidebar ([23b3a1f](https://github.com/mhack-agent-one/agent-one/commit/23b3a1f6b2855da30bc02f444aa6cf97eddd4806))
* **ui:** move EventLog next to map in right column ([16002c9](https://github.com/mhack-agent-one/agent-one/commit/16002c96876b3e27ae2ffe5da6dc287b3200f076))
* **ui:** narration text not showing and voice toggle broken ([51eb347](https://github.com/mhack-agent-one/agent-one/commit/51eb347dd518c0e51ddae4cb7840109e57d2e551))
* **ui:** narration text not showing and voice toggle broken ([b252cff](https://github.com/mhack-agent-one/agent-one/commit/b252cff5fc573db269466e3c991f9f87c76b8069))
* **ui:** resolve all ESLint warnings — zero warnings CI ([443fa89](https://github.com/mhack-agent-one/agent-one/commit/443fa896491fef25e7bb94c484a495520a2b6624))
* **ui:** resolve all ESLint warnings — zero warnings CI ([b13a9f5](https://github.com/mhack-agent-one/agent-one/commit/b13a9f53c2446a752cb87124f55e1db71f2987bf))
* **ui:** show dynamic task status instead of static mission objective ([bdb95b1](https://github.com/mhack-agent-one/agent-one/commit/bdb95b1f033acd9272dfe576f062c6571fcb08a4))


### Reverts

* undo all changes after 77526be ([dde8ff6](https://github.com/mhack-agent-one/agent-one/commit/dde8ff6076b888d662b11fe61b2e6095f2100e82))

## [Unreleased]

### Added (UI Polish Round 3 — Phases 3–8)

- **Persisted zoom preference**: Zoom level saved to `localStorage` via `usePreferences` composable; survives page refresh
- **Persisted legend visibility**: MiniMap legend open/closed state saved to `localStorage`; restored on load
- **Toast rate-limiting**: Max 5 visible toasts; oldest evicted when capacity reached
- **Toast dedup count badge**: Identical messages within 5s window show `×N` count badge instead of duplicating
- **Toast timer management**: Dedup resets dismiss timer; evicted toasts clean up their timers
- **EventLog skeleton state**: 6 pulsing skeleton rows with staggered animation delays shown before WebSocket data arrives

### Fixed (Zoom Scaling)

- **Dynamic viewport tile count**: WorldMap zoom now scales tile count proportionally — zooming out (0.7x) renders ~29×29 tiles, zooming in (2.2x) renders ~10×10 tiles, instead of fixed 20×20
- **Zoom re-centering**: Camera position adjusts on zoom change to keep the center tile stable, preventing viewport shift
- **MiniMap viewport accuracy**: MiniMap viewport box now reflects actual visible tile count via dynamic `viewportW`/`viewportH` props
- **MiniMap navigation**: Fixed rubber-band camera effect when clicking minimap by using `navigateTo()` method that sets both camera position and interpolation target
- **Dead code cleanup**: Removed unused `MAP_W`/`MAP_H` constants from `constants.js`

### Added (EventLog Virtual Scrolling — Round 3 Phase 2)

- **Virtual scrolling**: EventLog now renders only visible events (~20-25 DOM nodes) instead of all 200, using spacer-based windowing with 5-item buffer
- **Scroll-pinning**: Auto-scrolls to top for new events when already at top; preserves scroll position when browsing history
- **Enter animation**: New events slide in with 0.3s animation using CSS keyframes, triggered by UID tracking (works even at 200-event cap)
- **ResizeObserver**: Container height tracked dynamically for accurate visible window calculation
- **CSS containment**: Added `contain: content` to scroll container for browser paint optimization
- **Fixed-height rows**: 32px rows with `overflow: hidden` and `nowrap` prevent layout shifts during virtual scrolling

### Changed (Basalt Vein System)

- **Vein-based mineral system**: Replaced binary stone types (core/basalt) with a vein grade system. Every vein is basalt with a grade (low/medium/high/rich/pristine) determining quantity, following exponential rarity decay (`weight = 200 * e^(-1.3 * index)`)
- **Vein data model**: Each vein has hidden `_true_grade` and `_true_quantity` fields revealed on analyze. Grades map to quantity ranges: low (10-50), medium (51-150), high (151-350), rich (351-700), pristine (701-1000)
- **Quantity-based missions**: Mission success now requires collecting a target quantity of basalt (default 100 units) rather than a count of specific stone types. `target_count`/`collected_count` replaced with `target_quantity`/`collected_quantity`
- **Concentration map scaling**: Ground concentration boost near veins now scales with grade index — higher-grade veins produce stronger signals
- **Task planning**: Rover task generation prioritizes higher-grade veins (pristine first) when choosing navigation targets
- **Agent prompts**: All rover, drone, and station LLM prompts updated for vein terminology — tool descriptions, workflow instructions, and context display reference grades and quantities
- **Narrator keywords**: Updated narration keyword filter from "core" to "vein"
- **UI vein visualization**: Stone rendering replaced with grade-based colors (pristine=gold, rich=deep gold, high=amber, medium=silver, low=gray) and size scaling (6-14px by grade). Rich/pristine veins get SVG glow effect
- **UI inventory display**: Agent detail modal shows grade + quantity per vein (e.g., "HIGH x237")
- **UI mission progress**: Mission bar shows quantity-based progress (e.g., "237 / 100 basalt")
- **Pydantic models**: `StoneInfo` and `InventoryItem` gained `grade` and `quantity` fields; `RoverWorldView` uses `target_quantity`/`collected_quantity`
- **Test coverage**: 278 tests passing — added `TestVeinGradeDistribution` (5 tests) validating exponential rarity, updated all stone-related test classes for vein data structures

### Added (Solar Panels)

- **Solar panel system**: Rovers carry 2 deployable solar panels (`MAX_SOLAR_PANELS=2`). Deploy with `deploy_solar_panel` action (costs 1 fuel), recharge with `use_solar_battery` (gains 25% battery). Panels render on the map as gold rectangles (grey when depleted).
- **Solar panel tools**: `DEPLOY_SOLAR_PANEL_TOOL` and `USE_SOLAR_BATTERY_TOOL` added to rover LLM tool list.
- **Solar panel context**: Rover LLM prompt includes panels remaining and nearby panel status.
- **Solar panel rendering**: WorldMap.vue renders active/depleted panels with grid lines.
- **`_nearest_solar_panel` helper**: Low-battery task hints suggest nearby active panels as alternative to station return.

### Changed (Remove Mock Rover)

- **Removed `rover-mock` agent entirely**: `MockRoverReasoner`, `MockRoverAgent`, `RoverMockLoop` classes deleted from `agent.py`. No more mock rover in `_build_initial_world`, `AGENT_MAP`, `active_agents` config, or `AGENT_COLORS`.
- **`MistralRoverReasoner._fallback_turn`**: Now uses inline explore logic (random unvisited direction) instead of delegating to `MockRoverReasoner`.
- **`charge_rover` → `charge_agent`**: Renamed to accept any non-station agent (drone included). `charge_rover` kept as backward-compat alias.
- **Station prompt**: Updated to reference single rover `rover-mistral` instead of two rovers.

### Changed (Mission Return Logic)

- **Mission fulfillment check**: `_update_rover_tasks` now checks quantity-based fulfillment and instructs rover to return to station immediately with emoji prefix.
- **Rover LLM prompt**: Added "CRITICAL: Once you have collected enough basalt, STOP exploring and RETURN TO STATION IMMEDIATELY."
- **Mission indicator**: LLM context shows mission target met status when collected quantity meets target.

### Changed (UI Improvements)

- **Chronological event log**: `AgentPane.vue` now shows ALL events (thinking + actions) chronologically, not just thinking events. Actions show move coordinates or result text.
- **CSS refinements**: `.ae-type.think` colored `#668`, `.ae-text.action-text` colored `#7a9a7a`.

### Lessons Learned

- When spawning agent teams with file-editing permissions, coordinate edits carefully — concurrent writes to the same file cause "file modified since read" conflicts. Assign file ownership per agent to avoid collisions.
- When replacing a mock with real agent, test setUp methods that previously initialized two agents need careful deduplication.
- Mission state (`collected_quantity`) must be reset in test setUp to avoid cross-test contamination with new mission-fulfillment logic.

### Changed (Battery & Fuel Rebalance)

- **Fuel capacity system**: Rovers carry 350 fuel units, Drone carries 250 fuel units. Battery remains a 0.0–1.0 float (fraction of capacity)
- **1 fuel unit per tile**: All agents now cost 1 fuel unit per tile moved (~0.29% battery for rovers, ~0.4% for drone)
- **Action costs (in fuel units)**: move=1/tile, dig=6, analyze=3, pickup=2, scan=2. All expressed as fuel units divided by capacity
- **Return-to-base at 67%**: Agents must return to station when battery drops to 67% or below (dual check: threshold + distance safety net with 6% margin)
- **Constants centralized**: All battery costs use named constants from `world.py` — no more hardcoded magic numbers in `agent.py`
- **Updated LLM prompts**: Rover and drone system prompts now describe costs in fuel units with percentage equivalents
- **Updated tool descriptions**: All tool descriptions in `agent.py`, `world.py`, and `station.py` use fuel-unit-based costs
- **Documentation updated**: `WORLD.md` reflects new fuel capacity system and return-to-base rules

### Changed (Runtime Upgrade)

- **Python 3.12 → 3.14**: Updated `server/pyproject.toml` (`requires-python`), CI workflow (`python-version`), Dockerfile (`python:3.14-slim`), regenerated `uv.lock`
- **Node 22 → 24 LTS**: Updated `ui/package.json` (`engines.node`), CI workflow (`node-version`), Dockerfile (`node:24-slim`)
- Updated docs: `CLAUDE.md`, `README.md`, `DEV_README.md` to reflect new version requirements

### Added (Co-Authoring Guidelines)

- **Co-authoring standard**: All commits and PRs now use `Co-Authored-By: agent-one team <agent-one@yanok.ai>` — added to CLAUDE.md as mandatory rule and to PR template footer
- Replaces per-model attribution (e.g., `Claude Opus`) with unified team identity

### Added (Semantic PR Logs)

- **PR template** (`.github/PULL_REQUEST_TEMPLATE.md`): standardized semantic PR format with change type checkboxes, semantic diff (Added/Changed/Removed), file impact table (files added/modified/deleted, lines +/-), core files listing, and test coverage section
- **CLAUDE.md instructions** for auto-generating PR bodies: computes git diff stats, classifies files by filter (A/M/D), identifies core vs test files, and fills the template programmatically

### Added (Dual Narrators)

- **Dual-narrator dialogue system**: Two narrators — Commander Rex (male, dry humor) and Dr. Nova (female, science enthusiast) — banter about mission events in real time
  - `server/app/narrator.py` fully rewritten: new `NARRATOR_SYSTEM_PROMPT` defining both characters, `_parse_dialogue()` regex parser for `COMMANDER REX: ...` / `DR. NOVA: ...` output, `_generate_dialogue_audio()` using ElevenLabs Text-to-Dialogue API (`text_to_dialogue.convert()` with `DialogueInput` pairs), single-voice fallback via `_generate_audio_single()`
  - WebSocket narration payload now includes `dialogue: [{speaker, text}, ...]` alongside flat `text` for backward compatibility
  - `NarrationPlayer.vue` updated: speaker-labeled dialogue lines (REX in amber `#cc8844`, NOVA in teal `#44ccaa`), label changed from "NARRATOR" to "MISSION COMMS"
  - Config: `narration_voice_id_male` (George), `narration_voice_id_female` (Rachel), `narration_model` (`mistral-medium-latest`)
  - 14 new unit tests: `TestParseDialogue` (8 tests) and `TestStripAudioTags` (6 tests) covering dialogue parsing, speaker normalization, audio tag stripping

### Changed (Dual Narrators)

- Narration model switched from `magistral-medium-latest` to `mistral-medium-latest` (user-specified)
- Narration max tokens increased from 200 to 350 to accommodate dialogue format
- Config field `narration_voice_id` replaced with `narration_voice_id_male` and `narration_voice_id_female`

### Added

* **station-loop:** Station Reactive Intelligence (Feature E) — periodic LLM evaluation of field events with reactive coordination
* **station-loop:** `StationLoop` BaseAgent subclass with 20s evaluation interval and event buffering (max 50)
* **station:** `StationAgent.evaluate_situation()` method for periodic LLM-based field assessment
* **models:** `StationContext` extended with `tick`, `mission_status`, `collected_quantity`, `target_quantity`
* **host:** interesting field events (dig, scan, notify, etc.) automatically routed to station loop
* **tests:** 18 new tests (7 station + 11 host integration)
- **Infinite Grid with Viewport & Minimap**: World is no longer a fixed 20×20 grid
  - Chunk-based procedural generation: 16×16 tile chunks generated lazily as agents explore
  - Seeded/deterministic world: each chunk uses `sha256(world_seed:cx:cy)` for consistent generation
  - No boundaries: agents can move to any integer coordinate (negative included)
  - Per-chunk stone placement with origin chunk guaranteed ≥1 core stone
  - Hash-based noise concentration map with core-proximity boosting
  - Explored bounds tracking in `WORLD["bounds"]`
  - **Viewport camera**: 20×20 tile viewport that pans over the infinite world
  - **Auto-follow**: Camera tracks most recently moved agent by default
  - **Drag-to-pan**: Click-drag to manually navigate; double-click to re-enable auto-follow
  - **MiniMap component**: Reduced-scale overview of all explored terrain with viewport rectangle overlay and click-to-navigate
  - 7 new chunk system tests (149 total pass)

- **Entity Follow Selector**: UI controls to select which agent the camera tracks
  - Follow buttons for each mobile agent (rovers, drone) plus "Free" camera mode
  - Buttons styled with agent colors, highlight when active
  - Drag-to-pan automatically switches to free camera mode
  - No auto-follow by default — user chooses which entity to track

- **Battery Safety Return-to-Base**: Critical safety feature ensuring agents never strand
  - `must_return_to_base()` function calculates Manhattan distance to station × move cost + 6% safety margin
  - Battery check is the FIRST priority in both `_update_rover_tasks` and `_update_drone_tasks`
  - Overrides ALL other tasks (exploration, stone collection, scanning) when battery is critical
  - MockRoverAgent and MockDroneAgent enforce return-to-base at agent level (hard override)
  - Task system generates urgent "⚠️ LOW BATTERY" messages for LLM agents

- **Drone Scout Agent**: Aerial drone entity that scouts terrain for precious stone deposits
  - `DroneAgent` (LLM-powered via Mistral) + `MockDroneAgent` (deterministic fallback) in `agent.py`
  - Drone flies 1-6 tiles per move at 1% battery/tile (rovers: 1-3 tiles at 2%)
  - `scan` action: samples concentration map around drone position, returns probability readings
  - `drone_scans` shared memory: rovers read scan results and navigate toward high-concentration hotspots
  - Drone is a pure scout — cannot dig, analyze, or pick up stones
  - Per-agent reveal radius: `ROVER_REVEAL_RADIUS=3`, `DRONE_REVEAL_RADIUS=6`
  - Per-agent max move distance: rovers 3 tiles, drone 6 tiles
  - Purple triangle marker on UI map with larger dashed visibility circle
  - 12 new drone unit tests (142 total pass)

- **GitHub → Discord webhook notifications**: New workflow `.github/workflows/discord-git-notify.yml` sends PR and main-branch push events to Discord channels
  - Separate jobs for PR events (opened/reopened/synchronize/ready_for_review/closed/merged) and pushes to `main`
  - Channel routing via secrets: `DISCORD_WEBHOOK_URL` (default fallback), `DISCORD_WEBHOOK_URL_PR` (optional PR channel), `DISCORD_WEBHOOK_URL_MAIN` (optional main channel)
  - Task plan documented in `tasks/discord-git-integration.md`

- **ElevenLabs AI Narration**: Real-time narration of Mars mission events via ElevenLabs TTS
  - `server/app/narrator.py` — narration engine with event filtering (drama weights 1-3), Mistral LLM text generation ("David Attenborough meets space podcaster" persona), ElevenLabs TTS audio conversion, async event batching, and rate limiting
  - `ui/src/components/NarrationPlayer.vue` — audio player with base64 MP3 playback queue, skip/mute controls, pulsing mic icon, responsive layout
  - WebSocket `narration` event type (`{source: "narrator", type: "narration", payload: {text, audio, format}}`) for real-time audio delivery
  - `/narration/toggle` POST and `/narration/status` GET endpoints for runtime control
  - `ELEVENLABS_API_KEY`, `NARRATION_ENABLED`, `NARRATION_VOICE_ID`, `NARRATION_MIN_INTERVAL_SECONDS` config settings
  - Narrator hooks into simulation lifecycle: starts/stops/resets with simulation, feeds on all broadcast events

- **Upgraded TTS model to ElevenLabs v3**: replaced `eleven_flash_v2_5` with `eleven_v3` for premium voice quality with emotional expression
- Updated narrator system prompt to leverage v3 audio tags (`[whispers]`, `[gasps]`, `[laughs]`, `[sighs]`, `[clears throat]`) for dramatic vocal inflection during mission narration

### Fixed

- **Narration text not appearing in UI**: WebSocket event handler matched narrator events on `event.type` instead of `event.name` — both full narration and streaming chunks share `type: "narration"` but differ on `name` (`"narration"` vs `"narration_chunk"`). Fixed in `useWebSocket.js`
- **Voice toggle out of sync with server**: UI initialized `narrationEnabled` to `true` but server defaults to `false`. Fixed to `false` and added `/api/narration/status` fetch on WebSocket connect to sync toggle state

### Changed

- **Always-on text narration**: Mistral `magistral-medium-latest` generates narrative text regardless of ElevenLabs voice toggle — voice is now opt-in only
- **Streaming narration**: text streams to UI via `narration_chunk` WebSocket events using Mistral `chat.stream()`, with typewriter effect in NarrationPlayer
- Audio emotion tags (`[laughs]`, `[sighs]`, etc.) stripped from display text via `_strip_audio_tags()` — kept only for TTS synthesis
- NarrationPlayer toggle relabeled to "Voice ON" / "Voice OFF" to clarify it controls audio only
- Narration model upgraded from `mistral-small-latest` to `magistral-medium-latest`

### Changed

- **EventLog moved below map**: EventLog now renders below the map in the right column instead of below the sidebar, improving layout readability

### Fixed

- Fixed broken `WorldMap.vue` — undefined variable reference that prevented the map from rendering (`fix/worldmap-broken-ref`)

### Changed

- **Rover visibility radius**: per-rover colored dashed circle on the map shows each rover's visibility radius
- **Rovers start at station**: rovers now spawn at station coordinates `(0,0)` and explore outward from there
- Removed `check_ground` from rover actions
- Removed `charge` from rover actions — charging is now station-only via `charge_rover()`
- Mission success now requires delivering target stones to the station, not just collecting them
- Station agent can charge rovers (new `charge_rover` tool) and auto-charges them on arrival
- Mock rover now digs/picks up stones and navigates back to station when carrying target stone
- Updated rover system prompt with auto-charge and return-to-base instructions
- **Coordinate system flipped to math convention**: north = +Y, south = -Y; (0,0) renders at bottom-left of the map
- **Stone types are now hidden**: all stones spawn as `"unknown"` with a hidden `_true_type`; rovers must `analyze` before digging/picking up
- Stone generation uses **preferential attachment clustering** — core stones cluster together instead of uniform random placement

### Added

* **station-loop:** Station Reactive Intelligence (Feature E) — periodic LLM evaluation of field events with reactive coordination
* **station-loop:** `StationLoop` BaseAgent subclass with 20s evaluation interval and event buffering (max 50)
* **station:** `StationAgent.evaluate_situation()` method for periodic LLM-based field assessment
* **models:** `StationContext` extended with `tick`, `mission_status`, `collected_quantity`, `target_quantity`
* **host:** interesting field events (dig, scan, notify, etc.) automatically routed to station loop
* **tests:** 18 new tests (7 station + 11 host integration)
- **`analyze` action**: reveals a stone's true type (core/basalt), costs 3% battery; dig/pickup now require prior analysis
- **`analyze_ground` action**: reads ground concentration at current tile (0.0–1.0 indicating proximity to core deposits), costs 3% battery; readings stored in agent memory
- **Concentration map**: computed from core positions using Gaussian falloff (`exp(-d²/σ²)`, σ=4.0), serialized in snapshots for UI access
- Dynamic **task priority system** in `update_tasks()`: return-to-station > analyze > dig > pickup > navigate-to-stone > explore
- `_direction_hint()` helper for human-readable navigation hints in agent context
- GitHub Actions CI pipeline (`.github/workflows/ci.yml`) with 5 jobs: change detection, server lint (ruff), server test (rut + SurrealDB), UI lint + build (eslint + vite), and Docker build verification
- ESLint 9 flat config for Vue 3 frontend (`ui/eslint.config.js`)
- `unknown` stone color (`#4a4a6a`) in UI constants and AgentDetailModal CSS
- Snapshot filtering: `_true_type` stripped from broadcast to prevent UI leaking hidden info

### Fixed

- `rut` test runner dependency changed from broken local path to git source (`server/pyproject.toml`)
- SurrealDB readiness check in test conftest hardened with retry loop instead of fragile `time.sleep(1)` (`server/tests/conftest.py`)
- Ruff formatting applied to `server/app/agent.py` and `server/app/world.py`
- Removed unused `props` variable assignment in `MissionBar.vue` to fix ESLint `no-unused-vars` error
- Added Release Please annotation to FastAPI app version in `server/app/main.py` to prevent version drift across releases
- Updated rover task planning in `server/app/world.py` to keep revealed-tile filtering lint-clean in CI
- Applied Ruff formatting to `server/app/world.py` and `server/tests/test_world.py` to keep merge-ref CI formatting checks green
- Fixed Release Please TOML version path in `release-please-config.json` so `server/pyproject.toml` bumps on every release
- Made agent turn interval configurable via `agent_turn_interval_seconds` (mock, 0.5s) and `llm_turn_interval_seconds` (LLM, 3.0s) to prevent Mistral API rate-limit pressure
- Added RoverAgent runtime fallback so `rover-mistral` keeps moving with deterministic mock logic when LLM calls fail or return no tool action
- Narrowed RoverAgent exception handling from broad `Exception` to `(SDKError, ConnectionError, TimeoutError, RuntimeError)` so programming bugs surface instead of being silently swallowed
- Cached mock fallback instance in RoverAgent instead of creating a new `MockRoverAgent` per failure
- Added logging for hallucinated tool names and LLM thinking when no valid tool action is returned
- Installed GitHub Spec Kit (`github/spec-kit`) with shorthand aliases: `/c`, `/s`, `/p`, `/t`, `/i`, `/t2i`
- ESLint config now ignores `dist/` and `node_modules/` build output
- Auto-fixed 148 Vue template formatting warnings (attribute line breaks, indentation)
- Added `default` or `required` to all Vue component props to resolve 18 `vue/require-default-prop` warnings — zero ESLint warnings remain
