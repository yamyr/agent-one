# CI Fix Plan — Get CI Back to Green

## Status: COMPLETE

## Root Cause Analysis

### Timeline
- **02:52 UTC** — Last green CI on main (commit `6b6dd9c`)
- **02:58 UTC** — First red CI on main (commit `937e572` — HuggingFace PR #182)
- **03:00 UTC** — Still broken (commit `ba97421` — release 0.4.0)
- **03:05 UTC** — Still broken (commit `8323908` — test assertions PR #142)

### Who Broke It
PR #182 (`feat: add HuggingFace Inference API`) introduced:
1. A duplicate code block in `narrator.py:_generate_text_streaming()` with a variable scoping bug
2. An import for a non-existent module (`training_logger`) in `main.py`
3. Unformatted code in 5 files

### Three Distinct Failures

| # | Error | Root Cause | Fix Applied |
|---|-------|-----------|-------------|
| 1 | `ModuleNotFoundError: No module named 'app.training_logger'` | `main.py` imported `training_logger` (doesn't exist) instead of `training.collector` (exists) | Replaced import with correct `from .training import collector` |
| 2 | `UnboundLocalError: cannot access local variable 'client'` in `narrator.py:633` | Dead duplicate code block before `full_text=""`, and missing `client = self._get_mistral()` in else branch | Removed dead code, added proper client initialization in both branches |
| 3 | `ruff format --check` fails on 5 files | Code merged without running formatter | Ran `ruff format app/ tests/` |
| 3b | Test mock mismatch in `test_huggingface.py` | Test mocked `client.chat.stream` but code uses `client.chat.stream_async` | Updated test to use `AsyncMock` with `stream_async` |

## Prevention Measures

### Immediate
- [x] Fix all three CI failures
- [x] Verify 467/467 tests pass
- [x] Verify `ruff check` + `ruff format --check` pass

### Going Forward
1. **Enforce branch protection on main** — Require CI to pass before merge
2. **Add `ruff format` as pre-commit hook** — Prevents unformatted code from being committed
3. **Never merge PRs with cross-module dependencies** without verifying all imported modules exist
4. **Test locally before pushing** — `uv run rut tests/ && uv run ruff format --check app/ tests/`
5. **Review narrator.py carefully** — The HuggingFace integration introduced duplicate code blocks; future PRs adding provider alternatives should be reviewed for proper if/else structure

## Files Changed
- `server/app/main.py` — Fixed `training_logger` import → `training.collector`
- `server/app/narrator.py` — Removed dead code, fixed `client` scoping in streaming method
- `server/app/agent.py` — `ruff format` applied
- `server/app/station.py` — `ruff format` applied
- `server/tests/test_health.py` — `ruff format` applied
- `server/tests/test_huggingface.py` — Fixed mock for `stream_async` with `AsyncMock`
