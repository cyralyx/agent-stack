"""
Harder Discriminating Benchmark V4 — breaks the 100% ceiling.
Includes: multi-file, ambiguous bugs, tool-selection, broken envs, blocker recovery.
"""
import sys, os, tempfile, subprocess, shutil, re

TASKS_V4 = []

# ===== MULTI-FILE CODING (3 tasks) =====
TASKS_V4.append({
    "id": "v4-coding-001",
    "category": "coding",
    "difficulty": "hard",
    "prompt": "You have two files. In 'math_ops.py', write functions: add(a,b), subtract(a,b), multiply(a,b), divide(a,b) where divide raises ValueError on division by zero. In 'calculator.py', import from math_ops and provide a function calculate(a, op, b) that returns the result for ops '+', '-', '*', '/' and raises ValueError for unknown ops. Then write a test file 'test_calc.py' with 5 pytest tests covering normal operations and edge cases.",
    "validation": "python3 -m pytest test_calc.py -v 2>&1 | tail -5",
    "setups": ["math_ops.py: pass", "calculator.py: pass"],
})

TASKS_V4.append({
    "id": "v4-coding-002",
    "category": "coding",
    "difficulty": "hard",
    "prompt": "Write a Python package structure with 'utils/__init__.py', 'utils/strings.py' (contains reverse(s), capitalize_words(s)), 'utils/numbers.py' (contains is_prime(n), factorial(n)), and a 'setup.py' that makes it installable. The package must be importable and all functions must work correctly.",
    "validation": "python3 -c \"from utils.strings import reverse; assert reverse('hello')=='olleh'; from utils.numbers import is_prime; assert is_prime(7); assert not is_prime(4); print('OK')\"",
})

TASKS_V4.append({
    "id": "v4-coding-003",
    "category": "coding",
    "difficulty": "hard",
    "prompt": "Create a Python script that reads 'config.yaml' with fields: server.host, server.port, database.url, logging.level. Then generate a 'config.json' with the same values in JSON format. Handle missing file gracefully. The script must work even if 'config.yaml' uses indentation with 2 spaces instead of 4.",
    "validation": "python3 -c \"import yaml, json; yaml.safe_load(open('config.yaml')); json.load(open('config.json')); print('OK')\"",
})

# ===== AMBIGUOUS BUGS (3 tasks) =====
TASKS_V4.append({
    "id": "v4-bug-001",
    "category": "debugging",
    "difficulty": "hard",
    "prompt": "Fix the function:\n\ndef get_average(numbers):\n    total = sum(numbers)\n    count = len(numbers)\n    return total / count\n\nIt passes basic tests but returns wrong results for empty lists and has a subtle issue with integer division in Python 3. Fix ALL issues.",
    "validation": "python3 -c \"from fix_avg import get_average; assert get_average([1,2,3])==2.0; assert get_average([1])==1.0; assert get_average([])==0.0; assert isinstance(get_average([1,2]), float); print('OK')\"",
})

TASKS_V4.append({
    "id": "v4-bug-002",
    "category": "debugging",
    "difficulty": "hard",
    "prompt": "The function below claims to sort a list but has a hidden bug:\n\ndef sort_list(lst):\n    n = len(lst)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if lst[j] > lst[j+1]:\n                lst[j], lst[j+1] = lst[j+1], lst[j]\n    return lst\n\nIt works for [3,1,2] but fails for [5,4,3,2,1]. Find and fix the bug.",
    "validation": "python3 -c \"from fix_sort import sort_list; assert sort_list([3,1,2])==[1,2,3]; assert sort_list([5,4,3,2,1])==[1,2,3,4,5]; assert sort_list([])==[]; assert sort_list([1])==[1]; print('OK')\"",
})

TASKS_V4.append({
    "id": "v4-bug-003",
    "category": "debugging",
    "difficulty": "hard",
    "prompt": "Fix this caching decorator:\n\ndef cache(func):\n    cache_dict = {}\n    def wrapper(*args):\n        if args not in cache_dict:\n            cache_dict[args] = func(*args)\n        return cache_dict[args]\n    return wrapper\n\nThe function appears correct but has a serious issue: the cache_dict is shared across all decorated functions, so calling different functions with the same arguments returns wrong cached results. Fix it so each function has its own cache.",
    "validation": "python3 -c \"from fix_cache import cache\n@cache\ndef double(x): return x*2\n@cache\ndef triple(x): return x*3\nassert double(2)==4; assert triple(2)==6; assert double(2)==4; print('OK')\"",
})

# ===== TOOL-SELECTION (3 tasks) =====
TASKS_V4.append({
    "id": "v4-tool-001",
    "category": "tool_use",
    "difficulty": "medium",
    "prompt": "Find the 3 largest files in the current directory (excluding .git and __pycache__) and return their paths and sizes in bytes as a list of (path, size) tuples sorted by size descending. Write a Python function `largest_files()` that does this.",
    "validation": "python3 -c \"from find_large import largest_files; result = largest_files(); assert isinstance(result, list); assert all(len(item)==2 for item in result); print('OK')\"",
})

TASKS_V4.append({
    "id": "v4-tool-002",
    "category": "tool_use",
    "difficulty": "hard",
    "prompt": "Write a Python script that finds all Python files (.py) containing the string 'TODO' or 'FIXME' (case-insensitive) in comments. Print each match as 'filename:line_number:matched_text'. Handle the case where files might not be readable gracefully.",
    "validation": "python3 -c \"from find_todo import find_todo; result = find_todo('.'); assert isinstance(result, list); print('OK')\"",
})

TASKS_V4.append({
    "id": "v4-tool-003",
    "category": "tool_use",
    "difficulty": "medium",
    "prompt": "Write a Python script that parses 'server.log' (each line format: 'LEVEL:timestamp:message') and returns a dict with ERROR and WARN counts, the 5 most recent ERROR messages, and the time range of the log. If file is missing, return empty dict.",
    "validation": "python3 -c \"from log_analyzer import analyze_log; import tempfile, os; d=tempfile.mkdtemp(); open(d+'/server.log','w').write('ERROR:101:failed\\nWARN:102:slow\\nERROR:103:crashed\\n'); import sys; sys.path.insert(0,d); r=analyze_log(d+'/server.log'); assert r['error_count']==2; assert r['warn_count']==1; print('OK')\"",
})

# ===== BROKEN ENVIRONMENTS (3 tasks) =====
TASKS_V4.append({
    "id": "v4-env-001",
    "category": "debugging",
    "difficulty": "hard",
    "prompt": "The command 'pytest' fails saying 'bash: pytest: command not found'. But pytest IS installed. The issue is that the python -m path works but the shell can't find the pytest entry point. Write a fix and verify pytest runs.",
    "validation": "python3 -m pytest --version 2>&1 | head -1",
})

TASKS_V4.append({
    "id": "v4-env-002",
    "category": "debugging",
    "difficulty": "medium",
    "prompt": "A Python script 'app.py' imports a module 'config' but gets ModuleNotFoundError. The 'config.py' file exists in the same directory. The issue might be a naming conflict with Python's built-in or a sys.path issue. Diagnose and fix. Write a minimal fix and verify 'from app import *' works.",
    "validation": "python3 -c \"import sys; sys.path.insert(0,'.'); from app import *; print('OK')\"",
})

TASKS_V4.append({
    "id": "v4-env-003",
    "category": "debugging",
    "difficulty": "hard",
    "prompt": "A JSON file 'data.json' contains '{\"users\": [{\"name\": \"Alice\", \"age\": 30, \"email\": \"alice@test.com\"},]}' — note the trailing comma after the last array element. Python's json.load fails on this. Write a repair script that fixes the JSON and loads it successfully. The fix should handle trailing commas in both objects and arrays.",
    "validation": "python3 -c \"from fix_json import load_json; data = load_json('data.json'); assert len(data['users'])==1; assert data['users'][0]['name']=='Alice'; print('OK')\"",
})

# ===== ADVERSARIAL / FALSE SUCCESS (3 tasks) =====
TASKS_V4.append({
    "id": "v4-adversarial-001",
    "category": "debugging",
    "difficulty": "hard",
    "prompt": "The function below passes basic tests but has a subtle bug with mutable default arguments:\n\ndef add_item(item, items=[]):\n    items.append(item)\n    return items\n\nFix it so each call without items starts with a fresh empty list.",
    "validation": "python3 -c \"from fix_mutable import add_item; assert add_item(1)==[1]; assert add_item(2)==[2]; assert add_item(3)==[3]; print('OK')\"",
})

TASKS_V4.append({
    "id": "v4-adversarial-002",
    "category": "debugging",
    "difficulty": "hard",
    "prompt": "The following claims to be a palindrome checker but has a bug:\n\ndef is_palindrome(s):\n    return s == s[::-1]\n\nThis fails for 'Racecar' (case-sensitive) and 'A man, a plan' (ignores spaces/punctuation). Fix it to handle case and non-alphanumeric characters properly.",
    "validation": "python3 -c \"from fix_palindrome import is_palindrome; assert is_palindrome('racecar'); assert is_palindrome('Racecar'); assert is_palindrome('A man, a plan, a canal: Panama'); assert not is_palindrome('hello'); print('OK')\"",
})

TASKS_V4.append({
    "id": "v4-adversarial-003",
    "category": "debugging",
    "difficulty": "hard",
    "prompt": "This function appears to count word frequency correctly but silently fails for hyphenated words and words with apostrophes:\n\ndef word_count(text):\n    words = text.lower().split()\n    from collections import Counter\n    return dict(Counter(words))\n\nFix it to handle 'state-of-the-art', contractions like 'dont', and punctuation properly.",
    "validation": "python3 -c \"from fix_wordcount import word_count; r = word_count('dont stop the state-of-the-art music'); assert r.get('dont', 0)==1; assert r.get('state-of-the-art', 0)==1; print('OK')\"",
})

# ===== REPOSITORY NAVIGATION (2 tasks) =====
TASKS_V4.append({
    "id": "v4-repo-001",
    "category": "tool_use",
    "difficulty": "hard",
    "prompt": "Write a Python script 'repo_stats.py' that analyzes a git repository. It should return: total commits, number of unique authors, most recent commit message, and number of files tracked. Run it on the current directory.",
    "validation": "python3 -c \"from repo_stats import repo_stats; r = repo_stats('.'); assert isinstance(r['commits'], int); assert r['commits'] > 0; assert len(r['recent_message']) > 0; print('OK')\"",
})

TASKS_V4.append({
    "id": "v4-repo-002",
    "category": "tool_use",
    "difficulty": "hard",
    "prompt": "Find all Python files in the repository that import from 'os' or 'sys' modules. Write a function find_stdlib_imports() that returns a dict mapping filename to list of imported stdlib modules.",
    "validation": "python3 -c \"from find_imports import find_stdlib_imports; r = find_stdlib_imports(); assert isinstance(r, dict); print('OK')\"",
})

ALL_V4 = TASKS_V4
DEV_V4 = TASKS_V4[:5]  # 5 dev
HELD_OUT_V4 = TASKS_V4[5:]  # 15 held-out
