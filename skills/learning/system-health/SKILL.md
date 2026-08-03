---
name: system-health
description: "General health checks for the machine + agent stack — disk, memory, GPU, key services, and quick fixes. Use when the user asks about system health, 'is everything okay', performance problems, or wants a health-check routine. Also covers agent-stack health: Hermes gateway, OpenClaw, Obsidian vault reachability."
version: 1.0.0
author: AgentStack
license: MIT
---

# System Health — general health & hygiene

A lightweight health routine for the machine and the agent stack. Fast,
cheap, non-destructive.

## When to use

- User asks "is everything ok?" / "system health" / "why is it slow"
- Scheduled health check (cron-friendly)
- Before heavy work (check disk/mem headroom)

## Core checks (in order)

### 1. Machine
```bash
# disk
df -h / 2>/dev/null || wmic logicaldisk get size,freespace,caption
# memory
free -h 2>/dev/null || systeminfo | grep -iE "memory"
# CPU/GPU load (Windows)
tasklist | sort /R /+65 | head -8
# GPU (NVIDIA)
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv 2>/dev/null || echo "no nvidia-smi"
```

### 2. Agent stack
```bash
hermes gateway status 2>&1 | grep -iE "process|running|not" | head -3
stack status 2>&1 | head -10     # if the stack CLI is installed
# vault reachable?
ls "/c/Users/willi/Documents/Obsidian Vault/Agent Hub" >/dev/null 2>&1 && echo "vault OK" || echo "vault MISSING"
# openclaw pkg present?
ls "$APPDATA/npm/node_modules/openclaw/openclaw.mjs" >/dev/null 2>&1 && echo "openclaw OK" || echo "openclaw MISSING"
```

### 3. Quick hygiene (only if user asks / something is wrong)
- Clear temp files: `rm -rf "$TMP"/* 2>/dev/null` (safe-ish; check first)
- Prune hermes old sessions: `hermes sessions prune --older-than 30`
- Check big logs: `ls -la ~/AppData/Local/hermes/logs/ | sort -k5 -h | tail -5`

## Pitfalls
- Do NOT run destructive cleanup without asking first (user rule).
- `rm -rf` on temp dirs: verify path first — never on user data.
- On Windows via git-bash: `df -h /` works for the MSYS root; use `wmic`
  for real drive stats.
- GPU check needs `nvidia-smi` on PATH (usually `C:\Windows\System32\nvidia-smi.exe`).

## Output shape
```
Machine: disk OK (X free), mem OK (X free), GPU OK (X/Y used)
Stack: hermes gateway RUNNING, openclaw OK, vault OK
Hygiene: nothing needed / <one action>
```
