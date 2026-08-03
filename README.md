# 🤖 Agent Stack — Hermes + OpenClaw + Obsidian (Telegram-controlled)

A **full stack harness** that unifies three agents into one system you drive
from the **terminal** and reach from **Telegram** (or any of 20+ messaging
platforms).

| Agent | Role | Surface | Driven from |
|-------|------|---------|-------------|
| **Hermes** | 🧠 The Brain — orchestrator, memory, skills, manager | CLI + Telegram gateway | Terminal (`hermes`) & Telegram |
| **OpenClaw** | 🦞 The Hands — executor / worker | headless CLI | Terminal (`stack run openclaw …`) |
| **Obsidian** | 🗂️ The Shared Brain — persistent knowledge | vault on disk | Both agents read/write |

Everything is **wired together** so one command from the terminal — or one
message on Telegram — reaches the whole stack. The agents talk to each other
through the shared Obsidian vault and through the bridge scripts.

---

## ✨ What you get

- **One repo** that defines and provisions the whole stack on a fresh machine.
- **`stack` CLI** — a single entry point to drive every agent from the terminal.
- **Telegram front door** — message one bot, both agents are reachable.
- **Shared memory** — the Obsidian vault is the persistent brain both agents
  read and write, so nothing is lost across sessions or agents.
- **Hermes → OpenClaw handoff** — Hermes delegating a task to OpenClaw as the
  executor, via the bridge scripts.
- **OpenClaw → Hermes worker** — cheap CLI Hermes worker for sub-tasks.

---

## 🚀 Quick start (fresh machine)

```bash
git clone <your-repo-url> agent-stack && cd agent-stack
./setup.sh                # interactive: detect/install all three + Telegram
stack status              # verify everything is up
```

See [`docs/SETUP.md`](docs/SETUP.md) for the step-by-step, and
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how the pieces connect.

---

## 🖥️ The `stack` CLI

Central command for the whole stack (see [`docs/CLI.md`](docs/CLI.md) for all).

```bash
stack status                # health of all three agents + Telegram + vault
stack hermes "task"         # one-shot task for Hermes (brain)
stack openclaw "task"       # one-shot task for OpenClaw (hands)
stack ask "question"        # route by intent: vault/quick → brain/hands
stack note "add note to brain"  # write to the shared Obsidian vault
stack telegram on/off/status  # manage the Telegram gateway (on Hermes)
stack doctor                # diagnose the whole stack
```

---

## 📡 Reach everything from Telegram

The **Hermes gateway** connects to Telegram (`@<your-bot>`). Once it's up:

- **Message the bot** → goes to Hermes (the brain).
- Ask Hermes to **delegate to OpenClaw** → Hermes hands the task to OpenClaw
  via the bridge, OpenClaw does the work, reads/writes the vault.
- Ask about **your vault/notes** → Hermes (or OpenClaw) answers from Obsidian.

---

## 🧠 The shared brain (Obsidian vault)

Both Hermes and OpenClaw read/write the same vault. It holds:
- an `AGENTS.md` contract for all agents,
- an `Agent Hub/` core: decisions, working patterns, skills registry,
  playbooks, context snapshots, research.

---

## 🗂️ Repo layout

```
agent-stack/
├── README.md                # ← you are here
├── setup.sh                 # one-command full-stack provisioning
├── install/
│   ├── install-hermes.sh    # install/verify Hermes
│   ├── install-openclaw.sh  # install/verify OpenClaw
│   ├── install-vault.sh     # detect/init the Obsidian vault
│   └── link-bridges.sh      # symlink ~/bin bridge scripts
├── bin/
│   ├── stack                # the central CLI (bash, no deps)
│   └── stack.cmd            # Windows cmd wrapper
├── bridges/
│   ├── hermes-to-openclaw   # Hermes → OpenClaw handoff script
│   ├── hermes-worker        # OpenClaw/CLI → cheap Hermes worker
│   └── vault-note           # append a note to the shared vault
├── config/
│   ├── hermes.config.yaml   # Hermes config template (no secrets)
│   └── hermes.env.example   # secret key names (fill in your own)
├── hooks/
│   └── openclaw-wife-reviewer  # agent:end hook: OpenClaw reviews replies
├── docs/
│   ├── SETUP.md             # step-by-step provisioning guide
│   ├── ARCHITECTURE.md      # how the three agents connect
│   └── CLI.md               # full stack CLI reference
└── .gitignore
```

---

## 🔐 Security

- **No secrets in this repo.** Secrets (`TOKEN`, `API_KEY`) live in each
  agent's own env file / secret store. We only ship the **names** of the env
  vars you need to fill in.
- The vault's `AGENTS.md` contract forbids storing secrets in notes.
- Telegram tokens and API keys are never committed. See
  [`docs/SECURITY.md`](docs/SECURITY.md).

---

## 🧭 Next steps / roadmap

- [ ] Push this repo to GitHub for portability
- [ ] Wire more Telegram routes (OpenClaw as a separate bot or same-bot routing)
- [ ] Add a `stack install` that auto-configures the gateway from prompts
- [ ] Containerize for server (ZimaBlade) deployment

See [`docs/ROADMAP.md`](docs/ROADMAP.md).
