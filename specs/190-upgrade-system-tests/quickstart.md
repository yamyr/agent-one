# Quickstart: Upgrade System Tests

## Run the new tests

```bash
cd server
uv run pytest tests/test_upgrade_contract.py -x -q
```

## Run all tests (including existing upgrade tests)

```bash
cd server
uv run pytest tests/ -x -q
```

## Format and lint before committing

```bash
cd server && uv run ruff format app/ tests/ && uv run ruff check --fix app/ tests/
```

## File locations

- New test file: `server/tests/test_upgrade_contract.py`
- Production code under test: `server/app/world.py`
- Existing upgrade tests: `server/tests/test_upgrades.py`, `server/tests/test_coverage_expansion.py`, `server/tests/test_resources.py`
