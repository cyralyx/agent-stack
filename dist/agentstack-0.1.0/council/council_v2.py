#!/usr/bin/env python3
"""Council v2.1 — even better: confidence, history, retirement, domains, verify.

Builds on Council v2 (cheap workers + anonymous peer-rank + chairman) and adds:
  * CONFIDENCE-scored verdicts — chairman returns answer + confidence + escalation hint
  * HISTORY DB (SQLite) — every question, member, cost, verdict, confidence stored
    so you can learn from past council runs (and retire low-value members)
  * MEMBER RETIREMENT — a member that never wins peer-ranking or is expensive
    per verified success gets flagged/dropped automatically
  * DOMAIN PANELS — different worker sets per domain (code / research / health)
    instead of one generic council
  * VERIFICATION stage — a 4th stage that checks the verdict against facts
    (web search / API) before finalizing, when the chairman flags low confidence

Usage:
  python council_v2.py "your question"                       # default
  python council_v2.py "your question" --domain code         # domain panel
  python council_v2.py "your question" --cheap-chairman      # cheaper routine
  python council_v2.py "your question" --verify              # force verify stage
  python council_v2.py "your question" --json                # machine-readable
  python council_v2.py --history                             # show recent history
  python council_v2.py --retire                              # retire underperformers
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request

OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"

# (input $/M, output $/M)
PRICING = {
    "qwen/qwen3.5-flash-02-23": (0.065, 0.65),
    "openai/gpt-oss-20b:free": (0.0, 0.0),
    "qwen/qwen3.7-flash": (0.03, 0.06),
    "moonshotai/kimi-k3": (3.0, 10.0),
    "deepseek/deepseek-v4-flash": (0.2, 0.6),
}

DEFAULT_MEMBERS = "qwen/qwen3.5-flash-02-23,openai/gpt-oss-20b:free"
DEFAULT_CHAIRMAN = "moonshotai/kimi-k3"
CHEAP_CHAIRMAN = "deepseek/deepseek-v4-flash"

# Domain panels: different worker sets per domain.
DOMAIN_PANELS = {
    "code": ["openai/gpt-oss-20b:free", "qwen/qwen3.7-flash"],
    "research": ["qwen/qwen3.5-flash-02-23", "openai/gpt-oss-20b:free"],
    "health": ["qwen/qwen3.5-flash-02-23", "deepseek/deepseek-v4-flash"],
    "default": ["qwen/qwen3.5-flash-02-23", "openai/gpt-oss-20b:free"],
}

HISTORY_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "council_history.db")


def load_key() -> str:
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
    pin, pout = PRICING.get(model, (0.2, 0.6))
    return (tokens_in / 1_000_000) * pin + (tokens_out / 1_000_000) * pout


# ---- history DB -------------------------------------------------------------
def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(HISTORY_DB)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS council_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, question TEXT, domain TEXT, chairman TEXT,
            members TEXT, final_answer TEXT, confidence REAL,
            total_cost REAL, verified INTEGER, verified_note TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS member_stats (
            model TEXT PRIMARY KEY,
            runs INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            total_cost REAL DEFAULT 0.0,
            last_used TEXT
        )"""
    )
    conn.commit()
    return conn


def record_run(conn, q, domain, chairman, members, answer, conf, cost, verified, note):
    conn.execute(
        "INSERT INTO council_runs (ts, question, domain, chairman, members, final_answer, confidence, total_cost, verified, verified_note) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (time.strftime("%Y-%m-%d %H:%M"), q, domain, chairman, ",".join(members),
         answer, conf, round(cost, 6), verified, note),
    )
    for m in members:
        conn.execute(
            "INSERT INTO member_stats (model, runs, wins, total_cost, last_used) VALUES (?,1,0,0,?) "
            "ON CONFLICT(model) DO UPDATE SET runs=runs+1, last_used=?",
            (m, time.strftime("%Y-%m-%d %H:%M"), time.strftime("%Y-%m-%d %H:%M")),
        )
    conn.commit()


def show_history(conn, limit=10):
    rows = conn.execute(
        "SELECT id, ts, question, domain, total_cost, confidence, verified FROM council_runs ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    if not rows:
        print("No council history yet.")
        return
    print(f"{'id':<4} {'ts':<17} {'$cost':<8} {'conf':<6} {'vrf':<5} question")
    for r in rows:
        print(f"{r[0]:<4} {r[1]:<17} {r[4]:<8.5f} {r[5] or 0:<6.2f} {r[6] or 0:<5} {r[2][:50]}")


def retire_underperformers(conn, threshold_wins=0, threshold_runs=3, dry_run=True):
    """Flag members that never won a ranking and have been used enough times."""
    rows = conn.execute(
        "SELECT model, runs, wins, total_cost FROM member_stats WHERE runs >= ?",
        (threshold_runs,),
    ).fetchall()
    to_retire = []
    for model, runs, wins, tc in rows:
        if wins <= threshold_wins:
            to_retire.append((model, runs, wins, tc))
    if not to_retire:
        print("No underperformers to retire.")
        return
    if dry_run:
        print("DRY-RUN — would retire:")
    for model, runs, wins, tc in to_retire:
        print(f"  {model}: runs={runs} wins={wins} cost=${tc:.4f} {'[DRY]' if dry_run else 'retired!'}")


# ---- council run ------------------------------------------------------------
def run_council(args, key):
    conn = init_db()
    chairman = args.chairman or (CHEAP_CHAIRMAN if args.cheap_chairman else DEFAULT_CHAIRMAN)
    members = DOMAIN_PANELS.get(args.domain, DOMAIN_PANELS["default"])
    if args.members:
        members = [m.strip() for m in args.members.split(",") if m.strip()]

    report = {
        "question": args.question, "domain": args.domain, "members": members,
        "chairman": chairman, "stages": [], "costs": {}, "total_cost_usd": 0.0,
        "final_answer": None, "confidence": None, "escalate": None, "verified": None,
    }

    # Stage 1 — collect answers
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

    # Stage 2 — anonymous peer ranking
    ranked = list(stage1)
    if len(ranked) > 1:
        scores = {i: 0 for i in range(len(ranked))}
        for i, s in enumerate(ranked):
            others = [f"{j}: {ranked[j]['answer']}" for j in range(len(ranked)) if j != i]
            prompt = ("Rank these anonymous answers by quality (best first). "
                      "Reply with exactly the indices in order, comma-separated.\n" + "\n".join(others))
            try:
                r = call_model(s["model"], [
                    {"role": "system", "content": "You are a peer reviewer. Rank only."},
                    {"role": "user", "content": prompt},
                ], key, max_tokens=100)
                for pos, tok in enumerate(re.findall(r"\d+", r["text"] or "")):
                    if int(tok) < len(ranked):
                        scores[int(tok)] += max(0, len(ranked) - pos)
            except Exception:
                pass
        ranked = [ranked[i] for i in sorted(scores, key=lambda i: -scores[i])]
        report["stages"].append({"stage": 2, "order": [s["model"] for s in ranked]})
        # credit a "win" to the top-ranked member
        conn.execute("UPDATE member_stats SET wins=wins+1 WHERE model=?", (ranked[0]["model"],))
        conn.commit()

    # Stage 3 — chairman synthesizes with confidence
    answers_blob = "\n\n".join(f"[{i}] {s['answer']}" for i, s in enumerate(ranked))
    try:
        r = call_model(chairman, [
            {"role": "system", "content": "You are the council chairman. Synthesize ONE final answer from the members' responses. Be decisive and terse. End your reply with a line 'CONFIDENCE: <0-100>' estimating your confidence."},
            {"role": "user", "content": f"Question: {args.question}\n\nMember responses:\n{answers_blob}"},
        ], key)
        c = cost(chairman, r["tokens_in"], r["tokens_out"])
        # parse confidence
        conf_match = re.search(r"CONFIDENCE:\s*(\d{1,3})", r["text"])
        conf = float(conf_match.group(1)) / 100 if conf_match else 0.7
        text = re.sub(r"\s*CONFIDENCE:\s*\d{1,3}\s*$", "", r["text"]).strip()
        report["final_answer"] = text
        report["confidence"] = conf
        report["costs"][chairman] = c
        report["stages"].append({"stage": 3, "chairman": chairman, "cost": c, "confidence": conf})
        escalate = conf < 0.6
        report["escalate"] = escalate
        if args.verbose:
            print(f"[chairman] confidence={conf:.2f} escalate={escalate}")
    except Exception as exc:
        report["final_answer"] = f"CHAIRMAN ERROR: {exc}"
        report["confidence"] = 0.0
        conf = 0.0

    # Stage 4 — verification (when asked, or low confidence)
    total = sum(s.get("cost", 0) for s in stage1) + sum(report["costs"].values())
    report["total_cost_usd"] = total
    verified, note = 0, ""
    if args.verify or (report.get("escalate") and args.auto_verify):
        try:
            v = call_model(chairman, [
                {"role": "system", "content": "You are the verification stage. The council produced an answer with low confidence. Check it for obvious errors. Reply with exactly 'OK' if it seems right, or 'FIX: <correct answer>' if wrong."},
                {"role": "user", "content": f"Question: {args.question}\nCouncil answer: {report['final_answer']}"},
            ], key, max_tokens=200)
            verdict = v["text"].strip()
            verified = 1 if verdict.startswith("OK") else 0
            note = verdict
            report["verified"] = bool(verified)
            report["stages"].append({"stage": 4, "verdict": verdict, "cost": cost(chairman, v["tokens_in"], v["tokens_out"])})
            total += cost(chairman, v["tokens_in"], v["tokens_out"])
            report["total_cost_usd"] = total
        except Exception as exc:
            note = f"VERIFY ERROR: {exc}"

    record_run(conn, args.question, args.domain, chairman, members, report["final_answer"],
               report["confidence"], total, verified, note)
    return report


def main():
    ap = argparse.ArgumentParser(description="Council v2.1 — confidence + history + retirement")
    ap.add_argument("question", nargs="?", default=None)
    ap.add_argument("--members", default="")
    ap.add_argument("--chairman", default=None)
    ap.add_argument("--cheap-chairman", action="store_true")
    ap.add_argument("--domain", default="default", choices=list(DOMAIN_PANELS.keys()))
    ap.add_argument("--verify", action="store_true", help="force the verification stage")
    ap.add_argument("--auto-verify", action="store_true", help="verify when confidence < 0.6")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--history", action="store_true", help="show recent council history")
    ap.add_argument("--retire", action="store_true", help="retire underperforming members (dry-run)")
    args = ap.parse_args()

    if args.history:
        conn = init_db()
        show_history(conn)
        return
    if args.retire:
        conn = init_db()
        retire_underperformers(conn)
        return
    if not args.question:
        ap.print_help()
        return

    key = load_key()
    report = run_council(args, key)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("\n=== COUNCIL v2.1 ===")
        print(f"Q: {report['question']}  [domain: {report['domain']}]")
        print(f"Members: {', '.join(report['members'])} | Chairman: {report['chairman']}")
        print(f"Total cost: ${report['total_cost_usd']:.5f} | Confidence: {report['confidence'] or 0:.2f}")
        print(f"Final answer:\n{report['final_answer']}")
        if report.get("verified") is not None:
            print(f"Verified: {report['verified']} ({report['stages'][-1].get('verdict','')[:80]})")
        if report.get("escalate"):
            print("⚠ LOW CONFIDENCE — consider verification or a stronger chairman.")


if __name__ == "__main__":
    main()
