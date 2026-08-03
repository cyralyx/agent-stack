# Architecture — how the three agents connect

```
                         ┌──────────────────────────────────────────────┐
                         │                 TELEGRAM                     │
                         │   (@your-bot  /  20+ other platforms)        │
                         └───────────────────┬──────────────────────────┘
                                             │  (Hermes gateway)
                                             ▼
                  ┌─────────────────────────────────────────────┐
                  │              HERMES  (the Brain)             │
                  │   orchestrator · memory · skills · manager   │
                  └──────┬───────────────────────┬───────────────┘
                         │                       │
            hermes-to-openclaw (bridge)   │  hermes-worker (bridge)
                         │                       │
                         ▼                       ▼
        ┌──────────────────────────┐   ┌──────────────────────────┐
        │    OPENCLAW (the Hands)  │   │   cheap Hermes worker    │
        │    executor / worker     │   │   (gpt-4o-mini)          │
        └──────────┬───────────────┘   └──────────┬───────────────┘
                   │                              │
                   └──────────┬───────────────────┘
                              ▼
        ┌─────────────────────────────────────────────┐
        │       OBSIDIAN VAULT  (the Shared Brain)     │
        │  AGENTS.md · Agent Hub/ · notes · playbooks  │
        │  read/write by BOTH agents — no secrets      │
        └─────────────────────────────────────────────┘
```

## Roles

- **Hermes = the Brain.** Runs in the terminal (CLI) and is reachable via
  Telegram through the gateway. Holds persistent memory, skills, and manages
  the stack. It is the orchestrator: when a task needs "hands" work, it
  delegates.
- **OpenClaw = the Hands.** A headless executor invoked via the
  `hermes-to-openclaw` bridge. It does the actual work and writes results back
  to the shared vault. It is chat-first, multi-channel, model-agnostic.
- **Obsidian = the Shared Brain.** The persistent knowledge both agents read
  and write, giving them cross-session and cross-agent memory. The vault's
  `AGENTS.md` is the contract governing all agents.

## The bridges

| Bridge | Direction | What it does |
|--------|-----------|--------------|
| `hermes-to-openclaw` | Hermes → OpenClaw | Calls OpenClaw headless (`openclaw infer model run --local`) to delegate a one-shot task |
| `hermes-worker` | Any agent → Hermes | Calls a cheap Hermes worker (`hermes chat -q --provider openrouter --model openai/gpt-4o-mini`) for sub-tasks |
| `vault-note` | Both → vault | Appends a note to the shared Obsidian brain |

## The hook

`openclaw-wife-reviewer` (agent:end): after Hermes replies, OpenClaw reviews
the answer against the shared-brain context and can post a second opinion.
This gives the stack a **self-check loop** — one agent verifies the other.

## Why the three make a good team

| | Hermes | OpenClaw |
|--|--------|----------|
| Core strength | orchestration, memory, skills, scheduling | chat-first always-on execution, 30+ channels |
| Best at | deciding WHAT and managing context | DOING the work fast |
| Complementary | the brain | the hands |

Together they form a "brain + hands" system with a single shared memory
(Obsidian) — which is exactly what was already wired on this machine.
