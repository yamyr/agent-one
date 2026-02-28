# Task: Versioning and Release Management in CI

## Plan

- [x] Audit current version sources and CI triggers
- [x] Add release automation workflow on `main`
- [x] Configure version bump + changelog release PR behavior
- [x] Keep server/ui versions in sync from one release version
- [x] Document release workflow and operator steps
- [x] Validate workflow syntax and local project checks

## Review Notes

- Added Release Please workflow + manifest configuration for `main`.
- Wired release version propagation to server and UI package metadata from one manifest version, including `server/app/main.py` and `version.txt`.
- Documented release flow in README and changelog.
- Hardened release workflow with job-scoped permissions and optional `RELEASE_TOKEN` fallback.
- Validation run:
  - `python3 -m json.tool release-please-config.json`
  - `python3 -m json.tool .release-please-manifest.json`
  - `python3 -m py_compile mistral_base.py`
  - `uv run ruff check app tests` (server)
  - `npm --prefix ui run build`
