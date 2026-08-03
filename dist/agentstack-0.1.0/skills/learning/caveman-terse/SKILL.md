---
name: caveman-terse
description: "Token discipline: say more with fewer tokens. Use when writing agent output, bridge responses, or any LLM-generated text where token cost matters. Based on the caveman skill pattern (65% fewer output tokens)."
version: 1.0.0
author: AgentStack
license: MIT
---

# Caveman Terse — token discipline

The AgentStack runs on **cost-per-verified-success**. The cheapest token is
the one you don't output. This skill applies the caveman pattern: same
information, dramatically fewer output tokens.

## When to use

- Bridge outputs (`hermes-to-openclaw`, `hermes-worker`)
- Council verdicts
- Any agent response where the user wants the answer, not the essay
- Status/health/ledger output

## The discipline

1. **Answer first, explain only if asked.** Lead with the result/verdict.
2. **Use the smallest words that carry the meaning.**
   - "utilize" → "use"
   - "in order to" → "to"
   - "due to the fact that" → "because"
   - "at this point in time" → "now"
3. **Drop filler.** No "I think", "It seems", "As you know", "Let me".
4. **Use terse bullet format over prose** for structured data.
5. **Numbers speak.** "cost: $0.00005" beats "the cost was extremely low".

## Measured benefit

- Caveman reports **~65% fewer output tokens on prose**, 8.5% on agentic runs.
- For a bridge that writes 1K tokens/response, that's ~650 tokens saved per
  call — at deepseek-v4-flash output pricing, real money at scale.

## Pitfalls

- **Do not sacrifice correctness for terseness.** A wrong short answer costs
  more than a right long one (you pay twice).
- **Do not go full caveman on docs.** This discipline is for runtime output
  and bridges, not READMEs or architecture docs.
- Keep JSON/bridge protocol shapes stable — terse ≠ malformed.

## Verification

After applying, count output tokens before/after on a sample bridge call.
Target: ≥50% reduction with identical information content.
