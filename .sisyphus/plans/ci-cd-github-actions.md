# CI/CD GitHub Actions Pipeline

## TL;DR

> **Quick Summary**: Set up comprehensive GitHub Actions CI/CD for the agent-one monorepo — fixing 3 prerequisite blockers (rut dependency, ESLint config, conftest flakiness), then creating a single CI workflow with parallel jobs for server lint, server test (with SurrealDB), UI lint+build, and Docker build verification.
> 
> **Deliverables**:
> - Fixed `server/pyproject.toml` and `server/uv.lock` (rut dependency from git, not local path)
> - New `ui/eslint.config.js` (flat config for ESLint 9)
> - Hardened `server/tests/conftest.py` (proper SurrealDB readiness check)
> - New `.github/workflows/ci.yml` (comprehensive CI pipeline)
> - Updated `Changelog.md` documenting all changes
> 
> **Estimated Effort**: Medium (5-8 tasks)
> **Parallel Execution**: YES — 3 waves
> **Critical Path**: Task 1 (fix rut) → Task 5 (server-test job) → Task 7 (verify full pipeline)

---

## Context

### Original Request
User asked to "analyse and architect CI CD for our Github Actions for this repo" — a greenfield CI/CD setup for a Python+Vue monorepo.

### Interview Summary
**Key Findings**:
- No existing CI/CD — `.github/workflows/` directory doesn't exist
- Python backend uses `uv` package manager, `rut` test runner, SurrealDB
- Vue frontend uses Vite 7, ESLint 9, no TypeScript, no tests
- Deployed to Railway via multi-stage Dockerfile
- CLAUDE.md mandates feature branches → PR → merge to main workflow

**Research Findings**:
- `astral-sh/setup-uv@v7` with `enable-cache: true` is production standard (used by pydantic, microsoft/autogen)
- SurrealDB in CI: `docker run -d surrealdb/surrealdb:latest start --user root --pass root memory` or `surrealdb/setup-surreal@v2` action
- `dorny/paths-filter@v3` for monorepo change detection (better than `paths:` trigger filter)
- `rut` is `schettino72/rut` on GitHub — modern unittest runner

### Metis Review
**Identified Blockers** (addressed in plan):
1. `rut` dependency points to LOCAL PATH (`/home/eduardo/work/rut`) — `uv sync` WILL FAIL in CI → Fixed: change to git source
2. No `eslint.config.js` — ESLint 9 requires flat config → Fixed: create minimal config
3. SurrealDB readiness uses `time.sleep(1)` — fragile on cold CI runners → Fixed: use `is_port_in_use()` loop (function already exists in conftest)

**Metis also confirmed**:
- Tests do NOT call Mistral API — no secrets needed for CI
- `conftest.py` spawns its own SurrealDB subprocess — CI needs binary on PATH, not a running service
- Railway likely auto-deploys from main — no deploy job needed in CI
- `CaseWithDB` class exists in conftest but is unused by any current test

---

## Work Objectives

### Core Objective
Create a production-quality CI pipeline that gates PRs with automated lint, test, build, and Docker verification — preventing broken code from reaching main.

### Concrete Deliverables
- `server/pyproject.toml` — `rut` source changed from local path to git URL
- `server/uv.lock` — regenerated with resolvable dependencies
- `ui/eslint.config.js` — ESLint 9 flat config with Vue plugin
- `server/tests/conftest.py` — hardened SurrealDB readiness check
- `.github/workflows/ci.yml` — complete CI workflow
- `Changelog.md` — documenting all changes

### Definition of Done
- [ ] `uv sync --frozen --all-groups` succeeds in `server/` (exit 0)
- [ ] `uv run ruff check app/ tests/` passes (exit 0)
- [ ] `uv run rut tests/` runs all 8 tests successfully
- [ ] `npx eslint .` in `ui/` produces meaningful output (not "no config found")
- [ ] `npm run build` in `ui/` succeeds (exit 0, `dist/` created)
- [ ] `docker build -t agent-one-ci-test .` succeeds (exit 0)
- [ ] GitHub Actions workflow triggers on push/PR and all jobs pass
- [ ] PR to main shows green status checks

### Must Have
- Server lint job (ruff check + ruff format --check)
- Server test job (rut tests/ with SurrealDB binary)
- UI lint + build job (eslint + vite build)
- Docker build verification job
- Path-based change detection (only run relevant jobs)
- Caching for uv and npm dependencies
- Concurrency control (cancel in-progress PR runs)

### Must NOT Have (Guardrails)
- NO deployment step — Railway handles deploy via GitHub integration
- NO `MISTRAL_API_KEY` secret — tests don't call Mistral
- NO frontend test step — no test framework or tests exist
- NO changes to `railway.toml`, `Dockerfile`, or runtime app code (`server/app/*.py`)
- NO `pull_request_target` trigger (security risk)
- NO `--fix` flag on lint in CI — lint must CHECK, not auto-fix
- NO Python version matrix — single version (3.12) matches pyproject.toml requirement

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (rut + unittest)
- **Automated tests**: YES (tests-after — verify existing tests pass in CI context)
- **Framework**: rut (unittest runner)
- **No TDD**: This is infra/config work, not feature development

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Config changes**: Use Bash — run commands, assert exit codes and output
- **Workflow file**: Use Bash — validate YAML syntax, push to branch, verify GitHub Actions trigger
- **Full pipeline**: Push feature branch, verify all status checks pass via `gh` CLI

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — fix prerequisites, MAX PARALLEL):
├── Task 1: Fix rut dependency source + regenerate lockfile [quick]
├── Task 2: Create ESLint flat config for UI [quick]
└── Task 3: Harden conftest.py SurrealDB readiness [quick]

Wave 2 (After Wave 1 — create CI workflow):
└── Task 4: Create .github/workflows/ci.yml [deep]

Wave 3 (After Wave 2 — verify + document):
├── Task 5: End-to-end CI pipeline verification [unspecified-high]
└── Task 6: Create Changelog.md documenting all changes [quick]

Wave FINAL (After ALL tasks — independent review):
├── Task F1: Plan compliance audit [oracle]
├── Task F2: Code quality review [unspecified-high]
└── Task F3: Scope fidelity check [deep]
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 4, 5 | 1 |
| 2 | — | 4, 5 | 1 |
| 3 | — | 4, 5 | 1 |
| 4 | 1, 2, 3 | 5, 6 | 2 |
| 5 | 4 | F1-F3 | 3 |
| 6 | 4 | F1-F3 | 3 |
| F1 | 5, 6 | — | FINAL |
| F2 | 5, 6 | — | FINAL |
| F3 | 5, 6 | — | FINAL |

### Agent Dispatch Summary

- **Wave 1**: **3 tasks** — T1 `quick`, T2 `quick`, T3 `quick`
- **Wave 2**: **1 task** — T4 `deep`
- **Wave 3**: **2 tasks** — T5 `unspecified-high`, T6 `quick`
- **FINAL**: **3 tasks** — F1 `oracle`, F2 `unspecified-high`, F3 `deep`

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.
> **A task WITHOUT QA Scenarios is INCOMPLETE. No exceptions.**

- [x] 1. Fix `rut` dependency source in pyproject.toml + regenerate lockfile

  **What to do**:
  - Edit `server/pyproject.toml` line 35: change `rut = { path = "/home/eduardo/work/rut", editable = true }` to `rut = { git = "https://github.com/schettino72/rut", branch = "main" }`
  - Run `uv lock` in `server/` to regenerate `server/uv.lock` with resolvable dependencies
  - Verify `uv sync --frozen --all-groups` succeeds (exit 0)
  - If `import-deps` (transitive dep of rut) also has a local path issue, resolve it similarly
  - Run `uv run rut tests/` to verify the new rut version works with existing tests

  **Must NOT do**:
  - Do NOT change any test files
  - Do NOT modify runtime app code
  - Do NOT add new dependencies beyond fixing the source

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file edit + command execution, straightforward fix
  - **Skills**: []
    - No special skills needed — file edit + shell commands

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Task 4 (CI workflow needs working deps)
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `server/pyproject.toml:34-35` — Current `[tool.uv.sources]` section with local path that needs changing
  - `server/pyproject.toml:28-32` — `[dependency-groups]` dev group where rut is listed

  **API/Type References**:
  - uv documentation on git sources: `uv` supports `{ git = "url", branch = "name" }` syntax

  **External References**:
  - `schettino72/rut` on GitHub — the rut test runner source repo
  - uv docs on dependency sources: https://docs.astral.sh/uv/concepts/dependencies/#dependency-sources

  **WHY Each Reference Matters**:
  - `pyproject.toml:34-35` is the EXACT line to change — the local path `/home/eduardo/work/rut` is what breaks CI
  - The rut GitHub repo is the replacement source — branch `main` has the latest dev version

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: uv sync succeeds with git-sourced rut
    Tool: Bash
    Preconditions: server/pyproject.toml has been edited with git source
    Steps:
      1. cd server && uv sync --frozen --all-groups
      2. Assert exit code is 0
      3. Assert no "path does not exist" errors in output
    Expected Result: All dependencies resolve, .venv created with rut installed
    Failure Indicators: Exit code non-zero, error mentioning "/home/eduardo" or "path"
    Evidence: .sisyphus/evidence/task-1-uv-sync.txt

  Scenario: rut tests still pass after dependency change
    Tool: Bash
    Preconditions: uv sync succeeded, SurrealDB binary available on PATH
    Steps:
      1. cd server && uv run rut tests/
      2. Assert exit code is 0
      3. Assert output shows 8 tests passing
    Expected Result: All existing tests pass with git-sourced rut
    Failure Indicators: Import errors, test failures, rut not found
    Evidence: .sisyphus/evidence/task-1-rut-tests.txt
  ```

  **Commit**: YES
  - Message: `fix(server): switch rut dependency from local path to git source`
  - Files: `server/pyproject.toml`, `server/uv.lock`
  - Pre-commit: `cd server && uv sync --frozen --all-groups`

- [x] 2. Create ESLint flat config for Vue 3 frontend

  **What to do**:
  - Create `ui/eslint.config.js` with ESLint 9 flat config format
  - Include `@eslint/js` recommended rules and `eslint-plugin-vue` flat/recommended rules
  - Content:
    ```js
    import js from '@eslint/js'
    import pluginVue from 'eslint-plugin-vue'
    
    export default [
      js.configs.recommended,
      ...pluginVue.configs['flat/recommended'],
    ]
    ```
  - Run `npx eslint .` in `ui/` to verify config is loaded and produces meaningful output
  - If there are lint errors, note them but do NOT auto-fix (lint errors are expected in existing code)

  **Must NOT do**:
  - Do NOT run `eslint --fix` (don't change existing source code)
  - Do NOT add Prettier or other formatting tools
  - Do NOT add TypeScript-related ESLint config (project uses plain JS)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file creation with known content
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Task 4 (CI workflow needs working lint)
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `ui/package.json:19-24` — ESLint 9.31 and eslint-plugin-vue 10.3 are already installed as devDependencies
  - `ui/package.json:13` — `"lint": "eslint . --fix"` script exists (CI will run without --fix)

  **External References**:
  - ESLint 9 flat config docs: https://eslint.org/docs/latest/use/configure/configuration-files
  - eslint-plugin-vue flat config: https://eslint.vuejs.org/user-guide/#usage

  **WHY Each Reference Matters**:
  - `package.json` devDeps confirm the exact versions installed — config must match ESLint 9 flat format
  - The lint script uses `--fix` which is fine for dev but CI must NOT auto-fix

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: ESLint config is loaded and produces meaningful output
    Tool: Bash
    Preconditions: ui/eslint.config.js has been created
    Steps:
      1. cd ui && npx eslint . 2>&1 || true
      2. Assert output does NOT contain "no config" or "Could not find config"
      3. Assert output shows either "no problems" or specific lint rule violations
    Expected Result: ESLint loads config, applies Vue rules, reports findings
    Failure Indicators: "Could not find config", ESLint crash, "Parsing error" on .vue files
    Evidence: .sisyphus/evidence/task-2-eslint-output.txt

  Scenario: ESLint exits successfully on clean code (or with expected warnings)
    Tool: Bash
    Preconditions: eslint.config.js exists
    Steps:
      1. cd ui && npx eslint src/main.js 2>&1 || true
      2. Assert output shows rule violations OR clean pass (both acceptable)
      3. Assert ESLint did NOT crash or fail to parse
    Expected Result: Config properly processes .js files
    Evidence: .sisyphus/evidence/task-2-eslint-js.txt
  ```

  **Commit**: YES
  - Message: `feat(ui): add ESLint flat config for Vue 3`
  - Files: `ui/eslint.config.js`

- [x] 3. Harden SurrealDB readiness check in test conftest

  **What to do**:
  - Edit `server/tests/conftest.py`: replace `time.sleep(1)` (line 40) with a retry loop using the existing `is_port_in_use(_test_port)` function
  - Pattern:
    ```python
    # Replace time.sleep(1) with readiness loop
    for _ in range(30):  # 30 attempts × 0.2s = 6s max
        if is_port_in_use(_test_port):
            break
        time.sleep(0.2)
    else:
        raise RuntimeError(f"SurrealDB failed to start on port {_test_port}")
    ```
  - Run `uv run rut tests/` to verify tests still pass with the new readiness check

  **Must NOT do**:
  - Do NOT change the SurrealDB subprocess command or port
  - Do NOT modify any test case logic
  - Do NOT remove the `is_port_in_use` function (it's now being used)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small surgical edit to one function in one file
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Task 4 (CI needs reliable test setup)
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `server/tests/conftest.py:15-21` — `is_port_in_use()` function that already exists but is NEVER CALLED
  - `server/tests/conftest.py:24-41` — `rut_session_setup()` function with the `time.sleep(1)` on line 40 that needs replacing
  - `server/tests/conftest.py:12` — `_test_port = 8009` variable used by both functions

  **WHY Each Reference Matters**:
  - `is_port_in_use()` is the key function — it's already written but unused. We're wiring it into the startup flow
  - `rut_session_setup()` is where the fragile `time.sleep(1)` lives — this is the exact function to modify
  - Port 8009 is hardcoded and must remain consistent between the subprocess start and readiness check

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Tests pass with hardened readiness check
    Tool: Bash
    Preconditions: conftest.py has been edited with retry loop
    Steps:
      1. cd server && uv run rut tests/
      2. Assert exit code is 0
      3. Assert all 8 tests pass
    Expected Result: SurrealDB starts reliably, all tests pass
    Failure Indicators: "SurrealDB failed to start" RuntimeError, test timeouts
    Evidence: .sisyphus/evidence/task-3-conftest-tests.txt

  Scenario: Readiness check properly waits (not just sleep)
    Tool: Bash
    Preconditions: conftest.py edited
    Steps:
      1. grep -n "is_port_in_use" server/tests/conftest.py
      2. Assert is_port_in_use is called within rut_session_setup
      3. grep -n "time.sleep(1)" server/tests/conftest.py
      4. Assert the bare time.sleep(1) is NO LONGER present
    Expected Result: Old sleep removed, port check loop in place
    Evidence: .sisyphus/evidence/task-3-conftest-diff.txt
  ```

  **Commit**: YES
  - Message: `fix(server): harden SurrealDB readiness check in test conftest`
  - Files: `server/tests/conftest.py`

---

- [x] 4. Create `.github/workflows/ci.yml` — comprehensive CI pipeline

  **What to do**:
  - Create `.github/workflows/` directory
  - Create `.github/workflows/ci.yml` with the following structure:
    - **Trigger**: `push` (all branches) and `pull_request` (to main)
    - **Concurrency**: `group: ci-${{ github.ref }}`, `cancel-in-progress: true` for PRs
    - **Change detection job**: Uses `dorny/paths-filter@v3` to detect which directories changed
    - **Job: `server-lint`** (runs if `server/**` changed):
      - `ubuntu-latest`
      - `astral-sh/setup-uv@v7` with `enable-cache: true`, `python-version: "3.12"`
      - `uv sync --frozen --all-groups`
      - `uv run ruff check app/ tests/`
      - `uv run ruff format --check app/ tests/`
      - Working directory: `server/`
    - **Job: `server-test`** (runs if `server/**` changed):
      - `ubuntu-latest`
      - `astral-sh/setup-uv@v7` with `enable-cache: true`, `python-version: "3.12"`
      - Install SurrealDB: `curl -sSf https://install.surrealdb.com | sh` (binary needed on PATH for conftest subprocess)
      - `uv sync --frozen --all-groups`
      - `uv run rut tests/`
      - Working directory: `server/`
    - **Job: `ui-lint-build`** (runs if `ui/**` changed):
      - `ubuntu-latest`
      - `actions/setup-node@v4` with `node-version: 22`, `cache: npm`, `cache-dependency-path: ui/package-lock.json`
      - `npm ci`
      - `npx eslint .` (NO --fix flag)
      - `npm run build`
      - Working directory: `ui/`
    - **Job: `docker-build`** (runs if `server/**`, `ui/**`, or `Dockerfile` changed):
      - `ubuntu-latest`
      - `docker build -t agent-one-ci .` (verify image builds, don't push)

  **Critical implementation details**:
  - Use `defaults.run.working-directory` per job where appropriate
  - For `dorny/paths-filter`, use it in a dedicated `changes` job, then reference outputs via `needs.changes.outputs`
  - SurrealDB install: the `curl` installer puts the binary in `~/.surrealdb/`, so add to PATH: `echo "$HOME/.surrealdb" >> $GITHUB_PATH`
  - Do NOT use `surrealdb/setup-surreal@v2` to start a server — conftest manages its own SurrealDB subprocess
  - All lint commands must NOT auto-fix (no `--fix` flag)
  - Each job should have appropriate `if: needs.changes.outputs.server == 'true'` conditionals

  **Must NOT do**:
  - Do NOT add deployment steps
  - Do NOT add `MISTRAL_API_KEY` or any secrets
  - Do NOT add frontend test steps
  - Do NOT use `pull_request_target` trigger

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex YAML authoring with multiple jobs, dependencies, conditionals, and caching config requiring careful integration
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: Not needed — no browser testing in CI workflow
    - `git-master`: Not needed — file creation, not git operations

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (sequential after Wave 1)
  - **Blocks**: Task 5 (verification needs workflow to exist)
  - **Blocked By**: Tasks 1, 2, 3 (all prerequisites must be complete)

  **References**:

  **Pattern References**:
  - `Dockerfile:1-26` — Multi-stage build that CI Docker build job must replicate
  - `server/pyproject.toml:1-35` — Python version, deps, ruff config (line-length 100)
  - `ui/package.json:1-25` — Node version engine (>=22.12.0), scripts, deps
  - `server/tests/conftest.py:31-38` — SurrealDB subprocess spawn (needs `surreal` binary on PATH)
  - `server/run:2` — uvicorn command pattern (for reference, not used in CI)

  **External References (Production patterns to follow)**:
  - `microsoft/autogen/.github/workflows/checks.yml` — `astral-sh/setup-uv@v5` with `enable-cache: true`
  - `pydantic/pydantic/.github/workflows/ci.yml` — `astral-sh/setup-uv@v7` with `python-version` matrix
  - `surrealdb/surrealdb.go/.github/workflows/test.yml` — SurrealDB Docker run with health check loop
  - `dorny/paths-filter` GitHub repo — monorepo change detection patterns
  - `langflow-ai/langflow/.github/workflows/release.yml` — `cache-dependency-glob: "uv.lock"` pattern

  **WHY Each Reference Matters**:
  - Dockerfile tells us the exact base images and build steps CI must also validate
  - pyproject.toml defines Python version constraint that `setup-uv` must match
  - conftest.py shows SurrealDB is spawned as subprocess, so CI needs binary install, NOT running service
  - Production workflow examples provide tested, working YAML patterns to adapt

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Workflow YAML is valid syntax
    Tool: Bash
    Preconditions: .github/workflows/ci.yml created
    Steps:
      1. python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
      2. Assert exit code 0 (valid YAML)
      3. Verify top-level keys: 'name', 'on', 'concurrency', 'jobs'
      4. Verify jobs include: 'changes', 'server-lint', 'server-test', 'ui-lint-build', 'docker-build'
    Expected Result: Valid YAML with all required jobs
    Failure Indicators: YAML parse error, missing jobs
    Evidence: .sisyphus/evidence/task-4-yaml-valid.txt

  Scenario: Workflow has correct triggers and concurrency
    Tool: Bash
    Preconditions: .github/workflows/ci.yml created
    Steps:
      1. grep -A5 '^on:' .github/workflows/ci.yml
      2. Assert 'push' and 'pull_request' triggers present
      3. grep -A3 'concurrency:' .github/workflows/ci.yml
      4. Assert cancel-in-progress is configured
    Expected Result: Triggers on push+PR, cancels stale PR runs
    Evidence: .sisyphus/evidence/task-4-triggers.txt

  Scenario: No forbidden patterns in workflow
    Tool: Bash
    Preconditions: .github/workflows/ci.yml created
    Steps:
      1. grep -i 'MISTRAL_API_KEY' .github/workflows/ci.yml || echo 'CLEAN'
      2. Assert output is 'CLEAN' (no API key references)
      3. grep 'pull_request_target' .github/workflows/ci.yml || echo 'CLEAN'
      4. Assert output is 'CLEAN'
      5. grep '\-\-fix' .github/workflows/ci.yml || echo 'CLEAN'
      6. Assert output is 'CLEAN' (no auto-fix in CI)
    Expected Result: No forbidden patterns found
    Evidence: .sisyphus/evidence/task-4-forbidden-patterns.txt
  ```

  **Commit**: YES
  - Message: `feat(ci): add GitHub Actions CI pipeline with lint, test, build verification`
  - Files: `.github/workflows/ci.yml`
  - Pre-commit: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`

- [x] 5. End-to-end CI pipeline verification

  **What to do**:
  - Create a feature branch `ci/github-actions-pipeline`
  - Add all changes from Tasks 1-4 to the branch
  - Push the branch to remote
  - Verify GitHub Actions triggers and all jobs run
  - Monitor each job's status via `gh run watch` or `gh run view`
  - If any job fails, diagnose and fix the issue
  - Create a PR to main once all checks pass
  - Verify PR shows green status checks

  **Must NOT do**:
  - Do NOT merge the PR (leave for user)
  - Do NOT add any new features or fixes beyond CI pipeline

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires git operations, GitHub CLI interaction, monitoring CI runs, diagnosing failures
  - **Skills**: [`git-master`]
    - `git-master`: Branch creation, committing, pushing, PR creation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 6)
  - **Blocks**: Final verification wave
  - **Blocked By**: Task 4 (workflow must exist)

  **References**:

  **Pattern References**:
  - `.github/workflows/ci.yml` — The workflow file created in Task 4
  - `CLAUDE.md` — "create a new feature branch and do the changes in this dedicated feature branch"

  **WHY Each Reference Matters**:
  - The workflow file is what we're verifying works end-to-end
  - CLAUDE.md mandates the branch→PR→merge workflow we must follow

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: GitHub Actions triggers on push
    Tool: Bash
    Preconditions: Feature branch pushed to remote with all Task 1-4 changes
    Steps:
      1. gh run list --branch ci/github-actions-pipeline --workflow ci.yml --limit 1
      2. Assert a workflow run exists
      3. gh run view <run-id> --log 2>&1 | head -50
      4. Assert all jobs completed (no 'in_progress' status)
    Expected Result: CI workflow triggered and all jobs completed
    Failure Indicators: No workflow run, jobs stuck or failed
    Evidence: .sisyphus/evidence/task-5-gh-run-list.txt

  Scenario: All CI jobs pass
    Tool: Bash
    Preconditions: CI run completed
    Steps:
      1. gh run view <run-id> --json conclusion -q '.conclusion'
      2. Assert conclusion is 'success'
      3. gh run view <run-id> --json jobs -q '.jobs[].name' to list all job names
      4. Assert jobs include server-lint, server-test, ui-lint-build, docker-build
    Expected Result: All jobs pass with 'success' conclusion
    Failure Indicators: Any job with 'failure' conclusion
    Evidence: .sisyphus/evidence/task-5-ci-results.txt

  Scenario: PR shows green status checks
    Tool: Bash
    Preconditions: PR created to main
    Steps:
      1. gh pr create --base main --head ci/github-actions-pipeline --title 'feat(ci): add GitHub Actions CI pipeline' --body 'Adds CI pipeline with server lint, server test, UI lint+build, and Docker build verification.'
      2. gh pr checks ci/github-actions-pipeline
      3. Assert all checks show 'pass' status
    Expected Result: PR has all green status checks
    Evidence: .sisyphus/evidence/task-5-pr-checks.txt
  ```

  **Commit**: NO (commits handled in Tasks 1-4)

- [x] 6. Create Changelog.md documenting all CI/CD changes

  **What to do**:
  - Create `Changelog.md` at project root (per CLAUDE.md requirement: "update the Changelog.md file")
  - Document all changes made in this plan:
    - Fixed rut dependency source
    - Added ESLint flat config
    - Hardened conftest readiness check
    - Added GitHub Actions CI pipeline
  - Use Keep a Changelog format (https://keepachangelog.com/)

  **Must NOT do**:
  - Do NOT overwrite existing Changelog.md if one exists (append)
  - Do NOT include implementation details — high-level summary only

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file creation with known content
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 5)
  - **Blocks**: Final verification wave
  - **Blocked By**: Task 4 (need to know what was built)

  **References**:

  **Pattern References**:
  - `CLAUDE.md` — "After each change to the codebase, update the Changelog.md file"

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Changelog.md exists and documents changes
    Tool: Bash
    Preconditions: Changelog.md created
    Steps:
      1. test -f Changelog.md && echo 'EXISTS'
      2. Assert output is 'EXISTS'
      3. grep -i 'ci' Changelog.md
      4. Assert CI-related entries are present
      5. grep -i 'rut\|eslint\|conftest' Changelog.md
      6. Assert prerequisite fix entries are present
    Expected Result: Changelog exists with all entries
    Evidence: .sisyphus/evidence/task-6-changelog.txt
  ```

  **Commit**: YES
  - Message: `docs: add Changelog.md with CI/CD setup entries`
  - Files: `Changelog.md`


## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 3 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read workflow file, check jobs). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `ruff check` in server/. Run `npx eslint .` in ui/. Run `npm run build`. Validate workflow YAML syntax. Review all changed files for: hardcoded paths, local-only assumptions, missing error handling. Check AI slop: excessive comments, over-abstraction.
  Output: `Lint [PASS/FAIL] | Build [PASS/FAIL] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

All changes should be committed as a single logical unit on a feature branch, then PR to main:

- **Branch**: `ci/github-actions-pipeline`
- **Commit 1**: `fix(server): switch rut dependency from local path to git source` — `server/pyproject.toml`, `server/uv.lock`
- **Commit 2**: `feat(ui): add ESLint flat config for Vue 3` — `ui/eslint.config.js`
- **Commit 3**: `fix(server): harden SurrealDB readiness check in test conftest` — `server/tests/conftest.py`
- **Commit 4**: `feat(ci): add GitHub Actions CI pipeline` — `.github/workflows/ci.yml`
- **Commit 5**: `docs: add Changelog.md with CI/CD setup entries` — `Changelog.md`

---

## Success Criteria

### Verification Commands
```bash
# Server deps resolve
cd server && uv sync --frozen --all-groups  # Expected: exit 0

# Server lint passes
cd server && uv run ruff check app/ tests/  # Expected: exit 0

# Server tests pass (requires surreal binary)
cd server && uv run rut tests/  # Expected: 8 tests, 0 failures

# UI lint works
cd ui && npx eslint .  # Expected: meaningful output, not "no config"

# UI build succeeds
cd ui && npm ci && npm run build  # Expected: exit 0, dist/ created

# Docker build succeeds
docker build -t agent-one-ci-test .  # Expected: exit 0

# GitHub Actions workflow valid
gh workflow list  # Expected: ci.yml listed
gh run list --workflow=ci.yml  # Expected: recent runs visible
```

### Final Checklist
- [ ] All "Must Have" present (server lint, server test, UI lint+build, Docker build, path detection, caching, concurrency)
- [ ] All "Must NOT Have" absent (no deploy step, no MISTRAL_API_KEY, no frontend tests, no runtime code changes)
- [ ] All prerequisite fixes applied (rut dep, eslint config, conftest hardening)
- [ ] PR to main shows green status checks
- [ ] Changelog.md documents all changes
