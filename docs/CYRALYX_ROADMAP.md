# Cyralyx Vision → AgentStack Roadmap

AgentStack is evolving from a tri-agent stack (Hermes + OpenClaw + Obsidian) into
a complete, local-first **AI workspace operating system** (Cyralyx). The full
build specification lives in `spec/cyralyx-build-package/` (the Cyralyx Hermes
build package). This doc maps its phases to what AgentStack has today and what's
next.

## What Cyralyx is

> An open-source, local-first AI workspace OS unifying: persistent AI agents,
> multi-agent councils, project management, notes + knowledge graphs, files +
> local folder indexing, universal model providers, local AI, tools/skills/
> plugins/MCP, automations, visible execution, permissions + rollback, premium
> customisable UX, and evidence-driven improvement.
>
> — `spec/cyralyx-build-package/HERMES_MASTER_INSTRUCTION.md`

## Build phases (from spec, 13_tasks/)

| Phase | Focus | AgentStack status |
|-------|-------|------------------|
| 0 | Audit current repos + milestone report | ✅ agent-stack live, modules merged |
| 1 | Research | ✅ radar + competitor matrix |
| 2 | Architecture | ✅ ARCHITECTURE.md, monorepo |
| 3 | Clickable shell | ✅ Electron app (app/), stack CLI |
| 4 | Core runtime (agents, councils) | ✅ council v2.1 + bridges |
| 5 | Knowledge (graph, memory) | ⏳ Obsidian vault = shared brain (graph next) |
| 6 | Skills / plugins / MCP | ✅ skills tree + extra-skills; MCP next |
| 7 | Council + automation | ✅ council v2.1; automation engine ⏳ |
| 8 | Release | 🚧 packaging + release workflow in place |

## Reading order (spec)

Read `spec/cyralyx-build-package/00_control/START_HERE.md` → `EXECUTION_CONTRACT.md`
→ `PACKAGE_INDEX.md`, then the `13_tasks/PHASE_*.md` files. Use the templates in
`14_templates/` and schemas in `15_schemas/` rather than inventing formats.

## What the merged modules contribute

- **core-benchmarks** → Phase 8 (benchmark lab / quality gates) — real eval suite
- **evolution** → Phase 7 (evidence-driven improvement) — self-improvement engine
- **tools** → Phase 4 (core runtime tools) — exec/git/mcp/mutation toolkit
- **skills-pkg + extra-skills** → Phase 6 (skills) — diagnostics + eval skills

## Next concrete moves

1. Wire `modules/core-benchmarks` into `stack benchmark` (run a real suite).
2. Stand up the knowledge-graph model (Phase 5) on top of the vault.
3. Add MCP runtime (Phase 6) so skills/plugins/MCP servers load uniformly.
4. Surface council + evolution under the Electron app.
5. Hit the release gates (Phase 8): CI green, packaging, docs, security.
