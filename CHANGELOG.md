# Changelog

All notable changes to AgentStack.

AgentStack is a **secure compatibility and orchestration layer** connecting
Hermes, OpenClaw, Markdown knowledge workspaces, model provider APIs, councils,
skills, and the wider Cyralyx platform — not a single merged runtime.

## [Unreleased]

## [0.2.0] - 2026-08-04 — Foundation repair & repositioning

### Security
- **Deprecated** `install --token` (CLI secrets leak to shell history/process/
  logs); shows a strong warning, removal planned in v0.3.0.
- **Secure provider setup**: `agentstack provider add <name>` uses hidden input
  and rejects empty/placeholder/short keys.
- **Encrypted secret store**: AES-256-GCM file under `AGENTSTACK_HOME` with a
  machine-local key; provider config stores a `keychain://` ref, never the raw
  secret (`lib/secrets.js`).
- **Permission gates** (`lib/permissions.js`): categories + modes, default
  deny/ask for execution; decisions logged (`agentstack permissions`).
- **Security subsystem** (`lib/security.js`): `agentstack security
  secrets|dependencies|permissions|skills|config|full` replaces the old narrow
  audit; no longer claims external OpenRouter guardrails as verified.

### Platform
- **Platform-aware paths** (`lib/paths.js`, `lib/platform.js`): Windows
  `%LOCALAPPDATA%/Cyralyx/AgentStack`, macOS `~/Library/Application Support`,
  Linux `$XDG_CONFIG_HOME/agentstack`. No hard-coded `AppData/Local/hermes` or
  `Documents/Obsidian Vault`; any Markdown workspace via `STACK_VAULT`.

### Tasks
- **Durable UUID task storage** (`lib/tasks.js`): stable IDs that never collide,
  Markdown becomes an export/sync view not the source of truth.
- **Migration** from legacy `Tasks.md` (backs up, preserves open+completed,
  dedupes) — `agentstack task migrate`. `todo` kept as a compatibility alias.

### Providers
- **Provider adapter layer** (`lib/providers/`): 13+ providers (OpenRouter,
  OpenAI, Anthropic, Gemini, DeepSeek, xAI, Mistral, Groq, Together, Fireworks,
  Cerebras, Ollama, LM Studio) via an OpenAI-compatible core; error taxonomy
  (`lib/providers/errors.js`). `agentstack provider list|add|test|remove|disable`.

### Bridges & routing
- **Typed bridge contract** (`lib/bridges/schema.js`): validated envelope
  (version/request_id/status/input/result/usage/errors), status taxonomy,
  hermes/openclaw/mock adapters (`lib/bridges/runner.js`).
- **Layered routing** (`lib/routing.js`): explicit → rules → capability →
  fallback; `agentstack ask --agent <name>` and `--explain-route`.

### Health & integration (P2)
- **Structured doctor** (`agentstack doctor --json`): status taxonomy
  (healthy/degraded/misconfigured/incompatible/unsafe/offline), severity,
  repairability, suggested actions.
- **Localhost-only API** (`agentstack api serve`): `/api/status`,
  `/api/compatibility`, `/api/providers`, `/api/tasks`, `/api/events`,
  `/api/health`; structured event emitter (`lib/events.js`).

### Compatibility
- **Compatibility registry + checks** (`lib/compatibility.js`):
  `agentstack compatibility [check|report]`.

### CI & testing
- CI matrix: Ubuntu + Windows × Node 22/24; removed `|| true` suppression on the
  council import check; added `npm audit --audit-level=high` (no suppression).
- Tests expanded 5 → **25** across `test/cli.test.js`, `test/lib.test.js`,
  `test/bridges.test.js` (secrets, tasks/migration, permissions, routing,
  bridges, providers, compatibility).

### Documentation
- `docs/audits/current-state-audit.md` classifies every prior claim
  (VERIFIED/UNTESTED/PARTIAL/DOCS/BROKEN/UNKNOWN).
- Repositioned README + VISION + package.json + GitHub description: AgentStack
  is a compatibility/orchestration layer, not a merged runtime; cost/guardrail
  claims corrected to methodology + reproducible instructions.

## [0.1.0] - 2026-08-03
### Added
- Initial AgentStack harness: `stack` CLI, bridges, setup, docs
- Husband-and-wife partnership layer: `stack run/marry/sync` + compatibility ledger
- Council v2 (cheap workers + peer-rank + chairman with cost tracking)
- Learning skills (task-learning, system-health)
- Terminal-fast-commands skill
