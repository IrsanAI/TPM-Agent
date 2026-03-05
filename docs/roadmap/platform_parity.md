# Platform Parity Roadmap (Android/Termux, Docker, Linux, macOS, iPhone)

## Current baseline (already available)
- Unified web hub server (`scripts/web_hub_server.py`) for Oracle + Update APIs.
- Update cockpit (`scripts/update_cockpit_server.py`) with orchestrated update trigger.
- Shared state folders (`state`, `data`, `config`, `backups`) already used in both Termux and Docker.

## Android/Termux (target: full production)
- [x] Web Hub entrypoint via `python scripts/tpm_cli.py web --port 8765`.
- [x] Update cockpit + orchestrator available from CLI.
- [x] Oracle snapshot rendering in Playground.
- [ ] Add Termux notification channel integration for update phase transitions.
- [ ] Add battery/network guardrails before applying update.

## Docker (target: parity + optional super-set)
- [x] Compose services for `tpm-web` and `tpm-cockpit`.
- [x] Persistent volumes for state/data/config/backups.
- [x] Same API surface as Termux web hub.
- [ ] Add optional rolling update workflow for multi-container deployments.
- [ ] Add healthcheck-driven restart policy during handover.

## Linux desktop/server roadmap
- [x] Base compatibility (CLI + web hub run with Python 3.11).
- [x] Platform detection is exposed in `/api/capabilities`.
- [ ] Add systemd unit templates for `web`, `live`, and `cockpit`.
- [ ] Add package script (`./scripts/linux_install.sh`) for one-command bootstrap.

## macOS roadmap
- [x] Base compatibility path through Python CLI.
- [x] Capability detection in web API (`macos` flag via platform detection).
- [ ] Add launchd plist templates for persistent services.
- [ ] Add signed app-wrapper packaging path (long-term).

## iPhone roadmap (web-first)
- [x] Responsive web UI foundation in `playground/index.html`.
- [x] Browser-only access path via web hub APIs.
- [ ] Add iOS PWA manifest + install prompts.
- [ ] Add push-style alert bridge (server-side events + APNs relay option).
- [ ] Define secure remote-host pattern (iPhone as client, backend on Docker/Linux host).

## Cross-platform technical milestones
1. Introduce capability matrix contract versioning in `/api/capabilities`.
2. Add release channel support (`stable`, `beta`, `nightly`) in update orchestrator.
3. Add post-update smoke tests and rollback trigger before final handover.
4. Add "What's New" changelog localization for UI popup.
