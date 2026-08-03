# AgentStack VISION — cheaper, better, self-improving

**One personal-AI ecosystem: Hermes (brain) × OpenClaw (hands) × Obsidian
(shared brain).** This is the full vision with the expanded wish list —
every item is either built, building, or on the roadmap.

---

## The six pillars + expanded wishes

### 1. 💰 Lower API cost · improved quality
**Built:**
- ✅ Council v2.1 — cheap workers, cost tracking per verdict (~$0.0002/run)
- ✅ Cost ledger + `stack cost` — real cost-per-verified-success
- ✅ OpenRouter guardrails: $10/mo budget, prompt-injection flag
- ✅ Cache discipline playbook (docs/COST.md)

**Similar wishes (roadmap):**
- [ ] Sub-$0.001 default for 90% of questions
- [ ] Free-tier-first routing (`gpt-oss-20b:free` before any paid)
- [ ] Auto-throttle: if cost-per-verified-success exceeds budget, drop model tier
- [ ] Cache-hit dashboard (weekly %, goal ≥85%)
- [ ] No-waste session rules (auto-close throwaway sessions)
- [ ] Weekly spend alerts → Telegram

### 2. 🏛️ Better council system
**Built:**
- ✅ Confidence-scored verdicts (chairman returns answer + confidence + escalate hint)
- ✅ Council history DB (every question, member, cost, verdict stored)
- ✅ Member retirement (underperformers flagged after enough runs)
- ✅ Domain panels (code / research / health / default worker sets)
- ✅ Verification stage (4th stage when confidence low or `--verify`)

**Similar wishes (roadmap):**
- [ ] Council-as-a-service over Telegram
- [ ] Specialist panels auto-selected by question intent
- [ ] Model-bias parity tests (head-to-head on known answers)

### 3. 🔗 Better ecosystem (Hermes ↔ OpenClaw ↔ Obsidian)
**Built:**
- ✅ Shared task queue (`stack todo` in vault — both agents see it)
- ✅ Vault MCP server (Obsidian as read/write API, no delete)
- ✅ Bridges + `stack` CLI + Telegram gateway
- ✅ Compatibility ledger + wife-reviewer hook

**Similar wishes (roadmap):**
- [ ] State sync on change (auto-refresh, not on-demand)
- [ ] "Who's better at X" auto-memo from outcomes
- [ ] Single-brain tag system (shared tags/frontmatter)
- [ ] Echo loop: wife-reviewer second opinions get acted on

### 4. 🖥️ Better terminal commands & skills
**Built:**
- ✅ Alias pack (`terminal/aliases.sh` — s, sst, sdoc, scost, scouncil, mkskill, quicknote, pushit)
- ✅ Command-safety linter (`terminal/safety.sh`)
- ✅ Flow chains (`stack flow research|health`)
- ✅ Terminal-fast-commands skill

**Similar wishes (roadmap):**
- [ ] Skill auto-discovery (suggest skill for raw commands)
- [ ] Drill-down CLI across agents (predictable `stack <agent> <verb>`)
- [ ] Windows headless helper (`stack screen` / browse-to command)

### 5. 🎓 Learning skills — any task + general health
**Built:**
- ✅ Task-learning skill (log what worked, promote to skill)
- ✅ System-health skill + `stack health [--fix]`
- ✅ Health flow (check + log to vault)

**Similar wishes (roadmap):**
- [ ] Auto-learn on failure (no manual trigger)
- [ ] Skill retirement (archive never-used skills)
- [ ] Learning review weekly (Sunday digest: got faster at X, saved $Y)
- [ ] Benchmark-driven improvement (re-run known tasks to prove gains)

### 6. 🚀 A nice GitHub project
**Built:**
- ✅ Public repo: cyralyx/agent-stack
- ✅ README + VISION + docs (ARCHITECTURE, COUNCIL, COST, LEARNING, CLI, SETUP, SECURITY)
- ✅ CI workflow (bash+python syntax on push)
- ✅ `.env.example` with key NAMES only (no secrets)

**Similar wishes (roadmap):**
- [ ] Working demo GIF in README (`stack status` + `stack council`)
- [ ] README badges (CI, license, version)
- [ ] Skill installer from repo (`./install.sh --with-skills`)
- [ ] Issue templates + CONTRIBUTING
- [ ] Version tags + CHANGELOG

---

## North-star metric
**Cost per verified success.** Every design decision serves this: cheap where
possible, quality where it matters, verification always.
