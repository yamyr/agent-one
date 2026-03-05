# Quickstart: Running Expanded Tests

## Run all tests
```bash
cd server && uv run pytest tests/ -v
```

## Run only the new test file
```bash
cd server && uv run pytest tests/test_coverage_expansion.py -v
```

## Run a specific test class
```bash
cd server && uv run pytest tests/test_coverage_expansion.py::TestCollectGas -v
```

## Format check
```bash
cd server && uv run ruff format app/ tests/ && uv run ruff check --fix app/ tests/
```
