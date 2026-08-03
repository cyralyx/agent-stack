"""
Probe-based compression evaluation (adapted from hermes-compression-eval methodology).
Measures whether compressed context preserves critical information across 6 dimensions.
"""
import json, os, time
from typing import List, Dict, Optional

DIMENSIONS = [
    "accuracy",
    "context_awareness",
    "artifact_trail",
    "completeness",
    "continuity",
    "instruction_following",
]

DIMENSION_DESCRIPTIONS = {
    "accuracy": "Are concrete facts correct — file paths, function names, error codes, line numbers?",
    "context_awareness": "Does the answer reflect the CURRENT state, not a mid-session snapshot?",
    "artifact_trail": "Does the answer correctly enumerate artifacts (files, commands, tools)?",
    "completeness": "Does the answer address ALL parts of the probe question?",
    "continuity": "Could the next assistant continue work using only this answer?",
    "instruction_following": "Is the answer in the format the probe requested?",
}

SCORE_SCALE = {
    0: "No useful information; wrong or hallucinated.",
    1: "Major gaps or a key fact is wrong.",
    2: "Partially correct but significant omissions.",
    3: "Mostly correct with minor omissions or imprecision.",
    4: "Correct and complete with only trivial imprecision.",
    5: "Fully correct, complete, and in the requested format.",
}


class Probe:
    """A single probe question testing a specific dimension of compression quality."""
    def __init__(self, question: str, dimension: str, expected_info: List[str],
                 format: str = "free_text"):
        self.question = question
        self.dimension = dimension
        self.expected_info = expected_info
        self.format = format

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "dimension": self.dimension,
            "expected_info": self.expected_info,
            "format": self.format,
        }


class ProbeBank:
    """Collection of probes for a specific compression fixture."""
    def __init__(self, fixture_id: str, probes: List[Probe] = None):
        self.fixture_id = fixture_id
        self.probes = probes or []

    def add(self, probe: Probe):
        self.probes.append(probe)

    def to_dict(self) -> dict:
        return {
            "fixture_id": self.fixture_id,
            "probes": [p.to_dict() for p in self.probes],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProbeBank":
        pb = cls(data["fixture_id"])
        for p in data.get("probes", []):
            pb.add(Probe(
                question=p["question"],
                dimension=p["dimension"],
                expected_info=p.get("expected_info", []),
                format=p.get("format", "free_text"),
            ))
        return pb


class CompressionEvaluator:
    """Evaluates compression quality using probe-based methodology.
    
    Measures 6 dimensions (0-5 each). Generates structured report.
    Uses deterministic keyword matching as a fast proxy for LLM grading.
    """

    def __init__(self, grading_model: str = None):
        self.grading_model = grading_model

    def evaluate_probe(self, compressed_text: str, probe: Probe) -> dict:
        """Score a single probe response deterministically.
        
        Returns score 0-5 based on how many expected info items are present.
        """
        text_lower = compressed_text.lower()
        found = 0
        for info in probe.expected_info:
            if info.lower() in text_lower:
                found += 1
        
        total = len(probe.expected_info)
        if total == 0:
            score = 3  # neutral if no expected info defined
        else:
            ratio = found / total
            if ratio >= 0.9: score = 5
            elif ratio >= 0.75: score = 4
            elif ratio >= 0.6: score = 3
            elif ratio >= 0.4: score = 2
            elif ratio >= 0.2: score = 1
            else: score = 0
        
        return {
            "question": probe.question,
            "dimension": probe.dimension,
            "score": score,
            "found": found,
            "total": total,
            "found_items": [i for i in probe.expected_info if i.lower() in text_lower],
            "missing": [i for i in probe.expected_info if i.lower() not in text_lower],
        }

    def evaluate_bank(self, compressed_text: str, bank: ProbeBank) -> dict:
        """Evaluate all probes in a bank against compressed text."""
        results = []
        dimension_scores = {d: [] for d in DIMENSIONS}
        
        for probe in bank.probes:
            result = self.evaluate_probe(compressed_text, probe)
            results.append(result)
            dimension_scores[probe.dimension].append(result["score"])
        
        # Aggregate dimension scores
        aggregated = {}
        for d in DIMENSIONS:
            scores = dimension_scores[d]
            aggregated[d] = round(sum(scores) / max(len(scores), 1), 1)
        
        overall = round(sum(aggregated.values()) / len(aggregated), 1)
        
        return {
            "fixture_id": bank.fixture_id,
            "overall_score": overall,
            "dimension_scores": aggregated,
            "probe_count": len(results),
            "probe_results": results,
            "evaluator": "deterministic_keyword",
        }

    def generate_rubric(self) -> str:
        """Generate grading rubric text for LLM judge."""
        dims = "\n".join(f"  {d}: {DIMENSION_DESCRIPTIONS[d]}" for d in DIMENSIONS)
        scale = "\n".join(f"  {k}: {v}" for k, v in SCORE_SCALE.items())
        return f"""Grade on six dimensions, each 0-5:

Dimensions:
{dims}

Scale:
{scale}

Return JSON: {{"dimension": {{"accuracy": int, ...}}, "overall": float}}"""


# ===== BUILT-IN PROBE FIXTURES =====

FIXTURES = {
    "python-debug-session": ProbeBank("python-debug-session", [
        Probe(
            question="What file contained the bug?",
            dimension="accuracy",
            expected_info=["bug.py", "error", "traceback"],
            format="file_path",
        ),
        Probe(
            question="What was the error message?",
            dimension="accuracy",
            expected_info=["KeyError", "ValueError", "TypeError", "AttributeError"],
            format="error_message",
        ),
        Probe(
            question="What line number was the error on?",
            dimension="completeness",
            expected_info=["line", "lineno", ":"],
            format="number",
        ),
        Probe(
            question="What was the root cause of the bug?",
            dimension="continuity",
            expected_info=["fix", "solution", "changed", "replaced", "added"],
            format="description",
        ),
        Probe(
            question="What files were modified to fix the bug?",
            dimension="artifact_trail",
            expected_info=["py"],
            format="list",
        ),
        Probe(
            question="Did the fix require any new imports?",
            dimension="context_awareness",
            expected_info=["import"],
            format="yes/no",
        ),
    ]),

    "docker-service-failure": ProbeBank("docker-service-failure", [
        Probe(
            question="Which container/service failed?",
            dimension="accuracy",
            expected_info=["hermes", "jarvis", "container"],
            format="name",
        ),
        Probe(
            question="What was the failure mode?",
            dimension="accuracy",
            expected_info=["restart", "crash", "OOM", "error", "timeout"],
            format="description",
        ),
        Probe(
            question="What was the resolution?",
            dimension="continuity",
            expected_info=["restart", "increase", "memory", "limit", "config"],
            format="description",
        ),
        Probe(
            question="What port was the service listening on?",
            dimension="completeness",
            expected_info=["port", "80", "443", "8080", "3000"],
            format="number",
        ),
    ]),

    "git-conflict-resolution": ProbeBank("git-conflict-resolution", [
        Probe(
            question="Which branch had the conflict?",
            dimension="accuracy",
            expected_info=["branch", "main", "feature", "merge"],
            format="name",
        ),
        Probe(
            question="Which files had conflicts?",
            dimension="artifact_trail",
            expected_info=["py", "json", "yaml", "md"],
            format="list",
        ),
        Probe(
            question="How was the conflict resolved?",
            dimension="continuity",
            expected_info=["merge", "rebase", "keep", "accept", "resolve"],
            format="description",
        ),
        Probe(
            question="Was the fix committed?",
            dimension="context_awareness",
            expected_info=["commit", "push", "merged"],
            format="yes/no",
        ),
    ]),
}
