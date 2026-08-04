# AgentStack Threat Model

Scope: threats relevant to the AgentStack design as implemented in v0.2.0.
Each entry lists likelihood, impact, mitigation (with the code that provides
it), status, and residual risk. Status labels: **MITIGATED** (defense in
place), **PARTIAL** (defense exists but incomplete), **OPEN** (no defense yet).

Ratings are relative to a single-user local-first deployment on Windows
(primary target), macOS/Linux secondary.

---

## T1. Secrets in CLI arguments / shell history

- **Scenario:** `agentstack install --token sk-or-...` puts the key in the
  shell history, process list, and terminal logs.
- **Likelihood:** High — it was the documented one-shot flow.
- **Impact:** High — full provider account compromise (billing, model access).
- **Mitigation:** `--token` is **deprecated** in `bin/agentstack.js` (warning
  printed, removal planned for v0.3.0). Replacement: `agentstack provider add
  <name>` uses `lib/secrets.js` `promptHidden()` — raw-mode stdin with **no
  echo**, so the key never appears on the command line.
- **Status:** MITIGATED (deprecation + secure path). **Residual:** users on
  old habit or scripts still pass `--token`; history/process capture of the
  old flag remains until removal. Rotation of any key ever passed via `--token`
  is advised.

## T2. Plaintext secrets on disk

- **Scenario:** provider keys stored as plaintext in config or `.env`-style
  files readable by any local process/user.
- **Likelihood:** Medium — old flow wrote `OPENROUTER_API_KEY` plaintext to
  `$HERMES_HOME/.env`.
- **Impact:** High — local malware, shared machines, or a leaked repo/file
  exposes working keys.
- **Mitigation:** `lib/secrets.js` encrypted store: AES-256-GCM
  (`aes-256-gcm`, random 12-byte IV, auth tag) in `secrets.enc` under
  `AGENTSTACK_HOME`, keyed by a machine-local `.machine-key` (written mode
  0600). `providers.json` stores only `keychain://agentstack/<name>` refs —
  never the raw secret (enforced by test: `test/lib.test.js`
  "provider config stores ref not raw secret"). `lib/security.js`
  `providerConfig()` scans config for raw `sk-`/`AKIA`/`AIza` patterns and
  flags them.
- **Status:** MITIGATED for AgentStack-managed providers. **Residual:** (1)
  the key that encrypts the box sits next to the box (machine-local
  `.machine-key` — attacker with the same user account can decrypt; this is
  obfuscation-at-rest, not hardware security); (2) Hermes' own `$HERMES_HOME/.env`
  still holds `OPENROUTER_API_KEY` plaintext by design of the `install` flow —
  outside AgentStack's store; (3) Windows file modes are advisory (no POSIX
  0600 semantics) — `mode: 0o600` is best-effort there.

## T3. OpenClaw granted broad execution access

- **Scenario:** the OpenClaw bridge (`lib/bridges/runner.js` `openclaw()`) can
  run arbitrary commands; without gates, a prompt-injected or misdirected task
  executes anything.
- **Likelihood:** Medium — execution verbs route to OpenClaw by default in
  `lib/routing.js`.
- **Impact:** Critical — arbitrary code execution, file destruction,
  exfiltration.
- **Mitigation:** `lib/permissions.js`: default **deny/ask** for
  `process.execute` (and all non-read categories); `evaluate()` returns
  `{allowed: false|null, mode, reason}`; `promptApproval()` interactive
  approval (`y`=once, `a`=allow-for-project, default=deny); every decision
  logged to `config/permissions.json` (last 500) for `permissions audit`.
  `ask` surfaces `required_permissions: ['process.execute']` when routing to
  OpenClaw. `lib/security.js` `skills()` flags `curl|bash`, `chmod 777`,
  `sudo rm` in bundled skills.
- **Status:** PARTIAL. **Residual:** (1) `promptApproval` is a library
  function — the current CLI's `ask` path shells out through the legacy
  `bridges/` scripts and does not yet wire `evaluate()`/`promptApproval()` into
  the execution path end-to-end; (2) `allow_project`/`allow_permanent` reduce
  future friction by design — a session granted project-wide `process.execute`
  is as powerful as OpenClaw is; (3) no sandboxing (no container/VM/jail) — the
  permission gate is the only boundary.

## T4. Markdown-as-database corruption / ID collision

- **Scenario:** tasks stored in vault `Tasks.md` with IDs derived from open-task
  count → duplicate IDs after completion, or hand-edited Markdown corrupts the
  queue.
- **Likelihood:** High — the legacy `todo` flow did exactly this.
- **Impact:** Medium — lost/merged tasks, agents acting on wrong task IDs,
  trust erosion in the shared brain.
- **Mitigation:** `lib/tasks.js`: durable JSON store (`data/tasks.db`) keyed by
  **UUID** (`crypto.randomUUID()`) with monotonic `display` numbers;
  corruption handling backs up the file (`*.corrupt-<ts>`) and starts fresh;
  Markdown is an export **view** (`exportMarkdown`/`sync`), not source of
  truth; `migrateFromLegacy()` backs up then imports + dedupes old `Tasks.md`.
- **Status:** MITIGATED. **Residual:** `data/tasks.db` is JSON — a torn write
  (power loss mid-write) can still corrupt it (backup-then-reset mitigates,
  doesn't prevent); concurrent writers (two agents) have no locking; the
  Markdown view can drift from the store until `sync` runs.

## T5. Provider key theft via API/network

- **Scenario:** keys exfiltrated through the local API, provider adapters, or
  logs.
- **Likelihood:** Low–Medium.
- **Impact:** High.
- **Mitigation:** `lib/api.js` binds `127.0.0.1` only and **rejects
  non-loopback connections with 403**; the API exposes provider *status*
  (`configured/valid/…`), never keys; `lib/security.js` `scanSecrets()`
  redacts findings to the first 8 chars; no secrets are written to AgentStack
  logs.
- **Status:** MITIGATED (loopback-only, no key exposure in API).
  **Residual:** any process running as the same user can call the loopback API
  (no auth — by design); the encrypted store's key is on the same machine;
  provider requests themselves send `Authorization: Bearer` over TLS to
  third-party APIs (trust in the provider + TLS).

## T6. Config overwrite / destructive reinstall

- **Scenario:** `install`/`setup` clobbers existing Hermes config, `.env`, or
  vault content.
- **Likelihood:** Medium.
- **Impact:** High — losing provider configs, notes, or the task store.
- **Mitigation:** `bin/agentstack.js` `install`: preserves existing
  `config.yaml` and `.env` (only appends missing `OPENROUTER_API_KEY`);
  vault scaffold only creates missing dirs/files; `install.sh` documents
  "idempotent, never chmod 777, never sudo pip, never commits secrets" and
  `write_config`/`write_env` preserve existing files. `tasks.js` migration
  backs up before rewriting.
- **Status:** PARTIAL. **Residual:** no general backup/rollback subsystem yet
  (planned `repair` mode); the `.env` append path can still add a duplicate key
  line if the file has a variant spelling; a user-invoked `rm` of state dirs is
  out of scope.

## T7. Untrusted skills / prompt injection via skills

- **Scenario:** a downloaded or generated skill contains malicious shell
  commands (`curl | bash`, `chmod 777`, `sudo rm`) or prompt-injection text
  that steers an agent.
- **Likelihood:** Medium — skill ecosystems are third-party content.
- **Impact:** High — arbitrary command execution under the agent's permissions.
- **Mitigation:** `lib/security.js` `skills()` scans `skills/**` for suspicious
  patterns; `agentstack security skills|full` surfaces findings; docs policy:
  treat downloaded skills as untrusted until vetted (see `docs/SECURITY.md`);
  permission gates (T3) are the second line.
- **Status:** PARTIAL (shallow regex scan, no provenance tracking).
  **Residual:** regex scans miss obfuscated payloads; **no skill provenance
  (source/hash/review status) is recorded yet** — this is a roadmap P3 item;
  an injected skill that passes the scan and runs under an approved
  `allow_project` session is fully effective.

---

## Residual risk summary (honest)

1. **Machine-local key** = same-user attacker can decrypt `secrets.enc`.
   Mitigations that would help: OS keychain (keytar/cmdkey — stubbed today),
   DPAPI/TCC integration, hardware token.
2. **Permission gates are not yet wired end-to-end** in the CLI execution path
   (`ask` → legacy bridge scripts); `evaluate()`/`promptApproval()` exist and
   are tested as a library but the default deny/ask posture is not yet
   enforced on every execution route.
3. **No sandbox** for OpenClaw or skills; approval is a human-speed boundary.
4. **`.env` plaintext** for Hermes remains by design of the install flow —
   migrate to `provider add` + Hermes env-var indirection when possible.
5. **JSON stores** (tasks, permissions, providers) lack atomic-write/locking;
   corruption is detected-and-recovered, not prevented.

## What would move each to MITIGATED

- T2/T5: real OS keychain backend (keytar/cmdkey wired), keep encrypted-file
  fallback for headless Linux.
- T3/T7: enforce `evaluate()` + `promptApproval()` on every bridge call;
  add skill provenance (P3) and sandboxing.
- T4/T6: atomic writes (write-temp-rename), file locking, `repair` mode with
  backup→apply→verify→rollback (planned).
