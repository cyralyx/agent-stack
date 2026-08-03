#!/usr/bin/env python3
"""Weak-to-Strong Experiment Runner — Compares RAW model vs Cyralyx-augmented.
Records results to SQLite + JSONL. Generates report."""
import json, os, sys, time, hashlib, sqlite3, subprocess, tempfile, shutil
from datetime import datetime
from pathlib import Path

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

DB_PATH = os.path.join(RESULTS_DIR, "experiments.db")

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT, task_id TEXT, task_category TEXT,
            condition TEXT, model TEXT, provider TEXT,
            cyralyx_version TEXT, timestamp TEXT,
            prompt_hash TEXT, success INTEGER, score REAL,
            input_tokens INTEGER, output_tokens INTEGER,
            total_tokens INTEGER, estimated_cost REAL,
            latency_ms REAL, turns INTEGER, tool_calls INTEGER,
            skills_used INTEGER, retries INTEGER,
            verification_attempts INTEGER,
            failure_type TEXT, error_message TEXT,
            notes TEXT
        )
    """)
    db.commit()
    return db

FAILURE_TYPES = [
    "REASONING_ERROR", "CODING_ERROR", "SYNTAX_ERROR",
    "WRONG_TOOL", "TOOL_FAILURE", "INVALID_ARGUMENTS",
    "PLANNING_ERROR", "CONTEXT_LOSS", "HALLUCINATION",
    "TIMEOUT", "ENVIRONMENT_ERROR", "DEPENDENCY_ERROR",
    "VERIFICATION_FAILURE", "OUTPUT_FORMAT_ERROR",
    "MODEL_REFUSAL", "UNKNOWN"
]

def classify_failure(output, error_msg=""):
    """Simple failure classification based on output content."""
    if not output and not error_msg:
        return "UNKNOWN"
    err = (output + " " + error_msg).lower()
    if "timeout" in err: return "TIMEOUT"
    if "syntax" in err or "indentation" in err: return "SYNTAX_ERROR"
    if "traceback" in err or "error" in err: return "CODING_ERROR"
    if "module" in err and "found" in err: return "DEPENDENCY_ERROR"
    if "refus" in err or "cannot" in err: return "MODEL_REFUSAL"
    if "format" in err or "json" in err: return "OUTPUT_FORMAT_ERROR"
    if "tool" in err or "command" in err: return "WRONG_TOOL"
    if len(output or "") > 10000: return "CONTEXT_LOSS"
    return "UNKNOWN"

def check_task_code(task_dir, task):
    """Run deterministic validation for a task. Returns (success, score, detail)."""
    val_cmd = task["validation"]
    try:
        r = subprocess.run(val_cmd, shell=True, capture_output=True, text=True, timeout=10, cwd=task_dir)
        success = r.returncode == 0
        score = 1.0 if success else 0.0
        detail = r.stdout.strip()[:200] if success else r.stderr.strip()[:200]
        failure = "" if success else classify_failure(r.stdout + r.stderr, r.stderr)
        return success, score, detail, failure
    except subprocess.TimeoutExpired:
        return False, 0.0, "TIMEOUT", "TIMEOUT"
    except Exception as e:
        return False, 0.0, str(e)[:200], "ENVIRONMENT_ERROR"

def run_raw_condition(task, model="deepseek/deepseek-v4-flash", provider="openai-api"):
    """Run a task with the raw model — no Cyralyx augmentation."""
    work_dir = tempfile.mkdtemp()
    try:
        # Create the setup file
        setup_code = task.get("setup", "")
        with open(os.path.join(work_dir, "solution.py"), "w") as f:
            f.write(setup_code)
        
        # Record start time
        start = time.time()
        
        # Call the model via Hermes API
        prompt = task["prompt"]
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
        
        # Use the provider API directly
        import openai
        api_key = os.environ.get("OPENAI_API_KEY", "")
        api_base = os.environ.get("OPENAI_BASE_URL", "https://inference-api.nousresearch.com/v1")
        
        client = openai.OpenAI(api_key=api_key, base_url=api_base)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful programming assistant. Write a Python function as requested. Return ONLY the function code, no explanation."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        
        latency_ms = (time.time() - start) * 1000
        
        # Extract code from response
        content = response.choices[0].message.content or ""
        
        # Try to extract Python code block
        if "```python" in content:
            code = content.split("```python")[1].split("```")[0].strip()
        elif "```" in content:
            code = content.split("```")[1].strip()
        else:
            code = content.strip()
        
        # Extract the correct module name from the validation command
        import re
        is_json = "json.load(open(" in task["validation"] or "json.load(open('" in task["validation"]
        
        if is_json:
            # JSON tasks: extract filename from validation command
            m = re.search(r"open\('([^']+\.json)'", task["validation"])
            fname = m.group(1) if m else "output.json"
            with open(os.path.join(work_dir, fname), "w") as f:
                f.write(code)
        else:
            mod_name = re.search(r"from (\w+) import", task["validation"])
            mod_name = mod_name.group(1) if mod_name else task["id"].replace("-", "_")
            with open(os.path.join(work_dir, f"{mod_name}.py"), "w") as f:
                f.write(code)
        
        # Evaluate
        success, score, detail, failure = check_task_code(work_dir, task)
        
        tokens_in = response.usage.prompt_tokens if response.usage else 0
        tokens_out = response.usage.completion_tokens if response.usage else 0
        cost = (tokens_in * 0.0000005 + tokens_out * 0.0000015)  # approximate
        
        return {
            "success": success, "score": score,
            "latency_ms": latency_ms, "failure_type": failure,
            "input_tokens": tokens_in, "output_tokens": tokens_out,
            "total_tokens": tokens_in + tokens_out,
            "estimated_cost": cost, "turns": 1, "tool_calls": 0,
            "skills_used": 0, "retries": 0, "verification_attempts": 0,
            "error_message": detail, "prompt_hash": prompt_hash,
            "notes": "",
        }
    except Exception as e:
        return {
            "success": False, "score": 0.0,
            "latency_ms": (time.time() - start) * 1000,
            "failure_type": "ENVIRONMENT_ERROR",
            "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
            "estimated_cost": 0.0, "turns": 1, "tool_calls": 0,
            "skills_used": 0, "retries": 0, "verification_attempts": 0,
            "error_message": str(e)[:200], "prompt_hash": "",
            "notes": f"Exception: {e}",
        }
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

def run_cyralyx_condition(task, model="deepseek/deepseek-v4-flash", provider="openai-api"):
    """Run a task with full Cyralyx augmentation."""
    work_dir = tempfile.mkdtemp()
    try:
        setup_code = task.get("setup", "")
        with open(os.path.join(work_dir, "solution.py"), "w") as f:
            f.write(setup_code)
        
        start = time.time()
        prompt = task["prompt"]
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
        
        # Cyralyx-augmented system prompt
        system_prompt = """You are a precise code generator. Your task is to write correct, working Python code.

Guidelines:
1. Write ONLY the requested function/class — no extra code
2. Handle edge cases (empty input, None, etc.)
3. Use proper Python idioms
4. Your code will be tested programmatically — it MUST pass all test cases
5. If you need to use standard library modules, import them at the top
6. Do NOT include test code or print statements in your final output

Return ONLY the code block."""
        
        import openai
        api_key = os.environ.get("OPENAI_API_KEY", "")
        api_base = os.environ.get("OPENAI_BASE_URL", "https://inference-api.nousresearch.com/v1")
        
        client = openai.OpenAI(api_key=api_key, base_url=api_base)
        
        # Condition B: Full Cyralyx — structured prompt + code extraction + verification
        # Attempt 1: Generate code
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        
        content = response.choices[0].message.content or ""
        
        if "```python" in content:
            code = content.split("```python")[1].split("```")[0].strip()
        elif "```" in content:
            code = content.split("```")[1].strip()
        else:
            code = content.strip()
        
        # Extract the correct module name from the validation command
        import re
        is_json = "json.load(open(" in task["validation"] or "json.load(open('" in task["validation"]
        
        if is_json:
            m = re.search(r"open\('([^']+\.json)'", task["validation"])
            fname = m.group(1) if m else "output.json"
        else:
            mod_name = re.search(r"from (\w+) import", task["validation"])
            mod_name = mod_name.group(1) if mod_name else task["id"].replace("-", "_")
            fname = f"{mod_name}.py"
        
        with open(os.path.join(work_dir, fname), "w") as f:
            f.write(code)
        
        success, score, detail, failure = check_task_code(work_dir, task)
        
        # Cyralyx: retry on failure (up to 2 more attempts)
        retries = 0
        verification_attempts = 1
        all_results = [success]
        
        while not success and retries < 2:
            retries += 1
            verification_attempts += 1
            
            # Adaptive retry with error feedback
            error_context = detail[:500]
            retry_prompt = f"""The previous code failed. Here is the error:

{error_context}

Fix the code to handle this error. Write ONLY the corrected function."""
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": retry_prompt}
                ],
                temperature=0.2,
                max_tokens=2000,
            )
            
            content = response.choices[0].message.content or ""
            if "```python" in content:
                code = content.split("```python")[1].split("```")[0].strip()
            elif "```" in content:
                code = content.split("```")[1].strip()
            else:
                code = content.strip()
            
            with open(os.path.join(work_dir, fname), "w") as f:
                f.write(code)
            
            success, score, detail, failure = check_task_code(work_dir, task)
            all_results.append(success)
        
        latency_ms = (time.time() - start) * 1000
        
        tokens_in = response.usage.prompt_tokens if response.usage else 0
        tokens_out = response.usage.completion_tokens if response.usage else 0
        # Estimate total tokens across all attempts
        total_in = tokens_in * (retries + 1)
        total_out = tokens_out * (retries + 1)
        cost = (total_in * 0.0000005 + total_out * 0.0000015)
        
        return {
            "success": success, "score": score,
            "latency_ms": latency_ms, "failure_type": failure,
            "input_tokens": total_in, "output_tokens": total_out,
            "total_tokens": total_in + total_out,
            "estimated_cost": cost,
            "turns": 1, "tool_calls": 0,
            "skills_used": 0, "retries": retries,
            "verification_attempts": verification_attempts,
            "error_message": detail,
            "prompt_hash": prompt_hash,
            "notes": f"Attempts: {retries+1}, success chain: {all_results}",
        }
    except Exception as e:
        return {
            "success": False, "score": 0.0,
            "latency_ms": (time.time() - start) * 1000 if 'start' in dir() else 0,
            "failure_type": "ENVIRONMENT_ERROR",
            "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
            "estimated_cost": 0.0, "turns": 1, "tool_calls": 0,
            "skills_used": 0, "retries": 0, "verification_attempts": 0,
            "error_message": str(e)[:200], "prompt_hash": "",
            "notes": f"Exception: {e}",
        }
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

def record_result(db, task, condition, model, result, experiment_id):
    db.execute("""
        INSERT INTO results (experiment_id, task_id, task_category, condition,
            model, provider, cyralyx_version, timestamp, prompt_hash,
            success, score, input_tokens, output_tokens, total_tokens,
            estimated_cost, latency_ms, turns, tool_calls, skills_used,
            retries, verification_attempts, failure_type, error_message, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        experiment_id, task["id"], task["category"], condition,
        model, "openai-api", "1.0.0", datetime.now().isoformat(),
        result.get("prompt_hash", ""),
        1 if result["success"] else 0, result["score"],
        result["input_tokens"], result["output_tokens"], result["total_tokens"],
        result["estimated_cost"], result["latency_ms"],
        result["turns"], result["tool_calls"], result["skills_used"],
        result["retries"], result["verification_attempts"],
        result["failure_type"], result["error_message"][:200], result["notes"][:200],
    ))
    db.commit()

def generate_report(db, experiment_id, model):
    rows = db.execute("""
        SELECT condition, AVG(success*100) as rate, COUNT(*) as n,
               AVG(estimated_cost) as cost, AVG(latency_ms) as lat,
               AVG(total_tokens) as tokens, AVG(retries) as avg_retries,
               SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) as failures
        FROM results WHERE experiment_id=?
        GROUP BY condition ORDER BY rate DESC
    """, (experiment_id,)).fetchall()
    
    failure_rows = db.execute("""
        SELECT condition, failure_type, COUNT(*) as cnt
        FROM results WHERE experiment_id=? AND success=0
        GROUP BY condition, failure_type ORDER BY cnt DESC
    """, (experiment_id,)).fetchall()
    
    print("=" * 65)
    print(f"  WEAK-TO-STRONG EXPERIMENT: {experiment_id}")
    print(f"  Model: {model}")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65)
    print()
    print(f"  {'Metric':35s} {'Raw':>12s} {'Cyralyx':>12s}")
    print(f"  {'-'*60}")
    
    raw = {r[0]: r for r in rows}
    for metric, raw_key, cyralyx_key in [
        ("Success rate", "A-RAW", "B-CYRALYX"),
        ("Cost per task ($)", "A-RAW", "B-CYRALYX"),
        ("Median latency (ms)", "A-RAW", "B-CYRALYX"),
        ("Avg tokens per task", "A-RAW", "B-CYRALYX"),
        ("Avg retries per task", "A-RAW", "B-CYRALYX"),
    ]:
        r = raw.get(raw_key)
        c = raw.get(cyralyx_key)
        if r and c:
            if metric == "Success rate":
                print(f"  {metric:35s} {r[1]:>10.1f}%{'':>3s} {c[1]:>10.1f}%{'':>3s} Delta: {c[1]-r[1]:+.1f}pp")
            elif metric == "Cost per task ($)":
                print(f"  {metric:35s} ${r[3]:>9.6f}{'':>3s} ${c[3]:>9.6f}")
            elif metric == "Median latency (ms)":
                print(f"  {metric:35s} {r[4]:>10.1f}{'':>3s} {c[4]:>10.1f}")
            else:
                print(f"  {metric:35s} {r[5] if len(r)>5 else 0:>10.1f}{'':>3s} {c[5] if len(c)>5 else 0:>10.1f}")
    
    print()
    print("  Failure breakdown:")
    failures = {}
    for fr in failure_rows:
        cond = fr[0]
        failures.setdefault(cond, []).append(f"{fr[1]}:{fr[2]}")
    for cond in ["A-RAW", "B-CYRALYX"]:
        if cond in failures:
            fails = ", ".join(failures[cond])
            print(f"    {cond}: {fails}")
    
    return rows

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tasks"))
    from task_suite import get_suite, ALL_TASKS
    
    model = "deepseek/deepseek-v4-flash"
    experiment_id = f"w2s-{datetime.now().strftime('%Y%m%d-%H%M')}"
    
    suite = get_suite("heldout-v1")
    print(f"Running experiment {experiment_id}")
    print(f"Suite: heldout-v1 ({len(suite)} tasks)")
    print(f"Model: {model}")
    print()
    
    db = get_db()
    
    # Run each task under both conditions
    for i, task in enumerate(suite):
        print(f"[{i+1}/{len(suite)}] {task['id']} ({task['category']})...")
        
        # Condition A: RAW model
        result_a = run_raw_condition(task, model=model)
        record_result(db, task, "A-RAW", model, result_a, experiment_id)
        print(f"  RAW: {'✅' if result_a['success'] else '❌'} ({result_a['failure_type']})")
        
        # Condition B: Cyralyx
        result_b = run_cyralyx_condition(task, model=model)
        record_result(db, task, "B-CYRALYX", model, result_b, experiment_id)
        print(f"  CYX: {'✅' if result_b['success'] else '❌'} ({result_b['failure_type']})")
    
    print()
    generate_report(db, experiment_id, model)
