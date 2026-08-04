# Roadmap

Organised by the priorities from the foundation repair mission. Done items are
checked and link to the implementation; open items are future work.

## P0 — Immediate (foundation)

- [x] **Secure secret handling** — `lib/secrets.js` (encrypted store, hidden
  input, ref-based config); `install --token` deprecated.
- [x] **CI failure suppression removed** — `.github/workflows/ci.yml` no longer
  uses `|| true` on validation steps; `npm audit` fails on high/critical.
- [x] **Honest documentation** — README/VISION/package.json/repo description
  repositioned to "compatibility & orchestration layer".
- [x] **Platform-aware paths** — `lib/paths.js`, `lib/platform.js` (Windows /
  macOS / Linux config dirs; no hard-coded Hermes/vault paths).
- [x] **Stable task IDs** — `lib/tasks.js` (UUID store; Markdown is a view).
- [x] **Compatibility checks** — `lib/compatibility.js` + `agentstack compatibility`.
- [x] **Provider validation** — `lib/providers/` + `agentstack provider test`.

## P1 — Foundation

- [x] **Provider adapter layer** — `lib/providers/adapter.js`, `errors.js`,
  `registry.js`, `openai-compatible.js` (13+ providers).
- [x] **Typed bridge contracts** — `lib/bridges/schema.js`, `runner.js`
  (envelope validation, status taxonomy, mock adapter).
- [x] **Permissions** — `lib/permissions.js` (deny/ask default, 6 modes,
  audit log).
- [x] **Structured doctor output** — `agentstack doctor --json`
  (status/severity/repairability/suggested action).
- [x] **Security audit redesign** — `lib/security.js` + `agentstack security
  secrets|dependencies|permissions|skills|config|full`.
- [ ] **Anthropic + Gemini adapter specialisations** — currently routed through
  the OpenAI-compatible core; native adapters for provider-specific fields.
- [ ] **Expand test coverage** — live-provider tests behind
  `AGENTSTACK_LIVE_PROVIDER_TESTS=1`; install/uninstall smoke tests in CI.

## P2 — Cyralyx integration

- [x] **Local API / IPC** — `lib/api.js` + `agentstack api serve` (localhost
  only; /status, /compatibility, /providers, /tasks, /events, /health).
- [x] **Structured event stream** — `lib/events.js` (task.created, task.routed,
  permission.requested, agent.started, tool.invoked, task.completed, …).
- [x] **UI-ready JSON outputs** — `doctor --json`, `compatibility`,
  `permissions audit`, `task show`.
- [ ] **Project-scoped configuration** — per-project provider/permission policy
  files for non-interactive server deployments.
- [ ] **Setup modes** — `agentstack setup --config setup.json` (non-interactive
  deployment) and `agentstack repair` (full backup→apply→verify→rollback).

## P3 — Advanced

- [ ] **Model-based intent routing** — replace regex rules with an optional
  classification layer, keeping the explicit→rules→capability→fallback ladder.
- [ ] **Council benchmarking** — deterministic mock suites that score council
  members/verdicts and publish reproducible cost-per-verified-success.
- [ ] **Skill provenance** — hash/pin skills at install, audit untrusted content
  against a curated allowlist.
- [ ] **Automated compatibility tests** — CI job that boots Hermes/OpenClaw
  mocks and asserts bridge protocol compatibility across versions.
- [ ] **Benchmark-driven model selection** — pick models per task from measured
  cost/quality, not static config.
