---
name: terminal-fast-commands
description: "Curated fast, safe terminal commands for the AgentStack — Windows/git-bash aware. Use when the user wants quick terminal answers, efficient shell patterns, or asks for 'better terminal commands'. Includes speed/cost tips and safety rules."
version: 1.0.0
author: AgentStack
license: MIT
---

# Terminal Fast Commands

A curated set of **fast, safe, effective** shell patterns for this stack
(Windows 11 + git-bash/MSYS, with Linux server skills where noted).

## Speed patterns

```bash
# Search code FAST (ripgrep beats grep)
rg "pattern" -n path/            # grep -r replacement
rg --files path/ | head           # list files fast

# Find files by name FAST
fd "name" path/                   # find -name replacement
fd -e py                          # all .py under cwd

# Disk usage top
du -sh */ 2>/dev/null | sort -h | tail -10
# or Windows:  wmic logicaldisk get size,freespace,caption

# Kill a process by name (Windows)
taskkill //F //IM process.exe     # note: git-bash needs //
# or:  powershell -Command "Stop-Process -Name process"

# List open ports
netstat -ano | grep LISTEN | head -20
```

## Agent-stack fast commands

```bash
stack status                 # whole ecosystem health
stack hermes "task"          # the brain
stack openclaw "task"        # the hands
stack note "remember X"      # write to the shared Obsidian brain
stack marry "task"           # head-boss workflow (plan→delegate→verify→sync)

# Hermes quick
hermes chat -q "question"    # one-shot (no interactive session)
hermes --version
hermes gateway status

# OpenClaw quick
node "$APPDATA/npm/node_modules/openclaw/openclaw.mjs" --version
```

## Safety rules (non-negotiable)

1. **Never `rm -rf` user data without checking the exact path first.**
2. **Never chmod 777.** Use `chmod +x` only.
3. **Never sudo pip** (user rule). Use venv / `--user`.
4. **Git-bash specifics:** Windows flags need `//` prefix (e.g. `taskkill //F`),
   and `find`/`grep` work but `fd`/`rg` are much faster if installed.
5. **Pipe git output to `cat`** if it might page (e.g. `git log | cat`).

## Cost tip

Prefer `rg`/`fd`/`head`/`wc` over dumping whole files — the agent pays per
token read. Search → excerpt → full-read, in that order.
