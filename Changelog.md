# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0](https://github.com/mhack-agent-one/agent-one/compare/v0.1.0...v0.2.0) (2026-02-28)


### Features

* add event-driven station agent that assigns missions to rovers and reacts to field ([be23868](https://github.com/mhack-agent-one/agent-one/commit/be238685b05c7d917da75843845077fc7286cb86))
* add GitHub Actions CI/CD pipeline with lint, test, and build verification ([#2](https://github.com/mhack-agent-one/agent-one/issues/2)) ([651f13c](https://github.com/mhack-agent-one/agent-one/commit/651f13c759ac1789eee72a5df7626e0d7004071f))
* add rover dig/pickup tools, agent short-term memory, richer LLM context, and system ([d153f31](https://github.com/mhack-agent-one/agent-one/commit/d153f312fca2cb927d0e74b38fbef481d5ef70e3))
* add rover dig/pickup/charge actions, fog-of-war reveal, mission tracking, and UI ([a9201cb](https://github.com/mhack-agent-one/agent-one/commit/a9201cb43367babcc87ad60c1d9bafcbec0bb6fb))
* add stones, rover visited memory, auto ground-check, and sync docs with world state ([dd7021e](https://github.com/mhack-agent-one/agent-one/commit/dd7021e327f913a379a4a3e94216884d805b9ea8))
* add task system, coordinate hints, pause/resume, and 2s agent loop for reliable rover ([51c821e](https://github.com/mhack-agent-one/agent-one/commit/51c821e297969fe802abe9157d21588f0374fad5))
* **agent:** upgrade RoverAgent to magistral-medium and convert MockRoverAgent to LLM-powered ([#3](https://github.com/mhack-agent-one/agent-one/issues/3)) ([2e8a262](https://github.com/mhack-agent-one/agent-one/commit/2e8a262a4da02acf75e42050916d4fcfd00c0adb))
* **ci:** add automated release versioning and management ([#6](https://github.com/mhack-agent-one/agent-one/issues/6)) ([9cb1606](https://github.com/mhack-agent-one/agent-one/commit/9cb16062304977de970c22e2d2eaf9a02b3f2f71))
* multi-tile movement, larger fog radius, guaranteed core stones, and visible stone ([6e63457](https://github.com/mhack-agent-one/agent-one/commit/6e6345750b28bcc3f921521e2b22d418d72e38be))
* simplify rover actions — station-only charging and delivery-based success ([77526be](https://github.com/mhack-agent-one/agent-one/commit/77526be3b64e22001b6a9b3a43bb9d2898b5a61d))
* simplify rover actions — station-only charging, auto-scan, and delivery-based mission success ([89fab68](https://github.com/mhack-agent-one/agent-one/commit/89fab6813350b3fafcd77e075c500d0e95009c2a))


### Bug Fixes

* **release:** map pyproject version path for release-please ([#8](https://github.com/mhack-agent-one/agent-one/issues/8)) ([cd291e6](https://github.com/mhack-agent-one/agent-one/commit/cd291e6a8a71d9099b803a45446a5f6df2bb4cec))
* rover tasks only reference stones discovered through exploration, not pre-revealed at ([378df08](https://github.com/mhack-agent-one/agent-one/commit/378df08cbe63e9a835563251f7c67e6a4ccaad0f))

## [Unreleased]

### Changed

- Removed `check_ground` from rover actions — ground is now auto-scanned after every move
- Removed `charge` from rover actions — charging is now station-only via `charge_rover()`
- Mission success now requires delivering target stones to the station, not just collecting them
- Station agent can charge rovers (new `charge_rover` tool) and auto-charges them on arrival
- Mock rover now digs/picks up stones and navigates back to station when carrying target stone
- Updated rover system prompt with auto-charge and return-to-base instructions

### Added

- GitHub Actions CI pipeline (`.github/workflows/ci.yml`) with 5 jobs: change detection, server lint (ruff), server test (rut + SurrealDB), UI lint + build (eslint + vite), and Docker build verification
- ESLint 9 flat config for Vue 3 frontend (`ui/eslint.config.js`)
- RoverAgent default model upgraded from `mistral-small-latest` to `magistral-medium-latest` for improved reasoning
- GitHub Actions release workflow (`.github/workflows/release.yml`) using Release Please for automated versioning, release PRs, and GitHub Releases on `main`
- Release Please config (`release-please-config.json`, `.release-please-manifest.json`, `version.txt`) to keep version updates consistent across API and UI metadata

### Changed

- Renamed mock rover agent ID from `rover-mock` to `randy-rover` across all files (world state, agent code, tests, station prompts, UI constants)

### Fixed

- `rut` test runner dependency changed from broken local path to git source (`server/pyproject.toml`)
- SurrealDB readiness check in test conftest hardened with retry loop instead of fragile `time.sleep(1)` (`server/tests/conftest.py`)
- Ruff formatting applied to `server/app/agent.py` and `server/app/world.py`
- Removed unused `props` variable assignment in `MissionBar.vue` to fix ESLint `no-unused-vars` error
- Added Release Please annotation to FastAPI app version in `server/app/main.py` to prevent version drift across releases
- Updated rover task planning in `server/app/world.py` to keep revealed-tile filtering lint-clean in CI
- Applied Ruff formatting to `server/app/world.py` and `server/tests/test_world.py` to keep merge-ref CI formatting checks green
- Fixed Release Please TOML version path in `release-please-config.json` so `server/pyproject.toml` bumps on every release
