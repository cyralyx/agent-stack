#!/usr/bin/env python3
"""Quick task suite validator — runs all task solutions through their validation."""
import sys, tempfile, os, subprocess, re, shutil, json

sys.path.insert(0, "/opt/data")
from task_suite import ALL_TASKS, _module_name

def test_task(task):
    d = tempfile.mkdtemp()
    try:
        sol = task.get("solution", "")
        if not sol:
            print(f"  ⚠️  {task['id']}: no solution defined")
            return False
        
        # Determine if this is a JSON output task
        is_json = any(kw in task["validation"] for kw in ["json.load(open(", "json.load(open('"])
        
        if is_json:
            # JSON tasks: write the solution to a JSON file with the expected name
            # Extract filename from validation command
            m = re.search(r"open\('([^']+\.json)'", task["validation"])
            if m:
                fname = m.group(1)
                with open(os.path.join(d, fname), "w") as f:
                    f.write(sol)
            else:
                print(f"  ❌ {task['id']}: cant extract JSON filename")
                return False
        else:
            # Python module tasks
            mod_name = _module_name(task["validation"])
            with open(os.path.join(d, f"{mod_name}.py"), "w") as f:
                f.write(sol)
        
        r = subprocess.run(task["validation"], shell=True, capture_output=True, text=True, timeout=10, cwd=d)
        ok = r.returncode == 0
        if not ok:
            print(f"  ❌ {task['id']}: {r.stderr[:100]}")
        else:
            print(f"  ✅ {task['id']} ({task['category']})")
        return ok
    except Exception as e:
        print(f"  ❌ {task['id']}: {e}")
        return False
    finally:
        shutil.rmtree(d, ignore_errors=True)

passed = 0
total = len(ALL_TASKS)
print(f"Testing {total} tasks...\n")
for t in ALL_TASKS:
    if test_task(t):
        passed += 1

print(f"\n{passed}/{total} tasks validated successfully")
print("READY" if passed == total else f"FAILURES: {total - passed}")
