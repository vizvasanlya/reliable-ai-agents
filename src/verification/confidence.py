"""
Confidence Scorer — rates how sure the agent is about its output.

Combines multiple signals to produce a confidence score:
- Syntax validation
- Test results
- Security scan
- Historical success rate
"""

from dataclasses import dataclass
from typing import Dict, Optional

from .syntax import SyntaxChecker, SyntaxResult
from .security import SecurityScanner, SecurityReport


@dataclass
class ConfidenceReport:
    overall: float  # 0.0 to 1.0
    syntax_score: float
    security_score: float
    needs_human_review: bool
    factors: Dict[str, float]


class ConfidenceScorer:
    """
    Scores confidence in the agent's output.

    Higher confidence means the agent is more certain its work is correct.
    """

    def __init__(self):
        self.syntax_checker = SyntaxChecker()
        self.security_scanner = SecurityScanner()
        self.history: list = []

    def score(self, code: str, language: str = "auto",
              tests_passed: Optional[bool] = None) -> ConfidenceReport:
        """
        Calculate confidence score for code output.
        """
        # Syntax check
        syntax_result = self.syntax_checker.check(code, language)
        syntax_score = 1.0 if syntax_result.valid else 0.3

        # Security scan
        security_result = self.security_scanner.scan(code, language)
        security_score = security_result.score

        # Test result (if available)
        test_score = 1.0
        if tests_passed is not None:
            test_score = 1.0 if tests_passed else 0.2

        # Weighted average
        weights = {
            "syntax": 0.3,
            "security": 0.3,
            "tests": 0.4
        }

        overall = (
            syntax_score * weights["syntax"] +
            security_score * weights["security"] +
            test_score * weights["tests"]
        )

        # Determine if human review is needed
        needs_review = overall < 0.7 or not syntax_result.valid

        factors = {
            "syntax": syntax_score,
            "security": security_score,
            "tests": test_score
        }

        report = ConfidenceReport(
            overall=overall,
            syntax_score=syntax_score,
            security_score=security_score,
            needs_human_review=needs_review,
            factors=factors
        )

        self.history.append(report)
        return report

    def get_average_confidence(self) -> float:
        """Get average confidence across all scored outputs."""
        if not self.history:
            return 0.0
        return sum(h.overall for h in self.history) / len(self.history)

    def get_trend(self) -> str:
        """Get confidence trend over time."""
        if len(self.history) < 2:
            return "insufficient_data"

        recent = self.history[-5:]
        older = self.history[-10:-5] if len(self.history) >= 10 else self.history[:5]

        recent_avg = sum(h.overall for h in recent) / len(recent)
        older_avg = sum(h.overall for h in older) / len(older) if older else recent_avg

        if recent_avg > older_avg + 0.05:
            return "improving"
        elif recent_avg < older_avg - 0.05:
            return "declining"
        else:
            return "stable"
