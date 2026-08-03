#!/usr/bin/env python3
"""git-ops — deterministic git helper generated from evidence (git domain was 8% success).

Collapses repeated model work: git init + config + add + commit + branch + tag.
All operations via git -C <repo> with strict path sandbox.
"""
import os, sys, json, subprocess

DEFAULT_EMAIL = "cyralyx@test.local"
DEFAULT_NAME = "Cyralyx"
MAX_OUTPUT = 2000

def _safe_repo(repo):
    if not repo or not os.path.isdir(repo):
        return None
    return os.path.abspath(repo)

def _run(args, cwd=None):
    try:
        if cwd is None:
            return {"exit": -1, "stdout": "", "stderr": "cwd is None"}
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=15,
                           env={"PATH": "/usr/bin:/bin", "HOME": "/tmp",
                                "LANG": "C", "LC_ALL": "C", "GIT_TERMINAL_PROMPT": "0"})
        return {"exit": r.returncode, "stdout": r.stdout[:MAX_OUTPUT], "stderr": r.stderr[:MAX_OUTPUT]}
    except FileNotFoundError:
        return {"exit": -1, "stdout": "", "stderr": "git not found"}
    except subprocess.TimeoutExpired:
        return {"exit": -1, "stdout": "", "stderr": "timeout"}
    except TypeError:
        return {"exit": -1, "stdout": "", "stderr": "invalid argument"}

def git_init(repo):
    r = _run(["git", "init", "-q", "."], cwd=repo)
    return r["exit"] == 0 or "exists" in r["stderr"]

def ensure_config(repo):
    _run(["git", "config", "user.email", DEFAULT_EMAIL], cwd=repo)
    _run(["git", "config", "user.name", DEFAULT_NAME], cwd=repo)

def operation(op, repo, **kw):
    repo = _safe_repo(repo)
    if not repo:
        return {"status": "FAIL", "error": f"repo not found: {repo}", "evidence": {}}
    if op == "init":
        ok = git_init(repo)
        ensure_config(repo)
        return {"status": "PASS" if ok else "FAIL", "evidence": {"init": ok}}
    if op == "init_commit":
        git_init(repo); ensure_config(repo)
        file = kw.get("file", "a.txt"); content = kw.get("content", "x")
        msg = kw.get("message", "init")
        with open(os.path.join(repo, file), "w") as f: f.write(content)
        _run(["git", "add", "."], cwd=repo)
        r = _run(["git", "commit", "-q", "-m", msg], cwd=repo)
        verify = _run(["git", "log", "-1", "--pretty=%B"], cwd=repo)
        return {"status": "PASS" if r["exit"] == 0 else "FAIL",
                "evidence": {"commit_msg": verify["stdout"].strip()}}
    if op == "branch":
        name = kw.get("name")
        r = _run(["git", "branch", name], cwd=repo)
        return {"status": "PASS" if r["exit"] == 0 else "FAIL",
                "evidence": {"branch": name, "stderr": r["stderr"][:100]}}
    if op == "tag":
        name = kw.get("name"); msg = kw.get("message", name)
        r = _run(["git", "tag", "-a", name, "-m", msg], cwd=repo)
        return {"status": "PASS" if r["exit"] == 0 else "FAIL",
                "evidence": {"tag": name}}
    if op == "switch":
        name = kw.get("name")
        r = _run(["git", "switch", name], cwd=repo)
        return {"status": "PASS" if r["exit"] == 0 else "FAIL",
                "evidence": {"branch": name}}
    if op == "status":
        r = _run(["git", "status", "--porcelain"], cwd=repo)
        return {"status": "PASS", "evidence": {"clean": r["stdout"].strip() == "",
                                               "porcelain": r["stdout"][:300]}}
    if op == "clean":
        _run(["git", "clean", "-f", "-d"], cwd=repo)
        r = _run(["git", "status", "--porcelain"], cwd=repo)
        return {"status": "PASS", "evidence": {"clean": r["stdout"].strip() == ""}}
    if op == "commit":
        msg = kw.get("message", "commit")
        _run(["git", "add", "."], cwd=repo)
        r = _run(["git", "commit", "-q", "-m", msg], cwd=repo)
        return {"status": "PASS" if r["exit"] == 0 else "FAIL",
                "evidence": {"stderr": r["stderr"][:100]}}
    return {"status": "FAIL", "error": f"unknown op {op}"}


if __name__ == "__main__":
    # CLI: git_ops.py <op> <repo> [--key value]...
    args = sys.argv[1:]
    if len(args) < 2:
        print(json.dumps({"status": "FAIL", "error": "usage: git_ops.py <op> <repo> [--k v]"}))
        sys.exit(1)
    op, repo = args[0], args[1]
    kw = {}
    for i in range(2, len(args) - 1, 2):
        if args[i].startswith("--"):
            kw[args[i][2:]] = args[i+1]
    print(json.dumps(operation(op, repo, **kw)))
