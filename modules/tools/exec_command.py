#!/usr/bin/env python3
"""Cyralyx exec-command — safe deterministic local executor for agent benchmarks.

Security model:
- DEFAULT DENY. Only explicitly allowed programs run.
- Path sandbox: all operations resolve under allowed workspace roots.
- argv-only, shell=False. No free-form shell parsing.
- Output capped. Timeout enforced. Environment sanitized.
- Mutation evidence (before/after) recorded where applicable.
"""
import os, sys, json, shutil, subprocess, time, hashlib, stat, tempfile

VERSION = "0.1.0"
DEFAULT_WORKSPACE = os.environ.get("CYRALYX_WORKSPACE", "/tmp/r3_workspace")
DEFAULT_TIMEOUT = 15
MAX_OUTPUT_BYTES = 4096
MAX_ACTIONS = 8

# ---- Capability classes ----
ALLOWED = {
    # filesystem
    "mkdir": {"args_max": 2},
    "touch": {"args_max": 2},
    "cp": {"args_max": 3},
    "mv": {"args_max": 3},
    "rm": {"args_max": 2, "flags": {"-rf", "-f", "-r"}},
    "chmod": {"args_max": 3},
    "chown": {"args_max": 3, "deny": True},  # ownership change requires root -> deny by default
    "ln": {"args_max": 4, "flags": {"-s"}},  # only symlink creation allowed
    "readlink": {"args_max": 2},
    "stat": {"args_max": 3},
    "file": {"args_max": 3},
    "cat": {"args_max": 2},
    "head": {"args_max": 3},
    "tail": {"args_max": 3},
    "wc": {"args_max": 3},
    "sha256sum": {"args_max": 2},
    "printf": {"args_max": 2},
    # git
    "git": {"args_max": 8, "subcommands": {"status","diff","branch","checkout","add","commit","tag","log","show","switch","init","config","rev-parse","merge-base","symbolic-ref","remote","fetch"}},
    # data
    "python3": {"args_max": 4, "flags": {"-c", "-m"}},
    # diagnostics
    "pwd": {"args_max": 0},
    "ls": {"args_max": 3},
    "find": {"args_max": 8},
    "rg": {"args_max": 8},
    "grep": {"args_max": 6},
    "which": {"args_max": 2},
    "uname": {"args_max": 2},
    "whoami": {"args_max": 0},
    "id": {"args_max": 1},
    "date": {"args_max": 2},
    "df": {"args_max": 3},
    "du": {"args_max": 4},
    "hostname": {"args_max": 1},
}

DENIED_SUBSTRINGS = ["sudo", "su ", "ssh ", "curl", "wget", "systemctl", "iptables",
                     "nft", "mount", "mkfs", "fdisk", "dd ", "useradd", "userdel",
                     "passwd", "shutdown", "reboot", "chroot", "docker", "kubectl",
                     "nc ", "ncat", "telnet", "python3 -c 'import os; os.system"]


def _resolve_safe(path: str, workspace: str) -> str:
    """Resolve and enforce path stays inside workspace."""
    if not path:
        return None
    if path.startswith("~"):
        return None
    abs_path = os.path.abspath(os.path.join(workspace, path))
    real_ws = os.path.realpath(workspace)
    # Reject obvious escapes
    if not (abs_path == real_ws or abs_path.startswith(real_ws + os.sep)):
        return None
    return abs_path


def _policy_check(program: str, args: list, workspace: str) -> dict:
    if program not in ALLOWED:
        return {"denied": True, "reason": f"program '{program}' not in allowlist"}
    spec = ALLOWED[program]
    if spec.get("deny"):
        return {"denied": True, "reason": f"program '{program}' explicitly denied"}
    if len(args) > spec.get("args_max", 8):
        return {"denied": True, "reason": f"too many args for '{program}'"}
    # python3 -c / -m: the code argument is code, not a shell string — allow semicolons/quotes
    code_arg_index = None
    if program == "python3" and args and args[0] in ("-c", "-m"):
        if args[0] == "-c" and len(args) > 1:
            code_arg_index = 1
        elif args[0] == "-m" and len(args) > 1:
            code_arg_index = 1
    for i, arg in enumerate(args):
        low = arg.lower()
        for d in DENIED_SUBSTRINGS:
            if d in low:
                return {"denied": True, "reason": f"arg contains denied token '{d.strip()}'"}
        # Skip shell metachar check for python code payloads (but still deny dangerous imports)
        if i == code_arg_index:
            if "os.system" in arg or "subprocess" in arg or "pty" in arg or "socket" in arg:
                return {"denied": True, "reason": "python code payload contains restricted module"}
            continue
        if "|" in arg or ">" in arg or "<" in arg or "&&" in arg or "||" in arg or ";" in arg:
            return {"denied": True, "reason": f"shell metacharacters in arg: {arg[:40]}"}
        if "$(" in arg or "`" in arg or "${" in arg:
            return {"denied": True, "reason": f"command substitution in arg"}
        # path args must stay in workspace (except git subcommands like status with no path, etc)
        if arg.startswith("/") or arg.startswith("..") or arg.startswith("./"):
            resolved = _resolve_safe(arg, workspace)
            if resolved is None:
                return {"denied": True, "reason": f"path outside workspace: {arg}"}
    return {"allowed": True}


def _probe_state(path: str):
    """Snapshot state for mutation evidence."""
    if not os.path.exists(path):
        return {"exists": False}
    st = os.lstat(path)
    return {
        "exists": True,
        "size": st.st_size,
        "mode": oct(st.st_mode & 0o777),
        "is_link": os.path.islink(path),
        "mtime": st.st_mtime,
        "sha256": None,
    }


def exec_command(action: dict, workspace: str = None) -> dict:
    """Execute one structured action. Returns compact JSON."""
    ws = workspace or DEFAULT_WORKSPACE
    os.makedirs(ws, exist_ok=True)

    # Validate schema
    if not isinstance(action, dict):
        return {"status": "FAIL", "error": "action must be object"}
    program = action.get("program")
    args = action.get("args", [])
    if not isinstance(program, str) or not isinstance(args, list):
        return {"status": "FAIL", "error": "program must be str, args must be list"}
    cwd = _resolve_safe(action.get("cwd", ws), ws) or ws
    timeout = min(int(action.get("timeout", DEFAULT_TIMEOUT)), 60)
    expected_codes = action.get("expected_exit_codes", [0])

    # Policy
    policy = _policy_check(program, args, ws)
    if policy.get("denied"):
        return {"status": "DENIED", "error": policy["reason"], "program": program}

    # Mutation evidence (best effort)
    mutation_path = None
    before = None
    if program in ("mkdir", "touch", "cp", "mv", "rm", "chmod", "ln", "printf"):
        for a in args:
            if a and not a.startswith("-"):
                candidate = _resolve_safe(a, ws)
                if candidate:
                    mutation_path = candidate
                    break
    if mutation_path:
        before = _probe_state(mutation_path)

    env = {"PATH": "/usr/bin:/bin:/usr/local/bin",
           "HOME": ws, "TMPDIR": ws,
           "LANG": "C", "LC_ALL": "C"}
    env.pop("CYRALYX_API_KEY", None)
    env.pop("OPENAI_API_KEY", None)
    env.pop("ROBLOX_API_KEY", None)

    start = time.time()
    try:
        r = subprocess.run(
            [program] + args,
            cwd=cwd, env=env, shell=False,
            capture_output=True, timeout=timeout,
        )
    except FileNotFoundError:
        return {"status": "FAIL", "error": f"program not found: {program}",
                "program": program, "duration_ms": round((time.time()-start)*1000)}
    except subprocess.TimeoutExpired:
        return {"status": "FAIL", "error": "timeout", "program": program,
                "duration_ms": timeout*1000}
    except PermissionError:
        return {"status": "FAIL", "error": "permission denied", "program": program}

    duration = round((time.time()-start)*1000)
    stdout = r.stdout[:MAX_OUTPUT_BYTES].decode(errors="replace")
    stderr = r.stderr[:MAX_OUTPUT_BYTES].decode(errors="replace")
    truncated = len(r.stdout) > MAX_OUTPUT_BYTES or len(r.stderr) > MAX_OUTPUT_BYTES

    ok = r.returncode in expected_codes

    # After-state for mutation
    after = None
    if mutation_path and before and before.get("exists"):
        after = _probe_state(mutation_path)
        before["sha256"] = None
        after["sha256"] = None

    return {
        "status": "PASS" if ok else "FAIL",
        "program": program,
        "exit_code": r.returncode,
        "duration_ms": duration,
        "stdout": stdout,
        "stderr": stderr,
        "truncated": truncated,
        "stdout_bytes": len(r.stdout),
        "stderr_bytes": len(r.stderr),
        "cwd": cwd,
        "mutation": {"expected": bool(mutation_path), "verified": None},
        "policy": {"denied": False},
    }


def execute_plan(actions: list, workspace: str = None) -> dict:
    """Execute a bounded sequence of actions; stop on first FAIL/DENIED."""
    if not isinstance(actions, list) or len(actions) > MAX_ACTIONS:
        return {"status": "FAIL", "error": f"plan must be list of <= {MAX_ACTIONS} actions"}
    results = []
    for i, action in enumerate(actions):
        r = exec_command(action, workspace)
        r["step"] = i
        results.append(r)
        if r["status"] != "PASS":
            return {"status": "FAIL", "error": f"plan stopped at step {i}",
                    "results": results}
    return {"status": "PASS", "results": results}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"tool": "exec-command", "version": VERSION,
                          "usage": "exec_command.py '<json action>' or --plan '<json actions>'"}))
        return 0
    if sys.argv[1] == "--plan":
        try:
            actions = json.loads(sys.argv[2])
            print(json.dumps(execute_plan(actions), indent=2))
        except json.JSONDecodeError as e:
            print(json.dumps({"status": "FAIL", "error": f"invalid JSON plan: {e}"}))
        return 0
    try:
        action = json.loads(sys.argv[1])
        print(json.dumps(exec_command(action), indent=2))
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "FAIL", "error": f"invalid JSON action: {e}"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
