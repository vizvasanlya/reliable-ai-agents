"""
Trust System — tracks agent reliability over time.

As the agent demonstrates competence, its trust level increases,
allowing more autonomous operation. Errors decrease trust.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TrustLevel:
    score: float = 0.5  # 0.0 to 1.0
    successful_tasks: int = 0
    failed_tasks: int = 0
    consecutive_successes: int = 0
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        total = self.successful_tasks + self.failed_tasks
        return self.successful_tasks / total if total > 0 else 0.0

    @property
    def reliability_grade(self) -> str:
        if self.score >= 0.9:
            return "A"
        elif self.score >= 0.8:
            return "B"
        elif self.score >= 0.7:
            return "C"
        elif self.score >= 0.5:
            return "D"
        else:
            return "F"


class TrustSystem:
    """
    Tracks and manages agent trust levels.

    Trust increases with successful operations and decreases with failures.
    Higher trust allows more autonomous operation.
    """

    def __init__(self):
        self.levels: Dict[str, TrustLevel] = {}
        self.history: List[Dict] = []

    def get_trust(self, context: str = "global") -> TrustLevel:
        """Get trust level for a context."""
        if context not in self.levels:
            self.levels[context] = TrustLevel()
        return self.levels[context]

    def record_success(self, context: str = "global"):
        """Record a successful operation."""
        trust = self.get_trust(context)
        trust.successful_tasks += 1
        trust.consecutive_successes += 1
        trust.consecutive_failures = 0

        # Increase trust (diminishing returns)
        bonus = 0.05 * (1.0 - trust.score)  # More room to grow = bigger bonus
        trust.score = min(1.0, trust.score + bonus)

        self.history.append({
            "context": context,
            "event": "success",
            "new_score": trust.score
        })

    def record_failure(self, context: str = "global"):
        """Record a failed operation."""
        trust = self.get_trust(context)
        trust.failed_tasks += 1
        trust.consecutive_failures += 1
        trust.consecutive_successes = 0

        # Decrease trust (more severe for consecutive failures)
        penalty = 0.1 * (1.0 + trust.consecutive_failures * 0.5)
        trust.score = max(0.0, trust.score - penalty)

        self.history.append({
            "context": context,
            "event": "failure",
            "new_score": trust.score
        })

    def can_auto_execute(self, context: str = "global") -> bool:
        """Check if the agent has enough trust to execute without approval."""
        trust = self.get_trust(context)
        return trust.score >= 0.7 and trust.consecutive_failures < 2

    def needs_supervision(self, context: str = "global") -> bool:
        """Check if the agent needs human supervision."""
        trust = self.get_trust(context)
        return trust.score < 0.5 or trust.consecutive_failures >= 3

    def get_stats(self) -> Dict[str, any]:
        """Get overall trust statistics."""
        if not self.levels:
            return {"contexts": 0}

        total_success = sum(t.successful_tasks for t in self.levels.values())
        total_fail = sum(t.failed_tasks for t in self.levels.values())
        avg_score = sum(t.score for t in self.levels.values()) / len(self.levels)

        return {
            "contexts": len(self.levels),
            "total_successes": total_success,
            "total_failures": total_fail,
            "overall_success_rate": f"{(total_success/(total_success+total_fail))*100:.0f}%" if (total_success+total_fail) > 0 else "N/A",
            "average_trust_score": f"{avg_score:.2f}",
            "history_entries": len(self.history)
        }
