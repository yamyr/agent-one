# Discord Git Integration Plan

## Goal

Send key GitHub repository events to Discord channels so the team sees PR and main branch activity in real time.

## Tasks

- [x] Review existing workflow conventions in this repo
- [x] Design channel routing strategy (PR channel vs main channel)
- [x] Add GitHub Actions workflow for Discord notifications
- [x] Document required repository secrets and setup steps
- [x] Verify workflow syntax and repository status

## Notes

- Use Discord webhooks (official and reliable) rather than a Discord CLI.
- Keep notifications concise and useful: PR open/update/merge and pushes to `main`.
- Support optional separate webhooks per channel with a default fallback.

## Review

- Added `.github/workflows/discord-git-notify.yml` with separate jobs for PR and `main` push notifications.
- Added secret routing with fallback support:
  - `DISCORD_WEBHOOK_URL` (default)
  - `DISCORD_WEBHOOK_URL_PR` (optional PR channel)
  - `DISCORD_WEBHOOK_URL_MAIN` (optional main channel)
- Added setup documentation in `README.md`.
- YAML syntax validated locally via Ruby Psych (`YAML OK`).
