# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.9.x   | :white_check_mark: |
| < 0.9   | :x:                |

Only the latest `0.9.x` release receives security updates. Older versions are unsupported.

## Reporting a Vulnerability

**Please do not open public GitHub issues for security vulnerabilities.**

Report security issues privately via [GitHub Security Advisories](https://github.com/yamyr/agent-one/security/advisories/new).

You can expect:
- **Acknowledgement** within 48 hours of submission
- **Status update** within 7 days (accepted, declined, or needs more info)
- **Fix and disclosure** coordinated with you if the vulnerability is accepted

If a vulnerability is declined, we will explain why. If accepted, we will credit you in the release notes unless you prefer to remain anonymous.

## Known Security Considerations

### API Keys and Secrets

- `MISTRAL_API_KEY` and `ELEVENLABS_API_KEY` **must** be provided via environment variables or a `.env` file — never committed to the repository.
- The `.gitignore` excludes `.env` files. Verify your local `.env` is not tracked before pushing.
- No secrets are logged or included in WebSocket event payloads.

### SurrealDB Credentials

- SurrealDB defaults to `root`/`root` credentials in development (port 4002).
- **In production**, override these via the `SURREAL_USER` and `SURREAL_PASS` environment variables and restrict network access to the database port.
- Never expose SurrealDB directly to the public internet.

### CORS Configuration

- CORS is configured to allow specific origins only: `http://localhost:4089` (local dev) and the Railway deployment domain.
- Do not add wildcard (`*`) origins in production deployments.
- The allowed origins list is controlled via `Settings.cors_origins` in `server/app/config.py`.

### WebSocket Connections

- The `/ws` endpoint has a maximum concurrent connection limit enforced by the `Broadcaster` singleton.
- Connections that disconnect uncleanly are cleaned up via a `finally` block to prevent resource leaks.
- No authentication is required for WebSocket connections in the current version — restrict network access at the infrastructure level for production deployments.

### File Upload Endpoints

- The `/api/voice-command` endpoint accepts audio file uploads for Voxtral transcription.
- Uploaded files are validated against configured directories and are not persisted beyond the request lifecycle.
- File paths are never constructed from user-supplied input without sanitization.

### Training Data

- Training data logged to SurrealDB contains agent observations and LLM responses — no user credentials or secrets.
- The `TRAINING_DATA_DIR` path is configurable; ensure it points to a directory with appropriate permissions.

## Scope

### In Scope

- **Server API** (`server/app/`) — REST endpoints, WebSocket handler, authentication/authorization gaps
- **WebSocket event stream** — data leakage, injection via event payloads
- **File handling** — path traversal in voice command uploads or training data exports
- **Dependency vulnerabilities** — CVEs in pinned Python or Node.js dependencies
- **Secret exposure** — accidental logging or broadcasting of API keys

### Out of Scope

- **Third-party APIs** (Mistral AI, ElevenLabs, HuggingFace) — report vulnerabilities directly to those providers
- **Browser extensions** or client-side attacks outside the application's own JavaScript
- **SurrealDB internals** — report to the SurrealDB project
- **Railway / hosting infrastructure** — report to Railway
- **Social engineering** attacks against project maintainers
- **Denial-of-service** via resource exhaustion without a clear exploit path
