#!/usr/bin/env python3
"""Cyralyx Skill + Tool Creation Engine — turns evidence into capabilities.

Core loop:
  OBSERVE → CLUSTER → REPEATED PATTERN → SKILL or TOOL → BUILD → TEST → PROMOTE/REJECT
"""
import json, os, re, datetime, hashlib
from collections import defaultdict, Counter

ROOT = "/opt/data/repos/cyralyx-evolution/experiments/creation"
os.makedirs(f"{ROOT}/fitness", exist_ok=True)
os.makedirs(f"{ROOT}/rejected", exist_ok=True)


def classify_problem(failure_cluster: str) -> str:
    """Map failure cluster → component type."""
    mapping = {
        "KNOWLEDGE_PROBLEM": "SKILL",
        "DETERMINISTIC_EXECUTION_PROBLEM": "TOOL",
        "INTERFACE_PROBLEM": "TOOL_SCHEMA",
        "ROUTING_PROBLEM": "ROUTER",
        "CONTEXT_PROBLEM": "RETRIEVAL",
        "MODEL_LIMIT": "MODEL_ROUTING",
        "WRONG_TOOL": "TOOL_DESCRIPTION",
        "FORMAT_FAILURE": "TOOL_SCHEMA",
        "MODEL_REASONING": "SKILL",
    }
    return mapping.get(failure_cluster, "SKILL")


class ComponentFitnessDB:
    """Store measured fitness per component; used to learn what works."""
    def __init__(self):
        self.path = f"{ROOT}/fitness/components.json"
        self.components = {}
        if os.path.exists(self.path):
            with open(self.path) as f: self.components = json.load(f)

    def record(self, cid, version, ctype, mutation, domain, samples, successes,
               tokens_delta, cost_delta, result):
        key = f"{cid}@{version}"
        self.components[key] = {
            "id": cid, "version": version, "type": ctype, "mutation": mutation,
            "domain": domain, "samples": samples, "verified_successes": successes,
            "success_rate": round(successes/max(samples,1), 3),
            "tokens_delta": tokens_delta, "cost_delta": cost_delta,
            "result": result, "ts": datetime.datetime.now(datetime.UTC).isoformat(),
            "parent": None,
        }
        self._save()

    def record_strategy(self, strategy, tested, improved):
        path = f"{ROOT}/fitness/strategies.json"
        strat = {}
        if os.path.exists(path):
            with open(path) as f: strat = json.load(f)
        strat[strategy] = {"tested": tested, "improved": improved,
                           "rate": round(improved/max(tested,1), 3)}
        with open(path, "w") as f: json.dump(strat, f, indent=2)
        return strat

    def _save(self):
        with open(self.path, "w") as f: json.dump(self.components, f, indent=2)


class RejectedMemory:
    """Remember failed components to avoid recreating them."""
    def __init__(self):
        self.path = f"{ROOT}/rejected/rejected.json"
        self.rejected = {}
        if os.path.exists(self.path):
            with open(self.path) as f: self.rejected = json.load(f)

    def reject(self, cid, reason, evidence=""):
        self.rejected[cid] = {"reason": reason, "evidence": evidence,
                              "ts": datetime.datetime.now(datetime.UTC).isoformat()}
        with open(self.path, "w") as f: json.dump(self.rejected, f, indent=2)

    def check(self, cid):
        return self.rejected.get(cid)


class NoveltyCheck:
    """Search existing ecosystem before building something new."""
    def __init__(self):
        self.existing = [
            "doctor_host", "doctor_port", "doctor_docker", "doctor_repo",
            "doctor_dependency", "doctor_tools", "resolve_docs", "command_repair",
            "repo_map", "mutation_verifier", "mcp_session", "exec_command",
        ]
        self.skills = [
            "repo-diagnostics", "server-diagnostics", "safe-mutation", "mcp-diagnostics",
        ]

    def check_tool(self, candidate_name, purpose):
        for e in self.existing:
            if candidate_name in e or e in candidate_name:
                return {"exists": True, "existing": e,
                        "verdict": "USE_EXISTING_OR_SPECIALIZE"}
        # upstream candidates
        if "git" in candidate_name.lower():
            return {"exists": False, "verdict": "BUILD_SPECIALIZED_GIT_HELPER"}
        return {"exists": False, "verdict": "BUILD"}

    def check_skill(self, candidate_name):
        for s in self.skills:
            if candidate_name in s or s in candidate_name:
                return {"exists": True, "existing": s, "verdict": "PATCH_EXISTING"}
        return {"exists": False, "verdict": "BUILD"}


class ToolFactory:
    """Turn repeated deterministic work into candidate tool specs."""

    def __init__(self):
        self.novelty = NoveltyCheck()
        self.rejected = RejectedMemory()
        self.fitness = ComponentFitnessDB()

    def propose(self, pattern: dict) -> dict:
        """
        pattern: {"domain", "repeated_commands", "frequency", "tokens_wasted",
                  "failure_rate", "description"}
        """
        domain = pattern["domain"]
        cid = f"tool-{domain}-helper"
        nv = self.novelty.check_tool(cid, pattern.get("description",""))
        rej = self.rejected.check(cid)

        spec = {
            "candidate_id": cid,
            "class": "TOOL",
            "evidence": pattern,
            "novelty": nv,
            "previously_rejected": bool(rej),
            "rejection_reason": rej.get("reason") if rej else None,
            "specification": {
                "name": f"{cid}-v0.1",
                "purpose": pattern.get("description", ""),
                "trigger": pattern.get("trigger", f"tasks in {domain} domain requiring state change"),
                "inputs": pattern.get("inputs", ["workspace_path"]),
                "outputs": {"status": "PASS/FAIL/DENIED", "evidence": "structured state"},
                "failure_states": ["workspace missing", "git not repo", "denied op"],
                "security": "operates only under workspace root; allowlist programs",
                "dependencies": [],
                "expected_token_savings": pattern.get("tokens_wasted", 0),
                "expected_success_improvement": pattern.get("failure_rate", 0),
            },
            "required_tests": [
                "unit-valid-operation", "unit-bad-path", "unit-denied-op",
                "unit-nonzero-exit", "security-traversal", "security-metachar",
                "output-schema-valid", "known-good-passes", "known-bad-fails",
            ],
            "build_decision": "BUILD" if (nv.get("verdict") != "USE_EXISTING_OR_SPECIALIZE" and not rej) else "SKIP",
        }
        return spec

    def build(self, spec: dict) -> str:
        """Generate candidate tool code from spec. Returns file path."""
        cid = spec["candidate_id"]
        code = f'''"""Auto-generated candidate tool: {cid} (evidence-driven)."""
import os, sys, json, subprocess

def main():
    ws = sys.argv[1] if len(sys.argv) > 1 else "/tmp/workspace"
    # {spec["specification"]["purpose"]}
    if not os.path.isdir(ws):
        print(json.dumps({{"status":"FAIL","error":"workspace missing"}}))
        return 1
    print(json.dumps({{"status":"PASS","workspace":ws,"tool":"{cid}"}}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
        path = f"{ROOT}/candidates/{cid}.py"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f: f.write(code)
        return path


class SkillFactory:
    """Generate concise procedural skill variants from evidence."""

    def __init__(self):
        self.novelty = NoveltyCheck()
        self.fitness = ComponentFitnessDB()

    def generate_variants(self, evidence: dict) -> list:
        """
        evidence: {"domain", "failure_reasons", "success_procedure",
                   "verification_steps", "model"}
        Returns list of variant dicts.
        """
        domain = evidence.get("domain", "general")
        base_steps = evidence.get("success_procedure", [])
        verif = evidence.get("verification_steps", [])
        reasons = evidence.get("failure_reasons", [])

        variants = [
            {
                "id": f"skill-{domain}-compressed",
                "mutation": "COMPRESSED",
                "content": self._build_skill(domain, base_steps, verif, concise=True),
            },
            {
                "id": f"skill-{domain}-decisiontree",
                "mutation": "DECISION_TREE",
                "content": self._build_skill(domain, base_steps, verif, concise=False),
            },
            {
                "id": f"skill-{domain}-failurefirst",
                "mutation": "FAILURE_FIRST",
                "content": self._build_skill(domain, base_steps, verif, concise=False,
                                             failure_first=True, reasons=reasons),
            },
            {
                "id": f"skill-{domain}-verificationfirst",
                "mutation": "VERIFICATION_FIRST",
                "content": self._build_skill(domain, base_steps, verif, concise=False,
                                             verif_first=True),
            },
        ]
        return variants

    def _build_skill(self, domain, steps, verif, concise=False, failure_first=False,
                     verif_first=False, reasons=None):
        s = [f"# Skill: {domain} execution", ""]
        if failure_first and reasons:
            s += ["## Fail first — known failure modes", ""]
            for r in reasons[:3]:
                s += [f"- If {r}: stop, diagnose, then continue."]
            s += [""]
        if verif_first:
            s += ["## 0. Verify what success looks like BEFORE acting", ""]
        s += ["## Steps", ""]
        for i, st in enumerate(steps, 1):
            s += [f"{i}. {st}"]
        s += ["", "## Verification", ""]
        for v in verif:
            s += [f"- {v}"]
        if concise:
            # single-line compressed summary
            compact = "; ".join(steps)
            return f"# Skill: {domain}\n1. {compact}\nVerify: {'; '.join(verif)}"
        return "\n".join(s)


def analyze_trajectories(store_path):
    """Cluster repeated patterns from trajectory store for factory input."""
    patterns = defaultdict(list)
    for line in open(store_path):
        try: t = json.loads(line)
        except: continue
        dom = t.get("domain", "?")
        verified = t.get("verified", False)
        cost = t.get("cost", 0)
        tokens = t.get("tokens", 0)
        if dom == "git" and not verified:
            patterns["git_failures"].append({"task": t.get("task_id"), "cost": cost, "tokens": tokens})
        if dom == "filesystem" and not verified:
            patterns["fs_failures"].append({"task": t.get("task_id"), "cost": cost})
    return patterns


if __name__ == "__main__":
    print("=== SKILL+TOOL CREATION ENGINE ===")
    print(f"classify(DETERMINISTIC_EXECUTION_PROBLEM) = {classify_problem('DETERMINISTIC_EXECUTION_PROBLEM')}")
    print(f"classify(KNOWLEDGE_PROBLEM)              = {classify_problem('KNOWLEDGE_PROBLEM')}")
    print(f"classify(INTERFACE_PROBLEM)              = {classify_problem('INTERFACE_PROBLEM')}")

    tf = ToolFactory()
    spec = tf.propose({
        "domain": "git",
        "description": "Initialize git repo, configure user, stage file, commit with message in one deterministic operation",
        "repeated_commands": ["git init", "git config user.email", "git add", "git commit"],
        "frequency": 8, "tokens_wasted": 2400, "failure_rate": 0.5,
        "trigger": "git init/commit/branch/tag tasks",
    })
    print(f"\nTOOL PROPOSAL: {spec['candidate_id']} → {spec['build_decision']}")
    print(f"  novelty: {spec['novelty']['verdict']}")

    sf = SkillFactory()
    variants = sf.generate_variants({
        "domain": "git",
        "failure_reasons": ["repo not initialized", "git identity not configured", "wrong cwd"],
        "success_procedure": ["use git -C <path> for every command",
                              "configure user.email/user.name if missing",
                              "stage then commit in one command chain"],
        "verification_steps": ["git -C <path> log -1 shows expected message",
                               "git -C <path> branch shows expected refs"],
    })
    print(f"\nSKILL VARIANTS: {len(variants)}")
    for v in variants:
        print(f"  {v['id']}: {v['content'][:80]}...")
    print(f"\n  Factory ready — engines + fitness DB + rejected memory in place")
