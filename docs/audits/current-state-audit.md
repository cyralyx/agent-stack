# AgentStack Current-State Audit

**Branch:** `fix/agent-stack-foundation`
**Base commit:** `ef5e378a95ad2f1d1d748c95677f9ce0ca2f0840` (`master`)
**Date:** 2026-08-04
**Baseline tests:** `npm test` 5/5 pass; python `py_compile` all pass; bash `-n` all pass.

Every claim is classified as: **VERIFIED** (works + tested), **IMPLEMENTED BUT UNTESTED**,
**PARTIAL**, **DOCUMENTATION ONLY**, **BROKEN**, or **UNKNOWN**.

---

## 1. Core identity / positioning

| Claim | Status | Evidence |
|-------|--------|----------|
| "Hermes × OpenClaw × Obsidian merged into one runtime / one system" | **PARTIAL / OVERCLAIMED** | `bin/agentstack.js` routes via subprocess to `hermes` / bridge scripts. No single runtime. A compatibility+orchestration layer, not a merge. README + package.json overstate. |
| CLI `agentstack` and alias `stack` | **VERIFIED** | `bin/agentstack.js`, npm test 5/5. |
| Electron desktop app | **VERIFIED (separate app)** | `app/` builds via electron-packager; not part of core CLI. |

## 2. Council

| Claim | Status | Evidence |
|-------|--------|----------|
| `council_v2.py` exists, confidence + cost tracking + SQLite history | **VERIFIED** | code compiles; history DB persists (prior runs). |
| "~$0.0002/run" cost figure | **DOCUMENTATION ONLY / NOT REPRODUCIBLE** | no provider/model/token-count/pricing/sample-size in docs. Must be moved to a documented methodology or removed. |
| Cost-per-verified-success | **PARTIAL** | `cost_ledger.py` exists but "verified success" undefined; not wired to a validator. |
| Member retirement, anonymous ranking, domain panels | **IMPLEMENTED BUT UNTESTED** | code present (`council_v2.py`); no deterministic tests. |

## 3. Secrets / providers

| Claim | Status | Evidence |
|-------|--------|----------|
| `install --token sk-or-...` one-shot | **INSECURE** | command-line secret → shell history/process listing. P0 fix: deprecate + secure `provider add`. |
| OpenRouter-only | **BROKEN assumption** | hard-coded OPENROUTER_API_KEY; no provider abstraction. P0/P1: universal provider layer. |
| OpenRouter budget guardrails "enabled" | **UNVERIFIED** | docs claim budget $10/mo + prompt-injection flag; not confirmed via API. Must not claim. |

## 4. Platform

| Claim | Status | Evidence |
|-------|--------|----------|
| Cross-platform | **BROKEN** | hard-coded `AppData/Local/hermes`, `Documents/Obsidian Vault`, `python`, bash-only bridges. No `lib/paths.js`. P0: platform-aware paths. |
| Windows support | **PARTIAL** | some `.cmd` shims; but core relies on bash (git-bash) + `python` name. |

## 5. Tasks

| Claim | Status | Evidence |
|-------|--------|----------|
| `todo` task queue in vault `Tasks.md` | **BROKEN (ID fragility)** | IDs derived from count of open tasks → duplicate IDs after completion. P0: SQLite/JSON store with stable UUIDs + migration. |
| Vault as source of truth | **BROKEN design** | treating Markdown as a database. Must become export/sync view. |

## 6. Bridges & routing

| Claim | Status | Evidence |
|-------|--------|----------|
| Hermes/OpenClaw bridges | **PARTIAL** | loose string output, no typed JSON contract. P1: typed bridge schema. |
| Intent routing by regex verbs | **FRAGILE** | `doVerbs` regex only. P1: layered routing. |

## 7. Permissions & security

| Claim | Status | Evidence |
|-------|--------|----------|
| `stack audit` | **PARTIAL** | narrow; no `security` subcommands, no dependency scan, no permission gates. P1. |
| Permission model | **NOT PRESENT** | OpenClaw bridge can execute without gates. P1: permission categories + modes. |

## 8. Doctor / health

| Claim | Status | Evidence |
|-------|--------|----------|
| `doctor` | **PARTIAL** | no JSON output, no exit codes/severity/repairability taxonomy. P1. |

## 9. CI

| Claim | Status | Evidence |
|-------|--------|----------|
| CI runs | **PARTIAL** | single Ubuntu job, one `|| true` suppression (`council` import check must fail). P0: fix suppression. |
| Multi-platform | **NOT PRESENT** | no Windows/macOS matrix. P1/P2. |

## 10. Compatibility

| Claim | Status | Evidence |
|-------|--------|----------|
| Version/compatibility registry | **NOT PRESENT** | P0: add registry + checks. |

---

## Priority summary
- **P0 broken/overclaimed:** secrets (insecure token), CI `|| true`, honest docs, platform paths, task IDs, compatibility checks, provider validation.
- **P1 foundation:** provider layer, typed bridges, permissions, structured doctor, expanded tests, security redesign.
- **P2 Cyralyx integration:** local API/IPC + events, project config, UI JSON.
- **P3 advanced:** routing, council benchmark, skill provenance, model selection.

## How to reproduce baseline
```bash
git checkout fix/agent-stack-foundation
npm test                 # 5 pass
python -m py_compile council/*.py
bash -n bin/stack setup.sh install.sh
```
