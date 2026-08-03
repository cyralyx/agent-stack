#!/usr/bin/env python3
"""Obsidian Vault MCP server — expose the shared brain as an API for agents.

Read + write + search only. NO delete, NO arbitrary path escape. This is the
"single-brain tag system" and "Obsidian as full API" wish made real: both
Hermes and OpenClaw read/write the same vault consistently.

Endpoints exposed as MCP tools:
  vault_list(path)      list notes in a vault subpath
  vault_read(path)      read a note
  vault_write(path, content, append)  write or append (no delete)
  vault_search(query)   search note contents (ripgrep)
  vault_tree()          top-level layout

Runs as a stdio MCP server (hermes mcp add vault -- "python vault_mcp.py").
"""
import json
import os
import re
import subprocess
import sys

VAULT = os.environ.get(
    "STACK_VAULT",
    r"C:\Users\willi\Documents\Obsidian Vault",
)


def _safe(path: str) -> str:
    """Resolve a vault-relative path, forbidding escapes."""
    if not path:
        return VAULT
    # strip leading slashes / .. escapes
    cleaned = path.replace("\\", "/").lstrip("/")
    parts = [p for p in cleaned.split("/") if p not in ("", ".", "..")]
    target = os.path.normpath(os.path.join(VAULT, *parts))
    if not target.startswith(VAULT):
        raise ValueError("path escapes vault")
    return target


def vault_list(path: str = "") -> dict:
    root = _safe(path)
    out = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith((".md", ".txt")):
                rel = os.path.relpath(os.path.join(dirpath, f), VAULT)
                out.append(rel.replace("\\", "/"))
    return {"count": len(out), "notes": out[:300]}


def vault_read(path: str) -> dict:
    target = _safe(path)
    if not os.path.isfile(target):
        return {"error": f"not found: {path}", "content": ""}
    with open(target, encoding="utf-8") as fh:
        return {"path": path, "content": fh.read()[:20000]}


def vault_write(path: str, content: str, append: bool = False) -> dict:
    target = _safe(path)
    os.makedirs(os.path.dirname(target) or VAULT, exist_ok=True)
    mode = "a" if append else "w"
    with open(target, mode, encoding="utf-8") as fh:
        fh.write(content)
    return {"ok": True, "path": path, "append": append}


def vault_search(query: str, path: str = "") -> dict:
    root = _safe(path)
    try:
        r = subprocess.run(
            ["rg", "-l", "--no-ignore", query, root],
            capture_output=True, text=True, timeout=20,
        )
        files = [ln.strip().replace("\\", "/") for ln in r.stdout.splitlines() if ln.strip()]
        return {"query": query, "count": len(files), "files": files[:100]}
    except FileNotFoundError:
        return {"query": query, "error": "rg not installed", "files": []}


def vault_tree() -> dict:
    return {"vault": VAULT, "top": sorted(os.listdir(VAULT))}


HANDLERS = {
    "vault_list": vault_list,
    "vault_read": vault_read,
    "vault_write": vault_write,
    "vault_search": vault_search,
    "vault_tree": vault_tree,
}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = msg.get("method", "")
        if method == "initialize":
            resp = {"jsonrpc": "2.0", "id": msg.get("id"), "result": {"capabilities": {"tools": {}}, "serverInfo": {"name": "vault-mcp", "version": "1.0.0"}}}
        elif method == "tools/list":
            tools = [
                {"name": "vault_list", "description": "List notes in a vault subpath", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}},
                {"name": "vault_read", "description": "Read a vault note", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
                {"name": "vault_write", "description": "Write or append a vault note (no delete)", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}, "append": {"type": "boolean"}}, "required": ["path", "content"]}},
                {"name": "vault_search", "description": "Search vault note contents", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "path": {"type": "string"}}, "required": ["query"]}},
                {"name": "vault_tree", "description": "Top-level vault layout", "inputSchema": {"type": "object"}},
            ]
            resp = {"jsonrpc": "2.0", "id": msg.get("id"), "result": {"tools": tools}}
        elif method == "tools/call":
            params = msg.get("params", {})
            name = params.get("name", "")
            args = params.get("arguments", {})
            handler = HANDLERS.get(name)
            if not handler:
                resp = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32601, "message": f"unknown tool: {name}"}}
            else:
                try:
                    result = handler(**args)
                    resp = {"jsonrpc": "2.0", "id": msg.get("id"), "result": {"content": [{"type": "text", "text": json.dumps(result)}]}}
                except Exception as exc:
                    resp = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32000, "message": str(exc)}}
        else:
            resp = {"jsonrpc": "2.0", "id": msg.get("id"), "result": {}}
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
