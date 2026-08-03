# `stack` CLI reference

`stack` is a dependency-free bash CLI for the whole agent stack.

## Commands

### `stack status`
Health check for every component — Hermes, OpenClaw, the vault, the bridges,
and the Telegram gateway. Example output:
```
═══ Agent Stack Status ═══
  ✓ Hermes (brain):     /c/Users/willi/AppData/Local/hermes/hermes-agent/venv/Scripts/hermes.exe
  ✓ OpenClaw (hands):   /c/Users/willi/AppData/Roaming/npm/node_modules/openclaw/openclaw.mjs
  ✓ Obsidian vault:     /c/Users/willi/Documents/Obsidian Vault
  ✓ bridge: hermes-to-openclaw
  ✓ bridge: hermes-worker
  ✓ bridge: vault-note
  ✓ Telegram gateway:   running
```

### `stack hermes "<task>"`
One-shot task for Hermes (the brain) via `hermes chat -Q -q`.

### `stack openclaw "<task>"`
One-shot task for OpenClaw (the hands) via the node+`.mjs` invocation.

### `stack ask "<question>"`
Route a question. Defaults to the brain (Hermes). (Planned: intent-based
routing so execution-style asks go to the hands.)

### `stack note "<note>"`
Append a note to the shared Obsidian brain (`vault-note` bridge). Writes to a
dated daily note under `Agent Hub/Daily Notes/`.

### `stack telegram on|off|status`
Start / stop / check the Hermes Telegram gateway.

### `stack doctor`
Full diagnosis: status + versions (hermes, node, openclaw pkg).

### `stack help`
This reference.

## Environment overrides

| Var | Default | Meaning |
|-----|---------|---------|
| `HERMES_BIN` | auto-detect | Path to the `hermes` executable |
| `OPENCLAW_MJS` | auto-detect | Path to `openclaw.mjs` |
| `NODE_BIN` | `C:/Program Files/nodejs/node.exe` | Path to node.exe |
| `STACK_VAULT` | `C:/Users/willi/Documents/Obsidian Vault` | Shared vault path |
| `BIN_LINK_DIR` | `~/bin` | Where bridges/stack get linked |

## Layout

```
bin/stack               the CLI
bridges/hermes-to-openclaw
bridges/hermes-worker
bridges/vault-note
```
