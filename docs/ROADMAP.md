# Roadmap

Current status: **working local harness** — the `stack` CLI, bridges, setup
script, and Telegram wiring are all in place. The harness mirrors what's
already running on this machine.

## Done
- [x] `stack` CLI (status / hermes / openclaw / ask / note / telegram / doctor)
- [x] Bridges: `hermes-to-openclaw`, `hermes-worker`, `vault-note`
- [x] `setup.sh` — idempotent provisioning for all three agents
- [x] `openclaw-wife-reviewer` hook (Hermes → OpenClaw self-check)
- [x] Config templates (no secrets) + `.env.example`
- [x] Docs: SETUP, ARCHITECTURE, CLI

## Next
- [ ] **Push to GitHub** for versioning + portability (asked)
- [ ] Intent-based routing in `stack ask` (exec ask → hands, knowledge ask → brain)
- [ ] Telegram routing for **OpenClaw** (second bot or same-bot command routing)
- [ ] `stack install` interactive wizard (auto-configure gateway from prompts)
- [ ] Server deployment target (ZimaBlade / docker-compose) — the same stack as a service
- [ ] Auto-load shared-brain context (`Interop/Current State.md`) into both agents on session start
- [ ] Add Grafana/Langfuse cost telemetry for the whole stack
