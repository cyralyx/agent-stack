# Learning System — learn from every task, plus general health

Two complementary learning loops, both cheap and durable.

## 1. Per-task learning

After any non-trivial task, log what worked / what didn't / the fastest path
into the **Task Learning log** (`skills/learning/task-learning/SKILL.md`).

- Log location: `Agent Hub/Research/Task Learning/<task-slug>.md` (Obsidian shared brain)
- Format: compact markdown (what worked / what didn't / fastest path / cost note)
- **Promotion rule:** a learning that recurs 2-3 times becomes a real skill.

This makes the same task type **cheaper and faster every time** — the
definition of "learning skills for any given task."

## 2. General health

`skills/learning/system-health/SKILL.md` gives a cheap, non-destructive health
routine: disk / memory / GPU / agent-stack services / vault reachability.

- Run it when asked, or on a cron (e.g. daily at 9am).
- Never destructive without approval (user rule).

## How the loops reinforce each other

```
Task happens
  → learn (log what worked)
  → same task next time reads the log first → faster + cheaper
  → recurring learning promoted to a skill → whole stack improves
  → health checks keep the machine/stack ready so tasks don't fail on infra
```

## Cost discipline

- Learning entries are tiny (≤10 lines) — negligible token cost.
- Reading the log first saves more tokens than the log costs.
- Health checks are pure shell (no LLM) — free.
