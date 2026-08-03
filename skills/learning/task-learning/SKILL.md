---
name: task-learning
description: "Learn from any task — capture what worked, what didn't, and the fastest path, so the same task is faster and better next time. Use after completing any non-trivial task, when a task failed and you want to avoid repeating the mistake, or when you want to build a personal task-playbook."
version: 1.0.0
author: AgentStack
license: MIT
---

# Task Learning — learn from every task

The goal: **every task makes the next one cheaper and better.** After any
non-trivial task, capture a compact learning entry so the same task type gets
faster, cheaper, and higher-quality over time.

## When to use

- After completing a task that took 5+ tool calls or had friction.
- After a failure or a "should have done X first" moment.
- When the user asks "learn from that" or "make this faster next time."
- During a task when you realize a shortcut that would have helped.

## The learning log

Every learning entry is a short markdown block. Keep it TELEGRAPH — one to
three lines. Write to:
`Agent Hub/Research/Task Learning/<task-slug>.md` in the Obsidian vault
(or `~/AppData/Local/hermes/context-cache/learning/<task-slug>.md`).

## Format (one block per task, append-style)

```markdown
# <Task slug>  —  <date>

## What worked
- ...

## What didn't
- ...

## Fastest path (next time)
1. ...
2. ...

## Cost / quality note
- tokens/cost if known, quality observations
```

## Rules

1. **Only log non-obvious learnings.** Don't log "I used write_file" — log
   "write_file failed on X path format, use forward slashes".
2. **Prefer the fix over the description.** If the learning is "X failed", the
   next line must be the fix or workaround.
3. **Keep it small.** If a learning is bigger than ~10 lines, it belongs in a
   skill, not the log.
4. **Promote to skill:** when the same learning appears 2-3 times or is clearly
   reusable, propose creating/updating a real skill.

## Verification

After logging, next time the same task appears, read the log first (search
`Task Learning/` for the slug). That's where the speed comes from.
