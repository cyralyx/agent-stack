# AGENTSTACK REPAIR REPORT

**Base commit:** `ef5e378` (master)
**Branch:** `fix/agent-stack-foundation` (feature; master untouched)
**Rollback:** `backup/pre-foundation` (created at `ef5e378` baseline)
**Date:** 2026-08-04

---

## 1. Mission summary

AgentStack was audited, repaired, hardened, and repositioned from a prototype
that *claimed* to be "one merged runtime" (Hermes × OpenClaw × Obsidian) into a
**tested, secure, cross-platform compatibility and orchestration layer** that
honestly connects Hermes, OpenClaw, Markdown workspaces, model providers,
councils, skills, and the future Cyralyx desktop app.

**P0–P3 outcome: P0 complete, P1 complete, P2 core complete, P3 scoped.**

---

## 2. Priority-by-priority status

### P0 — Immediate (all done)

| Item | Status | Evidence |
|------|--------|----------|
| Secure secrets | ✅ | `lib/secrets.js` AES-256-GCM store; `install --token` deprecated with warning; `agentstack provider add` uses hidden input, rejects empty/placeholder/short keys; provider config stores `keychain://` refs only |
| CI without suppression | ✅ | `.github/workflows/ci.yml`: Ubuntu+Windows × Node 22/24; no `|| true` on validation; `npm audit --audit-level=high` fails loudly; package-lock.json added (0 vulnerabilities) |
| Honest docs | ✅ | README/VISION/package.json/repo description repositioned; undocumented cost/guardrail claims removed or converted to methodology; `docs/audits/current-state-audit.md` classifies every claim VERIFIED/UNTESTED/PARTIAL/DOCS/BROKEN/UNKNOWN |
| Platform paths | ✅ | `lib/paths.js`+`lib/platform.js`: `%LOCALAPPDATA%\Cyralyx\AgentStack` (win), `~/Library/Application Support/AgentStack` (mac), `$XDG_CONFIG_HOME/agentstack` (linux); no hard-coded `AppData/Local/hermes` or `Documents/Obsidian Vault`; `STACK_VAULT` override |
| Stable task IDs | ✅ | `lib/tasks.js` UUID store; Markdown is export view; `task migrate` (backup+dedupe); `todo` compat alias |
| Compatibility registry | ✅ | `lib/compatibility.js` + `agentstack compatibility [check|report]`; wired into `doctor` |
| Provider validation | ✅ | `lib/providers/` registry + 13 providers via OpenAI-compatible core; `provider test` pings endpoint |

### P1 — Foundation (core done, 2 open)

| Item | Status | Evidence |
|------|--------|----------|
| Provider adapter layer | ✅ | `lib/providers/{adapter,errors,openai-compatible,registry}.js`; error taxonomy (AUTHENTICATION_FAILED, RATE_LIMITED, PROVIDER_UNAVAILABLE…) |
| Typed bridge contracts | ✅ | `lib/bridges/schema.js` envelope (version/request_id/bridge/status/input/result/usage/errors); `runner.js` hermes/openclaw/mock adapters; status taxonomy incl. `awaiting_approval` |
| Permission gates | ✅ | `lib/permissions.js`: 9 categories, 6 modes, default deny/ask for execution, decision log; `agentstack permissions list\|set\|reset\|audit` |
| Structured doctor | ✅ | `agentstack doctor --json`: status taxonomy healthy/degraded/misconfigured/incompatible/unsafe/offline + severity/repairability/suggested_action |
| Security audit redesign | ✅ | `lib/security.js`: `agentstack security secrets\|dependencies\|permissions\|skills\|config\|full` |
| Anthropic/Gemini native adapters | ⬜ | routed via OpenAI-compatible core today; specialization planned |
| Expand tests (live-provider, install smoke) | ⬜ | 25 tests green locally; live-provider tests behind env flag planned |

### P2 — Cyralyx integration (core done)

| Item | Status | Evidence |
|------|--------|----------|
| Local API/IPC | ✅ | `lib/api.js` + `agentstack api serve` (127.0.0.1 only); verified live: `/api/health`, `/api/status`, POST `/api/tasks` return stable UUID |
| Structured event stream | ✅ | `lib/events.js` (task.created, task.routed, permission.requested, agent.started, tool.invoked, task.completed…) |
| UI-ready JSON outputs | ✅ | doctor/compatibility/permissions/task all emit JSON |
| Project-scoped config | ⬜ | planned for server deployments |
| Setup modes (`setup --config`, full repair) | ⬜ | detect-only `setup` + safe `repair [--yes]` + non-destructive `uninstall` implemented; non-interactive config-file setup planned |

### P3 — Advanced (scoped)

- Model-based intent routing (optional classifier above the explicit→rules→capability→fallback ladder)
- Council benchmarking with reproducible cost-per-verified-success
- Skill provenance (hash/pin, allowlist audit)
- Automated compatibility tests (Hermes/OpenClaw mocks in CI)
- Benchmark-driven model selection

---

## 3. Deliverables

**CLI commands added/changed** (all verified working):
`provider`, `secrets doctor`, `task` (+`migrate`), `permissions`,
`compatibility`, `security`, `api serve`, `doctor --json`, `setup`, `repair`,
`uninstall`, `ask --agent/--explain-route`. `install --token` deprecated.
`audit` superseded by `security`.

**Library modules** (`lib/`): paths, platform, secrets, tasks, permissions,
compatibility, security, events, api, routing + providers/{errors,adapter,
openai-compatible,registry} + bridges/{schema,runner}.

**Tests:** 5 → **25** (cli, lib, bridges): secrets validation, task
migration/dedupe, permission modes, routing ladder, envelope validation, error
taxonomy, compatibility checks.

**Docs (22 files in `docs/`):** current-state audit, architecture, vs-cyralyx,
threat model, credentials, bridge protocol, permissions guide, cost
methodology, roadmap, install guide, migration guide.

---

## 4. Honest status — what is NOT done / not verified

- **CI on GitHub still not registered** (fresh-repo lag; workflow file exists,
  branch pushed, but `gh` shows no runs). CI was validated **locally**:
  25/25 tests, bash -n, node --check, py_compile all green; npm audit 0 vulns.
- **Live provider calls** not run in CI (no secrets in CI); `provider test`
  exists for users to validate their own key.
- **The old "~$0.0002/run" cost claim is not reproducible** as stated —
  converted to methodology + reproducible command (`python
  council/council_v2.py "q" --domain code --cheap-chairman`); ledger holds one
  real verified entry at $0.00005.
- **Electron app** (from earlier work) remains a portable unsigned package;
  NSIS installer blocked by winCodeSign needing admin.
- **Anthropic/Gemini** still go through the OpenAI-compatible adapter (not
  specialised).

---

## 5. Rollback instructions

1. From the feature branch, master is untouched at `ef5e378`.
2. If anything on the feature branch must be discarded: `git checkout master`
   then `git branch -D fix/agent-stack-foundation`.
3. The `backup/pre-foundation` branch preserves the pre-repair state exactly.
4. Nothing in this mission deleted or modified user data (vault, credentials,
   task history, Hermes config) — `uninstall` and `repair` are deliberately
   non-destructive.

---

## 6. Verdict

**P0 acceptance criteria: ALL PASS.**
**P1 acceptance criteria: core PASS (2 open items are scope-additions, not
blockers).**
**P2 acceptance criteria: core PASS (3 open items are future work).**

**READY FOR RELEASE: YES** — for the foundation layer as a compatibility and
orchestration layer (not as "the entire Cyralyx app"). Remaining items are
scoped follow-ups tracked in `docs/roadmap/ROADMAP.md`.
