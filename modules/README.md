# AgentStack Monorepo — merged modules

This directory houses reusable components merged from the Cyralyx project family
into AgentStack as a single monorepo. Each module keeps its own MIT LICENSE and
is independently importable (add the module dir to `sys.path`).

| Module | Source | LOC | What it is |
|--------|--------|-----|-----------|
| `core-benchmarks` | `cyralyx/cyralyx-core` | ~12.9k | Elite benchmark suite: ablation, bench_v2, ranking, task suites (coding/debugging/structured-output/tool-use), weak-to-strong evals |
| `evolution` | `cyralyx/cyralyx-evolution` | ~1.7k | Self-improvement engine: evolutionary controller, creation/refinement/economy/generational loops |
| `tools` | `cyralyx/cyralyx-tools` | ~2.2k | Toolchain: data_ops, exec_command, git_ops, mcp_session, mutation_verifier, toolforge |
| `skills-pkg` | `cyralyx/cyralyx-skills` | ~0.3k | Skill evaluation: compression_probes, false_success, evolution |
| `extra-skills` | `cyralyx/cyralyx-skills/skills` | — | Ready-to-install SKILL.md skills: mcp-diagnostics, repo-diagnostics, safe-mutation, server-diagnostics (also copied into `../skills/diagnostics/`) |

## Run

```bash
stack modules      # list modules
stack benchmark    # inspect benchmark suite
python modules/evolution/engine.py   # evolution engine
python modules/tools/data_ops.py     # tools
```

Imports work because each module dir is itself the package (contains `__init__.py`):

```bash
PYPATH="modules/evolution:modules/tools:modules/skills-pkg"
PYTHONPATH=$PYPATH python -c "import engine; print('ok')"
```

## Provenance

All modules MIT-licensed © 2026 Cyralyx (same author/owner as AgentStack).
Merged to give AgentStack professional benchmarks + a self-improvement engine +
a toolchain, turning it from a stack into a workspace OS.
