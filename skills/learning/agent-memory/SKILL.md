---
name: agent-memory
description: "Structured agent memory for the AgentStack, inspired by mem0 / Hindsight / OpenViking. Use when deciding how to store, retrieve, and evolve knowledge in the Obsidian vault so the stack gets smarter over time. Covers memory tiers, retroactive learning, and context engineering."
version: 1.0.0
author: AgentStack
license: MIT
---

# Agent Memory — structured, evolving knowledge

The AgentStack shares an Obsidian vault as its brain. This skill applies the
patterns from the top agent-memory projects (mem0, Hindsight, OpenViking) to
make that brain **structured and self-improving** instead of a flat pile of
notes.

## Memory tiers

| Tier | Vault location | Purpose | Written by |
|---|---|---|---|
| **Short-term** | `Agent Hub/Daily Notes/` | Today's task state | Both agents |
| **Working** | `Agent Hub/Interop/` | Role contract, current state, ledger | Both agents |
| **Long-term** | `Agent Hub/Research/` + skills | Durable knowledge, playbooks | Hermes |
| **Episodic** | `Agent Hub/Research/Task Learning/` | What worked on past tasks | Hermes |

## Retroactive learning (Hindsight pattern)

Don't just log at task time — **revisit past notes when a new task completes**:

1. After a task, check `Task Learning/` for a matching slug.
2. Update the old entry with "this time, X worked better than Y".
3. When the same learning appears 2-3 times → promote to a real skill.

This is how memory *learns* rather than just *stores*.

## Context engineering (OpenViking pattern)

Treat the vault as a **context database**, not a folder of files:

- **Frontmatter tags** on every note (topic, agent, status, date).
- **Search before read** — `rg`/`ctx_search` the vault before reading files.
- **Excerpt before full** — pull the relevant 20 lines, not the whole file.
- **Indexes over dumps** — for "everything about X", build an index note that
  links/describes, not a giant paste.

## Retrieval discipline

```bash
# find the note that knows about X (fast, cheap)
rg -l "X" "Agent Hub/" | head

# then read only the relevant excerpt
# (use ctx_read_excerpt / ctx_smart_read in Hermes)
```

## Pitfalls

- **No delete without approval** (user rule) — memory is append-only.
- **Don't log trivia** — only non-obvious learnings (task-learning rule).
- **Don't let memory bloat** — promote to skill or archive; the vault is not a
  dump site.
- **Both agents must respect the same tags** or retrieval breaks — keep the
  shared tag list in `Agent Hub/Interop/Role Contract.md`.
