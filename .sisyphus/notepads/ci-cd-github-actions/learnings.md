## Notepad: Learnings
<!-- Append-only. Do not overwrite. -->

### Task 2: ESLint Config
- ESLint 9 flat config requires array export with `js.configs.recommended` and `...pluginVue.configs['flat/recommended']`
- The `no-undef` errors for `window`, `WebSocket`, `setTimeout` indicate we need browser globals config (e.g., `languageOptions: { globals: globals.browser }`) — to be addressed in a future task
- 91 vue template formatting warnings exist in App.vue — mostly `vue/max-attributes-per-line` and `vue/html-indent`
- npm dependencies must be installed before ESLint can run (`npm install` needed if node_modules missing)

### Task 1: Fix rut dependency source
- `rut` upstream repo (schettino72/rut) has broken `[tool.uv.sources]` pointing to developer's local path for `import-deps`
- When uv resolves a git dependency, it reads that package's own `tool.uv.sources` and tries to resolve transitive deps from there
- Fix: use `[[tool.uv.dependency-metadata]]` to provide static metadata for rut, bypassing its broken source config
- `import-deps>=0.5.1` is available on PyPI AND on GitHub (schettino72/import-deps, branch=master)
- `rut` on PyPI goes up to v0.3.0, not just v0.1.0 as previously thought
- `tool.uv.sources` overrides for transitive deps require the dep to also be listed as a direct dependency
- `--no-sources` flag in `uv lock` strips ALL source overrides (useful for debugging but resolves to PyPI versions)

## Task 4: CI Workflow Creation (2026-02-28)

- GitHub Actions YAML with `${{ }}` expressions validates fine with `yaml.safe_load()` since those are just strings to the YAML parser
- `dorny/paths-filter@v3` requires `pull-requests: read` permission to work on PRs
- SurrealDB install script puts binary in `~/.surrealdb/` — must add to `$GITHUB_PATH` explicitly
- `astral-sh/setup-uv@v7` is current production standard; supports `enable-cache` and `python-version`
- `uv sync --frozen --all-groups` ensures lockfile is respected and all dependency groups (including dev) are installed
- Concurrency group `ci-${{ github.ref }}` with `cancel-in-progress: true` prevents redundant CI runs on rapid pushes
- Path-based change detection keeps CI fast — only runs relevant jobs when specific directories change
