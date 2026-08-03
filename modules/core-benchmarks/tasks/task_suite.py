"""Deterministic task suite for weak-to-strong benchmarks.
20 held-out tasks + 10 development tasks.
Categories: coding, debugging, tool_use, structured_output.
Every task has deterministic validation."""
import json, os, tempfile, subprocess, shutil, re

TASKS_DIR = os.path.dirname(os.path.abspath(__file__))

TASKS = []

def _module_name(validation_cmd):
    """Extract the module name from a validation command."""
    import re
    m = re.search(r"from (\w+) import", validation_cmd)
    return m.group(1) if m else "solution"

# ===== CODING TASKS (8 tasks) =====
CODING = [
    {
        "id": "coding-001",
        "category": "coding",
        "difficulty": "easy",
        "prompt": "Write a Python function `fib(n)` that returns the nth Fibonacci number. n >= 0. fib(0)=0, fib(1)=1.",
        "validation": "python3 -c \"from fib import fib; assert fib(0)==0; assert fib(1)==1; assert fib(10)==55; assert fib(20)==6765; print('OK')\"",
        "setup": "def fib(n): pass",
        "solution": "def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a",
    },
    {
        "id": "coding-002",
        "category": "coding",
        "difficulty": "easy",
        "prompt": "Write a Python function `is_palindrome(s)` that returns True if string s is a palindrome (same forwards and backwards), ignoring case and non-alphanumeric characters.",
        "validation": "python3 -c \"from palindrome import is_palindrome; assert is_palindrome('racecar'); assert is_palindrome('A man, a plan, a canal: Panama'); assert not is_palindrome('hello'); print('OK')\"",
        "setup": "def is_palindrome(s): pass",
        "solution": "import re\ndef is_palindrome(s):\n    cleaned = re.sub(r'[^a-zA-Z0-9]', '', s).lower()\n    return cleaned == cleaned[::-1]",
    },
    {
        "id": "coding-003",
        "category": "coding",
        "difficulty": "medium",
        "prompt": "Write a Python class `Stack` with push, pop, peek, is_empty, and size methods. pop on empty stack should raise IndexError.",
        "validation": "python3 -c \"from stack import Stack; s=Stack(); s.push(1); s.push(2); assert s.pop()==2; assert s.peek()==1; assert not s.is_empty(); assert s.size()==1; s.pop(); assert s.is_empty();\ntry: s.pop()\nexcept IndexError: print('OK')\"",
        "setup": "class Stack:\n    def __init__(self): pass",
        "solution": "class Stack:\n    def __init__(self):\n        self._items = []\n    def push(self, item):\n        self._items.append(item)\n    def pop(self):\n        if not self._items:\n            raise IndexError('pop from empty stack')\n        return self._items.pop()\n    def peek(self):\n        if not self._items:\n            raise IndexError('peek from empty stack')\n        return self._items[-1]\n    def is_empty(self):\n        return len(self._items) == 0\n    def size(self):\n        return len(self._items)",
    },
    {
        "id": "coding-004",
        "category": "coding",
        "difficulty": "medium",
        "prompt": "Write a Python function `word_frequency(text, n)` that returns the n most common words in text as a list of (word, count) tuples. Ignore case and punctuation. Exclude stop words: the, a, an, is, are, was, were, in, on, at, to, for, of, by, with, and, or, be, have, has, it.",
        "validation": "python3 -c \"from wordfreq import word_frequency; result = word_frequency('The cat and the dog and the bird', 2); assert len(result)<=2; assert all(c==1 for _,c in result); print('OK')\"",
        "setup": "def word_frequency(text, n): pass",
        "solution": "import re\nfrom collections import Counter\nSTOP = {'the','a','an','is','are','was','were','in','on','at','to','for','of','by','with','and','or','be','have','has','it'}\ndef word_frequency(text, n):\n    words = re.findall(r'\\\\w+', text.lower())\n    words = [w for w in words if w not in STOP]\n    return Counter(words).most_common(n)",
    },
    {
        "id": "coding-005",
        "category": "coding",
        "difficulty": "hard",
        "prompt": "Write a Python function `merge_intervals(intervals)` that takes a list of [start, end] intervals and returns a list of merged intervals sorted by start. Each interval is a list of two integers.",
        "validation": "python3 -c \"from merge import merge_intervals; assert merge_intervals([[1,3],[2,6],[8,10],[15,18]])==[[1,6],[8,10],[15,18]]; assert merge_intervals([[1,4],[4,5]])==[[1,5]]; assert merge_intervals([[1,4],[0,0]])==[[0,0],[1,4]]; print('OK')\"",
        "setup": "def merge_intervals(intervals): pass",
        "solution": "def merge_intervals(intervals):\n    if not intervals:\n        return []\n    intervals.sort(key=lambda x: x[0])\n    merged = [intervals[0]]\n    for start, end in intervals[1:]:\n        if start <= merged[-1][1]:\n            merged[-1][1] = max(merged[-1][1], end)\n        else:\n            merged.append([start, end])\n    return merged",
    },
    {
        "id": "coding-006",
        "category": "coding",
        "difficulty": "easy",
        "prompt": "Write a Python function `fizzbuzz(n)` that returns a list of strings for numbers 1 to n. Multiples of 3: 'Fizz', multiples of 5: 'Buzz', multiples of both: 'FizzBuzz', otherwise the number as a string.",
        "validation": "python3 -c \"from fizzbuzz import fizzbuzz; r=fizzbuzz(15); assert r[2]=='Fizz'; assert r[4]=='Buzz'; assert r[14]=='FizzBuzz'; assert r[6]=='7'; print('OK')\"",
        "setup": "def fizzbuzz(n): pass",
        "solution": "def fizzbuzz(n):\n    result = []\n    for i in range(1, n+1):\n        if i % 15 == 0: result.append('FizzBuzz')\n        elif i % 3 == 0: result.append('Fizz')\n        elif i % 5 == 0: result.append('Buzz')\n        else: result.append(str(i))\n    return result",
    },
    {
        "id": "coding-007",
        "category": "coding",
        "difficulty": "medium",
        "prompt": "Write a Python function `deep_flatten(lst)` that takes a list of arbitrarily nested lists and returns a flat list of all elements (not including the lists themselves).",
        "validation": "python3 -c \"from flatten import deep_flatten; assert deep_flatten([1,[2,[3,4],5],6])==[1,2,3,4,5,6]; assert deep_flatten([])==[]; assert deep_flatten([1,2,3])==[1,2,3]; print('OK')\"",
        "setup": "def deep_flatten(lst): pass",
        "solution": "def deep_flatten(lst):\n    result = []\n    for item in lst:\n        if isinstance(item, list):\n            result.extend(deep_flatten(item))\n        else:\n            result.append(item)\n    return result",
    },
    {
        "id": "coding-008",
        "category": "coding",
        "difficulty": "hard",
        "prompt": "Write a Python function `lru_cache(maxsize)` that returns a decorator implementing a Least Recently Used cache. The cache should store up to maxsize items and evict the least recently used when full.",
        "validation": "python3 -c \"from lru import lru_cache\n@lru_cache(2)\ndef f(x): return x*2\nassert f(1)==2; assert f(2)==4; assert f(1)==2\nassert f(3)==6\nassert f(2)==4\nprint('OK')\"",
        "setup": "def lru_cache(maxsize): pass",
        "solution": "from collections import OrderedDict\ndef lru_cache(maxsize):\n    def decorator(func):\n        cache = OrderedDict()\n        def wrapper(*args):\n            if args in cache:\n                cache.move_to_end(args)\n                return cache[args]\n            result = func(*args)\n            cache[args] = result\n            if len(cache) > maxsize:\n                cache.popitem(last=False)\n            return result\n        return wrapper\n    return decorator",
    },
]

# ===== DEBUGGING TASKS (8 tasks) =====
DEBUGGING = [
    {
        "id": "debug-001",
        "category": "debugging",
        "difficulty": "easy",
        "prompt": "Fix this broken function that should return the sum of a list:\n\n```python\ndef sum_list(lst):\n    total = 0\n    for i in range(len(lst)):\n        total += lst[i]\n    retrun total\n```",
        "validation": "python3 -c \"from fix_sum import sum_list; assert sum_list([1,2,3])==6; assert sum_list([])==0; assert sum_list([-1,0,1])==0; print('OK')\"",
        "setup": "def sum_list(lst):\n    total = 0\n    for i in range(len(lst)):\n        total += lst[i]\n    retrun total",
        "solution": "def sum_list(lst):\n    total = 0\n    for i in range(len(lst)):\n        total += lst[i]\n    return total",
    },
    {
        "id": "debug-002",
        "category": "debugging",
        "difficulty": "easy",
        "prompt": "Fix this broken function that should return the index of a value in a list, or -1 if not found:\n\n```python\ndef find_index(lst, value):\n    for i in range(len(lst)):\n        if lst[i] = value:\n            return i\n    return None\n```",
        "validation": "python3 -c \"from find import find_index; assert find_index([1,2,3],2)==1; assert find_index([1,2,3],4)==-1; assert find_index([],1)==-1; print('OK')\"",
        "setup": "def find_index(lst, value):\n    for i in range(len(lst)):\n        if lst[i] = value:\n            return i\n    return None",
        "solution": "def find_index(lst, value):\n    for i in range(len(lst)):\n        if lst[i] == value:\n            return i\n    return -1",
    },
    {
        "id": "debug-003",
        "category": "debugging",
        "difficulty": "medium",
        "prompt": "Fix this broken function that should sort a list using bubble sort:\n\n```python\ndef bubble_sort(lst):\n    n = len(lst)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if lst[j] > lst[j+1]:\n                lst[j] = lst[j+1]\n                lst[j+1] = lst[j]\n    return lst\n```",
        "validation": "python3 -c \"from bubble import bubble_sort; assert bubble_sort([3,1,2])==[1,2,3]; assert bubble_sort([])==[]; assert bubble_sort([1])==[1]; assert bubble_sort([5,4,3,2,1])==[1,2,3,4,5]; print('OK')\"",
        "setup": "def bubble_sort(lst):\n    n = len(lst)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if lst[j] > lst[j+1]:\n                lst[j] = lst[j+1]\n                lst[j+1] = lst[j]\n    return lst",
        "solution": "def bubble_sort(lst):\n    n = len(lst)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if lst[j] > lst[j+1]:\n                lst[j], lst[j+1] = lst[j+1], lst[j]\n    return lst",
    },
    {
        "id": "debug-004",
        "category": "debugging",
        "difficulty": "medium",
        "prompt": "Fix this broken function that should return a dictionary counting character frequencies (case-insensitive):\n\n```python\ndef char_freq(text):\n    freq = {}\n    for char in text.upper():\n        if char in freq:\n            freq[char] += 1\n        else:\n            freq[char] == 1\n    return freq\n```",
        "validation": "python3 -c \"from freq import char_freq; r=char_freq('Hello'); assert r['H']==1; assert r['E']==1; assert r['L']==2; assert r['O']==1; print('OK')\"",
        "setup": "def char_freq(text):\n    freq = {}\n    for char in text.upper():\n        if char in freq:\n            freq[char] += 1\n        else:\n            freq[char] == 1\n    return freq",
        "solution": "def char_freq(text):\n    freq = {}\n    for char in text.upper():\n        if char in freq:\n            freq[char] += 1\n        else:\n            freq[char] = 1\n    return freq",
    },
    {
        "id": "debug-005",
        "category": "debugging",
        "difficulty": "hard",
        "prompt": "Fix this broken function that should return the longest common prefix of a list of strings:\n\n```python\ndef longest_common_prefix(strs):\n    if not strs:\n        return ''\n    prefix = ''\n    for i in range(min(len(s) for s in strs)):\n        char = strs[0][i]\n        for s in strs:\n            if s[i] != char:\n                return prefix\n        prefix += char\n        return prefix\n```",
        "validation": "python3 -c \"from lcp import longest_common_prefix; assert longest_common_prefix(['flower','flow','flight'])=='fl'; assert longest_common_prefix(['dog','racecar','car'])==''; assert longest_common_prefix([''])==''; print('OK')\"",
        "setup": "def longest_common_prefix(strs):\n    if not strs:\n        return ''\n    prefix = ''\n    for i in range(min(len(s) for s in strs)):\n        char = strs[0][i]\n        for s in strs:\n            if s[i] != char:\n                return prefix\n        prefix += char\n        return prefix",
        "solution": "def longest_common_prefix(strs):\n    if not strs:\n        return ''\n    prefix = ''\n    for i in range(min(len(s) for s in strs)):\n        char = strs[0][i]\n        for s in strs:\n            if s[i] != char:\n                return prefix\n        prefix += char\n    return prefix",
    },
    {
        "id": "debug-006",
        "category": "debugging",
        "difficulty": "easy",
        "prompt": "Fix this broken function that should return True if a number is even:\n\n```python\ndef is_even(n):\n    return n % 2 = 0\n```",
        "validation": "python3 -c \"from even import is_even; assert is_even(2); assert is_even(0); assert not is_even(1); assert not is_even(7); print('OK')\"",
        "setup": "def is_even(n):\n    return n % 2 = 0",
        "solution": "def is_even(n):\n    return n % 2 == 0",
    },
    {
        "id": "debug-007",
        "category": "debugging",
        "difficulty": "medium",
        "prompt": "Fix this broken function that should reverse a string in-place as a list of characters:\n\n```python\ndef reverse_string(s):\n    left, right = 0, len(s)\n    while left < right:\n        s[left], s[right] = s[right], s[left]\n        left += 1\n        right -= 1\n    return s\n```",
        "validation": "python3 -c \"from reverse import reverse_string; assert reverse_string(['h','e','l','l','o'])==['o','l','l','e','h']; assert reverse_string([])==[]; print('OK')\"",
        "setup": "def reverse_string(s):\n    left, right = 0, len(s)\n    while left < right:\n        s[left], s[right] = s[right], s[left]\n        left += 1\n        right -= 1\n    return s",
        "solution": "def reverse_string(s):\n    left, right = 0, len(s)-1\n    while left < right:\n        s[left], s[right] = s[right], s[left]\n        left += 1\n        right -= 1\n    return s",
    },
    {
        "id": "debug-008",
        "category": "debugging",
        "difficulty": "hard",
        "prompt": "Fix this broken function that should return a list of all primes up to n using Sieve of Eratosthenes:\n\n```python\ndef sieve(n):\n    if n < 2:\n        return []\n    primes = [True] * (n+1)\n    primes[0] = primes[1] = False\n    for i in range(2, n):\n        if primes[i]:\n            for j in range(i*i, n, i):\n                primes[j] = False\n    return [i for i in range(n) if primes[i]]\n```",
        "validation": "python3 -c \"from sieve import sieve; assert sieve(10)==[2,3,5,7]; assert sieve(1)==[]; assert sieve(30)==[2,3,5,7,11,13,17,19,23,29]; print('OK')\"",
        "setup": "def sieve(n):\n    if n < 2:\n        return []\n    primes = [True] * (n+1)\n    primes[0] = primes[1] = False\n    for i in range(2, n):\n        if primes[i]:\n            for j in range(i*i, n, i):\n                primes[j] = False\n    return [i for i in range(n) if primes[i]]",
        "solution": "def sieve(n):\n    if n < 2:\n        return []\n    primes = [True] * (n+1)\n    primes[0] = primes[1] = False\n    for i in range(2, int(n**0.5)+1):\n        if primes[i]:\n            for j in range(i*i, n+1, i):\n                primes[j] = False\n    return [i for i in range(n+1) if primes[i]]",
    },
]

# ===== TOOL USE TASKS (6 tasks) =====
TOOL_USE = [
    {
        "id": "tool-001",
        "category": "tool_use",
        "difficulty": "easy",
        "prompt": "Given a directory path, write a Python function `find_largest_file(path)` that returns the full path of the largest file (by size) in that directory. Return None if directory is empty.",
        "validation": "python3 -c \"from largest import find_largest_file; import tempfile, os; d=tempfile.mkdtemp(); open(d+'/a.txt','w').write('hello'); open(d+'/b.txt','w').write('hello world'); r=find_largest_file(d); assert r and 'b.txt' in r; print('OK')\"",
        "setup": "def find_largest_file(path): pass",
        "solution": "import os\ndef find_largest_file(path):\n    if not os.path.isdir(path):\n        return None\n    largest = None\n    largest_size = -1\n    for name in os.listdir(path):\n        full = os.path.join(path, name)\n        if os.path.isfile(full):\n            size = os.path.getsize(full)\n            if size > largest_size:\n                largest = full\n                largest_size = size\n    return largest",
    },
    {
        "id": "tool-002",
        "category": "tool_use",
        "difficulty": "easy",
        "prompt": "Write a Python function `file_stats(path)` that returns a dict with line_count, word_count, char_count for the given text file.",
        "validation": "python3 -c \"from stats import file_stats; import tempfile; d=tempfile.mkdtemp(); open(d+'/test.txt','w').write('hello world\\nfoo bar\\n'); r=file_stats(d+'/test.txt'); assert r['line_count']==2; assert r['word_count']==4; assert r['char_count']>=18; print('OK')\"",
        "setup": "def file_stats(path): pass",
        "solution": "def file_stats(path):\n    with open(path) as f:\n        content = f.read()\n    lines = content.split('\\n')\n    return {\n        'line_count': len(lines) - 1 if content.endswith('\\n') else len(lines),\n        'word_count': len(content.split()),\n        'char_count': len(content),\n    }",
    },
    {
        "id": "tool-003",
        "category": "tool_use",
        "difficulty": "medium",
        "prompt": "Write a Python function `json_to_csv(json_path, csv_path)` that converts a JSON file containing a list of objects to a CSV file. Use the keys of the first object as column headers.",
        "validation": "python3 -c \"from json2csv import json_to_csv; import tempfile, json; d=tempfile.mkdtemp(); json.dump([{'a':1,'b':2},{'a':3,'b':4}], open(d+'/in.json','w')); json_to_csv(d+'/in.json', d+'/out.csv'); print(open(d+'/out.csv').read()); print('OK')\"",
        "setup": "def json_to_csv(json_path, csv_path): pass",
        "solution": "import json, csv\ndef json_to_csv(json_path, csv_path):\n    with open(json_path) as f:\n        data = json.load(f)\n    if not data:\n        return\n    with open(csv_path, 'w', newline='') as f:\n        writer = csv.DictWriter(f, fieldnames=data[0].keys())\n        writer.writeheader()\n        writer.writerows(data)",
    },
    {
        "id": "tool-004",
        "category": "tool_use",
        "difficulty": "medium",
        "prompt": "Write a Python function `list_files_by_extension(directory)` that returns a dict mapping file extensions (like '.py', '.txt') to lists of filenames found in that directory.",
        "validation": "python3 -c \"from ext import list_files_by_extension; import tempfile, os; d=tempfile.mkdtemp(); open(d+'/a.py','w'); open(d+'/b.py','w'); open(d+'/c.txt','w'); r=list_files_by_extension(d); assert '.py' in r and len(r['.py'])==2; print('OK')\"",
        "setup": "def list_files_by_extension(directory): pass",
        "solution": "import os\ndef list_files_by_extension(directory):\n    result = {}\n    for f in os.listdir(directory):\n        path = os.path.join(directory, f)\n        if os.path.isfile(path):\n            _, ext = os.path.splitext(f)\n            result.setdefault(ext, []).append(f)\n    return result",
    },
    {
        "id": "tool-005",
        "category": "tool_use",
        "difficulty": "hard",
        "prompt": "Write a Python function `find_duplicate_files(directory)` that returns a list of lists, where each inner list contains paths of files that have identical content (by MD5 hash).",
        "validation": "python3 -c \"from dupes import find_duplicate_files; import tempfile, os; d=tempfile.mkdtemp(); open(d+'/a.txt','w').write('same'); open(d+'/b.txt','w').write('same'); open(d+'/c.txt','w').write('diff'); r=find_duplicate_files(d); assert any(len(g)>1 and 'a.txt' in str(g) and 'b.txt' in str(g) for g in r); print('OK')\"",
        "setup": "def find_duplicate_files(directory): pass",
        "solution": "import os, hashlib\ndef find_duplicate_files(directory):\n    hashes = {}\n    for root, _, files in os.walk(directory):\n        for f in files:\n            path = os.path.join(root, f)\n            h = hashlib.md5(open(path,'rb').read()).hexdigest()\n            hashes.setdefault(h, []).append(path)\n    return [g for g in hashes.values() if len(g) > 1]",
    },
    {
        "id": "tool-006",
        "category": "tool_use",
        "difficulty": "medium",
        "prompt": "Write a Python function `parse_log_file(log_path)` that reads a log file where each line is format 'LEVEL: message' and returns a dict with counts per level (INFO, WARN, ERROR).",
        "validation": "python3 -c \"from logparse import parse_log_file; import tempfile; d=tempfile.mkdtemp(); open(d+'/log.txt','w').write('INFO: started\\nERROR: failed\\nINFO: retrying\\nWARN: slow\\n'); r=parse_log_file(d+'/log.txt'); assert r['INFO']==2; assert r['ERROR']==1; assert r['WARN']==1; print('OK')\"",
        "setup": "def parse_log_file(log_path): pass",
        "solution": "def parse_log_file(log_path):\n    counts = {}\n    with open(log_path) as f:\n        for line in f:\n            level = line.split(':')[0].strip()\n            counts[level] = counts.get(level, 0) + 1\n    return counts",
    },
]

# ===== STRUCTURED OUTPUT TASKS (8 tasks) =====
STRUCTURED_OUTPUT = [
    {
        "id": "struct-001",
        "category": "structured_output",
        "difficulty": "easy",
        "prompt": "Return a JSON object representing a person with fields: name (string), age (int), email (string). Example: {\"name\": \"Alice\", \"age\": 30, \"email\": \"alice@example.com\"}.",
        "validation": "python3 -c \"import json; d=json.load(open('person.json')); assert isinstance(d['name'], str); assert isinstance(d['age'], int); assert '@' in d['email']; print('OK')\"",
        "solution": '{"name": "Alice", "age": 30, "email": "alice@example.com"}',
    },
    {
        "id": "struct-002",
        "category": "structured_output",
        "difficulty": "easy",
        "prompt": "Return a JSON array of 5 numbers: the first 5 positive odd numbers.",
        "validation": "python3 -c \"import json; d=json.load(open('odds.json')); assert d==[1,3,5,7,9]; print('OK')\"",
        "solution": "[1, 3, 5, 7, 9]",
    },
    {
        "id": "struct-003",
        "category": "structured_output",
        "difficulty": "medium",
        "prompt": "Return valid JSON that conforms to this schema: {\"users\": [{\"id\": int, \"name\": str, \"roles\": [str]}], \"total\": int, \"page\": int}. total should equal the number of users. Make at least 2 users.",
        "validation": "python3 -c \"import json; d=json.load(open('users.json')); assert isinstance(d['users'], list); assert len(d['users'])>=2; assert d['total']==len(d['users']); assert all(isinstance(u['id'], int) for u in d['users']); print('OK')\"",
        "solution": '{"users": [{"id": 1, "name": "Alice", "roles": ["admin"]}, {"id": 2, "name": "Bob", "roles": ["user"]}], "total": 2, "page": 1}',
    },
    {
        "id": "struct-004",
        "category": "structured_output",
        "difficulty": "medium",
        "prompt": "Return a JSON object representing a binary tree node with fields: value (int), left (object or null), right (object or null). Create a tree with root value 5, left child value 3, right child value 7.",
        "validation": "python3 -c \"import json; d=json.load(open('tree.json')); assert d['value']==5; assert d['left']['value']==3; assert d['right']['value']==7; print('OK')\"",
        "solution": '{"value": 5, "left": {"value": 3, "left": null, "right": null}, "right": {"value": 7, "left": null, "right": null}}',
    },
    {
        "id": "struct-005",
        "category": "structured_output",
        "difficulty": "easy",
        "prompt": "Return a JSON object representing a configuration object with fields: host (str), port (int), debug (bool), allowed_origins (list of strings).",
        "validation": "python3 -c \"import json; d=json.load(open('config.json')); assert isinstance(d['host'], str); assert isinstance(d['port'], int); assert isinstance(d['debug'], bool); assert isinstance(d['allowed_origins'], list); print('OK')\"",
        "solution": '{"host": "localhost", "port": 8080, "debug": true, "allowed_origins": ["http://localhost:3000"]}',
    },
    {
        "id": "struct-006",
        "category": "structured_output",
        "difficulty": "hard",
        "prompt": "Return a JSON object representing a directed graph with nodes labeled A, B, C, D. Include edges as a list of {source, target} objects. There should be at least 4 edges. All nodes must have at least one edge.",
        "validation": "python3 -c \"import json; d=json.load(open('graph.json')); assert len(d['edges'])>=4; nodes=set(); [nodes.add(e['source']) for e in d['edges']]; [nodes.add(e['target']) for e in d['edges']]; assert len(nodes)>=4; print('OK')\"",
        "solution": '{"nodes": ["A","B","C","D"], "edges": [{"source":"A","target":"B"},{"source":"B","target":"C"},{"source":"C","target":"D"},{"source":"D","target":"A"},{"source":"A","target":"C"}]}',
    },
    {
        "id": "struct-007",
        "category": "structured_output",
        "difficulty": "medium",
        "prompt": "Return a JSON object that represents a todo list with fields: title (str), items (array of {id: int, text: str, done: bool, priority: int}). Include at least 3 items with different priority levels.",
        "validation": "python3 -c \"import json; d=json.load(open('todo.json')); assert len(d['items'])>=3; assert all(isinstance(i['done'], bool) for i in d['items']); assert all(isinstance(i['priority'], int) for i in d['items']); print('OK')\"",
        "solution": '{"title": "My Tasks", "items": [{"id": 1, "text": "Buy milk", "done": false, "priority": 2}, {"id": 2, "text": "Write report", "done": true, "priority": 1}, {"id": 3, "text": "Call dentist", "done": false, "priority": 3}]}',
    },
    {
        "id": "struct-008",
        "category": "structured_output",
        "difficulty": "hard",
        "prompt": "Return a JSON object representing a menu with nested categories. The structure should be: {\"menu\": [{\"category\": str, \"items\": [{\"name\": str, \"price\": float, \"ingredients\": [str]}]}]}. Include at least 2 categories with 2 items each.",
        "validation": "python3 -c \"import json; d=json.load(open('menu.json')); assert len(d['menu'])>=2\nfor cat in d['menu']: assert len(cat['items'])>=2\nfor cat in d['menu']:\n for i in cat['items']: assert isinstance(i['price'], float)\nprint('OK')\"",
        "solution": '{"menu": [{"category": "Drinks", "items": [{"name": "Coffee", "price": 3.5, "ingredients": ["coffee", "water"]}, {"name": "Tea", "price": 2.5, "ingredients": ["tea", "water"]}]}, {"category": "Food", "items": [{"name": "Sandwich", "price": 7.0, "ingredients": ["bread", "cheese", "lettuce"]}, {"name": "Soup", "price": 5.0, "ingredients": ["tomato", "cream"]}]}]}',
    },
]

# ===== ASSEMBLE =====
ALL_TASKS = CODING + DEBUGGING + TOOL_USE + STRUCTURED_OUTPUT

# Split: 10 dev, 20 held-out
DEV_TASKS = ALL_TASKS[:10]
HELD_OUT_TASKS = ALL_TASKS[10:]

def get_task_by_id(task_id):
    for t in ALL_TASKS:
        if t["id"] == task_id:
            return t
    return None

def get_suite(name="heldout-v1"):
    if name == "heldout-v1":
        return HELD_OUT_TASKS
    elif name == "dev-v1":
        return DEV_TASKS
    elif name == "all":
        return ALL_TASKS
    return ALL_TASKS
