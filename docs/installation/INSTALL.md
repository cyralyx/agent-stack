# Installation Guide

AgentStack is designed around **non-destructive, detect-first installation**.
It never overwrites your vault, notes, credentials, or configuration without an
explicit confirmed action.

## Modes

| Mode | Command | What it does | Changes system? |
|------|---------|--------------|-----------------|
| Detect-only | `agentstack doctor` | Checks components, providers, compat; exit code reflects health | Never |
| Guided setup | `agentstack setup` | Explains what exists and what's next; does not auto-modify | No (detect-only) |
| One-shot install | `agentstack install` | Writes AgentStack state dirs, config template, links CLI | Yes (AgentStack state only) |
| Non-interactive | `agentstack setup --config setup.json` | **Planned** — deployment from a JSON policy file | Yes (explicit) |
| Repair | `agentstack repair [--yes]` | Diagnoses, proposes fixes, backs up, applies only safe fixes | Only safe fixes, with confirmation |
| Uninstall | `agentstack uninstall` | Leaves the system; never deletes vault/notes/credentials/tasks | No user data deleted |

## Quick start

```bash
# 1. Install the CLI
npm i -g agentstack          # or use install.sh from a checkout

# 2. Detect (never changes anything)
agentstack doctor --json

# 3. Configure a provider securely (hidden input, no CLI secret)
agentstack provider add openrouter

# 4. Verify
agentstack status
agentstack compatibility
```

## What `install` writes

- `AGENTSTACK_HOME` state dirs (Windows:
  `%LOCALAPPDATA%\Cyralyx\AgentStack`; macOS:
  `~/Library/Application Support/AgentStack`; Linux:
  `$XDG_CONFIG_HOME/agentstack` or `~/.config/agentstack`).
- Provider config with **secret references** (`keychain://agentstack/<name>`),
  never raw secrets (`lib/secrets.js` writes `providers.json`).
- CLI links in `~/bin` (or the npm global bin).

It does **not** modify Hermes' config, OpenClaw, or your vault.

## Repair

`agentstack repair` is the safe path when something is broken:

1. **Diagnose** — runs the same checks as `doctor`.
2. **Propose** — lists the fixes it would apply, marking destructive ones.
3. **Back up** — creates backups before touching anything.
4. **Apply** — applies only approved (non-destructive) fixes.
5. **Verify** — re-runs `doctor`.
6. **Rollback** — via the backups created in step 3.

Run `agentstack repair` without `--yes` to see the proposal first.

## Uninstall

`agentstack uninstall` deliberately does **not** delete:

- your vault / notes,
- your credentials / provider keys,
- your task history,
- your config backups.

It tells you where AgentStack state lives (in case you want to remove it
manually) and reminds you to remove the package from the registry. Purging user
data requires an explicit, deliberate action that is intentionally **not**
supported by a flag.

## First-run workspace selection

AgentStack supports **any Markdown workspace folder** — it does not require an
Obsidian vault named "Obsidian Vault". Set `STACK_VAULT` to your folder:

```bash
export STACK_VAULT=/path/to/any/markdown/workspace
agentstack task add "first task"
```

Obsidian compatibility is preserved (the `.obsidian` dir and `AGENTS.md` are
recognised) but Obsidian itself is optional.
