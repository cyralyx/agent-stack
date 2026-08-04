# Council Cost Methodology

AgentStack tracks the cost of council runs through `council/cost_ledger.py` and
`council/council_v2.py`. This document defines what "verified success" means,
how cost is recorded, and how to reproduce any cost figure.

## Cost per verified success — definition

> A task counts as a **verified success** only when the requested result exists,
> the required checks pass, and an independent validator or deterministic test
> confirms the outcome.

For council runs this means:

- the chairman produces a verdict (answer + confidence),
- the run completes without error,
- the result passes any supplied verification (e.g. a deterministic check on
  the answer, or a human/validator approval recorded as `verified=1` in the
  ledger),
- token counts and cost are recorded at the time of the run.

## What is recorded

Each ledger entry (`council/cost_ledger.py`) records:

| Field | Meaning |
|-------|---------|
| `task` | short description of the question |
| `cost` | total estimated cost of the run (USD) |
| `verified` | 1 if independently verified, 0 otherwise |
| `model` | model(s) used (e.g. `deepseek-v4-flash`) |
| `timestamp` | when the run happened |

The ledger aggregates **cost per verified success** as:
`total cost / count(verified=1)`.

## How the numbers were produced

A deterministic sample run:

```bash
python council/council_v2.py "What is 12*7? Just the number." --domain code --cheap-chairman
```

This produced (2026-08-03, ledger row 1): **$0.00005**, verified, model
`deepseek-v4-flash`. That is a single reproducible observation under
`--cheap-chairman`, not a guarantee for all runs.

## Important disclaimer on the earlier ~$0.0002 claim

The earlier README/VISION claim of **"~$0.0002/run"** is **not reproducible as
stated** because it did not document:

- the provider (OpenRouter) and exact model IDs,
- input/output token counts,
- the date and pricing assumptions,
- the sample size,
- the success criteria.

Until those are pinned down, AgentStack treats cost claims as **methodology +
reproducible run instructions**, not hard guarantees. When you quote a cost,
include: provider, models, token counts, date, pricing source, sample size, and
success criteria.

## How to add a verified entry

```bash
# run a council question (records its own history + cost)
python council/council_v2.py "question" --domain code --cheap-chairman

# log a verified outcome in the ledger
python council/cost_ledger.py log --task "question" --cost 0.00005 --verified 1 --model deepseek-v4-flash

# report
python council/cost_ledger.py report --days 7
```

## Limits of the ledger

- Cost is **estimated** from token counts × published pricing; it is not a bill.
- "Verified" is only as strong as the verification method (deterministic check,
  validator, or human). State the method when quoting a figure.
- The ledger is local SQLite; it is not a financial audit trail.
