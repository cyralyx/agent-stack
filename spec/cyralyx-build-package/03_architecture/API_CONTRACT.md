# API Contract

Use a versioned local API even when desktop UI and backend ship together. This prevents UI code from directly depending on storage internals.

## Minimum resource groups

- `/v1/projects`
- `/v1/conversations`
- `/v1/tasks`
- `/v1/events`
- `/v1/providers`
- `/v1/models`
- `/v1/tools`
- `/v1/permissions`
- `/v1/notes`
- `/v1/search`
- `/v1/memory`
- `/v1/skills`
- `/v1/mcp-servers`
- `/v1/automations`
- `/v1/settings`

## API rules

- Use generated or shared types.
- Validate all inputs at the boundary.
- Return stable machine-readable error codes.
- Use cursor pagination for event and search collections.
- Support cancellation of streaming requests.
- Require idempotency keys for create operations that may be retried.
- Never return raw provider secrets.
- Make project scope explicit in every mutating request.
- Keep desktop-only privileged operations behind a separate capability bridge.

## Streaming

Use WebSocket or SSE based on an ADR. Streaming must support:

- reconnect with last event ID;
- ordered delivery;
- task cancellation;
- backpressure;
- heartbeat;
- redacted logs;
- graceful shutdown.
