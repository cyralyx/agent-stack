# System Architecture

## Preferred high-level design

### Applications

- `apps/desktop` — Tauri + React desktop shell
- `apps/web` — optional browser client
- `apps/server` — local or hosted API and orchestration
- `apps/cli` — diagnostics, automation, import/export
- `apps/gateway` — messaging and remote access

### Core packages

- `agent-runtime`
- `council-runtime`
- `task-engine`
- `model-router`
- `provider-adapters`
- `tool-runtime`
- `skill-runtime`
- `mcp-runtime`
- `memory-engine`
- `knowledge-engine`
- `search-engine`
- `permissions`
- `sandbox`
- `scheduler`
- `event-bus`
- `plugin-sdk`
- `database`
- `shared-types`
- `ui-system`
- `observability`

## Technology preferences

- TypeScript for shared contracts and UI
- React for interface
- Tauri for desktop unless research proves Electron is necessary
- Rust for sensitive local-system bridges where useful
- Python only where AI ecosystems materially benefit
- SQLite for local mode
- PostgreSQL for optional server mode
- Markdown for portable notes
- WebSockets or SSE for live execution events
- Docker Compose for self-hosting

## Architecture rules

- Typed contracts between modules
- No circular package ownership
- Provider-specific code stays inside adapters
- Agent state is durable
- Tasks are resumable
- External content is untrusted
- UI never receives raw secrets
- Plugins receive capabilities, not unrestricted internals
