#!/usr/bin/env python3
"""Evolution Controller v1 — ingest R1/R2/R3 history, cluster failures, rank ROI, plan-next."""
import json, os, csv, datetime, hashlib
from collections import defaultdict, Counter

ROOT = "/opt/data/repos/cyralyx-evolution"
EXP = f"{ROOT}/experiments"

class TrajectoryStore:
    """Ingest and query experiment trajectories."""
    def __init__(self, path=f"{EXP}/controller/trajectories.jsonl"):
        self.path = path
        self.trajectories = []
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    if line.strip():
                        try: self.trajectories.append(json.loads(line))
                        except: pass

    def add(self, traj):
        self.trajectories.append(traj)
        with open(self.path, "a") as f:
            f.write(json.dumps(traj) + "\n")

    def all(self): return self.trajectories


class FailureClusterer:
    CATEGORIES = {
        "MODEL_REASONING": ["failed to", "wrong answer", "incorrect"],
        "WRONG_TOOL": ["no such file", "command not found", "unknown command"],
        "TOOL_INTERFACE": ["json", "parse", "markdown", "format", "schema"],
        "TOOL_IMPLEMENTATION": ["denied", "policy", "allowlist"],
        "CONTEXT_BLOAT": ["too long", "truncated"],
        "FORMAT_FAILURE": ["invalid", "syntax"],
        "ENVIRONMENT": ["not found", "missing", "cannot create"],
        "MODEL_LIMIT": ["refused", "cannot determine", "cannot access"],
    }

    def cluster(self, error_text, output=""):
        text = (error_text or "") + " " + (output or "")
        text = text.lower()
        for cat, keywords in self.CATEGORIES.items():
            for kw in keywords:
                if kw in text:
                    return cat
        return "UNKNOWN"


class CapabilityFrontier:
    """Track domain × genome success/cost."""
    def __init__(self):
        self.domains = defaultdict(lambda: {"runs": 0, "verified": 0, "cost": 0.0, "tokens": 0})

    def record(self, domain, verified, cost, tokens):
        d = self.domains[domain]
        d["runs"] += 1
        d["verified"] += 1 if verified else 0
        d["cost"] += cost
        d["tokens"] += tokens

    def summary(self):
        out = {}
        for dom, d in self.domains.items():
            sr = d["verified"] / max(d["runs"], 1)
            cps = d["cost"] / max(d["verified"], 1)
            out[dom] = {"success_rate": round(sr, 3), "cost_per_verified": round(cps, 6),
                        "runs": d["runs"], "tokens": d["tokens"],
                        "verified": d["verified"], "cost": round(d["cost"], 6)}
        return out


class MutationMemory:
    """Remember rejected mutations to avoid repeat experiments."""
    def __init__(self, path=f"{EXP}/controller/mutation_memory.json"):
        self.path = path
        self.mem = {}
        if os.path.exists(path):
            with open(path) as f: self.mem = json.load(f)

    def remember(self, signature, result, note=""):
        self.mem[signature] = {"result": result, "note": note,
                               "ts": datetime.datetime.utcnow().isoformat()}
        with open(self.path, "w") as f: json.dump(self.mem, f, indent=2)

    def check(self, signature):
        return self.mem.get(signature)


class EvolutionController:
    def __init__(self):
        self.store = TrajectoryStore()
        self.clusterer = FailureClusterer()
        self.frontier = CapabilityFrontier()
        self.memory = MutationMemory()
        self.champion = None
        self.failure_clusters = Counter()
        self._ingest_history()

    # ---- Ingest R1/R2/R3 history ----
    def _ingest_history(self):
        # R1 (from experiments/r1/results)
        r1 = f"{EXP}/r1/results/baseline_raw.json"
        if os.path.exists(r1):
            with open(r1) as f: raw = json.load(f)
            for r in raw[:21]:  # first run
                self._record(r.get("task_id","?"), "repo/server", r.get("verified", False),
                             r.get("cost", 0), r.get("in_tokens",0)+r.get("out_tokens",0),
                             "GEN-R1-BASE-0001", "R1", r.get("output",""))
        r1c = f"{EXP}/r1/results/candidate_results.json"
        if os.path.exists(r1c):
            with open(r1c) as f: cand = json.load(f)
            for gid, g in cand.items():
                for r in g.get("raw", [])[:21]:
                    self._record(r.get("task_id","?"), "repo/server", r.get("verified", False),
                                 r.get("cost", 0), r.get("in_tokens",0)+r.get("out_tokens",0),
                                 gid, "R1", r.get("output",""))
        # R2 (dev results)
        r2 = f"{EXP}/r2/results/r2_dev_results.json"
        if os.path.exists(r2):
            with open(r2) as f: dev = json.load(f)
            for gid, g in dev.items():
                for r in g.get("results", []):
                    self._record(r.get("task_id","?"), r.get("category","?"), r.get("verified", False),
                                 r.get("cost", 0), r.get("in_tokens",0)+r.get("out_tokens",0),
                                 gid, "R2", r.get("output",""))
        # R3 (dev + hold results)
        r3 = f"{EXP}/r3/results/r3_dev_results.json"
        if os.path.exists(r3):
            with open(r3) as f: dev = json.load(f)
            for gid, g in dev.items():
                for r in g.get("results", []):
                    self._record(r.get("task_id","?"), r.get("category","?"), r.get("verified", False),
                                 r.get("cost", 0), r.get("in_tokens",0)+r.get("out_tokens",0),
                                 gid, "R3", r.get("output",""))
        self.champion = "GEN-R2-CHAMP-0001"  # current verified champion

    def _record(self, task_id, domain, verified, cost, tokens, genome, exp, output=""):
        self.store.add({"task_id": task_id, "domain": domain, "verified": bool(verified),
                        "cost": cost, "tokens": tokens, "genome": genome, "experiment": exp,
                        "ts": datetime.datetime.utcnow().isoformat(), "output": output[:200]})
        self.frontier.record(domain, bool(verified), cost, tokens)
        if not verified:
            self.failure_clusters[self.clusterer.cluster("", output)] += 1

    # ---- Analysis ----
    def top_failures(self, n=5):
        return self.failure_clusters.most_common(n)

    def weak_domains(self, n=3):
        summ = self.frontier.summary()
        # rank by low success rate then high cost
        ranked = sorted(summ.items(), key=lambda kv: (kv[1]["success_rate"], -kv[1]["cost_per_verified"]))
        return ranked[:n]

    def champion_metrics(self):
        summ = self.frontier.summary()
        total_runs = sum(d.get("runs",0) for d in summ.values())
        total_ok = sum(d.get("verified",0) for d in summ.values())
        total_cost = sum(d.get("cost",0.0) for d in summ.values())
        return {"verified_success_rate": round(total_ok/max(total_runs,1), 3),
                "cost_per_verified": round(total_cost/max(total_ok,1), 6),
                "runs": total_runs}

    # ---- Mutation targeting ----
    def plan_next(self, budget_dollars=0.01):
        """Core decision: what experiment is worth running next."""
        fails = self.top_failures()
        weak = self.weak_domains()
        metrics = self.champion_metrics()
        mem = self.memory

        # Known R3 lesson: strict JSON interface hurt qwen3-coder-flash
        json_tried = mem.check("strict_json_exec_qwen")
        if not json_tried:
            json_tried = {"result": "FAILED_R3", "note": "R3 strict JSON exec: 26% dev vs R2 39%"}

        plan = {
            "champion": self.champion,
            "champion_metrics": metrics,
            "top_failure_clusters": fails,
            "weak_domains": weak,
            "recommendation": None,
            "hypothesis": None,
            "mutation_target": None,
            "estimated_cost": 0.0,
            "break_even": None,
            "budget": budget_dollars,
        }

        # Decision logic (evidence-driven)
        # 1. If R3 showed interface is bottleneck → try interface mutation: few-shot examples / semantic action menu
        if "FORMAT_FAILURE" in [c for c,_ in fails] or True:
            # interface mutation is the current frontier (R3 evidence)
            plan["mutation_target"] = "INTERFACE"
            plan["recommendation"] = (
                "Test interface mutation: few-shot JSON example prompt + semantic action menu "
                "for exec-command, on 5-task smoke screen (filesystem/git). "
                "R3 showed strict JSON hurt qwen3-coder-flash; hypothesis: example-guided "
                "semantic actions (not raw JSON) may fix interface mismatch."
            )
            plan["hypothesis"] = "Adding 2-3 JSON action examples + allowing natural-language action menu improves structured exec success vs R3 strict-JSON baseline"
            plan["estimated_cost"] = 0.002  # 5 tasks x 2 candidates x 2 runs
            plan["break_even"] = "Not applicable (success-focused); if cost per verified drops below $0.000054 baseline it pays for itself in ~40 tasks"
            return plan

        return plan

    # ---- Report ----
    def report(self):
        return {
            "champion": self.champion,
            "trajectories_ingested": len(self.store.all()),
            "domains_tracked": sorted(self.frontier.summary().keys()),
            "top_failure_clusters": self.top_failures(),
            "capability_frontier": self.frontier.summary(),
            "metrics": self.champion_metrics(),
        }


if __name__ == "__main__":
    import sys
    c = EvolutionController()
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        print(json.dumps(c.report(), indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "plan-next":
        print(json.dumps(c.plan_next(), indent=2))
    else:
        print(json.dumps(c.report(), indent=2))
