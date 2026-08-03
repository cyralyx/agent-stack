# Benchmark Design

## Objective
Measure whether Cyralyx orchestration improves the same AI model compared to the model operating alone.

## Conditions
- **A-RAW**: Model receives task prompt + minimal system prompt. No Cyralyx augmentation.
- **B-CYRALYX**: Same model + Cyralyx-augmented system prompt + retry on failure + verification.

## Task Suite
30 tasks across 4 categories: coding (8), debugging (8), tool_use (6), structured_output (8).
10 dev tasks, 20 held-out tasks.

## Scoring
Each task has deterministic validation. Pass/fail = 1.0/0.0.
No subjective scoring. No LLM-as-judge.
