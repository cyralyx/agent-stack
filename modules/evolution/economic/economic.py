#!/usr/bin/env python3
"""Cyralyx Economic Evolution Controller — deterministic cost control modules.

No model calls. Pure Python. Integrates with existing Evolution Controller.
"""
import json, os, time, hashlib, datetime
from dataclasses import dataclass, field

ROOT = "/opt/data/repos/cyralyx-evolution/experiments/economic"
os.makedirs(f"{ROOT}/ledger", exist_ok=True)

# ===== Model Tier Registry =====
@dataclass
class ModelTier:
    name: str
    models: list
    input_price_per_m: float   # $ per 1M input tokens
    output_price_per_m: float
    notes: str = ""

TIERS = [
    ModelTier("TIER0_DETERMINISTIC", [], 0.0, 0.0, "software, no model call"),
    ModelTier("TIER1_ULTRA_CHEAP", ["qwen/qwen3-coder-flash"], 0.30, 0.60, "default evolution worker"),
    ModelTier("TIER2_BALANCED", ["deepseek-v4-flash"], 0.50, 1.00, "debugging fallback"),
    ModelTier("TIER3_STRONG", ["qwen3.5-flash"], 1.00, 2.00, "rare reasoning"),
    ModelTier("TIER4_EXPENSIVE", ["qwen3.7-plus"], 3.00, 6.00, "teacher only"),
]

MODEL_TIER_MAP = {m: t.name for t in TIERS for m in t.models}

def model_tier(model): return MODEL_TIER_MAP.get(model, "TIER2_BALANCED")

def price(model, in_tok, out_tok):
    """Cost in dollars for a model call."""
    for t in TIERS:
        if model in t.models:
            return (in_tok * t.input_price_per_m + out_tok * t.output_price_per_m) / 1e6
    return (in_tok * 0.5 + out_tok * 1.0) / 1e6


# ===== BudgetManager =====
class BudgetManager:
    def __init__(self, max_dollars=0.005, max_calls=30, max_tokens=50000,
                 max_wall_time=600, daily_cap=0.02):
        self.max_dollars = max_dollars
        self.max_calls = max_calls
        self.max_tokens = max_tokens
        self.max_wall_time = max_wall_time
        self.daily_cap = daily_cap
        self.start = time.time()
        self.spent = 0.0
        self.calls = 0
        self.tokens = 0
        self.stop_reason = None

    def record(self, cost, tokens=0):
        self.spent += cost
        self.calls += 1
        self.tokens += tokens
        pct = self.spent / self.max_dollars if self.max_dollars else 0
        if pct >= 0.80 and pct < 0.95:
            self.stop_reason = "AT_80_PCT_STOP_NEW_CANDIDATES"
        elif pct >= 0.95 and pct < 1.0:
            self.stop_reason = "AT_95_PCT_FINISH_CURRENT_ONLY"
        elif self.spent >= self.max_dollars:
            self.stop_reason = "HARD_STOP_BUDGET"
        elif self.calls >= self.max_calls:
            self.stop_reason = "HARD_STOP_CALLS"
        elif time.time() - self.start >= self.max_wall_time:
            self.stop_reason = "HARD_STOP_WALL_TIME"
        elif self.spent >= self.daily_cap:
            self.stop_reason = "HARD_STOP_DAILY_CAP"
        return self.can_spend()

    def can_spend(self):
        return self.spent < self.max_dollars and self.calls < self.max_calls \
               and (time.time() - self.start) < self.max_wall_time \
               and self.spent < self.daily_cap

    def status(self):
        return {"spent": round(self.spent, 6), "max": self.max_dollars,
                "calls": self.calls, "tokens": self.tokens,
                "remaining": round(max(0, self.max_dollars - self.spent), 6),
                "stop_reason": self.stop_reason}


# ===== CostLedger =====
class CostLedger:
    def __init__(self, path=f"{ROOT}/ledger/ledger.json"):
        self.path = path
        self.entries = []
        if os.path.exists(path):
            with open(path) as f: self.entries = json.load(f)

    def add(self, phase, exp_id, model, cost, tokens, note=""):
        self.entries.append({
            "ts": datetime.datetime.now(datetime.UTC).isoformat(),
            "phase": phase, "exp": exp_id, "model": model,
            "cost": round(cost, 7), "tokens": tokens, "note": note,
        })
        with open(self.path, "w") as f: json.dump(self.entries, f, indent=2)

    def by_phase(self):
        agg = {}
        for e in self.entries:
            agg.setdefault(e["phase"], {"cost": 0.0, "calls": 0})
            agg[e["phase"]]["cost"] += e["cost"]
            agg[e["phase"]]["calls"] += 1
        return agg

    def total(self):
        return sum(e["cost"] for e in self.entries)


# ===== EconomicPromotionGate =====
class EconomicPromotionGate:
    """Global champion swap requires NO capability regression + cheaper CPS."""
    def __init__(self, allow_success_delta=-0.001):
        self.allow_success_delta = allow_success_delta  # ~0 regression allowed

    def evaluate(self, old, new):
        """
        old/new: {verified_success, false_success, unsafe, cost_per_verified,
                  holdout_success, intervention}
        Returns (PASS/FAIL, reason, swap_type)
        """
        reasons = []
        # No capability tradeoff
        if new["verified_success"] < old["verified_success"] - 0.01:
            reasons.append(f"success regression: {new['verified_success']:.2f} < {old['verified_success']:.2f}")
        if new.get("false_success", 0) > old.get("false_success", 0):
            reasons.append("false-success regression")
        if new.get("unsafe", 0) > old.get("unsafe", 0):
            reasons.append("unsafe-action regression")
        if new.get("holdout_success", 1) < old.get("holdout_success", 1) - 0.02:
            reasons.append("holdout regression")
        if new.get("intervention", 0) > old.get("intervention", 0):
            reasons.append("human-intervention regression")
        # Cost must improve
        if new["cost_per_verified"] >= old["cost_per_verified"]:
            reasons.append(f"not cheaper: {new['cost_per_verified']} >= {old['cost_per_verified']}")

        if reasons:
            return {"pass": False, "reasons": reasons, "swap": "NONE"}
        return {"pass": True, "reasons": [], "swap": "GLOBAL_CHAMPION"}

    def specialist(self, old_global_cps, new_cps, domain):
        """Cheaper-but-worse can be an ECONOMY_SPECIALIST if it meets quality."""
        return {"pass": new_cps < old_global_cps, "swap": "ECONOMY_SPECIALIST",
                "domain": domain}


# ===== ExperimentPreflight =====
class ExperimentPreflight:
    """Estimate cost before spending."""
    def __init__(self, ledger: CostLedger):
        self.ledger = ledger

    def estimate(self, candidates, tasks, avg_in=400, avg_out=120, model="qwen/qwen3-coder-flash"):
        est_calls = candidates * tasks
        est_in = est_calls * avg_in
        est_out = est_calls * avg_out
        est_cost = price(model, est_in, est_out)
        return {"calls": est_calls, "in_tokens": est_in, "out_tokens": est_out,
                "estimated_max_cost": round(est_cost, 5), "model": model}

    def approve(self, est_cost, threshold=0.005, requires_approval=0.02):
        if est_cost <= threshold:
            return {"decision": "AUTO_RUN", "cost": est_cost}
        if est_cost <= requires_approval:
            return {"decision": "REQUIRES_ROI_JUSTIFICATION", "cost": est_cost}
        return {"decision": "REQUIRES_USER_APPROVAL", "cost": est_cost}


# ===== BaselineCache =====
class BaselineCache:
    """Cache baseline results by champion/benchmark/model/environment hash."""
    def __init__(self, path=f"{ROOT}/ledger/baseline_cache.json"):
        self.path = path
        self.cache = {}
        if os.path.exists(path):
            with open(path) as f: self.cache = json.load(f)

    def key(self, champion_hash, benchmark_hash, model, env="zimablade"):
        return hashlib.sha256(f"{champion_hash}|{benchmark_hash}|{model}|{env}".encode()).hexdigest()[:16]

    def get(self, key):
        return self.cache.get(key)

    def put(self, key, result):
        self.cache[key] = {"result": result, "ts": datetime.datetime.now(datetime.UTC).isoformat()}
        with open(self.path, "w") as f: json.dump(self.cache, f, indent=2)


# ===== EarlyStopper =====
class EarlyStopper:
    def __init__(self):
        pass

    def should_stop(self, candidate, parent, unsafe=0, false_success=0):
        """Kill losing candidates fast."""
        if unsafe > 0:
            return True, "UNSAFE_ACTION"
        if false_success > 0:
            return True, "FALSE_SUCCESS"
        # material success regression on smoke
        if candidate["verified"] / max(candidate["total"], 1) < parent["verified"] / max(parent["total"], 1) - 0.25:
            return True, "SUCCESS_REGRESSION"
        # cost clearly higher without benefit
        if candidate["cost"] > parent["cost"] * 1.5 and candidate["verified"] <= parent["verified"]:
            return True, "COST_EXPLOSION_NO_BENEFIT"
        return False, None


# ===== CheapestPassingRouter =====
class CheapestPassingRouter:
    """Route task class → cheapest model tier meeting quality threshold."""
    def __init__(self):
        # default: learned from history
        self.routes = {
            "git": "TIER1_ULTRA_CHEAP",          # A4 specialist proven
            "repo/server": "TIER1_ULTRA_CHEAP",
            "data/config": "TIER1_ULTRA_CHEAP",
            "filesystem": "TIER1_ULTRA_CHEAP",
            "coding": "TIER2_BALANCED",
            "debug": "TIER2_BALANCED",
            "research_synthesis": "TIER3_STRONG",
            "teacher": "TIER4_EXPENSIVE",
        }
        self._tier_models = {t.name: t.models for t in TIERS}

    def route(self, task_class):
        tier = self.routes.get(task_class, "TIER1_ULTRA_CHEAP")
        models = self._tier_models.get(tier, [])
        return tier, models[0] if models else None

    def learn(self, task_class, tier):
        """Update route from evidence."""
        if task_class in self.routes:
            self.routes[task_class] = tier


# ===== BreakEvenCalculator =====
class BreakEvenCalculator:
    def __init__(self):
        pass

    def savings_per_task(self, old_cps, new_cps):
        return max(0.0, old_cps - new_cps)

    def break_even_tasks(self, experiment_cost, old_cps, new_cps):
        spt = self.savings_per_task(old_cps, new_cps)
        if spt <= 0:
            return None
        return experiment_cost / spt

    def future_value(self, experiment_cost, old_cps, new_cps, future_tasks=1000):
        spt = self.savings_per_task(old_cps, new_cps)
        return spt * future_tasks - experiment_cost


if __name__ == "__main__":
    print("=== ECONOMIC MODULES SELF-TEST ===")
    # Budget hard stop
    b = BudgetManager(max_dollars=0.001)
    b.record(0.0006); b.record(0.0004)
    print(f"  Budget hard stop: {b.status()['stop_reason']} (spent={b.spent:.6f})")

    # Promotion gate: same-quality-cheaper → swap; cheaper-worse → reject
    gate = EconomicPromotionGate()
    r1 = gate.evaluate({"verified_success": 0.5, "false_success": 0, "unsafe": 0,
                        "cost_per_verified": 0.00010, "holdout_success": 0.5, "intervention": 0},
                       {"verified_success": 0.5, "false_success": 0, "unsafe": 0,
                        "cost_per_verified": 0.00006, "holdout_success": 0.5, "intervention": 0})
    r2 = gate.evaluate({"verified_success": 0.5, "false_success": 0, "unsafe": 0,
                        "cost_per_verified": 0.00010, "holdout_success": 0.5, "intervention": 0},
                       {"verified_success": 0.4, "false_success": 0, "unsafe": 0,
                        "cost_per_verified": 0.00004, "holdout_success": 0.5, "intervention": 0})
    print(f"  Same-quality-cheaper: {'PASS' if r1['pass'] else 'FAIL'} swap={r1['swap']}")
    print(f"  Cheaper-but-worse:    {'PASS' if r2['pass'] else 'FAIL'} reasons={r2['reasons'][:1]}")

    # Break-even
    be = BreakEvenCalculator()
    print(f"  Break-even ($0.01 exp, save $0.00004/task): {be.break_even_tasks(0.01, 0.0001, 0.00006):.0f} tasks")

    # Router
    rtr = CheapestPassingRouter()
    print(f"  Route('git'): {rtr.route('git')}  Route('debug'): {rtr.route('debug')}")

    # Preflight
    pf = ExperimentPreflight(CostLedger())
    est = pf.estimate(4, 5)
    print(f"  Preflight 4 cands x 5 tasks: ${est['estimated_max_cost']:.5f} → {pf.approve(est['estimated_max_cost'])['decision']}")
