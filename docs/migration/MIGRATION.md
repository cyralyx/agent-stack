# Migration Guide — Markdown tasks → durable task store

In v0.2.0, AgentStack moved task storage from a fragile Markdown file
(`Obsidian Vault/Agent Hub/Tasks.md`) to a **durable JSON store** keyed by
stable UUIDs (`data/tasks.db.json` under the AgentStack data dir). Markdown is
now an **export/sync view**, not the source of truth.

## Why

The old system derived task IDs from the **count of open tasks**. Completing a
task changed the count and could produce **duplicate IDs**, corrupting the
queue. The new store assigns each task a stable UUID + a monotonically
increasing display number that never changes, even after completion.

## To migrate existing tasks

```bash
# 1. (Recommended) back up first — migration also auto-backs up:
agentstack task migrate

# 2. Verify:
agentstack task list            # both open and completed should appear

# 3. Re-export the Markdown view (optional, view not source of truth):
agentstack task export
```

The migration:
- backs up the legacy `Tasks.md` to `Tasks.md.bak-<timestamp>`
- imports every open and completed task
- dedupes by title so nothing is double-imported
- writes a fresh Markdown view

## Rollback

If the migration needs undoing:
1. The original `Tasks.md` backup is at `Tasks.md.bak-<timestamp>`.
2. Delete the new store: remove `data/tasks.db.json` under the AgentStack
   data dir (Windows: `%LOCALAPPDATA%\Cyralyx\AgentStack\data\`).
3. Restore `Tasks.md` from the backup.

This never deletes your vault notes or any user data outside the AgentStack
data directory.

## `todo` compatibility alias

`agentstack todo` is kept as a **compatibility alias** for `agentstack task`
so existing scripts keep working. New work should use `agentstack task`.

## Configuration backup

Provider config and permissions are stored under the AgentStack config dir:
- `config/providers.json` — provider definitions (secret **refs**, never raw keys)
- `config/permissions.json` — permission policy + decision log

These are not touched by task migration.
