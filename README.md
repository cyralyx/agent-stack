# 🧠 AgentStack — Hermes × OpenClaw × Obsidian

**One repo. Six goals. Lower cost, better quality, a smarter ecosystem.**

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/cyralyx/agent-stack/actions/workflows/ci.yml/badge.svg)](https://github.com/cyralyx/agent-stack/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.1.0-orange.svg)](CHANGELOG.md)
[![Made by Cyralyx](https://img.shields.io/badge/made%20by-Cyralyx-8A2BE2.svg)](https://github.com/cyralyx)

The AgentStack is a complete personal AI-agent ecosystem that makes your
**Hermes (brain) + OpenClaw (hands) + Obsidian (shared brain)** work as one
tight system — cheaper, faster, and self-improving.

---

## 🎯 The six goals (your wish list, made real)

### 1. 💰 Lower API cost · improved quality
- **Cost-per-verified-success** as the north-star metric (not raw tokens).
- Cheap workers deliberate; quality reviewer only where it matters.
- Budget guardrails on OpenRouter (spend limits, prompt-injection flag, no-latency safety).
- Cache discipline: keep conversations alive, avoid `/reset` churn.

### 2. 🏛️ Better council system
- **Council v2** — Karpathy 3-stage with role separation + **real cost tracking per verdict**:
  - Stage 1: cheap workers (`qwen`/`gpt-oss-20b:free`) collect independent answers
  - Stage 2: anonymous peer-ranking (kills model-prestige bias)
  - Stage 3: chairman synthesizes (`kimi-k3` only on hard cases)
  - Every run records: members, models, token cost, verdict, and cost-per-verified-success.

### 3. 🔗 Better ecosystem: Hermes ↔ OpenClaw ↔ Obsidian
- **Hermes = the brain** (orchestrator/memory/skills), **OpenClaw = the hands** (executor),
  **Obsidian = the shared brain** (persistent knowledge both read/write).
- Bridges: `hermes-to-openclaw`, `hermes-worker`, `vault-note`.
- The `stack` CLI drives all three from one terminal; Telegram reaches them all.

### 4. 🖥️ Better terminal commands & skills
- Curated **terminal-tools** skill set: fast, safe, effective commands.
- `stack` CLI as the one command for the whole ecosystem.

### 5. 🎓 Learning skills — any task + general health
- **Per-task learning**: after any task, capture "what worked / what didn't" into a
  task-learning log; next time the same task is faster.
- **General health skills**: system hygiene, disk/GPU/memory watch, cleanup routines.

### 6. 🚀 A nice GitHub project
- Everything here, versioned, documented, public — ready for others to fork.

---

## 🏗️ Repo layout

```
agent-stack/
├── README.md              # ← you are here
├── VISION.md              # the six-goal spec (source of truth)
├── bin/
│   └── stack              # one CLI for the whole ecosystem
├── bridges/
│   ├── hermes-to-openclaw # Hermes → OpenClaw handoff
│   ├── hermes-worker      # cheap Hermes worker (reverse direction)
│   └── vault-note         # append to the Obsidian shared brain
├── council/
│   └── council_v2.py      # better council: role separation + cost tracking
├── skills/
│   ├── learning/          # per-task + general-health learning skills
│   ├── terminal/          # curated fast terminal commands
│   └── ecosystem/         # Hermes↔OpenClaw↔Obsidian patterns
├── hooks/
│   └── openclaw-wife-reviewer  # second-opinion self-check loop
├── config/
│   ├── hermes.config.yaml # Hermes config template (no secrets)
│   └── hermes.env.example # env var names (fill your own)
├── docs/
│   ├── ARCHITECTURE.md    # how the three agents connect
│   ├── COUNCIL.md         # the better council spec
│   ├── LEARNING.md        # the learning-system spec
│   ├── COST.md            # cost-optimization playbook
│   ├── SETUP.md           # bring up the whole stack
│   └── CLI.md             # stack CLI reference
└── .github/
    └── workflows/ci.yml   # validate the repo on push
```

---

## 🚀 Quick start

```bash
git clone <repo-url> agent-stack && cd agent-stack
./setup.sh                 # provision Hermes + OpenClaw + vault + Telegram
stack status               # verify everything is up
```

## 📡 Reach everything from Telegram

The Hermes gateway connects to Telegram. Message the bot → reaches the brain;
ask it to delegate → hands (OpenClaw) do the work; answers draw on the shared
brain (Obsidian).

---

## 🤝 License

MIT — free to use, fork, and build on.
