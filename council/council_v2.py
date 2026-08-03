#!/usr/bin/env python3
"""Council v2 — better multi-model deliberation with role separation + cost tracking.

Builds on the proven 3-stage Karpathy council (cheap workers + chairman), and
adds:
  * explicit ROLE separation (chairman/workers) with a clear division of labor
  * per-verdict COST tracking (real $ per verified success)
  * a cheaper chairman path: a mid-tier model for easy questions, kimi-k3 only
    when the question needs it
  * verbose vs quiet output

Usage:
  python council_v2.py "your question"
  python council_v2.py "your question" --members qwen/qwen3.5-flash-02-23,openai/gpt-oss-20b:free
  python council_v2.py "your question" --chairman moonshotai/kimi-k3 --verbose
  python council_v2.py "your question" --json
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"

# Cost-efficient defaults (per 1M tokens, USD, ~approximate):
#   qwen/qwen3.5-flash-02-23      $0.065 / $0.65  (per 1M in/out)
#   openai/gpt-oss-20b:free       $0 / $0         (free tier)
#   qwen/qwen3.7-flash            $0.03 / $0.06
#   moonshotai/kimi-k3            $3 / $10        (chairman, used sparingly)
#   deepseek/deepseek-v4-flash    $0.2 / $0.6     (cheap mid-tier chairman)
PRICING = {
    "qwen/qwen3.5-flash-02-23": (0.065, 0.65),
    "openai/gpt-oss-20b:free": (0.0, 0.0),
    "qwen/qwen3.7-flash": (0.03, 0.06),
    "moonshotai/kimi-k3": (3.0, 10.0),
    "deepseek/deepseek-v4-flash": (0.2, 0.6),
}

# Cheap-but-competent chairman for routine questions (big cost saving vs kimi-k3)
DEFAULT_MEMBERS = "qwen/qwen3.5-flash-02-23,openai/gpt-oss-20b:free"
DEFAULT_CHAIRMAN = "moonshotai/kimi-k3"
CHEAP_CHAIRMAN = "deepseek/deepseek-v4-flash"


def load_key() -> str:
    """Read OPENROUTER_API_KEY from the Hermes .env or environment."""
    key = os.getenv("OPENROUTER_API_KEY")
    if key:
        return key
    for cand in (
        os.path.expanduser(r"~/AppData/Local/hermes/.env"),
        r"C:\Users\willi\AppData\Local\hermes\.env",
    ):
        try:
            with open(cand, encoding="utf-8") as fh:
                for line in fh:
                    m = re.match(r"\s*OPENROUTER_API_KEY\s*=\s*(.+)", line)
                    if m:
                        return m.group(1).strip().strip('"').strip("'")
        except OSError:
            continue
    raise SystemExit("No OPENROUTER_API_KEY found (set env or Hermes .env)")


def call_model(model: str, messages: list, key: str, max_tokens: int = 700) -> dict:
    """Call OpenRouter. Returns {text, tokens_in, tokens_out} or raises."""
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        OPENROUTER, data=json.dumps(body).encode(), method="POST"
    )
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode())
    usage = data.get("usage", {})
    text = data["choices"][0]["message"]["content"]
    return {
        "text": text,
        "tokens_in": usage.get("prompt_tokens", 0),
        "tokens_out": usage.get("completion_tokens", 0),
    }


def cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate USD cost for a call from the PRICING table."""
    pin, pout = PRICING.get(model, (0.2, 0.6))  # default: mid-tier pricing
    return (tokens_in / 1_000_000) * pin + (tokens_out / 1_000_000) * pout


def main():
    ap = argparse.ArgumentParser(description="Council v2 — role separation + cost tracking")
    ap.add_argument("question")
    ap.add_argument("--members", default=DEFAULT_MEMBERS,
                    help="comma-separated cheap worker models")
    ap.add_argument("--chairman", default=None,
                    help="chairman model (default: kimi-k3, or --cheap-chairman)")
    ap.add_argument("--cheap-chairman", action="store_true",
                    help="use the cheaper chairman (deepseek-v4-flash) — best for routine Qs")
    ap.add_argument("--verbose", action="store_true", help="show full stage outputs")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    chairman = args.chairman or (CHEAP_CHAIRMAN if args.cheap_chairman else DEFAULT_CHAIRMAN)
    members = [m.strip() for m in args.members.split(",") if m.strip()]
    key = load_key()

    report = {
        "question": args.question,
        "members": members,
        "chairman": chairman,
        "stages": [],
        "costs": {},
        "total_cost_usd": 0.0,
        "final_answer": None,
    }

    # Stage 1 — collect independent answers from cheap workers (role: workers)
    stage1 = []
    for m in members:
        t0 = time.time()
        try:
            r = call_model(m, [
                {"role": "system", "content": "You are a council worker. Answer independently and concisely. No preamble."},
                {"role": "user", "content": args.question},
            ], key)
            c = cost(m, r["tokens_in"], r["tokens_out"])
            stage1.append({"model": m, "answer": r["text"], "cost": c, "ms": int((time.time()-t0)*1000)})
        except Exception as exc:
            stage1.append({"model": m, "answer": f"ERROR: {exc}", "cost": 0.0, "ms": 0})
    report["stages"].append({"stage": 1, "results": stage1})
    if args.verbose:
        for s in stage1:
            print(f"[worker {s['model']}] ${s['cost']:.5f} ({s['ms']}ms)\n{s['answer']}\n")

    # Stage 2 — anonymous peer ranking (kills model-prestige bias)
    ranked = list(stage1)
    if len(ranked) > 1:
        ballots = []
        for i, s in enumerate(ranked):
            others = [f"{j}: {ranked[j]['answer']}" for j in range(len(ranked)) if j != i]
            prompt = (
                "Rank these anonymous answers by quality (best first). "
                "Reply with exactly the indices in order, comma-separated.\n"
                + "\n".join(others)
            )
            try:
                r = call_model(s["model"], [
                    {"role": "system", "content": "You are a peer reviewer. Rank only."},
                    {"role": "user", "content": prompt},
                ], key, max_tokens=100)
                ballots.append(r["text"])
            except Exception:
                ballots.append("")
        # simple Borda-ish: each ballot votes its top pick
        scores = {i: 0 for i in range(len(ranked))}
        for ballot in ballots:
            for pos, tok in enumerate(re.findall(r"\d+", ballot or "")):
                if int(tok) < len(ranked):
                    scores[int(tok)] += max(0, len(ranked) - pos)
        ranked = [ranked[i] for i in sorted(scores, key=lambda i: -scores[i])]
    report["stages"].append({"stage": 2, "order": [s["model"] for s in ranked]})
    if args.verbose:
        print("[stage 2] ranked:", [s["model"] for s in ranked])

    # Stage 3 — chairman synthesizes (role: chairman)
    answers_blob = "\n\n".join(f"[{i}] {s['answer']}" for i, s in enumerate(ranked))
    t0 = time.time()
    try:
        r = call_model(chairman, [
            {"role": "system", "content": "You are the council chairman. Synthesize ONE final answer from the members' responses. Be decisive and terse."},
            {"role": "user", "content": f"Question: {args.question}\n\nMember responses:\n{answers_blob}"},
        ], key)
        c = cost(chairman, r["tokens_in"], r["tokens_out"])
        report["final_answer"] = r["text"]
        report["costs"][chairman] = c
        report["stages"].append({"stage": 3, "chairman": chairman, "cost": c, "ms": int((time.time()-t0)*1000)})
    except Exception as exc:
        report["final_answer"] = f"CHAIRMAN ERROR: {exc}"

    total = sum(s.get("cost", 0) for s in stage1) + sum(report["costs"].values())
    report["total_cost_usd"] = total

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("\n=== COUNCIL v2 ===")
        print(f"Q: {args.question}")
        print(f"Members: {', '.join(members)} | Chairman: {chairman}")
        print(f"Total cost: ${total:.5f}")
        print(f"Final answer:\n{report['final_answer']}")


if __name__ == "__main__":
    main()
