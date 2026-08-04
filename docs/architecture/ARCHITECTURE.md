# AgentStack Architecture

> Status: accurate for `agentstack` v0.2.0 (`bin/agentstack.js`).
> Companion audit: [`docs/audits/current-state-audit.md`](../audits/current-state-audit.md).

## 1. Role: a compatibility & orchestration layer

AgentStack is **not** a merged runtime. It is the integration layer that
connects independently-installed external systems:

| System | Role in the stack | How AgentStack talks to it |
|--------|-------------------|----------------------------|
| **Hermes** | Brain (reasoning agent) | `lib/bridges/runner.js` → `hermes chat -Q -q` subprocess; version-checked via `lib/compatibility.js` |
| **OpenClaw** | Hands (execution agent) | `lib/bridges/runner.js` subprocess; permission-gated upstream (`lib/permissions.js`) |
| **Markdown workspace / Obsidian vault** | Shared memory | `lib/tasks.js` exports a Markdown view; `lib/paths.js` resolves the vault |
| **Model providers** | Inference | `lib/providers/` adapters (OpenAI-compatible core) + `lib/secrets.js` credential refs |
| **Councils** | Cheap multi-model deliberation | `council/council_v2.py` invoked by `agentstack council` |
| **Skills** | Reusable procedures | Bundled under `skills/`, deployed to Hermes on install |
| **Cyralyx** | Future desktop app | `lib/api.js` localhost-only HTTP API (`agentstack api serve`) |

The layer separation is:

```
┌────────────────────────────────────────────────────────────┐
│  CLI  (bin/agentstack.js)   — commands, flags, exit codes   │
├────────────────────────────────────────────────────────────┤
│  lib/   (core services, no UI logic)                        │
│    paths / platform / secrets / tasks / permissions         │
│    compatibility / security / events / api / routing        │
│    providers/  adapter · errors · openai-compatible · registry│
│    bridges/    schema · runner                              │
├────────────────────────────────────────────────────────────┤
│  External: hermes, openclaw, vault, provider APIs, council │
└────────────────────────────────────────────────────────────┘
```

The audit (2026-08-04) verified this repositioning: the old claim of "one
merged runtime" is marked **PARTIAL / OVERCLAIMED**; the verified reality is a
compatibility + orchestration layer over subprocess calls.

## 2. `lib/` module layout

### `lib/paths.js` — platform-aware directory resolution
- `agentStackHome()`: AgentStack's own state dir (`AGENTSTACK_HOME` env, else
  `%LOCALAPPDATA%\Cyralyx\AgentStack` on Windows, `~/Library/Application
  Support/AgentStack` on macOS, `$XDG_CONFIG_HOME/agentstack` on Linux).
- `hermesHome()`: Hermes state (`HERMES_HOME` env, else platform default).
- Derived: `dataHome/`, `configHome/`, `cacheHome/`, `dbPath`,
  `tasksDbPath()` (`data/tasks.db`), `permissionsPath()` (`config/permissions.json`),
  `providersConfigPath()` (`config/providers.json`), `configFilePath()`.
- `workspace()`: vault override (`STACK_VAULT`) or `~/Documents/Obsidian Vault`.
- `ensureDirs()`: creates all state dirs.
- Fixes the P0 audit finding "hard-coded AppData paths".

### `lib/platform.js` — platform detection + tool resolution
- `isWindows/isMac/isLinux` from `os.platform()`.
- `resolveCommand()`: `where` on Windows with `.exe/.cmd/.bat/.ps1` candidates,
  `which` on POSIX.
- `resolvePython()`: `py` → `python` → `python3` on Windows; `python3` first on
  POSIX, each verified by `--version`.
- `resolveNode/resolveNpm`, `packageManager()` (informational).

### `lib/secrets.js` — credential storage (see `docs/security/CREDENTIALS.md`)
- Encrypted AES-256-GCM fallback store `secrets.enc` under `AGENTSTACK_HOME`,
  keyed by machine-local `.machine-key` (mode 0600).
- `setSecret/getSecret/removeSecret` by logical service name; returns a
  `keychain://agentstack/<service>` ref.
- Provider config (`providers.json`) stores **refs only, never raw secrets**:
  `addProvider()` writes `{ secret_ref, base_url, enabled }`.
- `validateKey()` rejects empty/placeholder/too-short keys; `promptHidden()`
  provides echo-free interactive input.
- `STATUS` taxonomy: `not_configured … unsupported`.

### `lib/tasks.js` — durable structured task storage
- JSON store (`data/tasks.db`) keyed by stable **UUID** (`crypto.randomUUID()`)
  with human-friendly `display` numbers; `nextDisplay` monotonic.
- CRUD: `add/list/getById/update/complete/reopen/remove`; filters by
  `status`/`project`.
- Markdown is an **export view only** (`toMarkdown/exportMarkdown` → vault
  `Agent Hub/Tasks.md`), not the source of truth.
- `migrateFromLegacy()` imports old `Tasks.md` with backup + dedupe.

### `lib/permissions.js` — permission gates (see `docs/permissions/GUIDE.md`)
- 10 categories, 6 modes; defaults deny/ask (safe reads `allow_project`).
- `evaluate()` returns `{allowed, mode, reason}` and logs every decision.
- `promptApproval()` interactive prompt (`y` / `a` / default deny).

### `lib/compatibility.js` — version registry + checks
- `REGISTRY`: hermes ≥ 0.18.0, openclaw ≥ 1.0.0, node ≥ 20, python ≥ 3.9,
  bridge protocol 1.0.
- `checkNode/checkPython/checkHermes/checkOpenClaw`, `report()` → structured
  per-component result used by `doctor` and the API.

### `lib/security.js` — security audit subsystem
- `scanSecrets()`: regex scan for `sk-`, `ghp_`, `AIza`, `xox`, `AKIA`, private
  keys (findings redacted to first 8 chars).
- `unsafePermissions()` (POSIX): world/group-readable config files.
- `dependencies()`: `npm audit` wrapper.
- `skills()`: shallow scan of `skills/` for `curl|bash`, `chmod 777`, `sudo rm`.
- `providerConfig()`: raw secrets in config, enabled-without-key providers.
- `full()`: aggregates into `{secrets, permissions, skills, providers, all_clear}`.

### `lib/events.js` — structured event emission
- 12 typed events: `task.created`, `task.routed`, `permission.requested`,
  `agent.started`, `tool.invoked`, `output.received`, `validation.started`,
  `task.completed`, `task.failed`, `memory.written`, `provider.error`,
  `budget.warning`.
- `emit(type, data, {persist, handler})`; persisted to `data/events/events.ndjson`.
- `subscribe(fn)` for in-memory UI subscribers; `recent(limit)` replay.

### `lib/api.js` — localhost IPC boundary (for Cyralyx)
- HTTP on `127.0.0.1:38765` only; **non-loopback connections rejected (403)**.
- Endpoints: `GET /api/status`, `/api/compatibility`, `/api/providers`,
  `/api/tasks`, `/api/events`, `/api/health`; `POST /api/tasks`.
- See `docs/architecture/AGENTSTACK_VS_CYRALLYX.md` — this is the contract the
  future Cyralyx desktop app consumes.

### `lib/routing.js` — layered intent routing
Layers (in order): 1 explicit user selection (`--agent`) → 2 deterministic
verb rules (`EXECUTION_VERBS` → openclaw "hands"; `RESEARCH_VERBS`/`?` →
hermes "brain") → 3 capability matching (future) → 4 model-based classification
(future) → 5 safe fallback (ambiguous → hermes, confidence 0.6).
`route()` returns `{selected_target, reason, confidence, alternatives,
required_permissions}` — surfaced by `ask --explain-route`.

## 3. `lib/providers/`

### `adapter.js` — base `Adapter` class
- `capabilities()` flags: `listModels, chat, streaming, toolCalling,
  structuredOutput, vision, embeddings, usage, rateLimitMetadata`.
- `test()` / `listModels()` / `chat()` overridable; `_request()` = timed fetch
  with `AbortController`, cancellation, and HTTP-status → typed error mapping.

### `errors.js` — error taxonomy
- `ERROR_CODES`: `AUTHENTICATION_FAILED, RATE_LIMITED, PROVIDER_UNAVAILABLE,
  INVALID_REQUEST, MODEL_NOT_FOUND, TOOL_CALL_UNSUPPORTED,
  CONTEXT_LIMIT_EXCEEDED, TIMEOUT, CANCELLED, MALFORMED_RESPONSE,
  UNKNOWN_PROVIDER_ERROR`.
- `toTypedError(status, detail)` maps provider statuses (401/403/429/404/400/502/503…)
  to codes; `ProviderError` carries `code` + `meta`.

### `openai-compatible.js` — generic adapter
- One adapter covers OpenAI, DeepSeek, xAI, Mistral, Groq, Together, Fireworks,
  Cerebras, LM Studio, and any OpenAI-compatible endpoint.
- Implements `test()` via `GET /models`, `listModels()`, `chat()` via
  `/chat/completions` with streaming/tools/response_format passthrough and
  normalized `usage`.

### `registry.js` — provider registry
- `PROVIDERS` map: 10 `openai-compatible` kinds + `anthropic`, `gemini`,
  `ollama` declared as future-specialized kinds (currently all constructed as
  `OpenAICompatibleAdapter`).
- `getAdapter(name)` wires stored secret + config base_url; custom endpoints via
  `providers.json` (`custom: true`).
- `list()`, `configuredStatus(name)` (`not_configured/configured/…` — config-level,
  no network).

## 4. `lib/bridges/`

### `schema.js` — typed envelope contract (see `docs/bridges/PROTOCOL.md`)
- `PROTOCOL_VERSION = '1.0'`; 6 statuses; `validate()`; builders
  `success()/failure()/timedOut()`; `newRequestId()` = UUID.

### `runner.js` — adapters
- `runBridge()`: `spawnSync` with timeout/maxBuffer, maps outcomes to envelopes
  (non-zero → `failed`/`BRIDGE_ERROR`, `ETIMEDOUT` → `timed_out`, abort →
  `cancelled`).
- `hermes()`: `hermes chat -Q -q <task> --provider … --model … --source
  agentstack-bridge`.
- `openclaw()`: `openclaw <task>` (caller must permission-gate).
- `mock()`: deterministic success/failure/timeout for tests.

## 5. Data flow examples

**`agentstack ask "create a file"`**: `routing.route()` → `openclaw` (execution
verb) → `bridges/` script runs OpenClaw with `required_permissions:
['process.execute']` → output surfaced; envelope validated by `schema.js`.

**`agentstack provider add openrouter`**: `promptHidden()` captures key with no
echo → `validateKey()` → `setSecret()` writes encrypted store →
`addProvider()` writes `providers.json` with `keychain://` ref →
`getAdapter().test()` live-validates.

## 6. See also
- [`docs/audits/current-state-audit.md`](../audits/current-state-audit.md) — what was verified vs overclaimed.
- `docs/architecture/AGENTSTACK_VS_CYRALLYX.md` — boundary with the desktop app.
- `docs/security/THREAT_MODEL.md`, `docs/security/CREDENTIALS.md`.
- `docs/bridges/PROTOCOL.md`, `docs/permissions/GUIDE.md`, `docs/roadmap/ROADMAP.md`.
