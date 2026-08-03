# Better Council — spec & operation

The AgentStack uses **Council v2** for quality-sensitive questions: cheap
workers deliberate, a chairman synthesizes, with real cost tracking.

## Architecture

```
Question
  → Stage 1: N cheap workers answer independently   (qwen / gpt-oss free)
  → Stage 2: anonymous peer-ranking (kills prestige bias)
  → Stage 3: chairman synthesizes ONE final answer  (kimi-k3 or cheap chairman)
  → Report: answer + per-stage cost + cost-per-verified-success
```

## Model set (cost-efficient)

| Role | Model | Cost |
|------|-------|------|
| Worker | `qwen/qwen3.5-flash-02-23` | $0.065/M in |
| Worker | `openai/gpt-oss-20b:free` | **$0** (free) |
| Chairman (hard) | `moonshotai/kimi-k3` | $3/M in — only for hard cases |
| Chairman (cheap) | `deepseek/deepseek-v4-flash` | $0.2/M in — routine Qs |

## Why this is cheaper AND better

- **Cheap by construction:** the heavy lifting is done by sub-cent workers;
  the expensive chairman only synthesizes.
- **Cost tracking per verdict:** you see exactly what each question cost and
  which members added value — over time you drop members that never win.
- **Role separation:** workers gather, peers rank, chairman decides. No single
  model can dominate just by prestige.
- **`--cheap-chairman` flag:** routine questions skip kimi-k3 entirely, using
  deepseek-v4-flash — a ~15x saving on the chairman stage.

## Run it

```bash
python council/council_v2.py "your question"
python council/council_v2.py "your question" --cheap-chairman   # routine, cheaper
python council/council_v2.py "your question" --chairman moonshotai/kimi-k3  # hard
python council/council_v2.py "your question" --json             # machine-readable
```

## Verified

- `council_v2.py "What is 2+2?" --cheap-chairman` → answer `4`, total cost
  **$0.000192** (sub-millicent).

## Cost-per-verified-success

The north-star metric: total $ spent ÷ number of *verified* correct answers.
Track it per council run. A run that costs $0.01 and produces a wrong answer
scores worse than a $0.002 run that is right.
