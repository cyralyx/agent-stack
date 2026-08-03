# Council Chairman Upgrade — Kimi K3

The council already uses `moonshotai/kimi-k3` as its default chairman for hard
questions. Kimi K3 is now **open-sourced** (MoonshotAI/Kimi-K3, 8K★, Aug 2026) —
"Open Frontier Intelligence."

## What this means for the council

- **Kimi K3 was already the chairman** (via OpenRouter) — the open-source
  release means it's here to stay, likely cheaper/more accessible over time.
- The council's `--cheap-chairman` path (`deepseek/deepseek-v4-flash`) remains
  the default for routine questions (~15x cheaper than kimi-k3).

## Upgrade path

1. **Watch** MoonshotAI/Kimi-K3 for self-hostable weights (GGUF).
2. **When available**: run kimi-k3 locally (llama.cpp / Ollama) → council
   chairman becomes **free** for hard questions too.
3. **Cost impact**: chairman stage currently ~$3/M in on OpenRouter; local
   would drop it to ~$0 (electricity only).

## Recommendation

Keep kimi-k3 as the *hard-case* chairman on OpenRouter. Add a `--local-chairman`
flag to `council_v2.py` when local weights ship, routing the chairman call to
`http://localhost:11434/api/chat` (Ollama) instead of OpenRouter.

## Status

- [ ] Kimi-K3 local weights released
- [ ] `--local-chairman` flag added to council
- [ ] Benchmark local vs OpenRouter chairman (cost + quality per verified success)
