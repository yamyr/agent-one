# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
