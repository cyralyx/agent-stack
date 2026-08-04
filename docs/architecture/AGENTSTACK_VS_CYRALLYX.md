# AgentStack vs Cyralyx — who owns what

Two projects, one boundary. This document exists so nobody blurs them.

## The short version

- **AgentStack** is the **backend integration layer**: CLI + `lib/` services +
  local API. It runs headless, works without any GUI, and is the only component
  that talks to Hermes, OpenClaw, providers, the vault, and councils.
- **Cyralyx** is the **future desktop application** (Electron shell already
  scaffolded under `app/`): the graphical face. It calls AgentStack — never the
  other way around.
- The boundary is **`lib/api.js`** (localhost-only HTTP, `agentstack api serve`).
  Everything Cyralyx needs from the stack must be reachable through that API or
  through the CLI; everything AgentStack needs from the user must be reachable
  without a GUI.

## AgentStack — backend integration layer

### Implemented today (code + tests, v0.2.0)

| Capability | Where |
|------------|-------|
| CLI `agentstack` / alias `stack` | `bin/agentstack.js` |
| Secure credential store (encrypted, ref-based config) | `lib/secrets.js` |
| Provider registry + adapters (OpenAI-compatible core, 13+ providers) | `lib/providers/` |
| Durable UUID task storage + Markdown export view + legacy migration | `lib/tasks.js` |
| Permission gates (deny/ask default, 6 modes, logged decisions) | `lib/permissions.js` |
| Platform-aware paths + tool resolution | `lib/paths.js`, `lib/platform.js` |
| Compatibility registry + checks | `lib/compatibility.js` |
| Provider error taxonomy | `lib/providers/errors.js` |
| Security audit subsystem | `lib/security.js` |
| Typed bridge envelopes + hermes/openclaw/mock adapters | `lib/bridges/` |
| Layered intent routing | `lib/routing.js` |
| Council v2.1 + cost ledger | `council/` |
| CI (node/python/bash checks + npm audit on ubuntu+windows) | `.github/workflows/ci.yml` |

### Experimental (works conditionally)

- `install --token` — **deprecated**, kept for backwards compat until v0.3.0
  (CLI secrets leak to shell history/process listings). Use
  `agentstack provider add <name>`.
- `agentstack api serve` — functional localhost API; UI-ready JSON polish still
  pending (see roadmap P2).
- Provider live connection tests — run behind `AGENTSTACK_LIVE_PROVIDER_TESTS=1`
  (no real paid calls in CI).

### Planned (roadmap, not yet code)

- Anthropic + Gemini adapter specializations (today: OpenAI-compatible core).
- Project-scoped configuration.
- Bundled task SQLite backend (currently durable JSON).
- Expanded test matrix.

## Cyralyx — future desktop application

Cyralyx provides everything graphical. AgentStack deliberately does **not**
implement these:

| Cyralyx responsibility | Notes |
|------------------------|-------|
| Graphical project management | Projects UI over AgentStack task/state APIs |
| Main user interface | Window shell, panels, settings screens |
| Memory management UI | Visualize/manage the vault + memory events |
| Provider setup wizard | GUI over `agentstack provider …` / the API |
| Permission management UI | GUI over `agentstack permissions …` / `permission.requested` events |
| Task views | Boards/lists backed by `/api/tasks` |
| Themes | Presentation layer only — no backend coupling |
| Knowledge graphs | Phase-5 spec item (`spec/cyralyx-build-package/`) |
| Plugin / skills management | Install, enable, provenance review UI |

The Electron scaffold in `app/` (`main.js`, `preload.js`, `index.html`) is the
starting point; it is a separate package from the CLI core.

## The boundary: `lib/api.js`

- Binds **`127.0.0.1:38765`** only; any non-loopback connection is refused
  (403) — this is the local trust model: no auth for loopback, no exposure to
  the network.
- Current endpoints: `GET /api/status`, `/api/compatibility`, `/api/providers`,
  `/api/tasks`, `/api/events`, `/api/health`; `POST /api/tasks`.
- Events (`lib/events.js`) feed the UI: `task.created`, `task.routed`,
  `permission.requested`, `agent.started`, `tool.invoked`, `output.received`,
  `validation.started`, `task.completed`, `task.failed`, `memory.written`,
  `provider.error`, `budget.warning`.
- Rule: **no new UI feature may reach behind the API into `lib/`.** If the API
  lacks what the UI needs, extend the API first.

## Design rules

1. AgentStack must remain **fully usable from a terminal** (headless).
2. Cyralyx must remain **a client** — no business logic it can't get via the
   API or CLI.
3. Secrets never cross the boundary: the API exposes provider *status*
   (`configured/valid/…`), never keys.
4. Anything marked "experimental" in AgentStack is not a contract Cyralyx may
   depend on.

## See also

- `docs/architecture/ARCHITECTURE.md` — module layout and layer separation.
- `docs/audits/current-state-audit.md` — verified-vs-overclaimed status.
- `docs/roadmap/ROADMAP.md` — P0–P3 priorities for both sides of the boundary.
- `docs/CYRALYX_ROADMAP.md` — build-package mapping to AgentStack status.
