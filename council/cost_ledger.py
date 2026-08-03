#!/usr/bin/env python3
"""Cost ledger — track API spend per task / per council run.

Stores every task's real cost + whether it was verified right, so you can see
your true cost-per-verified-success. Also reports OpenRouter account credits.

Usage:
  python cost_ledger.py log --task "T" --cost 0.0012 --verified 1 --model qwen
  python cost_ledger.py report [--days 7]
  python cost_ledger.py credits
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request

LEDGER_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cost_ledger.db")
OPENROUTER_CREDITS = "https://openrouter.ai/api/v1/credits"


def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(LEDGER_DB)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, task TEXT, cost REAL, verified INTEGER, model TEXT,
            category TEXT
        )"""
    )
    conn.commit()
    return conn


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
    return ""


def log_entry(conn, args):
    conn.execute(
        "INSERT INTO ledger (ts, task, cost, verified, model, category) VALUES (?,?,?,?,?,?)",
        (time.strftime("%Y-%m-%d %H:%M"), args.task, args.cost,
         int(args.verified), args.model, args.category),
    )
    conn.commit()
    print(f"logged: {args.task} ${args.cost:.5f} verified={args.verified}")


def report(conn, days):
    cutoff = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - days * 86400))
    rows = conn.execute(
        "SELECT task, cost, verified, model, ts FROM ledger WHERE ts >= ? ORDER BY id DESC",
        (cutoff,),
    ).fetchall()
    total = sum(r[1] for r in rows)
    verified = sum(1 for r in rows if r[2])
    print(f"Ledger (last {days}d): {len(rows)} entries, total ${total:.4f}, "
          f"verified {verified}/{len(rows)}")
    print(f"Cost-per-verified-success: ${total/max(verified,1):.4f}/verified")
    for r in rows[:15]:
        print(f"  {r[4][5:]}  ${r[1]:<8.5f} v={r[2]}  {r[3]:<30} {r[0][:45]}")


def credits():
    key = load_key()
    if not key:
        print("No OPENROUTER_API_KEY — can't fetch credits.")
        return
    req = urllib.request.Request(OPENROUTER_CREDITS)
    req.add_header("Authorization", "Bearer " + key)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            d = json.loads(resp.read().decode())
        total = d.get("total_credits", 0)
        used = d.get("total_usage", 0)
        print(f"OpenRouter credits: total=${total:.2f} used=${used:.2f} remaining=${total-used:.2f}")
    except Exception as exc:
        print(f"credits fetch failed: {exc}")


def main():
    ap = argparse.ArgumentParser(description="Cost ledger")
    sub = ap.add_subparsers(dest="cmd")
    l = sub.add_parser("log")
    l.add_argument("--task", required=True)
    l.add_argument("--cost", type=float, required=True)
    l.add_argument("--verified", type=int, default=0)
    l.add_argument("--model", default="")
    l.add_argument("--category", default="task")
    r = sub.add_parser("report")
    r.add_argument("--days", type=int, default=7)
    c = sub.add_parser("credits")
    args = ap.parse_args()
    conn = init_db()
    if args.cmd == "log":
        log_entry(conn, args)
    elif args.cmd == "report":
        report(conn, args.days)
    elif args.cmd == "credits":
        credits()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
