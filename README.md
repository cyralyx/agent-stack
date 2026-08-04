# 🧠 AgentStack

> **A secure compatibility and orchestration layer connecting Hermes, OpenClaw,
> Markdown knowledge workspaces, model provider APIs, councils, skills, and the
> wider Cyralyx platform.**

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.0-orange.svg)](CHANGELOG.md)
[![Made by Cyralyx](https://img.shields.io/badge/made%20by-Cyralyx-8A2BE2.svg)](https://github.com/cyralyx)

AgentStack is **not** a single merged runtime for Hermes, OpenClaw, and Obsidian.
It is the **integration layer** that connects them: it detects compatible
external systems, safe routes work between agents, stores tasks durably,
configures model providers, tracks cost and verified outcomes, checks
compatibility and health, and produces structured events for a future Cyralyx
UI.

The future **Cyralyx desktop application** will provide the graphical
projects, UI, memory management, themes, and knowledge graphs. AgentStack is
the reliable backend Cyralyx calls.

---

## 📦 Implemented now (code + tests)

These features have working implementation and passing tests
(`test/cli.test.js`, `test/lib.test.js`):

| Feature | Implementation | Tests |
|---------|----------------|-------|
| CLI `agentstack` / alias `stack` | `bin/agentstack.js` | `test/cli.test.js` |
| Secure secret storage (encrypted fallback, ref-based provider config) | `lib/secrets.js` | `test/lib.test.js` |
| Provider registry + adapters (13+ providers, OpenAI-compatible core) | `lib/providers/` | `test/lib.test.js` |
| Durable UUID task storage + Markdown export view | `lib/tasks.js` | `test/lib.test.js` |
| Task migration from legacy `Tasks.md` (backup + dedupe) | `lib/tasks.js` | `test/lib.test.js` |
| Permission gates (default deny/ask, 6 modes) | `lib/permissions.js` | `test/lib.test.js` |
| Platform-aware paths (Win/macOS/Linux) | `lib/paths.js`, `lib/platform.js` | `test/lib.test.js` |
| Compatibility registry + checks | `lib/compatibility.js` | `test/lib.test.js` |
| Council v2.1 + cost ledger | `council/council_v2.py`, `council/cost_ledger.py` | import-compile; outputs |
| Provider error taxonomy | `lib/providers/errors.js` | `test/lib.test.js` |

**Supported platforms:** Windows, Linux (CI matrix), macOS (paths handled;
not CI-tested).

## 🧪 Experimental

Features that work only in restricted conditions:

- **`--token` on `install`** — **deprecated** (CLI secrets leak to history/
  process/logs). Kept only for backwards compatibility; will be removed in
  `v0.3.0`. Use `agentstack provider add <provider>` (hidden input).
- **`agentstack api serve`** — planned local IPC; not yet shipped.
- **Provider live connection tests** — run behind
  `AGENTSTACK_LIVE_PROVIDER_TESTS=1` (no real paid calls in CI).

## 🗺️ Planned

- Local API / IPC service + structured event stream for the Cyralyx UI.
- Anthropic + Gemini adapter specialisations (currently OpenAI-compatible core).
- Layered intent routing (explicit → rules → capability → model → fallback).
- Bundled task SQLite backend (currently durable JSON).

## 🔌 External dependencies

Provided by external services — AgentStack connects to them, does not replace them:

- **Hermes** — the reasoning/brain agent. Version-checked via `compatibility`.
- **OpenClaw** — the hands/execution agent. Version-checked; permission-gated.
- **Obsidian / Markdown workspace** — the shared memory. Not mandatory; any
  Markdown folder can be used (`STACK_VAULT`).
- **OpenRouter / OpenAI / Anthropic / Gemini / etc.** — model providers.
- **Telegram** — optional gateway channel.

---

## 🚀 Install

```bash
# Recommended — secure provider setup (hidden input, no CLI secret):
npm i -g agentstack
agentstack setup                 # guided, non-destructive
agentstack provider add openrouter   # enter key hidden
agentstack status                 # verify

# Detect-only (never changes the system):
agentstack doctor --json
```

## 🛠️ Commands

```
agentstack provider list|add|test|remove|disable <name>
agentstack secrets doctor
agentstack compatibility [check|report]
agentstack task add|list|show|complete|reopen|remove|export|sync|migrate
agentstack permissions list|set|reset|audit
agentstack doctor | status | ask | council | note | todo | cost | skills | audit | telegram
```

`todo` is a **compatibility alias** for `task` (kept for backwards compat).

## 🔒 Security

- Secrets are stored via an **encrypted local file** (AES-256-GCM) with a
  machine-local key, referenced by `keychain://agentstack/<provider>` in config
  — never plaintext in config.
- `provider add` uses **hidden interactive input**; `--token` CLI flag is
  deprecated.
- Permissions default to **deny/ask** for execution agents — nothing runs
  without approval.
- See `docs/security/` for the threat model and credential guide.

## 🤝 License

MIT — free to use, fork, and build on.
