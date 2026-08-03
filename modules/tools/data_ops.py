#!/usr/bin/env python3
"""data-ops v2 — deterministic structured-data specialist.

Safe JSON/YAML/config operations inside a workspace root.
Semantic actions only; no shell, no raw Python execution.
Quoting-aware: values are structured Python objects, not shell text.
"""
import os, sys, json, tempfile, shutil

try:
    import yaml
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False


class DataOps:
    def __init__(self, workspace):
        self.workspace = os.path.realpath(workspace)
        if not os.path.isdir(self.workspace):
            os.makedirs(self.workspace, exist_ok=True)

    # ---- path safety ----
    def _safe_path(self, rel):
        """Resolve path under workspace; reject traversal and symlink escape."""
        if not rel or rel.startswith("/") or ".." in rel.split(os.sep):
            return None
        p = os.path.realpath(os.path.join(self.workspace, rel))
        if not p.startswith(self.workspace + os.sep) and p != self.workspace:
            return None
        return p

    # ---- read/write helpers ----
    def _read(self, path):
        with open(path) as f:
            return f.read()

    def _write_atomic(self, path, content):
        """Write temp file + validate + atomic replace; rollback on failure."""
        d = os.path.dirname(path) or "."
        os.makedirs(d, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            f.write(content)
        os.replace(tmp, path)

    def _load(self, path, fmt):
        try:
            if fmt == "json":
                return json.loads(self._read(path))
            if fmt == "yaml":
                if not HAVE_YAML:
                    return {"status": "FAIL", "error": "yaml not available"}
                return yaml.safe_load(self._read(path))
        except Exception as e:
            return {"status": "FAIL", "error": f"{fmt.upper()}_PARSE: {e}"}
        return {"status": "FAIL", "error": "unknown format"}

    def _dump(self, data, fmt):
        if fmt == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        if fmt == "yaml":
            if not HAVE_YAML:
                return None
            return yaml.safe_dump(data, default_flow_style=False, sort_keys=False)
        return None

    def _split_key(self, key):
        """Split 'a.b[2].c' into path parts handling bracket array indexes."""
        parts = []
        for seg in key.split("."):
            while "[" in seg:
                head, _, rest = seg.partition("[")
                if head:
                    parts.append(head)
                idx, _, rest = rest.partition("]")
                if idx:
                    parts.append(idx)
                seg = rest
            if seg:
                parts.append(seg)
        return parts

    # ---- key navigation ----
    def _get_key(self, data, key):
        """key = 'a.b.c' or 'list.0' — nested access. Returns (found, value)."""
        if not key or key == ".":
            return True, data
        for p in self._split_key(key):
            if isinstance(data, dict) and p in data:
                data = data[p]
            elif isinstance(data, list) and p.isdigit() and int(p) < len(data):
                data = data[int(p)]
            else:
                return False, None
        return True, data

    def _set_key(self, data, key, value):
        if not key or key == ".":
            return data, True
        parts = self._split_key(key)
        cur = data
        for p in parts[:-1]:
            if isinstance(cur, dict) and p not in cur:
                cur[p] = {}
            if isinstance(cur, dict):
                cur = cur[p]
            elif isinstance(cur, list) and p.isdigit():
                idx = int(p)
                while len(cur) <= idx:
                    cur.append({})
                cur = cur[idx]
            else:
                return data, False
        last = parts[-1]
        if isinstance(cur, dict):
            cur[last] = value
            return data, True
        elif isinstance(cur, list) and last.isdigit():
            idx = int(last)
            while len(cur) <= idx:
                cur.append(None)
            cur[idx] = value
            return data, True
        return data, False

    def _del_key(self, data, key):
        if not key or key == ".":
            return data, False
        parts = self._split_key(key)
        cur = data
        for p in parts[:-1]:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            elif isinstance(cur, list) and p.isdigit() and int(p) < len(cur):
                cur = cur[int(p)]
            else:
                return data, False
        last = parts[-1]
        if isinstance(cur, dict) and last in cur:
            del cur[last]
            return data, True
        if isinstance(cur, list) and last.isdigit() and int(last) < len(cur):
            cur.pop(int(last))
            return data, True
        return data, False

    # ---- value coercion with type preservation ----
    @staticmethod
    def coerce(value):
        """Convert string tokens to typed values when clearly indicated."""
        if isinstance(value, (dict, list, bool, int, float)) or value is None:
            return value
        s = str(value)
        if s == "true": return True
        if s == "false": return False
        if s == "null" or s == "None": return None
        try:
            return int(s)
        except ValueError:
            pass
        try:
            return float(s)
        except ValueError:
            pass
        return s

    # ---- operations ----
    def operate(self, op, rel_path, key=None, value=None, fmt=None):
        path = self._safe_path(rel_path)
        if not path:
            return {"status": "DENIED", "error": "path outside workspace or traversal", "path": rel_path}
        if fmt is None:
            fmt = "yaml" if rel_path.endswith((".yaml", ".yml")) else "json"

        if op == "CREATE":
            if os.path.exists(path):
                # Repair semantics: allow overwrite only if existing file is invalid
                data = self._load(path, fmt)
                if not (isinstance(data, dict) and data.get("status") == "FAIL"):
                    return {"status": "FAIL", "error": "file exists and is valid"}
            content = str(value) if value is not None else ("{}" if fmt == "json" else "")
            if fmt == "json":
                try:
                    json.loads(content)
                except Exception as e:
                    return {"status": "FAIL", "error": f"invalid json content: {e}"}
            self._write_atomic(path, content)
            return {"status": "PASS", "operation": op, "path": rel_path, "changed": True, "verified": True}

        if op == "VALIDATE":
            if not os.path.exists(path):
                return {"status": "FAIL", "error": "file missing"}
            data = self._load(path, fmt)
            if isinstance(data, dict) and data.get("status") == "FAIL":
                return {"status": "FAIL", "error": data["error"]}
            return {"status": "PASS", "operation": op, "path": rel_path, "valid": True}

        if op == "GET":
            if not os.path.exists(path):
                return {"status": "FAIL", "error": "file missing"}
            data = self._load(path, fmt)
            if isinstance(data, dict) and data.get("status") == "FAIL":
                return {"status": "FAIL", "error": data["error"]}
            found, val = self._get_key(data, key or ".")
            if not found:
                return {"status": "FAIL", "error": f"key not found: {key}"}
            return {"status": "PASS", "operation": op, "path": rel_path,
                    "key": key, "value": val, "changed": False, "verified": True}

        if op in ("SET", "DELETE"):
            if not os.path.exists(path):
                return {"status": "FAIL", "error": "file missing"}
            before = self._read(path)
            data = self._load(path, fmt)
            if isinstance(data, dict) and data.get("status") == "FAIL":
                return {"status": "FAIL", "error": data["error"]}
            if op == "SET":
                data, ok = self._set_key(data, key, DataOps.coerce(value))
            else:
                data, ok = self._del_key(data, key)
            if not ok:
                return {"status": "FAIL", "error": f"cannot apply {op} at {key}"}
            out = self._dump(data, fmt)
            if out is None:
                return {"status": "FAIL", "error": f"{fmt.upper()}_DUMP failed"}
            # rollback if dump invalid
            try:
                if fmt == "json":
                    json.loads(out)
                elif HAVE_YAML:
                    yaml.safe_load(out)
            except Exception as e:
                return {"status": "FAIL", "error": f"rollback: output invalid ({e})"}
            self._write_atomic(path, out)
            # verify: reparse + confirm semantic state
            data2 = self._load(path, fmt)
            if isinstance(data2, dict) and data2.get("status") == "FAIL":
                return {"status": "FAIL", "error": data2["error"]}
            _, val = self._get_key(data2, key)
            return {"status": "PASS", "operation": op, "path": rel_path,
                    "key": key, "value": val, "changed": before != out,
                    "verified": True}

        return {"status": "FAIL", "error": f"unknown operation: {op}"}


if __name__ == "__main__":
    # CLI: data_ops.py <op> <path> [--key k --value v]
    args = sys.argv[1:]
    if len(args) < 2:
        print(json.dumps({"status": "FAIL", "error": "usage: data_ops.py <op> <path> [--key k --value v] [--fmt json|yaml]"}))
        sys.exit(1)
    op, rel = args[0], args[1]
    kw = {"key": None, "value": None, "fmt": None}
    for i in range(2, len(args) - 1, 2):
        if args[i].startswith("--"):
            k = args[i][2:]
            if k in kw:
                kw[k] = args[i+1]
    ws = os.environ.get("DATAOPS_WS", "/tmp/dataops")
    d = DataOps(ws)
    print(json.dumps(d.operate(op, rel, key=kw["key"], value=kw["value"], fmt=kw["fmt"])))
