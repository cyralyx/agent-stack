# Permission System Guide

How AgentStack gates what agents (Hermes, OpenClaw, future Cyralyx) are
allowed to do. Implementation: `lib/permissions.js`; CLI: `agentstack
permissions …`.

## 1. Categories

Ten capability categories (`lib/permissions.js` `CATEGORIES`):

| Category | Covers |
|----------|--------|
| `files.read` | Reading files outside the vault |
| `files.write` | Writing/creating/deleting files |
| `process.execute` | Running commands / subprocesses |
| `network.access` | Outbound network calls |
| `browser.control` | Driving a browser |
| `secrets.read` | Reading stored credentials |
| `git.write` | Git mutations (commit/push/merge) |
| `system.admin` | Admin/system-level changes |
| `messaging.send` | Sending messages (Telegram, …) |
| `vault.write` | Writing into the shared Markdown vault |

## 2. Modes

Six modes (`MODES`), from most restrictive to most permissive:

| Mode | Effect |
|------|--------|
| `deny` | Always refused, no prompt, decision logged |
| `ask` | Prompt the user every time (default for most categories) |
| `allow_once` | Allow a single action, then back to `ask` |
| `allow_session` | Allow for the current session |
| `allow_project` | Allow for the project scope (permanent until changed) |
| `allow_permanent` | Allow forever |

**Defaults** (created on first load, version 1):

- `files.read` → `allow_project` (safe reads are useful by default)
- `vault.write` → `allow_project` (the vault is the shared brain)
- everything else → **`ask`** — including `process.execute`, `network.access`,
  `secrets.read`, `system.admin`, `browser.control`, `git.write`,
  `messaging.send`, `files.write`.

> Nothing executes without a decision: the default posture for execution is
> **deny/ask** — `evaluate()` returns `allowed: false` for `deny`, `null`
> (requires approval) for `ask`, and `true` only for an allow mode.

## 3. Commands

```bash
agentstack permissions list                # category -> effective mode
agentstack permissions set <category> <mode>
agentstack permissions reset               # delete policy file, restore defaults
agentstack permissions audit               # defaults + entries + last 10 decisions
```

- `set` validates category and mode; unknown values are rejected with a usage
  error. Scope keys: `default` (policy defaults), `agent:<name>`, or
  `project:<name>` (the library `set()` supports agent/project scope; the CLI
  `permissions set` writes the default scope today).
- `audit` prints `{ defaults, entries, recent_log }` — every decision is logged
  with a timestamp, category, agent/project, action, mode, and outcome; the log
  is capped at the last 500 entries.
- Policy file: `config/permissions.json` under `AGENTSTACK_HOME`
  (`lib/paths.js` `permissionsPath()`), written mode 0600.

## 4. Evaluation

`evaluate({ category, agent, project, action })`:

1. Looks up the effective mode: agent entry → project entry → default.
2. Logs the decision (outcome: `denied` | `asked` | `allowed`).
3. Returns `{ allowed, mode, reason }`:
   - `deny` → `{ allowed: false, reason: "denied by policy (…)" }`
   - any allow mode → `{ allowed: true, reason: "allowed by policy (…: mode)" }`
   - `ask` → `{ allowed: null, reason: "requires approval" }`

Consumers must treat `allowed: null` as "pause and prompt" — never as "go".

## 5. The interactive approval prompt

`promptApproval(spec)` renders a human-readable request and asks for a
decision (`lib/permissions.js`):

```
=== AgentStack permission request ===
Target agent:  openclaw
Proposed:      install the package
Command:       npm i -g openclaw
Working dir:   C:\Users\willi\project
Files:         package.json
Network:       registry.npmjs.org
Rollback:      none
Allow process.execute? (y=once/N=deny/a=allow-project-forever)
```

- `y` → `allow_once`, logged, resolved `{ allowed: true, mode: 'allow_once' }`.
- `a` → persists `allow_project` for that agent+project, logged, resolved
  `{ allowed: true, mode: 'allow_project' }`.
- anything else (incl. Enter) → **denied**, logged,
  `{ allowed: false, mode: 'deny' }`.

Every response is recorded in the policy log, so `permissions audit` shows the
full history of what was requested, decided, and under which mode.

## 6. Where it plugs in

- **Routing:** `lib/routing.js` `route()` returns `required_permissions`
  (e.g. `['process.execute']` when an execution verb routes to OpenClaw) so
  callers know which gates to consult.
- **Bridges:** `lib/bridges/runner.js` `openclaw()` is documented as
  "permission-gated upstream by caller" — the adapter itself does not gate.
- **Events:** `permission.requested` is a typed event (`lib/events.js`) for UI
  surfacing (future Cyralyx permission dialogs).
- **Bridge status:** `awaiting_approval` exists in the bridge protocol
  (`lib/bridges/schema.js`) as the envelope status a gated bridge should emit
  while waiting; no producer emits it yet.

> **Honest status:** the policy engine, defaults, logging, and prompt are
> implemented and tested (`test/lib.test.js`); the legacy CLI `ask` path
> shells out through `bridges/` scripts and does not yet call
> `evaluate()`/`promptApproval()` end-to-end for every execution. Wiring the
> gates into every bridge call is an open task (see roadmap P1/P2 and the
> threat model T3).

## 7. Policy file example

```json
{
  "version": 1,
  "defaults": {
    "files.read": "allow_project",
    "vault.write": "allow_project",
    "process.execute": "ask",
    "network.access": "ask",
    "secrets.read": "ask",
    "system.admin": "ask"
  },
  "entries": {
    "agent:openclaw": { "process.execute": "allow_project" }
  },
  "log": [ { "ts": "…", "category": "process.execute", "outcome": "allow_project" } ]
}
```

## 8. See also

- `lib/permissions.js`, `lib/routing.js`, `lib/events.js`, `lib/bridges/schema.js`.
- `docs/security/THREAT_MODEL.md` (T3 — openclaw exec access, residual risk).
- `docs/bridges/PROTOCOL.md` (`awaiting_approval` status).
