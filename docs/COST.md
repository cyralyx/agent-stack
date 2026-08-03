# Cost Optimization Playbook

Lower API cost while improving quality. Every lever here is **free or
cheaper-than-alternative**, ordered by impact.

## 1. Cache discipline (biggest lever, free)
- Keep long conversations alive; avoid `/reset` churn (each reset re-pays the
  full system prompt).
- Don't change toolsets mid-conversation (kills the cache).
- Measure: `hermes insights --days 7` or the usage-report skill.
- Target: cache_read ≥ 80% of input.

## 2. Search before reading (medium lever, free)
- `rg`/`fd`/`ctx_search` before `read_file`/`cat`.
- Excerpts before full reads. Never dump a whole repo into context.

## 3. Cheap models for cheap work (big lever)
- Council v2: workers = qwen/gpt-oss-free, chairman = deepseek (routine) or
  kimi-k3 (hard). Verified: routine council = **$0.0002**.
- Worker/bridge: `hermes-worker` uses `openai/gpt-4o-mini` (cheap) instead of
  the main model.
- Vision/aux: `openai/gpt-4o-mini` (fixed from the broken text-only deepseek).

## 4. Budget guardrails (safety, free)
- OpenRouter Workspace Guardrail: **$10/month credit limit** (set).
- **Prompt Injection: Flag** (set, free + no latency).
- Consider: model/provider restrictions to block accidentally-expensive models.

## 5. Verify success, don't trust claims
- The north-star is **cost-per-verified-success**, not tokens or "it worked".
- Cheap wrong answers cost more than slightly-expensive right ones (you pay
  twice: the wrong run + the redo).
- Council tracks real $ per verdict so you can drop low-value members.

## 6. Batch independent calls
- One parallel tool block beats N sequential round-trips.
- Fewer round-trips = less context resend = lower cost.

## Measure

```bash
python "C:/Users/willi/AppData/Local/hermes/skills/productivity/hermes-usage-report/scripts/hermes_usage_report.py" --days 7
```
Track: sessions, API calls, cache hit rate, top sessions, waste signals.
