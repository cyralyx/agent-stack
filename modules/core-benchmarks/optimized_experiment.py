#!/usr/bin/env python3
"""Optimized Cyralyx runner — smarter retry, faster, cheaper."""
import sys, json, tempfile, os, subprocess, re, time, shutil

sys.path.insert(0, "/opt/data")
from task_suite import get_suite

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://inference-api.nousresearch.com/v1")

def classify_failure(output, error_msg=""):
    err = (output + " " + error_msg).lower()
    if "traceback" in err or "error" in err: return "CODING_ERROR"
    if "syntax" in err: return "SYNTAX_ERROR"
    if "refus" in err: return "MODEL_REFUSAL"
    if "json" in err or "decode" in err: return "OUTPUT_FORMAT_ERROR"
    return "UNKNOWN"

def check_task(task_dir, task):
    val_cmd = task["validation"]
    try:
        r = subprocess.run(val_cmd, shell=True, capture_output=True, text=True, timeout=10, cwd=task_dir)
        return r.returncode == 0, r.stdout.strip()[:200] if r.returncode == 0 else r.stderr.strip()[:200]
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as e:
        return False, str(e)[:200]

def extract_code(content):
    if "```python" in content:
        return content.split("```python")[1].split("```")[0].strip()
    if "```json" in content:
        return content.split("```json")[1].split("```")[0].strip()
    if "```" in content:
        return content.split("```")[1].strip()
    return content.strip()

def run_optimized(task, model="deepseek/deepseek-v4-flash"):
    import openai
    client = openai.OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    d = tempfile.mkdtemp()
    start = time.time()
    
    is_json = "json.load(open(" in task["validation"]
    if is_json:
        m = re.search(r"open\('([^']+\.json)'", task["validation"])
        fname = m.group(1) if m else "output.json"
    else:
        mod_name = re.search(r"from (\w+) import", task["validation"])
        mod_name = mod_name.group(1) if mod_name else task["id"].replace("-", "_")
        fname = f"{mod_name}.py"
    
    # Shorter, task-specific system prompt
    fmt_hint = "Return ONLY valid JSON." if is_json else "Return ONLY Python code in a ```python block."
    system = f"You are a precise code generator. {fmt_hint} No explanation."
    
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": task["prompt"]}],
        temperature=0.1, max_tokens=2000,
    )
    content = resp.choices[0].message.content or ""
    code = extract_code(content)
    
    with open(os.path.join(d, fname), "w") as f:
        f.write(code)
    
    success, detail = check_task(d, task)
    tokens_in = resp.usage.prompt_tokens or 0
    tokens_out = resp.usage.completion_tokens or 0
    total_in, total_out = tokens_in, tokens_out
    
    retries = 0
    failure_type = ""
    if not success:
        failure_type = classify_failure(detail)
    
    # Smart retry: only retry CODING_ERROR or SYNTAX_ERROR
    while not success and retries < 2 and failure_type in ("CODING_ERROR", "SYNTAX_ERROR"):
        retries += 1
        # Extract the actual error concisely
        err_short = detail.split("\n")[-1] if "\n" in detail else detail
        err_short = err_short[:300]
        retry_prompt = f"The code had this error:\n{err_short}\n\nFix it. {fmt_hint}"
        
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": retry_prompt}],
            temperature=0.1, max_tokens=2000,
        )
        content = resp.choices[0].message.content or ""
        code = extract_code(content)
        total_in += resp.usage.prompt_tokens or 0
        total_out += resp.usage.completion_tokens or 0
        
        with open(os.path.join(d, fname), "w") as f:
            f.write(code)
        
        success, detail = check_task(d, task)
        if not success:
            failure_type = classify_failure(detail)
    
    lat = (time.time() - start) * 1000
    cost = (total_in * 0.0000005 + total_out * 0.0000015)
    shutil.rmtree(d, ignore_errors=True)
    return success, failure_type, cost, lat, total_in + total_out, retries

# Main benchmark
suite = get_suite("heldout-v1")
print(f"Optimized Cyralyx — {len(suite)} tasks\n")

results = []
for i, task in enumerate(suite):
    suc, ft, cost, lat, tok, ret = run_optimized(task)
    results.append((task["id"], suc, cost, lat, tok, ret))
    mark = "PASS" if suc else "FAIL"
    print(f"  [{i+1:2d}] {task['id']:15s} {mark:4s} cost=${cost:.5f} lat={lat:.0f}ms ret={ret}")

print(f"\n=== SUMMARY ===")
n = len(results)
succ = sum(1 for r in results if r[1])
total_cost = sum(r[2] for r in results) / n
total_lat = sum(r[3] for r in results) / n
total_tok = sum(r[4] for r in results) / n
total_ret = sum(r[5] for r in results) / n
print(f"Success rate: {succ}/{n} = {succ/n*100:.0f}%")
print(f"Avg cost/task: ${total_cost:.6f}")
print(f"Avg latency: {total_lat:.0f}ms")
print(f"Avg tokens/task: {total_tok:.0f}")
print(f"Avg retries/task: {total_ret:.2f}")
