# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- GitHub Actions CI pipeline (`.github/workflows/ci.yml`) with 5 jobs: change detection, server lint (ruff), server test (rut + SurrealDB), UI lint + build (eslint + vite), and Docker build verification
- ESLint 9 flat config for Vue 3 frontend (`ui/eslint.config.js`)
- RoverAgent default model upgraded from `mistral-small-latest` to `magistral-medium-latest` for improved reasoning
- MockRoverAgent converted from random direction picker to full LLM-powered agent using `mistral-small-latest` with 8 randomized personality prompts (daring scout, cautious geologist, speed-runner, etc.)

### Changed

- MockRoverAgent now builds full context (position, battery, inventory, visible stones, station distance) and uses Mistral API for decision-making instead of random.choice

### Fixed

- `rut` test runner dependency changed from broken local path to git source (`server/pyproject.toml`)
- SurrealDB readiness check in test conftest hardened with retry loop instead of fragile `time.sleep(1)` (`server/tests/conftest.py`)
- Ruff formatting applied to `server/app/agent.py` and `server/app/world.py`
