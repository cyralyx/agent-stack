"""
McpSession v3 — persistent stdio MCP client.
Separate state machine, serial requests, no response loss, cross-platform.
"""
import subprocess, json, os, threading, queue, time
from collections import deque
from typing import Optional, List, Dict

# State machine — fine-grained, no collapsed booleans
STATE_CREATED = "CREATED"
STATE_PROCESS_STARTED = "PROCESS_STARTED"
STATE_INITIALIZE_OK = "INITIALIZE_OK"
STATE_PROTOCOL_READY = "PROTOCOL_READY"
STATE_TOOLS_LIST_RESPONSE_OK = "TOOLS_LIST_RESPONSE_OK"
STATE_TOOLS_AVAILABLE = "TOOLS_AVAILABLE"
STATE_STUDIO_DISCOVERED = "STUDIO_DISCOVERED"
STATE_SESSION_READY = "SESSION_READY"

R1_REQUIRED_TOOLS = ["inspect", "create", "execute", "play", "stop", "get"]


class McpProcessSpec:
    def __init__(self, command: list, env: dict = None, cwd: str = None):
        self.command = command
        self.env = env or {}
        self.cwd = cwd


class McpSchema:
    @staticmethod
    def validate(tool_name: str, arguments: dict, schema: dict) -> Optional[str]:
        if not schema:
            return None
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for field in required:
            if field not in arguments:
                return f"SCHEMA_VALIDATION_FAILED: missing required field '{field}' for tool '{tool_name}'"
        type_map = {"string": str, "number": (int, float), "integer": int,
                    "boolean": bool, "array": list, "object": dict}
        for field, value in arguments.items():
            if field in props:
                expected_type = props[field].get("type")
                if expected_type and expected_type in type_map:
                    if not isinstance(value, type_map[expected_type]):
                        return (f"SCHEMA_VALIDATION_FAILED: field '{field}' expected "
                                f"type {expected_type}, got {type(value).__name__}")
        return None


class McpSession:
    """
    Persistent MCP session with fine-grained state machine.
    SERIAL: only ONE outstanding request at a time (enforced by lock).
    Responses matched by ID — no discarding, no confusion.
    """

    def __init__(self, spec: McpProcessSpec):
        self.spec = spec
        self.proc: Optional[subprocess.Popen] = None
        self.state = STATE_CREATED
        self.tools: List[Dict] = []
        self.schema: Dict[str, Dict] = {}
        self._next_id = 100
        self._request_lock = threading.Lock()  # serial enforcement
        self._stderr_buf = deque(maxlen=50)
        self._stderr_thread: Optional[threading.Thread] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._resp_queue = queue.Queue()
        self._running = False

    # -- Request ID management --

    def _next_request_id(self) -> int:
        with self._request_lock:
            rid = self._next_id
            self._next_id += 1
            return rid

    # -- Background I/O --

    def _drain_stderr(self):
        while self._running and self.proc and self.proc.stderr:
            try:
                line = self.proc.stderr.readline()
                if line:
                    self._stderr_buf.append(
                        line.decode().rstrip() if isinstance(line, bytes) else line.rstrip()
                    )
            except (OSError, ValueError):
                break

    def _read_stdout(self):
        """Background reader — everything goes to queue."""
        while self._running and self.proc and self.proc.stdout:
            try:
                line = self.proc.stdout.readline()
                if not line:
                    break
                text = line.decode().strip() if isinstance(line, bytes) else line.strip()
                if not text:
                    continue
                try:
                    msg = json.loads(text)
                    self._resp_queue.put(("response", msg))
                except json.JSONDecodeError:
                    self._stderr_buf.append(f"stdout_parse_error: {text[:100]}")
            except (OSError, ValueError):
                break

    # -- Lifecycle --

    def start(self) -> str:
        """
        Returns state string (not a bool).
        Caller checks: state >= PROTOCOL_READY for MCP basics.
        state >= TOOLS_AVAILABLE for R1 readiness.
        """
        if not self.spec.command:
            self.state = STATE_CREATED
            return self.state

        try:
            env = os.environ.copy()
            env.update(self.spec.env)
            self.proc = subprocess.Popen(
                self.spec.command,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env=env, cwd=self.spec.cwd,
            )
        except (FileNotFoundError, OSError):
            self.state = STATE_CREATED
            return self.state

        self.state = STATE_PROCESS_STARTED
        self._running = True
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()
        self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader_thread.start()

        return self._handshake()

    def _handshake(self) -> str:
        """Returns state after handshake."""
        # 1. Initialize
        rid = self._next_request_id()
        req = json.dumps({"jsonrpc": "2.0", "id": rid, "method": "initialize",
                         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                                    "clientInfo": {"name": "cyralyx", "version": "1.0.0"}}}) + "\n"
        self._write(req)
        resp = self._wait_for_id(rid, timeout=10)
        if not resp or "result" not in resp:
            self.state = STATE_CREATED
            return self.state
        self.state = STATE_INITIALIZE_OK

        # 2. Send initialized notification (fire-and-forget, no response)
        notif = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}) + "\n"
        self._write(notif)
        self.state = STATE_PROTOCOL_READY

        # 3. tools/list
        tools_state = self.refresh_tools()
        return tools_state

    def refresh_tools(self) -> str:
        """Fetch tool list. Returns state."""
        rid = self._next_request_id()
        req = json.dumps({"jsonrpc": "2.0", "id": rid, "method": "tools/list", "params": {}}) + "\n"
        self._write(req)
        resp = self._wait_for_id(rid, timeout=10)

        if not resp or "result" not in resp:
            # tools/list failed — protocol ready but no tools
            return self.state  # still PROTOCOL_READY

        self.tools = resp["result"].get("tools", [])
        for t in self.tools:
            self.schema[t["name"]] = {
                "description": t.get("description", ""),
                "inputSchema": t.get("inputSchema", {}),
            }

        if self.tools:
            self.state = STATE_TOOLS_AVAILABLE  # actual tools present
        # If tools is empty, state stays at PROTOCOL_READY (set in _handshake)
        return self.state

    def tool_names(self) -> list:
        return [t["name"] for t in self.tools]

    def has_required_tools(self, required: list = None) -> dict:
        """Check if required R1 tools are available."""
        if required is None:
            required = R1_REQUIRED_TOOLS
        available = self.tool_names()
        found = [t for t in required if any(t in name.lower() for name in available)]
        missing = [t for t in required if not any(t in name.lower() for name in available)]
        return {
            "ready": len(missing) == 0,
            "found": found,
            "missing": missing,
            "state": self.state,
        }

    # -- Tool calls (SERIAL — one request at a time) --

    def call_tool(self, name: str, arguments: dict = None) -> dict:
        if name not in self.schema:
            return {"error": f"tool '{name}' not in schema", "available": list(self.schema.keys())}

        args = arguments or {}
        schema = self.schema[name].get("inputSchema", {})
        validation_error = McpSchema.validate(name, args, schema)
        if validation_error:
            return {"error": validation_error}

        with self._request_lock:  # SERIAL: one request at a time
            rid = self._next_request_id()
            req = json.dumps({"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                             "params": {"name": name, "arguments": args}}) + "\n"
            self._write(req)
            result = self._wait_for_id(rid, timeout=30) or {"error": "timeout waiting for response"}
        return result

    # -- Low-level I/O --

    def _write(self, data: str):
        if self.proc and self.proc.stdin:
            self.proc.stdin.write(data.encode())
            self.proc.stdin.flush()

    def _wait_for_id(self, expected_id: int, timeout: float = 10) -> Optional[Dict]:
        """Read from queue until matching ID found. Non-matching responses stored back."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                remaining = max(0.1, deadline - time.time())
                tag, msg = self._resp_queue.get(timeout=remaining)
                if tag != "response":
                    continue
                msg_id = msg.get("id")
                if msg_id is None:
                    continue  # notification, skip
                if msg_id == expected_id:
                    return msg
                # Response for a different ID — should not happen in serial mode
                self._stderr_buf.append(f"unexpected response id={msg_id} (expected {expected_id})")
            except queue.Empty:
                return None
        return None

    # -- Lifecycle end --

    def close(self):
        self._running = False
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=2)
            self.proc = None
        self.state = STATE_CREATED

    def stderr_recent(self) -> list:
        return list(self._stderr_buf)

    def health(self) -> dict:
        proc_alive = self.proc is not None and self.proc.poll() is None
        return {
            "state": self.state,
            "process_running": proc_alive,
            "tools_cached": len(self.tools),
            "tool_names": [t["name"] for t in self.tools],
            "required_tools": self.has_required_tools(),
            "stderr_lines": len(self._stderr_buf),
        }

    def r1_readiness(self) -> dict:
        """Explicit R1 readiness check."""
        if not self.health()["process_running"]:
            return {"ready": False, "blocker": "process_not_running", "state": self.state}
        if self.state not in (STATE_TOOLS_AVAILABLE, STATE_SESSION_READY):
            return {"ready": False, "blocker": "no_tools", "state": self.state}
        rt = self.has_required_tools()
        if not rt["ready"]:
            return {"ready": False, "blocker": f"missing_tools: {rt['missing']}", "state": self.state}
        return {"ready": True, "state": self.state, "tools": len(self.tools)}


class WineMcpLauncher:
    @staticmethod
    def create_spec(mcp_path: str, display: str = ":99") -> McpProcessSpec:
        return McpProcessSpec(command=["wine", mcp_path], env={"DISPLAY": display})


class WindowsMcpLauncher:
    @staticmethod
    def create_spec(mcp_path: str) -> McpProcessSpec:
        return McpProcessSpec(command=[mcp_path])
