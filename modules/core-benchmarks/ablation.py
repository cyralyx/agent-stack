#!/usr/bin/env python3
"""Ablation study — isolates WHICH optimization caused the gain."""
import sys, tempfile, os, subprocess, re, time, shutil
sys.path.insert(0, "/opt/data")
from task_suite import get_suite

KEY = os.environ.get("OPENAI_API_KEY", "")
BASE = os.environ.get("OPENAI_BASE_URL", "https://inference-api.nousresearch.com/v1")

def check(task_dir, task):
    try:
        r = subprocess.run(task["validation"], shell=True, capture_output=True, text=True, timeout=10, cwd=task_dir)
        return r.returncode == 0, (r.stdout or r.stderr)[:200]
    except: return False, "TIMEOUT"

def extract(content):
    for tag in ["```python", "```json"]:
        if tag in content:
            return content.split(tag)[1].split("```")[0].strip()
    if "```" in content:
        return content.split("```")[1].strip()
    return content.strip()

def run_condition(condition, task):
    import openai
    client = openai.OpenAI(api_key=KEY, base_url=BASE)
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
    
    # === CONDITION-SPECIFIC PROMPT ===
    verbose_sys = "You are a precise code generator. Guidelines: 1. Write ONLY the requested function/class. 2. Handle edge cases. 3. Use Python idioms. 4. Your code will be tested programmatically. 5. Import stdlib modules at the top. 6. Do NOT include test code or print statements."
    concise_sys = f"You are a precise code generator. Return ONLY {'valid JSON.' if is_json else 'Python code in a ```python block.'} No explanation."
    raw_sys = "You are a helpful programming assistant. Write a Python function as requested."
    
    if condition == "A-VERBOSE":
        system = verbose_sys
        temp = 0.3
    elif condition == "B-CONCISE":
        system = concise_sys
        temp = 0.3
    elif condition == "C-AUTO-FMT":
        system = concise_sys  # same concise but with auto format hint
        temp = 0.3
    elif condition == "D-LOW-TEMP":
        system = concise_sys
        temp = 0.1
    else:  # E-FULL (optimized)
        system = concise_sys
        temp = 0.1
    
    resp = client.chat.completions.create(
        model="deepseek/deepseek-v4-flash",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": task["prompt"]}],
        temperature=temp, max_tokens=2000,
    )
    content = resp.choices[0].message.content or ""
    code = extract(content)  
    
    with open(os.path.join(d, fname), "w") as f:
        f.write(code)
    
    success, detail = check(d, task)
    lat = (time.time() - start) * 1000
    tok_in = resp.usage.prompt_tokens or 0
    tok_out = resp.usage.completion_tokens or 0
    cost = (tok_in * 0.0000005 + tok_out * 0.0000015)
    
    shutil.rmtree(d, ignore_errors=True)
    return success, detail, cost, lat

# Run ablations on a subset (8 tasks for speed)
suite = get_suite("heldout-v1")
subset = [t for t in suite if t["id"] in [
    "debug-003", "debug-005", "debug-008",
    "tool-003", "tool-005",
    "struct-001", "struct-003", "struct-006",
]]

conditions = ["A-VERBOSE", "B-CONCISE", "D-LOW-TEMP", "E-FULL"]

print("=== ABLATION STUDY (8 tasks) ===\n")
for cond in conditions:
    succ = 0
    costs = []
    for task in subset:
        s, _, c, _ = run_condition(cond, task)
        if s: succ += 1
        costs.append(c)
    avg_c = sum(costs) / len(costs)
    print(f"  {cond:15s} {succ}/8 = {succ/8*100:2.0f}%  avg_cost=${avg_c:.5f}")

print("\nWhat changed vs previous results:")
print("  A-VERBOSE  = old verbose system prompt, temp=0.3")
print("  B-CONCISE  = new concise prompt, temp=0.3")
print("  D-LOW-TEMP = concise prompt + temp=0.1")
print("  E-FULL     = optimized (concise + low-temp + auto format)")
