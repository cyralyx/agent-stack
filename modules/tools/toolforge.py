#!/usr/bin/env python3
"""
Cyralyx ToolForge v0.2 — curated deterministic tool layer for Hermes.
All tools output compact structured JSON.
"""
import sys, json, subprocess, os, shutil, time, platform

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_DEGRADED = "DEGRADED"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_NA = "NOT_APPLICABLE"


def run_argv(argv: list, timeout: int = 15) -> dict:
    """Execute via argv. No shell interpretation. Returns structured result."""
    start = time.time()
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return {
            "exit": r.returncode,
            "stdout": r.stdout[:5000],
            "stderr": r.stderr[:2000],
            "duration_ms": round((time.time() - start) * 1000),
            "argv": argv,
        }
    except subprocess.TimeoutExpired:
        return {"exit": -1, "error": "timeout", "duration_ms": timeout * 1000, "argv": argv}
    except FileNotFoundError:
        return {"exit": -1, "error": f"command not found: {argv[0]}", "argv": argv}
    except PermissionError:
        return {"exit": -1, "error": f"permission denied: {argv[0]}", "argv": argv}


def run_shell(command: str, timeout: int = 15) -> dict:
    """Execute via shell. Only for cases where argv is genuinely impractical."""
    start = time.time()
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return {
            "exit": r.returncode,
            "stdout": r.stdout[:5000],
            "stderr": r.stderr[:2000],
            "duration_ms": round((time.time() - start) * 1000),
            "shell": command[:200],
        }
    except subprocess.TimeoutExpired:
        return {"exit": -1, "error": "timeout", "duration_ms": timeout * 1000}
    except OSError as e:
        return {"exit": -1, "error": str(e)[:200]}


def read_proc_file(path: str) -> str:
    """Safely read a /proc file. Returns empty string on failure."""
    try:
        with open(path) as f:
            return f.read()
    except (FileNotFoundError, PermissionError, OSError):
        return ""


def cmd_doctor_host() -> int:
    """cyralyx doctor host — comprehensive server health with probe results."""
    result = {
        "tool": "doctor host",
        "probes": {},
    }

    # CPU probe
    cpuinfo = read_proc_file("/proc/cpuinfo")
    if cpuinfo:
        cores = cpuinfo.count("processor\t:")
        result["probes"]["cpu"] = {"status": STATUS_PASS, "evidence": f"{cores} cores", "cores": cores}
    else:
        result["probes"]["cpu"] = {"status": STATUS_UNKNOWN, "evidence": "unable to read /proc/cpuinfo"}

    # RAM probe
    meminfo = read_proc_file("/proc/meminfo")
    if meminfo:
        for line in meminfo.split("\n"):
            if line.startswith("MemTotal:"):
                kb = int(line.split()[1])
                gb = round(kb / 1024 / 1024, 1)
                result["probes"]["ram"] = {"status": STATUS_PASS, "evidence": f"{gb} GB", "ram_gb": gb}
                break
    else:
        result["probes"]["ram"] = {"status": STATUS_UNKNOWN, "evidence": "unable to read /proc/meminfo"}

    # GPU probe
    gpu = run_argv(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,utilization.gpu",
                     "--format=csv,noheader"])
    if gpu["exit"] == 0:
        parts = [p.strip() for p in gpu["stdout"].split(",")]
        result["probes"]["gpu"] = {
            "status": STATUS_PASS,
            "evidence": f"{parts[0]} driver={parts[1]} vram={parts[2]} util={parts[3]}",
            "model": parts[0] if len(parts) > 0 else "?",
            "driver": parts[1] if len(parts) > 1 else "?",
        }
    else:
        result["probes"]["gpu"] = {"status": STATUS_FAIL, "evidence": "nvidia-smi failed"}

    # OS probe
    result["probes"]["os"] = {
        "status": STATUS_PASS,
        "evidence": f"{platform.system()} {platform.release()}",
        "host": platform.node(),
    }

    # Uptime probe
    uptime = run_argv(["uptime", "-p"])
    if uptime["exit"] == 0:
        result["probes"]["uptime"] = {"status": STATUS_PASS, "evidence": uptime["stdout"].strip()}

    # Overall status derived from probes
    fails = [k for k, v in result["probes"].items() if v.get("status") == STATUS_FAIL]
    result["status"] = STATUS_DEGRADED if fails else STATUS_PASS
    if fails:
        result["failures"] = fails

    print(json.dumps(result, indent=2))
    return 0


def cmd_doctor_port(port_str: str) -> int:
    """cyralyx doctor port <n> — diagnose port/service."""
    import socket
    result = {"tool": "doctor port", "probes": {}}
    try:
        port = int(port_str)
    except ValueError:
        result["status"] = STATUS_FAIL
        result["error"] = f"invalid port: {port_str}"
        print(json.dumps(result))
        return 1

    # Listening check via socket connect
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect(("127.0.0.1", port))
        result["probes"]["listening"] = {"status": STATUS_PASS, "evidence": f"127.0.0.1:{port} is open"}
        s.close()
    except (socket.timeout, ConnectionRefusedError, OSError):
        result["probes"]["listening"] = {"status": STATUS_FAIL, "evidence": f"127.0.0.1:{port} not reachable"}

    # Process info via ss (argv, not shell)
    ss = run_argv(["ss", "-antp"], timeout=5)
    if ss["exit"] == 0:
        for line in ss["stdout"].split("\n"):
            if f":{port}" in line:
                result["probes"]["process"] = {"status": STATUS_PASS, "evidence": line.strip()[:200]}
                break
        if "process" not in result["probes"]:
            result["probes"]["process"] = {"status": STATUS_FAIL, "evidence": "no process found on port"}

    # Docker container check
    docker_ps = run_argv(["docker", "ps", "--format", "{{.Names}} {{.Ports}}"])
    if docker_ps["exit"] == 0:
        for line in docker_ps["stdout"].split("\n"):
            if f":{port}" in line or f":{port_str}" in line:
                result["probes"]["container"] = {"status": STATUS_PASS, "evidence": line.strip(), "port": port}
                break

    result["status"] = STATUS_PASS if any(p.get("status") == STATUS_PASS for p in result["probes"].values()) else STATUS_FAIL
    result["port"] = port
    print(json.dumps(result, indent=2))
    return 0


def cmd_doctor_docker(name: str = "") -> int:
    """cyralyx doctor docker [name] — container diagnostics."""
    result = {"tool": "doctor docker", "probes": {}}

    if name:
        inspect = run_argv(["docker", "inspect", name])
        if inspect["exit"] == 0:
            try:
                data = json.loads(inspect["stdout"])[0]
                state = data.get("State", {})
                result["probes"]["state"] = {
                    "status": STATUS_PASS if state.get("Status") == "running" else STATUS_DEGRADED,
                    "evidence": state.get("Status", "?"),
                    "name": data.get("Name", "").lstrip("/"),
                }
                result["probes"]["health"] = {
                    "status": STATUS_PASS if state.get("Health", {}).get("Status", "none") in ("healthy", "none") else STATUS_DEGRADED,
                    "evidence": state.get("Health", {}).get("Status", "no health check"),
                }
            except (json.JSONDecodeError, IndexError, KeyError) as e:
                result["probes"]["inspect"] = {"status": STATUS_FAIL, "evidence": str(e)[:200]}
        else:
            result["probes"]["container"] = {"status": STATUS_FAIL, "evidence": f"container '{name}' not found"}
    else:
        ps = run_argv(["docker", "ps", "--format", "{{.Names}}|{{.Status}}|{{.Image}}"])
        if ps["exit"] == 0:
            containers = []
            for line in ps["stdout"].strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("|", 2)
                containers.append({"name": parts[0], "status": parts[1] if len(parts) > 1 else "?", "image": parts[2] if len(parts) > 2 else "?"})
            result["probes"]["containers"] = {
                "status": STATUS_PASS,
                "evidence": f"{len(containers)} container(s)",
                "list": containers,
            }
        else:
            result["probes"]["docker"] = {"status": STATUS_FAIL, "evidence": "docker ps failed"}

    result["status"] = STATUS_PASS if any(p.get("status") == STATUS_PASS for p in result["probes"].values()) else STATUS_FAIL
    print(json.dumps(result, indent=2))
    return 0


def cmd_doctor_repo(path: str = ".") -> int:
    """cyralyx doctor repo [path] — git repository analysis."""
    result = {"tool": "doctor repo", "probes": {}}

    abs_path = os.path.abspath(path)
    git_dir = os.path.join(abs_path, ".git")

    if not os.path.isdir(git_dir):
        result["probes"]["git"] = {"status": STATUS_FAIL, "evidence": "not a git repository"}
    else:
        # SHA
        sha = run_argv(["git", "-C", abs_path, "rev-parse", "--short", "HEAD"])
        result["probes"]["sha"] = {"status": STATUS_PASS, "evidence": sha.get("stdout", "?").strip()} if sha["exit"] == 0 else {"status": STATUS_FAIL, "evidence": sha.get("error", "?")}

        # Branch
        branch = run_argv(["git", "-C", abs_path, "rev-parse", "--abbrev-ref", "HEAD"])
        if branch["exit"] == 0:
            result["probes"]["branch"] = {"status": STATUS_PASS, "evidence": branch["stdout"].strip()}

        # Dirty
        dirty = run_argv(["git", "-C", abs_path, "status", "--short"])
        if dirty["exit"] == 0:
            count = len([l for l in dirty["stdout"].split("\n") if l.strip()])
            result["probes"]["dirty"] = {"status": STATUS_PASS if count == 0 else STATUS_DEGRADED, "evidence": f"{count} dirty file(s)"}

        # Tracked files
        files = run_argv(["git", "-C", abs_path, "ls-files"])
        if files["exit"] == 0:
            count = len([l for l in files["stdout"].split("\n") if l.strip()])
            result["probes"]["tracked"] = {"status": STATUS_PASS, "evidence": f"{count} files"}

    # Language counts via os.walk (not shell)
    py_count = json_count = yaml_count = 0
    try:
        for root, dirs, fnames in os.walk(abs_path):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "node_modules", ".git")]
            for f in fnames:
                if f.endswith(".py"): py_count += 1
                elif f.endswith(".json"): json_count += 1
                elif f.endswith((".yaml", ".yml")): yaml_count += 1
    except PermissionError:
        pass
    result["probes"]["languages"] = {
        "status": STATUS_PASS,
        "evidence": f"{py_count} python, {json_count} json, {yaml_count} yaml",
    }

    result["status"] = STATUS_PASS if any(p.get("status") == STATUS_PASS for p in result["probes"].values()) else STATUS_FAIL
    result["path"] = abs_path
    print(json.dumps(result, indent=2))
    return 0


def cmd_doctor_dependency(tool_name: str) -> int:
    """cyralyx doctor dependency <tool> — check tool availability."""
    result = {"tool": "doctor dependency", "probes": {}}

    path = shutil.which(tool_name)
    if path:
        result["probes"]["installed"] = {"status": STATUS_PASS, "evidence": path}
        v = run_argv([tool_name, "--version"])
        if v["exit"] == 0:
            result["probes"]["version"] = {"status": STATUS_PASS, "evidence": v["stdout"].strip().split("\n")[0]}
        result["status"] = STATUS_PASS
    else:
        result["probes"]["installed"] = {"status": STATUS_FAIL, "evidence": f"'{tool_name}' not found in PATH"}
        result["status"] = STATUS_FAIL

    print(json.dumps(result, indent=2))
    return 0


def cmd_doctor_tools() -> int:
    """cyralyx doctor tools — inventory all known tools with probes."""
    tools_to_check = ["rg", "jq", "yq", "gh", "uv", "hyperfine", "python3", "node", "docker", "git", "curl", "openssl"]
    result = {"tool": "doctor tools", "probes": {}}

    for t in tools_to_check:
        path = shutil.which(t)
        probe = {"status": STATUS_PASS if path else STATUS_FAIL, "evidence": path or "not found"}
        if path:
            v = run_argv([t, "--version"])
            if v["exit"] == 0:
                probe["version"] = v["stdout"].strip().split("\n")[0]
        result["probes"][t] = probe

    result["status"] = STATUS_PASS if any(p.get("status") == STATUS_PASS for p in result["probes"].values()) else STATUS_FAIL
    print(json.dumps(result, indent=2))
    return 0


def cmd_doctor_benchmark(command_str: str) -> int:
    """cyralyx doctor benchmark <command> — benchmark using hyperfine."""
    result = {"tool": "doctor benchmark", "command": command_str, "probes": {}}

    if shutil.which("hyperfine"):
        bm = run_argv(["hyperfine", "--warmup", "2", "--runs", "5",
                        command_str, "--export-json", "/dev/stdout"], timeout=60)
        if bm["exit"] == 0:
            try:
                data = json.loads(bm["stdout"])
                r = data.get("results", [{}])[0]
                result["probes"]["hyperfine"] = {
                    "status": STATUS_PASS,
                    "evidence": f"mean={round(r.get('mean',0)*1000,1)}ms min={round(r.get('min',0)*1000,1)}ms max={round(r.get('max',0)*1000,1)}ms",
                    "mean_ms": round(r.get("mean", 0) * 1000, 1),
                    "min_ms": round(r.get("min", 0) * 1000, 1),
                    "max_ms": round(r.get("max", 0) * 1000, 1),
                    "stddev_ms": round(r.get("stddev", 0) * 1000, 2),
                }
            except (json.JSONDecodeError, IndexError, KeyError) as e:
                result["probes"]["hyperfine"] = {"status": STATUS_FAIL, "evidence": f"parse error: {str(e)[:100]}"}
        else:
            result["probes"]["hyperfine"] = {"status": STATUS_FAIL, "evidence": bm.get("stderr", "?")[:200]}
    else:
        # Fallback: Python timing
        times = []
        for _ in range(3):
            start = time.time()
            r = subprocess.run(command_str, shell=True, capture_output=True, timeout=30)
            times.append((time.time() - start) * 1000)
        mean = sum(times) / len(times)
        result["probes"]["fallback"] = {
            "status": STATUS_DEGRADED,
            "evidence": f"mean={round(mean,1)}ms (no hyperfine)",
            "mean_ms": round(mean, 1),
        }

    result["status"] = STATUS_PASS if any(p.get("status") == STATUS_PASS for p in result["probes"].values()) else STATUS_DEGRADED
    print(json.dumps(result, indent=2))
    return 0


def cmd_resolve_docs(tool_name: str) -> int:
    """cyralyx resolve-docs <tool> — version-aware documentation resolver."""
    result = {"tool": "resolve-docs", "probes": {}}

    # Detect tool and version
    path = shutil.which(tool_name)
    if not path:
        result["probes"]["tool"] = {"status": STATUS_FAIL, "evidence": f"'{tool_name}' not found"}
        result["status"] = STATUS_FAIL
        print(json.dumps(result, indent=2))
        return 0

    result["probes"]["tool"] = {"status": STATUS_PASS, "evidence": path}

    # Detect version
    v = run_argv([tool_name, "--version"])
    version = v["stdout"].strip().split("\n")[0] if v["exit"] == 0 else "?"
    result["probes"]["version"] = {"status": STATUS_PASS, "evidence": version}

    # Known doc sources with version-aware URLs
    known_docs = {
        "rg": {"project": "ripgrep", "base": "https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md"},
        "jq": {"project": "jq", "base": "https://jqlang.github.io/jq/manual/"},
        "yq": {"project": "yq", "base": "https://mikefarah.gitbook.io/yq/"},
        "gh": {"project": "gh", "base": "https://cli.github.com/manual/"},
        "uv": {"project": "uv", "base": "https://docs.astral.sh/uv/"},
        "docker": {"project": "docker", "base": "https://docs.docker.com/reference/"},  # Changed from hardcoded path
        "python3": {"project": "python", "base": "https://docs.python.org/3/"},
        "git": {"project": "git", "base": f"https://git-scm.com/docs/git/{version}" if "2." in version else "https://git-scm.com/docs"},
    }

    if tool_name in known_docs:
        info = known_docs[tool_name]
        result["probes"]["docs"] = {"status": STATUS_PASS, "evidence": info["base"], "url": info["base"]}
    else:
        # Try local help
        help_out = run_argv([tool_name, "--help"])
        if help_out["exit"] == 0 and help_out["stdout"]:
            result["probes"]["help"] = {"status": STATUS_PASS, "evidence": "local --help available"}
        else:
            result["probes"]["docs"] = {"status": STATUS_FAIL, "evidence": f"no known documentation for '{tool_name}'"}

    result["status"] = STATUS_PASS if any(p.get("status") == STATUS_PASS for p in result["probes"].values()) else STATUS_FAIL
    print(json.dumps(result, indent=2))
    return 0


def cmd_command_repair(command_str: str) -> int:
    """cyralyx command-repair <cmd> — diagnose broken command syntax."""
    result = {"tool": "command-repair", "probes": {}}

    # Parse: is it argv or shell?
    parts = command_str.split()
    if not parts:
        result["status"] = STATUS_FAIL
        result["error"] = "empty command"
        print(json.dumps(result))
        return 1

    tool = parts[0]
    path = shutil.which(tool)

    if not path:
        suggestions = {
            "jq": "sudo apt install jq",
            "yq": "sudo apt install yq",
            "rg": "sudo apt install ripgrep",
            "gh": "install from https://cli.github.com/",
            "hyperfine": "download from https://github.com/sharkdp/hyperfine/releases",
        }
        suggestion = suggestions.get(tool, f"install via: sudo apt install {tool}")
        result["probes"]["installed"] = {"status": STATUS_FAIL, "evidence": f"'{tool}' not found"}
        result["repair"] = {"candidate": suggestion, "confidence": "high", "retryable": True}
        result["status"] = STATUS_FAIL
        print(json.dumps(result, indent=2))
        return 0

    # Tool exists. Try --version
    v = run_argv([tool, "--version"])
    if v["exit"] == 0:
        result["probes"]["version"] = {"status": STATUS_PASS, "evidence": v["stdout"].strip().split("\n")[0]}
        result["status"] = STATUS_PASS
    else:
        result["probes"]["version"] = {"status": STATUS_DEGRADED, "evidence": v.get("stderr", "?")[:100]}
        result["repair"] = {"candidate": f"{tool} --help", "confidence": "medium", "retryable": False}
        result["status"] = STATUS_DEGRADED

    print(json.dumps(result, indent=2))
    return 0


def cmd_repo_map(path: str = ".") -> int:
    """cyralyx repo-map [path] — repository structure map (agent context compression)."""
    abs_path = os.path.abspath(path)
    result = {"tool": "repo-map", "path": abs_path, "probes": {}}

    # Directories at top 2 levels
    dirs = []
    py_files = []
    configs = []
    try:
        for root, dirnames, fnames in os.walk(abs_path):
            depth = root.replace(abs_path, "").count(os.sep)
            if depth > 2:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("__pycache__", "node_modules")]
            if depth > 0:
                dirs.append(os.path.relpath(root, abs_path))
            for f in fnames:
                rel = os.path.relpath(os.path.join(root, f), abs_path)
                if f.endswith(".py"):
                    py_files.append(rel)
                if f in ("pyproject.toml", "setup.py", "package.json", "Cargo.toml", "Makefile", "go.mod"):
                    configs.append(rel)
    except PermissionError:
        result["probes"]["walk"] = {"status": STATUS_DEGRADED, "evidence": "permission denied reading some paths"}

    result["probes"]["directories"] = {"status": STATUS_PASS, "evidence": f"{len(dirs)} directories", "list": dirs[:20]}
    result["probes"]["python_files"] = {"status": STATUS_PASS, "evidence": f"{len(py_files)} python files", "count": len(py_files)}
    result["probes"]["configs"] = {"status": STATUS_PASS if configs else STATUS_DEGRADED, "evidence": configs or "none found"}
    result["status"] = STATUS_PASS
    print(json.dumps(result, indent=2))
    return 0


# Dispatch
COMMANDS = {
    "doctor host": cmd_doctor_host,
    "doctor port": cmd_doctor_port,
    "doctor docker": cmd_doctor_docker,
    "doctor repo": cmd_doctor_repo,
    "doctor dependency": cmd_doctor_dependency,
    "doctor tools": cmd_doctor_tools,
    "doctor benchmark": cmd_doctor_benchmark,
    "resolve-docs": cmd_resolve_docs,
    "command-repair": cmd_command_repair,
    "repo-map": cmd_repo_map,
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmds = "\n".join(f"  {k}" for k in sorted(COMMANDS.keys()))
        print(f"Cyralyx ToolForge v0.2. Commands:\n{cmds}")
        sys.exit(0)

    # Build lookup key
    key = " ".join(sys.argv[1:3]) if len(sys.argv) > 2 and f"{sys.argv[1]} {sys.argv[2]}" in COMMANDS else sys.argv[1]

    if key in COMMANDS:
        remaining = len(key.split())
        args = sys.argv[1 + remaining:]
        sys.exit(COMMANDS[key](*args))
    else:
        print(json.dumps({"status": STATUS_FAIL, "error": f"unknown command: {sys.argv[1]}", "available": list(COMMANDS.keys())}))
        sys.exit(1)
