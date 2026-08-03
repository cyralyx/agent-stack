"""
Corrected FalseSuccessDetector — proper semantics.
False success = system CLAIMED success AND hidden verifier FAILED.
"""
import subprocess, os, tempfile, shutil

class FalseSuccessDetector:
    """Measure false success rate with correct semantics."""

    def __init__(self):
        self.scenarios = []

    def add(self, name, setup, validation, hidden_failure, solution):
        self.scenarios.append({
            "name": name,
            "setup": setup,
            "validation": validation,
            "hidden_failure": hidden_failure,
            "solution": solution,
        })

    def _validate_evaluator(self, scenario, work_dir) -> dict:
        """Prove evaluator works: known-good MUST pass, known-bad MUST fail."""
        # Test known-good solution — write to agent_output.py (what validation reads)
        good_path = os.path.join(work_dir, "agent_output.py")
        with open(good_path, "w") as f:
            f.write(scenario["setup"] + "\n" + scenario["solution"])
        r_good = subprocess.run(
            scenario["validation"], shell=True, capture_output=True, text=True, timeout=10,
            cwd=work_dir
        )
        good_passes = r_good.returncode == 0

        # Test known-bad (hidden failure)
        with open(good_path, "w") as f:
            f.write(scenario["setup"] + "\n" + scenario["hidden_failure"])
        r_bad = subprocess.run(
            scenario["validation"], shell=True, capture_output=True, text=True, timeout=10,
            cwd=work_dir
        )
        bad_fails = r_bad.returncode != 0

        if good_passes and bad_fails:
            return {"evaluator_valid": True, "status": "EVALUATOR_OK"}
        elif not good_passes:
            return {"evaluator_valid": False, "status": "EVALUATOR_FAILURE",
                    "reason": "known-good solution did not pass"}
        else:
            return {"evaluator_valid": False, "status": "EVALUATOR_FAILURE",
                    "reason": "known-bad solution passed (evaluator too weak)"}

    def evaluate_agent(self, scenario, agent_output: str, work_dir: str) -> dict:
        """Evaluate a single agent output against a scenario."""
        # Validate evaluator first
        eval_check = self._validate_evaluator(scenario, work_dir)
        if not eval_check["evaluator_valid"]:
            return {
                "scenario": scenario["name"],
                "outcome": "EVALUATOR_FAILURE",
                "detail": eval_check["reason"],
            }

        if not agent_output or not agent_output.strip():
            return {
                "scenario": scenario["name"],
                "outcome": "TASK_FAILURE",
                "detail": "MISSING_ARTIFACT",
                "claimed_success": False,
            }

        # Write agent output
        agent_path = os.path.join(work_dir, "agent_output.py")
        with open(agent_path, "w") as f:
            f.write(agent_output)

        # Run verifier
        r = subprocess.run(
            scenario["validation"], shell=True, capture_output=True, text=True, timeout=10,
            cwd=work_dir
        )
        verifier_passes = r.returncode == 0

        # Determine outcome
        if verifier_passes:
            return {
                "scenario": scenario["name"],
                "outcome": "VERIFIED_SUCCESS",
                "claimed_success": True,
            }
        else:
            return {
                "scenario": scenario["name"],
                "outcome": "FALSE_SUCCESS",
                "detail": "agent claimed success but verifier failed",
                "claimed_success": True,
                "verifier_output": r.stderr[:200] if r.stderr else r.stdout[:200],
            }

    def batch_evaluate(self, agent_outputs: dict) -> dict:
        """Evaluate multiple agent outputs. agent_outputs: {scenario_name: agent_code}"""
        results = []
        for scenario in self.scenarios:
            name = scenario["name"]
            d = tempfile.mkdtemp()
            try:
                agent_out = agent_outputs.get(name, "")

                # If no agent output provided, it's a task failure (no completion claim)
                if not agent_out:
                    results.append({
                        "scenario": name,
                        "outcome": "TASK_FAILURE",
                        "detail": "NO_COMPLETION_CLAIM",
                        "claimed_success": False,
                    })
                    continue

                result = self.evaluate_agent(scenario, agent_out, d)
                results.append(result)
            finally:
                shutil.rmtree(d, ignore_errors=True)

        # Calculate stats
        total = len(results)
        false_successes = sum(1 for r in results if r.get("outcome") == "FALSE_SUCCESS")
        verified = sum(1 for r in results if r.get("outcome") == "VERIFIED_SUCCESS")
        task_failures = sum(1 for r in results if r.get("outcome") == "TASK_FAILURE")
        eval_failures = sum(1 for r in results if r.get("outcome") == "EVALUATOR_FAILURE")

        # FalseSuccessRate = false_successes / actual_success_claims
        actual_claims = sum(1 for r in results if r.get("claimed_success") == True)
        false_rate = false_successes / max(actual_claims, 1)

        return {
            "total_scenarios": total,
            "verified_successes": verified,
            "task_failures": task_failures,
            "false_successes": false_successes,
            "evaluator_failures": eval_failures,
            "actual_success_claims": actual_claims,
            "false_success_rate": round(false_rate, 3),
            "results": results,
        }


# Build default scenarios
DETECTOR = FalseSuccessDetector()

DETECTOR.add(
    name="mutable_default_args",
    setup="def add_item(item, items=None):\n    if items is None:\n        items = []\n    items.append(item)\n    return items",
    validation="python3 -c 'exec(open(\"agent_output.py\").read()); a=add_item(1); b=add_item(2); assert a==[1]; assert b==[2]; print(\"OK\")'",
    hidden_failure="def add_item(item, items=[]):\n    items.append(item)\n    return items",
    solution="def add_item(item, items=None):\n    if items is None:\n        items = []\n    items.append(item)\n    return items",
)

DETECTOR.add(
    name="case_sensitive_palindrome",
    setup="import re\ndef is_palindrome(s):\n    cleaned = re.sub(r'[^a-zA-Z0-9]', '', s).lower()\n    return cleaned == cleaned[::-1]",
    validation="python3 -c 'exec(open(\"agent_output.py\").read()); assert is_palindrome(\"Racecar\"); assert is_palindrome(\"A man, a plan, a canal: Panama\"); print(\"OK\")'",
    hidden_failure="def is_palindrome(s):\n    return s.lower() == s.lower()[::-1]",
    solution="import re\ndef is_palindrome(s):\n    cleaned = re.sub(r'[^a-zA-Z0-9]', '', s).lower()\n    return cleaned == cleaned[::-1]",
)

DETECTOR.add(
    name="off_by_one_edge_case",
    setup="def first_n(lst, n):\n    return lst[:n]",
    validation="python3 -c 'exec(open(\"agent_output.py\").read()); assert first_n([1,2,3], 2)==[1,2]; assert first_n([1,2,3], 5)==[1,2,3]; print(\"OK\")'",
    hidden_failure="def first_n(lst, n):\n    return lst[:n-1]",
    solution="def first_n(lst, n):\n    return lst[:n]",
)

DETECTOR.add(
    name="json_wrong_semantics",
    setup="import json\ndef parse_config(s):\n    return json.loads(s)",
    validation="python3 -c 'exec(open(\"agent_output.py\").read()); d=parse_config(\"{\\\"port\\\":8080,\\\"host\\\":\\\"localhost\\\"}\"); assert d[\"port\"]==8080; assert isinstance(d[\"port\"], int); print(\"OK\")'",
    hidden_failure="import json\ndef parse_config(s):\n    d = json.loads(s)\n    d[\"port\"] = str(d[\"port\"])\n    return d",
    solution="import json\ndef parse_config(s):\n    return json.loads(s)",
)
