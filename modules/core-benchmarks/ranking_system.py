#!/usr/bin/env python3
"""Cyralyx Ranking System — runs benchmark suite, tracks results, generates leaderboard."""
import json, os, sys, time, sqlite3, subprocess, hashlib
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

DB_PATH = os.path.join(RESULTS_DIR, "ranking.db")

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT, timestamp TEXT,
            cyralyx_version TEXT, git_sha TEXT,
            model TEXT, condition TEXT,
            suite TEXT, n_tasks INTEGER,
            success_rate REAL, avg_cost REAL,
            avg_latency_ms REAL, avg_tokens REAL,
            avg_retries REAL, total_cost REAL,
            run_time_s REAL, notes TEXT
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS task_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT, task_id TEXT, category TEXT,
            condition TEXT, success INTEGER,
            cost REAL, latency_ms REAL,
            tokens INTEGER, retries INTEGER,
            failure_type TEXT
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT, config_name TEXT, config_value TEXT
        )
    """)
    db.commit()
    return db

GIT_SHA = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=BASE).stdout.strip() or "unknown"

def run_benchmark(suite_name="heldout-v1", model="deepseek/deepseek-v4-flash"):
    """Run a full benchmark and return stats per condition."""
    sys.path.insert(0, os.path.join(BASE, "tasks"))
    from task_suite import get_suite
    
    import openai
    api_key = os.environ.get("OPENAI_API_KEY", "")
    api_base = os.environ.get("OPENAI_BASE_URL", "https://inference-api.nousresearch.com/v1")
    client = openai.OpenAI(api_key=api_key, base_url=api_base)
    
    suite = get_suite(suite_name)
    n = len(suite)
    run_id = f"r{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    conditions = [
        ("RAW", "You are a helpful programming assistant. Return ONLY the requested code.", 0.3),
        ("CYRALYX-CONCISE", "You are a precise code generator. Return what was asked.", 0.1),
        ("CYRALYX-OPTIMIZED", None, 0.1),  # dynamic per task
    ]
    
    all_results = []
    
    for cond_name, sys_prompt, temperature in conditions:
        start_time = time.time()
        task_results = []
        
        for i, task in enumerate(suite):
            is_json = "json.load(open(" in task["validation"]
            
            # Determine system prompt
            if cond_name == "CYRALYX-OPTIMIZED":
                fmt = "Return ONLY valid JSON. No explanation." if is_json else "Return ONLY Python code in a ```python block. No explanation."
                system = f"You are a precise code generator. {fmt}"
            elif sys_prompt:
                system = sys_prompt
            else:
                system = "You are a helpful assistant."
            
            # Determine output filename
            if is_json:
                m = __import__("re").search(r"open\('([^']+\.json)'", task["validation"])
                fname = m.group(1) if m else "output.json"
            else:
                mod_name = __import__("re").search(r"from (\w+) import", task["validation"])
                mod_name = mod_name.group(1) if mod_name else task["id"].replace("-", "_")
                fname = f"{mod_name}.py"
            
            t_start = time.time()
            import tempfile, os as os2
            d = tempfile.mkdtemp()
            
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": task["prompt"]}],
                    temperature=temperature, max_tokens=2000,
                )
                content = resp.choices[0].message.content or ""
                
                # Extract code
                code = content
                for tag in ["```python", "```json"]:
                    if tag in content:
                        code = content.split(tag)[1].split("```")[0].strip()
                        break
                if "```" in content and code == content:
                    code = content.split("```")[1].strip()
                
                with open(os2.path.join(d, fname), "w") as f:
                    f.write(code)
                
                r = subprocess.run(task["validation"], shell=True, capture_output=True, text=True, timeout=10, cwd=d)
                success = r.returncode == 0
                failure = ""
                if not success:
                    err = (r.stdout + " " + r.stderr).lower()
                    if "traceback" in err or "error" in err: failure = "CODING_ERROR"
                    elif "syntax" in err: failure = "SYNTAX_ERROR"
                    elif "refus" in err: failure = "MODEL_REFUSAL"
                    elif "json" in err or "decode" in err: failure = "OUTPUT_FORMAT"
                    else: failure = "UNKNOWN"
                
                lat_ms = (time.time() - t_start) * 1000
                tok_in = resp.usage.prompt_tokens or 0
                tok_out = resp.usage.completion_tokens or 0
                cost = (tok_in * 0.0000005 + tok_out * 0.0000015)
                
                task_results.append({
                    "task_id": task["id"], "category": task["category"],
                    "success": 1 if success else 0, "cost": cost,
                    "latency_ms": lat_ms, "tokens": tok_in + tok_out,
                    "retries": 0, "failure_type": failure,
                })
            except Exception as e:
                task_results.append({
                    "task_id": task["id"], "category": task["category"],
                    "success": 0, "cost": 0, "latency_ms": 0,
                    "tokens": 0, "retries": 0, "failure_type": "ERROR",
                })
            finally:
                __import__("shutil").rmtree(d, ignore_errors=True)
        
        run_time = time.time() - start_time
        n_ok = sum(r["success"] for r in task_results)
        total_cost = sum(r["cost"] for r in task_results)
        avg_lat = sum(r["latency_ms"] for r in task_results) / n if n else 0
        avg_tok = sum(r["tokens"] for r in task_results) / n if n else 0
        avg_ret = sum(r["retries"] for r in task_results) / n if n else 0
        
        all_results.append({
            "condition": cond_name, "n_tasks": n,
            "success_rate": n_ok / n * 100,
            "avg_cost": total_cost / n if n else 0,
            "avg_latency_ms": avg_lat,
            "avg_tokens": avg_tok,
            "avg_retries": avg_ret,
            "total_cost": total_cost,
            "run_time_s": run_time,
            "task_results": task_results,
        })
    
    return run_id, all_results

def store_results(db, run_id, results, suite):
    for r in results:
        db.execute("""
            INSERT INTO rankings (run_id, timestamp, cyralyx_version, git_sha,
                model, condition, suite, n_tasks, success_rate, avg_cost,
                avg_latency_ms, avg_tokens, avg_retries, total_cost, run_time_s)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (run_id, datetime.now().isoformat(), "1.0.0", GIT_SHA,
              "deepseek/deepseek-v4-flash", r["condition"], suite,
              r["n_tasks"], r["success_rate"], r["avg_cost"],
              r["avg_latency_ms"], r["avg_tokens"], r["avg_retries"],
              r["total_cost"], r["run_time_s"]))
        
        for tr in r["task_results"]:
            db.execute("""
                INSERT INTO task_results (run_id, task_id, category, condition,
                    success, cost, latency_ms, tokens, retries, failure_type)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (run_id, tr["task_id"], tr["category"], r["condition"],
                  tr["success"], tr["cost"], tr["latency_ms"],
                  tr["tokens"], tr["retries"], tr["failure_type"]))
    db.commit()

def generate_leaderboard(db):
    print("=" * 75)
    print("  CYRALYX RANKING SYSTEM")
    print(f"  Git: {GIT_SHA}  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 75)
    
    runs = db.execute("""
        SELECT run_id, timestamp, condition, suite, n_tasks,
               success_rate, avg_cost, avg_latency_ms, avg_tokens,
               avg_retries, total_cost, run_time_s
        FROM rankings ORDER BY timestamp DESC LIMIT 30
    """).fetchall()
    
    if not runs:
        print("  No results yet.")
        return
    
    # Find the most recent run_id
    latest = runs[0][0]
    conditions = {}
    for r in runs:
        if r[0] == latest:
            cond = r[2]
            conditions[cond] = {
                "suite": r[3], "tasks": r[4], "rate": r[5],
                "cost": r[6], "lat": r[7], "tok": r[8],
                "ret": r[9], "total": r[10], "time": r[11],
            }
    
    print(f"\n  Latest Run: {latest}")
    print(f"  Suite: {conditions.get(list(conditions.keys())[0],{}).get('suite','?')}") if conditions else None
    print()
    
    print(f"  {'Condition':25s} {'Rate':>6s} {'Cost':>10s} {'Lat':>8s} {'Tkns':>6s} {'Ret':>5s}")
    print(f"  {'-'*60}")
    
    for cond, data in sorted(conditions.items()):
        print(f"  {cond:25s} {data['rate']:5.1f}% {data['cost']:9.5f} {data['lat']:7.0f}ms {data['tok']:5.0f} {data['ret']:4.1f}")
    
    # Historical comparison
    print(f"\n  Historical runs:")
    seen = {}
    for r in runs:
        run_id = r[0]
        if run_id not in seen:
            seen[run_id] = True
            d = datetime.fromisoformat(r[1]) if isinstance(r[1], str) else r[1]
            print(f"    {run_id:20s} {r[2]:25s} {r[5]:5.1f}%  cost={r[6]:.5f}")
    
    # Export to JSON
    lb = {"git_sha": GIT_SHA, "timestamp": datetime.now().isoformat(), "runs": []}
    for r in runs:
        run = dict(zip(["run_id","timestamp","condition","suite","n_tasks",
                       "success_rate","avg_cost","avg_latency_ms","avg_tokens",
                       "avg_retries","total_cost","run_time_s"], list(r)))
        lb["runs"].append(run)
    
    with open(os.path.join(RESULTS_DIR, "leaderboard.json"), "w") as f:
        json.dump(lb, f, indent=2, default=str)
    print(f"\n  Leaderboard: {RESULTS_DIR}/leaderboard.json")

def generate_markdown(db):
    runs = db.execute("""
        SELECT run_id, timestamp, condition, success_rate, avg_cost, avg_latency_ms, avg_tokens
        FROM rankings ORDER BY timestamp DESC LIMIT 20
    """).fetchall()
    
    lines = [
        "# Cyralyx Benchmark Results\n",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Git: {GIT_SHA}*\n",
        "| Run | Date | Condition | Rate | Cost/Task | Latency | Tokens |",
        "|-----|------|-----------|------|-----------|---------|--------|",
    ]
    for r in runs[:12]:
        run_id, ts, cond, rate, cost, lat, tok = r
        date = ts[:10] if isinstance(ts, str) else ""
        lines.append(f"| {run_id[:12]} | {date} | {cond} | {rate:.1f}% | ${cost:.5f} | {lat:.0f}ms | {tok:.0f} |")
    
    with open(os.path.join(RESULTS_DIR, "benchmark-results.md"), "w") as f:
        f.write("\n".join(lines))
    
    print(f"  Report: {RESULTS_DIR}/benchmark-results.md")

if __name__ == "__main__":
    db = init_db()
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="heldout-v1")
    parser.add_argument("--model", default="deepseek/deepseek-v4-flash")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    
    if args.report_only:
        generate_leaderboard(db)
        generate_markdown(db)
    else:
        run_id, results = run_benchmark(args.suite, args.model)
        store_results(db, run_id, results, args.suite)
        generate_leaderboard(db)
        generate_markdown(db)
