#!/usr/bin/env python3
"""Cyralyx Interface Lab — refine the model↔tool interface layer.

Component refinement loop:
  PROPOSED → BUILT → TECHNICALLY_VERIFIED → INTERFACE_TESTING → REFINEMENT
  → BENCHMARK_WINNER → PROMOTED | REJECTED | RETIRED
"""
import json, os, datetime, re

ROOT = "/opt/data/repos/cyralyx-evolution/experiments/refinement"
os.makedirs(f"{ROOT}/lineage", exist_ok=True)

COMPONENT_STATES = [
    "PROPOSED", "BUILT", "TECHNICALLY_VERIFIED", "INTERFACE_TESTING",
    "REFINEMENT", "BENCHMARK_WINNER", "PROMOTED", "REJECTED", "RETIRED",
]

REFINEMENT_TYPES = [
    "DESCRIPTION", "SCHEMA", "INTERFACE", "OUTPUT_COMPRESSION",
    "ERROR_FEEDBACK", "ROUTING", "IMPLEMENTATION_PATCH", "SPECIALIZE",
    "MERGE", "SPLIT",
]


def root_cause(unit_tests_ok, invocation_ok, selected_ok, executed_ok, state_ok, token_delta):
    """Automatic root-cause classification with confidence."""
    if not unit_tests_ok:
        return {"layer": "IMPLEMENTATION", "confidence": "HIGH",
                "reason": "unit tests fail — code bug"}
    if not selected_ok:
        return {"layer": "DESCRIPTION_OR_ROUTING", "confidence": "HIGH",
                "reason": "model never selected the tool"}
    if not invocation_ok:
        return {"layer": "INTERFACE", "confidence": "HIGH",
                "reason": "tool selected but invocation malformed"}
    if not executed_ok:
        return {"layer": "IMPLEMENTATION_OR_ARGUMENT", "confidence": "MEDIUM",
                "reason": "invocation valid but execution failed"}
    if not state_ok:
        return {"layer": "MODEL_ARGUMENT", "confidence": "MEDIUM",
                "reason": "executed but wrong state — arguments likely wrong"}
    if token_delta and token_delta > 0.3:
        return {"layer": "CONTEXT_SKILL_COST", "confidence": "MEDIUM",
                "reason": "same success but token cost much higher"}
    return {"layer": "MODEL_LIMIT", "confidence": "LOW",
            "reason": "all harness variants fail similarly"}


class RefinementTracker:
    """Records component lifecycle + funnel metrics."""

    def __init__(self):
        self.path = f"{ROOT}/lineage/components.json"
        self.components = {}
        if os.path.exists(self.path):
            with open(self.path) as f: self.components = json.load(f)

    def create(self, cid, parent, version, mutation, hypothesis):
        self.components[cid] = {
            "cid": cid, "parent": parent, "version": version,
            "mutation": mutation, "hypothesis": hypothesis,
            "state": "PROPOSED", "funnel": {},
            "ts": datetime.datetime.now(datetime.UTC).isoformat(),
        }
        self._save()

    def set_funnel(self, cid, funnel):
        if cid in self.components:
            self.components[cid]["funnel"] = funnel
            self._save()

    def set_state(self, cid, state):
        if cid in self.components:
            self.components[cid]["state"] = state
            self._save()

    def record_child(self, cid, child):
        if cid in self.components:
            self.components[cid].setdefault("children", []).append(child)
            self._save()

    def _save(self):
        with open(self.path, "w") as f: json.dump(self.components, f, indent=2)

    def status(self, cid=None):
        if cid:
            return self.components.get(cid)
        return self.components


class FunnelMetrics:
    """Interface funnel: tasks → selected → valid → executed → verified."""

    def __init__(self):
        self.tasks = 0; self.selected = 0; self.valid = 0
        self.executed = 0; self.verified = 0; self.cost = 0.0

    def record(self, selected, valid, executed, verified, cost):
        self.tasks += 1
        self.selected += 1 if selected else 0
        self.valid += 1 if valid else 0
        self.executed += 1 if executed else 0
        self.verified += 1 if verified else 0
        self.cost += cost

    def to_dict(self):
        return {"tasks": self.tasks, "selected": self.selected,
                "valid": self.valid, "executed": self.executed,
                "verified": self.verified, "cost": round(self.cost, 6)}


# ===== Interface variants (reusable patterns) =====
class InterfaceVariant:
    """Generate model system prompts per interface pattern."""
    PATTERNS = ["DIRECT_TOOL_CALL", "FEW_SHOT", "TRIGGER_DESCRIPTION",
                "SEMANTIC_MENU", "HYBRID_NORMALIZER", "TWO_STAGE_SELECTION"]

    @staticmethod
    def build(pattern, tool_name="git-ops", domain="git"):
        if pattern == "FEW_SHOT":
            return ("You are an automation agent.\nTo perform git operations output EXACTLY one line:\n"
                    "GITOPS <op> <repo> [--file f --content c --message m --name n]\n"
                    "Examples:\n"
                    "  GITOPS init_commit /tmp/repo --file a.txt --content hello --message init\n"
                    "  GITOPS branch /tmp/repo --name dev\n"
                    "  GITOPS tag /tmp/repo --name v1.0 --message release\n"
                    "  GITOPS status /tmp/repo\n"
                    "Supported ops: init, init_commit, branch, tag, switch, status, clean, commit\n"
                    "Output ONLY the GITOPS line. For questions output ONLY the value.")
        if pattern == "TRIGGER_DESCRIPTION":
            return ("You are an automation agent. Use git-ops for deterministic Git state changes "
                    "such as init, branch, switch, commit and tag inside an allowed repository. "
                    "Do NOT emit raw Git commands when git-ops can perform the operation.\n"
                    "Output format: GITOPS <op> <repo> [--key value]\n"
                    "Output ONLY the GITOPS line.")
        if pattern == "SEMANTIC_MENU":
            return ("You are an automation agent with a fixed git action menu.\n"
                    "Choose ONE action + arguments:\n"
                    "  STATUS <repo>\n"
                    "  INIT <repo>\n"
                    "  INIT_COMMIT <repo> FILE=<f> CONTENT=<c> MSG=<m>\n"
                    "  CREATE_BRANCH <repo> NAME=<n>\n"
                    "  SWITCH_BRANCH <repo> NAME=<n>\n"
                    "  CREATE_TAG <repo> NAME=<n> MSG=<m>\n"
                    "  COMMIT <repo> MSG=<m>\n"
                    "  CLEAN <repo>\n"
                    "Output ONLY one menu line.")
        if pattern == "HYBRID_NORMALIZER":
            return ("You are an automation agent. Output standard git commands using ONLY:\n"
                    "  git init | git config user.email/name | git add . | git commit -m \"...\" | "
                    "git branch <name> | git checkout -b <name> | git switch <name> | "
                    "git tag <name> | git status | git clean -fd\n"
                    "Use absolute paths with `git -C <repo>`.\n"
                    "No shell chaining (&&, |), no redirection, no substitution.\n"
                    "Output ONLY the git command.")
        if pattern == "DIRECT_TOOL_CALL":
            return ("You are an automation agent.\nFor any task that creates/modifies files or git state, "
                    "output ONLY the exact bash command to do it.\nFor pure questions, output ONLY the value.\n"
                    "Commands must use absolute paths and be runnable with `sh -c`.")
        return ""


class GitNormalizer:
    """Restricted hybrid parser: safe git grammar → semantic action."""
    # safe patterns: git -C <repo> <cmd> ...
    GRAMMAR = [
        (r"git\s+-C\s+(\S+)\s+init(?:\s+-q)?", lambda m, kw: ("init", m.group(1), {})),
        (r"git\s+-C\s+(\S+)\s+config\s+user\.email\s+(\S+)", None),
        (r"git\s+-C\s+(\S+)\s+config\s+user\.name\s+(\S+)", None),
        (r"git\s+-C\s+(\S+)\s+add\s+\.", None),
        (r"git\s+-C\s+(\S+)\s+commit\s+-[qm]+\s+[\"']?([^\"']+)[\"']?", lambda m, kw: ("commit", m.group(1), {"message": m.group(2)})),
        (r"git\s+-C\s+(\S+)\s+branch\s+(\S+)", lambda m, kw: ("branch", m.group(1), {"name": m.group(2)})),
        (r"git\s+-C\s+(\S+)\s+switch\s+(\S+)", lambda m, kw: ("switch", m.group(1), {"name": m.group(2)})),
        (r"git\s+-C\s+(\S+)\s+checkout\s+-b\s+(\S+)", lambda m, kw: ("branch", m.group(1), {"name": m.group(2)})),
        (r"git\s+-C\s+(\S+)\s+tag\s+(\S+)", lambda m, kw: ("tag", m.group(1), {"name": m.group(2)})),
        (r"git\s+-C\s+(\S+)\s+status(?:\s+--porcelain)?", lambda m, kw: ("status", m.group(1), {})),
        (r"git\s+-C\s+(\S+)\s+clean\s+-f[d]?", lambda m, kw: ("clean", m.group(1), {})),
    ]
    UNSAFE = ["&&", "||", "|", ">", "<", "$(", "`", "rm -rf", "push", "fetch", "clone", "remote"]

    @staticmethod
    def parse(text):
        if any(u in text for u in GitNormalizer.UNSAFE):
            return {"valid": False, "reason": "unsafe pattern"}
        for pattern, handler in GitNormalizer.GRAMMAR:
            m = re.search(pattern, text)
            if m and handler:
                return {"valid": True, "action": handler(m, {})}
        return {"valid": False, "reason": "no matching safe grammar"}


if __name__ == "__main__":
    # Unit self-test of normalizer
    tests = [
        ("git -C /tmp/r init -q", True),
        ("git -C /tmp/r commit -m \"first\"", True),
        ("git -C /tmp/r branch dev", True),
        ("git -C /tmp/r push origin main", False),
        ("git -C /tmp/r status && rm -rf /", False),
        ("echo hi > /tmp/x", False),
    ]
    ok = 0
    for text, expect in tests:
        r = GitNormalizer.parse(text)
        passed = (r["valid"] == expect)
        ok += passed
        print(f"  {'✅' if passed else '❌'} {text!r} → valid={r['valid']} expected={expect}")
    print(f"\n  Normalizer self-test: {ok}/{len(tests)}")

    print(f"\n  Interface Lab ready. Variants: {InterfaceVariant.PATTERNS}")
