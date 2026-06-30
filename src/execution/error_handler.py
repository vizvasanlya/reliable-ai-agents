"""
Error Handler — catches and recovers from execution errors.

When a task fails, the error handler:
1. Classifies the error severity
2. Checks for known solutions in memory
3. Decides whether to retry, replan, or escalate
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from memory.errors import ErrorTracker


class ErrorSeverity(Enum):
    LOW = "low"         # Can auto-fix (syntax error, typo)
    MEDIUM = "medium"   # Needs replanning (wrong approach)
    HIGH = "high"       # Needs human input (permissions, missing info)
    CRITICAL = "critical"  # Stop everything


class RecoveryAction(Enum):
    RETRY = "retry"
    REPLAN = "replan"
    ESCALATE = "escalate"
    SKIP = "skip"


@dataclass
class ErrorAnalysis:
    severity: ErrorSeverity
    action: RecoveryAction
    known_solution: Optional[str]
    message: str


class ErrorHandler:
    """
    Handles errors during task execution.

    Learns from errors to improve future recovery.
    """

    def __init__(self, error_tracker: ErrorTracker):
        self.error_tracker = error_tracker
        self.error_history = []

    def analyze(self, error_message: str, task_attempts: int) -> ErrorAnalysis:
        """
        Analyze an error and determine recovery action.
        """
        # Record the error
        self.error_history.append({
            "error": error_message,
            "attempts": task_attempts
        })

        # Check for known solution
        known_solution = self.error_tracker.get_solution(error_message)

        # Classify severity
        severity = self._classify_severity(error_message)

        # Determine action
        action = self._determine_action(severity, task_attempts, known_solution)

        return ErrorAnalysis(
            severity=severity,
            action=action,
            known_solution=known_solution,
            message=error_message
        )

    def record_error(self, error_type: str, description: str,
                     cause: str, solution: str):
        """Record a new error pattern for future reference."""
        self.error_tracker.record(error_type, description, cause, solution)

    def _classify_severity(self, error_message: str) -> ErrorSeverity:
        """Classify error severity based on the message."""
        error_lower = error_message.lower()

        # Critical errors
        if any(w in error_lower for w in ["permission denied", "access denied", "fatal"]):
            return ErrorSeverity.CRITICAL

        # High severity
        if any(w in error_lower for w in ["not found", "missing", "no such file"]):
            return ErrorSeverity.HIGH
        if "connection" in error_lower or "timeout" in error_lower:
            return ErrorSeverity.HIGH

        # Medium severity
        if any(w in error_lower for w in ["syntax", "parse", "invalid"]):
            return ErrorSeverity.MEDIUM
        if "type" in error_lower or "attribute" in error_lower:
            return ErrorSeverity.MEDIUM

        # Low severity (default)
        return ErrorSeverity.LOW

    def _determine_action(self, severity: ErrorSeverity,
                          attempts: int,
                          known_solution: Optional[str]) -> RecoveryAction:
        """Determine what to do based on severity and history."""
        # If we have a known solution and haven't tried too many times
        if known_solution and attempts < 3:
            return RecoveryAction.RETRY

        # Low severity — retry
        if severity == ErrorSeverity.LOW and attempts < 3:
            return RecoveryAction.RETRY

        # Medium severity — replan after 2 attempts
        if severity == ErrorSeverity.MEDIUM:
            if attempts < 2:
                return RecoveryAction.RETRY
            return RecoveryAction.REPLAN

        # High severity — escalate
        if severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL):
            return RecoveryAction.ESCALATE

        # Default — skip if too many attempts
        if attempts >= 3:
            return RecoveryAction.SKIP

        return RecoveryAction.RETRY
