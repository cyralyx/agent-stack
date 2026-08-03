"""
Lightweight tool evolution — inspired by GEPA methodology from hermes-agent-self-evolution.
Evolves tool descriptions and skills using execution-trace-driven mutation.
"""
import json, hashlib, time

class ToolEvolution:
    """Evolutionary optimization for tool descriptions using execution trace analysis.
    
    Cycle:
    1. Read current tool description
    2. Collect execution traces (failures, confusion points)
    3. Generate candidate variants by mutating description
    4. Evaluate variants against criteria
    5. Select best variant
    """

    def __init__(self, outcome_store=None):
        self.outcome_store = outcome_store
        self.history = []

    def analyze_trace(self, tool_name: str, trace: dict) -> dict:
        """Analyze a single execution trace for improvement opportunities."""
        issues = []
        score = 5  # start perfect, deduct
        
        if trace.get("error"):
            score -= 2
            issues.append(f"error: {trace['error'][:100]}")
        
        if trace.get("retries", 0) > 0:
            score -= trace["retries"]
            issues.append(f"retries: {trace['retries']}")
        
        if trace.get("timeout", False):
            score -= 1
            issues.append("timeout")
        
        # Check description quality indicators
        if trace.get("confused", False):
            score -= 1
            issues.append("agent confused by description")
        
        if trace.get("wrong_tool_first", False):
            score -= 1
            issues.append("wrong tool chosen first")
        
        return {
            "tool": tool_name,
            "score": max(0, score),
            "issues": issues,
            "improvement_needed": score < 4,
        }

    def suggest_mutations(self, current_desc: str, issues: list, max_length: int = 500) -> list:
        """Generate candidate description mutations based on observed issues."""
        candidates = []
        
        if "retries" in str(issues):
            candidates.append(current_desc + " Include common failure modes and how to fix them.")
        
        if "confused" in str(issues):
            candidates.append("Simplified: " + current_desc[:max_length-20])
        
        if "wrong_tool" in str(issues):
            candidates.append(current_desc + " Use this tool when: <exact trigger condition>.")
        
        if "error" in str(issues):
            candidates.append(current_desc + " Common errors: <list>, solutions: <list>.")
        
        # Truncate and deduplicate
        seen = set()
        unique = []
        for c in candidates:
            h = hashlib.md5(c.encode()).hexdigest()
            if h not in seen:
                seen.add(h)
                unique.append(c[:max_length])
        
        return unique or [current_desc]

    def evaluate_variant(self, variant: str, criteria: dict) -> float:
        """Score a variant against criteria (0-1)."""
        score = 1.0
        
        # Length check
        if len(variant) > criteria.get("max_length", 500):
            score -= 0.2
        if len(variant) < criteria.get("min_length", 20):
            score -= 0.2
        
        # Keywords present
        for kw in criteria.get("required_keywords", []):
            if kw not in variant:
                score -= 0.1
        
        # No prohibited patterns
        for p in criteria.get("prohibited", []):
            if p in variant.lower():
                score -= 0.3
        
        return max(0, score)


class SkillEvolution:
    """Evolve skill SKILL.md content based on usage traces."""

    @staticmethod
    def suggest_improvements(skill_name: str, usage_stats: dict) -> list:
        """Generate improvement suggestions for a skill based on usage."""
        suggestions = []
        
        if usage_stats.get("failure_rate", 0) > 0.3:
            suggestions.append(f"Skill '{skill_name}' has high failure rate ({usage_stats['failure_rate']:.0%}). "
                             "Add troubleshooting section with common failure modes.")
        
        if usage_stats.get("avg_tokens", 0) > 2000:
            suggestions.append(f"Skill '{skill_name}' uses {usage_stats['avg_tokens']} tokens. "
                             "Compress examples, remove redundant instructions.")
        
        if usage_stats.get("unused", False):
            suggestions.append(f"Skill '{skill_name}' has not been triggered recently. "
                             "Consider merging into broader skill.")
        
        return suggestions
