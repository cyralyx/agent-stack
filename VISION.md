# VISION — AgentStack: cheaper, better, self-improving

**One personal-AI ecosystem: Hermes (brain) × OpenClaw (hands) × Obsidian
(shared brain).** The six goals, the why, and how they reinforce each other.

## 1. Lower API cost · improved quality
Cost is a *function of design*, not luck:
- cheap workers for bulk, quality models only where they pay for themselves
- cache discipline (long conversations, no mid-context toolset churn)
- cost-per-verified-success as the metric, not tokens
- budget guardrails so nothing can silently blow past

## 2. Better council system
Council v2 = cheap workers deliberate → anonymous peer-rank → chairman
synthesizes, with **real cost tracking per verdict**. The expensive chairman is
reserved for hard cases; routine questions use a 15x cheaper chairman.
Verified cost: ~$0.0002 per routine question.

## 3. Better ecosystem: Hermes ↔ OpenClaw ↔ Obsidian
- Hermes decides + remembers (brain), OpenClaw executes (hands), Obsidian
  persists the shared context (shared brain).
- Bridges make the handoff trivial: `hermes-to-openclaw`, `hermes-worker`,
  `vault-note`.
- The `stack` CLI drives all three from one terminal; Telegram reaches them all.

## 4. Better terminal commands & skills
Curated fast/ safe commands (rg/fd/agent-stack CLI), plus the stack itself as
a one-command control plane.

## 5. Learning skills — any task + general health
Two loops:
- **Per-task learning** — after every non-trivial task, log what worked so the
  next one is faster/cheaper; recurring learnings become skills.
- **General health** — cheap shell-based checks keep the machine + stack ready.

## 6. A nice GitHub project
This repo. Public, MIT, documented, forkable — a reference implementation of a
cheap, high-quality, self-improving personal agent ecosystem.

## North-star metric
**Cost per verified success.** Every design decision in this repo serves that:
cheap where possible, quality where it matters, verification always.
