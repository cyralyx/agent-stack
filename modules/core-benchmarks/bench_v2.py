#!/usr/bin/env python3
"""4-Condition Benchmark: RAW / HERMES / CYRALYX / TOOL-FIRST
Measures model calls, tokens, cost, latency, success across conditions.
"""
import json, os, sys, time, sqlite3, subprocess, tempfile, re, shutil, hashlib
from datetime import datetime

sys.path.insert(0, "/opt/data")
from task_suite import get_suite
from tool_output_compressor import ToolOutputCompressor
from context_reducers import (
    LogReducer, TracebackReducer, TestOutputReducer,
    TestFailureParser, CodeFenceExtractor, JsonRepair, DiffReducer
)

KEY = os.environ.get("OPENAI_API_KEY", "")
BASE = os.environ.get("OPENAI_BASE_URL", "https://inference-api.nousresearch.com/v1")

RESULTS_DIR = "/opt/data/bench_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

DB = sqlite3.connect(os.path.join(RESULTS_DIR, "bench_v2.db"))
DB.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT, task_id TEXT, category TEXT,
        condition TEXT, model TEXT, timestamp TEXT,
        success INTEGER, score REAL,
        input_tokens INTEGER, output_tokens INTEGER,
        total_tokens INTEGER, estimated_cost REAL,
        latency_ms REAL, model_calls INTEGER,
        tool_calls INTEGER, retries INTEGER,
        failure_type TEXT, notes TEXT
    )
""")
DB.commit()

def check_task(task_dir, task):
    try:
        r = subprocess.run(task["validation"], shell=True, capture_output=True, text=True, timeout=10, cwd=task_dir)
        return r.returncode == 0, (r.stdout or r.stderr)[:200]
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as e:
        return False, str(e)[:200]

def extract_code(content):
    blocks = CodeFenceExtractor.extract(content)
    if blocks:
        return blocks[0]["code"]
    return content.strip()

def get_fname(task):
    is_json = "json.load(open(" in task["validation"]
    if is_json:
        m = re.search(r"open\('([^']+\.json)'", task["validation"])
        return m.group(1) if m else "output.json", is_json
    mod_name = re.search(r"from (\w+) import", task["validation"])
    mod_name = mod_name.group(1) if mod_name else task["id"].replace("-", "_")
    return f"{mod_name}.py", False

def run_condition_A_RAW(task, model="deepseek/deepseek-v4-flash"):
    """RAW: minimal prompt, no tools, no retries."""
    import openai
    client = openai.OpenAI(api_key=KEY, base_url=BASE)
    d = tempfile.mkdtemp()
    start = time.time()
    fname, _ = get_fname(task)
    
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                  {"role": "user", "content": task["prompt"]}],
        temperature=0.3, max_tokens=2000,
    )
    content = resp.choices[0].message.content or ""
    code = extract_code(content)
    with open(os.path.join(d, fname), "w") as f: f.write(code)
    success, detail = check_task(d, task)
    lat = (time.time() - start) * 1000
    tin = resp.usage.prompt_tokens or 0
    tout = resp.usage.completion_tokens or 0
    cost = tin * 0.0000005 + tout * 0.0000015
    shutil.rmtree(d, ignore_errors=True)
    return success, cost, lat, tin+tout, 1, 0, detail

def run_condition_B_HERMES(task, model="deepseek/deepseek-v4-flash"):
    """HERMES: standard verbose system prompt, no retries."""
    import openai
    client = openai.OpenAI(api_key=KEY, base_url=BASE)
    d = tempfile.mkdtemp()
    start = time.time()
    fname, _ = get_fname(task)
    
    system = "You are a precise code generator. Write ONLY the requested function/class. Handle edge cases. Use Python idioms. Your code will be tested programmatically."
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": task["prompt"]}],
        temperature=0.3, max_tokens=2000,
    )
    content = resp.choices[0].message.content or ""
    code = extract_code(content)
    with open(os.path.join(d, fname), "w") as f: f.write(code)
    success, detail = check_task(d, task)
    lat = (time.time() - start) * 1000
    tin = resp.usage.prompt_tokens or 0
    tout = resp.usage.completion_tokens or 0
    cost = tin * 0.0000005 + tout * 0.0000015
    shutil.rmtree(d, ignore_errors=True)
    return success, cost, lat, tin+tout, 1, 0, detail

def run_condition_C_CYRALYX(task, model="deepseek/deepseek-v4-flash"):
    """CYRALYX: optimized concise prompt, low temperature, no retries."""
    import openai
    client = openai.OpenAI(api_key=KEY, base_url=BASE)
    d = tempfile.mkdtemp()
    start = time.time()
    fname, is_json = get_fname(task)
    
    fmt = "Return ONLY valid JSON. No explanation." if is_json else "Return ONLY Python code in a ```python block. No explanation."
    system = f"You are a precise code generator. {fmt}"
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": task["prompt"]}],
        temperature=0.1, max_tokens=2000,
    )
    content = resp.choices[0].message.content or ""
    code = extract_code(content)
    with open(os.path.join(d, fname), "w") as f: f.write(code)
    success, detail = check_task(d, task)
    lat = (time.time() - start) * 1000
    tin = resp.usage.prompt_tokens or 0
    tout = resp.usage.completion_tokens or 0
    cost = tin * 0.0000005 + tout * 0.0000015
    shutil.rmtree(d, ignore_errors=True)
    return success, cost, lat, tin+tout, 1, 0, detail

def run_condition_D_TOOL_FIRST(task, model="deepseek/deepseek-v4-flash"):
    """TOOL-FIRST: compress outputs before model, use tools for parsing."""
    import openai
    client = openai.OpenAI(api_key=KEY, base_url=BASE)
    d = tempfile.mkdtemp()
    start = time.time()
    fname, is_json = get_fname(task)
    model_calls = 1
    tool_calls = 0
    
    # Tool 1: Compress the task prompt itself for token efficiency
    from prompt_compiler import PromptCompiler
    pc = PromptCompiler()
    task_prompt = pc.compile(task["prompt"], format_hint=True)
    task_prompt = pc.minify(task_prompt)
    
    fmt = "Return ONLY valid JSON." if is_json else "Return ONLY Python code."
    system = f"You are a precise code generator. {fmt}"
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": task_prompt}],
        temperature=0.1, max_tokens=2000,
    )
    content = resp.choices[0].message.content or ""
    
    # Tool 2: Extract code using CodeFenceExtractor instead of regex
    code = extract_code(content)
    tool_calls += 1
    
    # Tool 3: Try JsonRepair if it's JSON (no LLM needed)
    if is_json:
        repaired = JsonRepair.repair(code)
        if repaired["success"]:
            code = json.dumps(repaired["data"])
        tool_calls += 1
    
    with open(os.path.join(d, fname), "w") as f: f.write(code)
    success, detail = check_task(d, task)
    
    # Tool 4: If failed, use TestFailureParser to structure the error
    if not success:
        parsed = TestFailureParser.parse(detail)
        tool_calls += 1
        # Try one retry with compressed error context
        err_context = TracebackReducer.reduce(detail)
        retry_prompt = f"Fix this error:\n{err_context['compressed']}\n\n{fmt}"
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": retry_prompt}],
            temperature=0.1, max_tokens=2000,
        )
        model_calls += 1
        content = resp.choices[0].message.content or ""
        code = extract_code(content)
        with open(os.path.join(d, fname), "w") as f: f.write(code)
        success, detail = check_task(d, task)
    
    lat = (time.time() - start) * 1000
    tin = (resp.usage.prompt_tokens or 0) * model_calls
    tout = (resp.usage.completion_tokens or 0) * model_calls
    cost = tin * 0.0000005 + tout * 0.0000015
    shutil.rmtree(d, ignore_errors=True)
    return success, cost, lat, tin+tout, model_calls, tool_calls, detail

CONDITIONS = {
    "A-RAW": run_condition_A_RAW,
    "B-HERMES": run_condition_B_HERMES,
    "C-CYRALYX": run_condition_C_CYRALYX,
    "D-TOOL-FIRST": run_condition_D_TOOL_FIRST,
}

if __name__ == "__main__":
    suite = get_suite("heldout-v1")
    run_id = f"v2-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    model = "deepseek/deepseek-v4-flash"
    
    print(f"Benchmark V2 — {run_id}")
    print(f"Model: {model}")
    print(f"Suite: {len(suite)} tasks × 4 conditions = {len(suite)*4} runs\n")
    
    for cond_name, cond_fn in CONDITIONS.items():
        print(f"\n{'='*55}")
        print(f"  CONDITION: {cond_name}")
        print(f"{'='*55}")
        successes, total_cost, total_lat, total_tok = 0, 0, 0, 0
        total_calls, total_tools, total_retries = 0, 0, 0
        
        for i, task in enumerate(suite):
            s, c, lat, tok, calls, tools, detail = cond_fn(task, model)
            successes += 1 if s else 0
            total_cost += c
            total_lat += lat
            total_tok += tok
            total_calls += calls
            total_tools += tools
            
            # Record to DB
            DB.execute("""
                INSERT INTO results (run_id, task_id, category, condition, model,
                    timestamp, success, score, input_tokens, output_tokens,
                    total_tokens, estimated_cost, latency_ms, model_calls,
                    tool_calls, retries, failure_type, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (run_id, task["id"], task["category"], cond_name, model,
                  datetime.now().isoformat(), 1 if s else 0, 1.0 if s else 0,
                  tok//2, tok//2, tok, c, lat, calls, tools, 0,
                  "OK" if s else "FAIL", detail[:200]))
            DB.commit()
            
            mark = "PASS" if s else "FAIL"
            print(f"  [{i+1:2d}/{len(suite)}] {task['id']:15s} {mark:4s} cost=${c:.5f} lat={lat:.0f}ms calls={calls}")
        
        n = len(suite)
        rate = successes / n * 100
        avg_cost = total_cost / n
        avg_lat = total_lat / n
        avg_tok = total_tok / n
        avg_calls = total_calls / n
        avg_tools = total_tools / n
        cps = total_cost / successes if successes > 0 else float("inf")
        
        print(f"\n  {'─'*40}")
        print(f"  {cond_name:20s} {rate:5.1f}%  cost=${avg_cost:.5f}  cps=${cps:.5f}")
        print(f"  {'':20s} lat={avg_lat:.0f}ms  tok={avg_tok:.0f}  calls={avg_calls:.1f}  tools={avg_tools:.1f}")
    
    # Summary table
    print(f"\n{'='*65}")
    print(f"  BENCHMARK V2 SUMMARY — {run_id}")
    print(f"{'='*65}")
    print(f"  {'Condition':20s} {'Rate':>6s} {'Cost/task':>10s} {'CPS':>10s} {'Lat':>7s} {'Tok':>6s} {'Calls':>6s}")
    print(f"  {'─'*65}")
    
    for cond_name in CONDITIONS:
        rows = DB.execute("""
            SELECT AVG(success*100), AVG(estimated_cost), AVG(latency_ms),
                   AVG(total_tokens), AVG(model_calls), AVG(tool_calls)
            FROM results WHERE run_id=? AND condition=?
        """, (run_id, cond_name)).fetchone()
        if rows:
            rate = rows[0] or 0
            cost = rows[1] or 0
            lat = rows[2] or 0
            tok = rows[3] or 0
            calls = rows[4] or 0
            tools = rows[5] or 0
            cps_val = cost / (rate/100) if rate > 0 else float("inf")
            print(f"  {cond_name:20s} {rate:5.1f}%  ${cost:.5f}  ${cps_val:.5f}  {lat:5.0f}ms {tok:5.0f}  {calls:4.1f}")
    
    # Generate JSON report
    report = {"run_id": run_id, "model": model, "timestamp": datetime.now().isoformat(), "conditions": {}}
    for cond_name in CONDITIONS:
        rows = DB.execute("""
            SELECT AVG(success*100), AVG(estimated_cost), AVG(latency_ms),
                   AVG(total_tokens), AVG(model_calls), SUM(CASE WHEN success=0 THEN 1 ELSE 0 END)
            FROM results WHERE run_id=? AND condition=?
        """, (run_id, cond_name)).fetchone()
        if rows:
            rate = rows[0] or 0
            failures = rows[5] or 0
            report["conditions"][cond_name] = {"rate": rate, "cost": rows[1], "latency": rows[2], "tokens": rows[3], "model_calls": rows[4], "failures": failures}
    
    report_path = os.path.join(RESULTS_DIR, f"report-{run_id}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report: {report_path}")
