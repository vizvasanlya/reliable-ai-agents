"""
Error Tracker — learns from mistakes to avoid repeating them.

When an error occurs, the tracker:
1. Checks if it matches a known pattern
2. If yes, suggests the stored solution
3. If no, records the new error for future reference
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class ErrorPattern:
    error_type: str
    description: str
    cause: str
    solution: str
    occurrences: int = 1
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)


class ErrorTracker:
    """
    Tracks error patterns and their solutions.

    Goal: never make the same mistake twice.
    """

    def __init__(self, storage_dir: str = ".agent-memory"):
        self.storage_dir = storage_dir
        self.patterns: Dict[str, ErrorPattern] = {}
        self._load()

    def _load(self):
        """Load error patterns from disk."""
        os.makedirs(self.storage_dir, exist_ok=True)
        path = os.path.join(self.storage_dir, "errors.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for key, val in data.items():
                    self.patterns[key] = ErrorPattern(**val)

    def _save(self):
        """Persist error patterns to disk."""
        os.makedirs(self.storage_dir, exist_ok=True)
        path = os.path.join(self.storage_dir, "errors.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(
                {k: asdict(v) for k, v in self.patterns.items()},
                f, indent=2
            )

    def record(self, error_type: str, description: str,
               cause: str, solution: str,
               tags: Optional[List[str]] = None):
        """
        Record an error pattern.

        If this error type already exists, increment the count
        and update the last_seen timestamp.
        """
        if error_type in self.patterns:
            pattern = self.patterns[error_type]
            pattern.occurrences += 1
            pattern.last_seen = datetime.now().isoformat()
            # Update solution if a better one is found
            if solution and len(solution) > len(pattern.solution):
                pattern.solution = solution
        else:
            self.patterns[error_type] = ErrorPattern(
                error_type=error_type,
                description=description,
                cause=cause,
                solution=solution,
                tags=tags or []
            )

        self._save()

    def find(self, error_message: str) -> Optional[ErrorPattern]:
        """
        Check if an error matches a known pattern.

        Searches for the error type in the message.
        Returns the pattern if found, None otherwise.
        """
        error_lower = error_message.lower()

        # First try exact error type match
        for pattern in self.patterns.values():
            if pattern.error_type.lower() in error_lower:
                return pattern

        # Then try tag matching
        for pattern in self.patterns.values():
            for tag in pattern.tags:
                if tag.lower() in error_lower:
                    return pattern

        return None

    def get_solution(self, error_message: str) -> Optional[str]:
        """Get the stored solution for an error, if known."""
        pattern = self.find(error_message)
        return pattern.solution if pattern else None

    def get_all(self) -> List[ErrorPattern]:
        """Get all recorded error patterns."""
        return list(self.patterns.values())

    def get_most_common(self, limit: int = 10) -> List[ErrorPattern]:
        """Get the most frequently occurring errors."""
        sorted_patterns = sorted(
            self.patterns.values(),
            key=lambda p: p.occurrences,
            reverse=True
        )
        return sorted_patterns[:limit]

    def delete(self, error_type: str) -> bool:
        """Delete an error pattern."""
        if error_type in self.patterns:
            del self.patterns[error_type]
            self._save()
            return True
        return False

    def get_stats(self) -> Dict:
        """Get error tracking statistics."""
        if not self.patterns:
            return {"total_patterns": 0}

        total_occurrences = sum(p.occurrences for p in self.patterns.values())

        return {
            "total_patterns": len(self.patterns),
            "total_occurrences": total_occurrences,
            "most_common": self.get_most_common(3)
        }
