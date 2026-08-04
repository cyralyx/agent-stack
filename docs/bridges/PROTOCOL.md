# Bridge Protocol — typed envelope contract

Every bridge invocation in AgentStack produces a **typed envelope** that is
validated against a fixed schema before being trusted. This is the contract
between the orchestration layer (`lib/bridges/`) and the execution backends
(Hermes, OpenClaw, mock).

Implementation: `lib/bridges/schema.js` (contract) and
`lib/bridges/runner.js` (adapters). Tests: `test/bridges.test.js`.

## 1. Envelope schema

`PROTOCOL_VERSION = '1.0'` (`lib/bridges/schema.js`).

```jsonc
{
  "version": "1.0",          // string; must equal PROTOCOL_VERSION
  "request_id": "uuid",      // string, non-empty; crypto.randomUUID()
  "bridge": "hermes",        // string; which adapter produced this
  "status": "success",       // one of the 6 statuses below
  "started_at": "ISO-8601",  // string
  "completed_at": "ISO-8601",// string
  "input": { "task": "..." },// object — the request
  "result": {                // object (required on success/partial)
    "summary": "string",     // short summary (first ~200 chars of output)
    "output": "string",      // full output text
    "artifacts": []          // array of artifact references
  },
  "usage": {},               // object (optional; token/usage metadata)
  "errors": []               // array of { code, message } — empty on success
}
```

Validation rules (`schema.validate(envelope)`):

| Rule | Failure |
|------|---------|
| envelope not null | `envelope is null` |
| `version === '1.0'` | `version mismatch: …` |
| `request_id` is non-empty string | `missing request_id` |
| `bridge` present | `missing bridge` |
| `status` ∈ STATUS list | `invalid status: …` |
| `result` is object (if present) | `result must be an object` |
| `errors` is array (if present) | `errors must be an array` |
| `usage` is object (if present) | `usage must be an object` |

Builders: `schema.success(...)`, `schema.failure(...)`, `schema.timedOut(...)`;
`schema.newRequestId()` returns a UUID.

## 2. Status values

Defined in `lib/bridges/schema.js`:

| Status | Meaning | Produced by |
|--------|---------|-------------|
| `success` | Completed with exit 0 and output | `runBridge` exit 0; `mock` default |
| `partial` | Completed with caveats (reserved; no producer yet) | — |
| `failed` | Non-zero exit or transport error | `runBridge` non-zero → `BRIDGE_ERROR`; spawn throw → `PROVIDER_UNAVAILABLE`; `mock` failure mode |
| `cancelled` | Aborted via signal (e.g. caller `AbortSignal`) | `runBridge` spawn throw with `signal.aborted` → code `CANCELLED` |
| `timed_out` | Exceeded the timeout window | `runBridge` `ETIMEDOUT` (default 120 000 ms, `maxBuffer` 10 MiB) → code `TIMEOUT`; `mock` timeout mode |
| `awaiting_approval` | Blocked on a permission decision (reserved; no producer yet — see `docs/permissions/GUIDE.md`) | — |

`partial` and `awaiting_approval` are part of the contract today so consumers
can handle them; no adapter emits them yet.

## 3. Versioning rules

- `PROTOCOL_VERSION` is the single source of truth: **1.0**.
- An envelope whose `version` does not equal `PROTOCOL_VERSION` **fails
  validation** — mismatched producers/consumers must not silently interoperate.
- Bump policy: additive fields may land in a minor version without breaking
  consumers that validate; any change to required fields, status values, or
  semantics of existing fields requires a major version bump and a
  compatibility entry in `lib/compatibility.js` `REGISTRY.agentstack`
  (`bridge_protocol: '1.0'`).
- `compatibility` reports the protocol version in `doctor` output
  (`component: bridge_protocol`).

## 4. Adapters (`lib/bridges/runner.js`)

### `runBridge({ bridge, task, cmd, args, timeoutMs, signal })` — generic runner

`spawnSync` (no shell; `encoding: utf8`), outcome → envelope:

- spawn throws → `failed` (`PROVIDER_UNAVAILABLE`), or `cancelled`
  (`CANCELLED`) if the caller's `AbortSignal` fired.
- `status === null` / `signal` / `error` → `timed_out` (`TIMEOUT`) on
  `ETIMEDOUT`, else `failed` (`PROVIDER_UNAVAILABLE`).
- non-zero exit → `failed` (`BRIDGE_ERROR`, stderr/stdout trimmed to 500 chars).
- exit 0 → `success` (summary = first 200 chars, output = full stdout).

### `hermes(task, opts)` — brain adapter

- Resolves the Hermes binary (`findHermes()`: checks `HERMES_HOME` venv
  candidates, then `PATH`).
- Invokes: `hermes chat -Q -q <task> --provider <openrouter> --model
  <openai/gpt-4o-mini> --source agentstack-bridge`.
- Missing binary → `failed` (`PROVIDER_UNAVAILABLE`, "hermes not found").

### `openclaw(task, opts)` — hands adapter

- Resolves via `platform.resolveCommand('openclaw')`.
- Invokes: `openclaw <task>`.
- **The caller must permission-gate before invoking** — this adapter performs
  no gating itself (see `docs/permissions/GUIDE.md`).

### `mock(task, { mode })` — deterministic test adapter

- `mode: 'success'` (default) → `success` envelope, output
  `mock result for: <task>`.
- `mode: 'failure'` → `failed` (`BRIDGE_ERROR`).
- `mode: 'timeout'` → `timed_out` with the given `timeoutMs`.

## 5. Error taxonomy

Bridge envelopes carry `errors: [{ code, message }]`; codes come from the
provider error taxonomy in `lib/providers/errors.js`:

| Code | Meaning |
|------|---------|
| `AUTHENTICATION_FAILED` | 401/403 — bad/expired key |
| `RATE_LIMITED` | 429 — back off |
| `PROVIDER_UNAVAILABLE` | 502/503/network — backend down |
| `INVALID_REQUEST` | 400-class request error |
| `MODEL_NOT_FOUND` | 404 model/endpoint |
| `TOOL_CALL_UNSUPPORTED` | tools requested, backend can't |
| `CONTEXT_LIMIT_EXCEEDED` | context window overflow (400 mapping) |
| `TIMEOUT` | request exceeded timeout |
| `CANCELLED` | aborted by caller |
| `MALFORMED_RESPONSE` | unparseable backend response |
| `UNKNOWN_PROVIDER_ERROR` | everything else |
| `BRIDGE_ERROR` | non-zero bridge exit (bridge-local; used by runner) |

`toTypedError(status, detail)` maps provider statuses (401/403/429/404/400/
502/503, names) to codes; `ProviderError` carries `code` + `meta`.

## 6. Contract guarantees

1. Every adapter returns a **validated envelope** (validated in tests via
   `schema.validate`).
2. Adapters never throw across the boundary — failures are envelopes.
3. Secrets never appear in envelopes (inputs are task text; usage is numeric).
4. `partial` and `awaiting_approval` must be handled by consumers even though
   no adapter emits them yet.

## 7. See also

- `lib/bridges/schema.js`, `lib/bridges/runner.js`, `test/bridges.test.js`.
- `docs/architecture/ARCHITECTURE.md` (§4 bridges).
- `docs/permissions/GUIDE.md` — where `awaiting_approval` will be produced.
