"""
Progress Tracker — monitors execution progress.

Tracks:
- Tasks completed vs pending
- Time spent
- Error rate
- Overall completion percentage
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from planning.decomposer import Task


@dataclass
class ProgressSnapshot:
    total_tasks: int
    completed: int
    failed: int
    pending: int
    in_progress: int
    completion_percent: float
    error_rate: float
    elapsed_seconds: float


class ProgressTracker:
    """
    Tracks and reports execution progress.
    """

    def __init__(self):
        self.start_time: Optional[float] = None
        self.task_timings: Dict[str, float] = {}

    def start(self):
        """Start tracking progress."""
        import time
        self.start_time = time.time()

    def snapshot(self, tasks: List[Task]) -> ProgressSnapshot:
        """Take a snapshot of current progress."""
        import time

        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == "completed")
        failed = sum(1 for t in tasks if t.status == "failed")
        in_progress = sum(1 for t in tasks if t.status == "in_progress")
        pending = total - completed - failed - in_progress

        completion = (completed / total * 100) if total > 0 else 0
        error_rate = (failed / (completed + failed) * 100) if (completed + failed) > 0 else 0

        elapsed = 0.0
        if self.start_time:
            elapsed = time.time() - self.start_time

        return ProgressSnapshot(
            total_tasks=total,
            completed=completed,
            failed=failed,
            pending=pending,
            in_progress=in_progress,
            completion_percent=completion,
            error_rate=error_rate,
            elapsed_seconds=elapsed
        )

    def is_complete(self, tasks: List[Task]) -> bool:
        """Check if all tasks are done (completed or failed)."""
        return all(t.status in ("completed", "failed") for t in tasks)

    def has_failures(self, tasks: List[Task]) -> bool:
        """Check if any tasks have failed."""
        return any(t.status == "failed" for t in tasks)

    def get_failed_tasks(self, tasks: List[Task]) -> List[Task]:
        """Get all failed tasks."""
        return [t for t in tasks if t.status == "failed"]

    def summary(self, tasks: List[Task]) -> str:
        """Get a human-readable summary of progress."""
        snap = self.snapshot(tasks)
        return (
            f"Progress: {snap.completed}/{snap.total_tasks} tasks "
            f"({snap.completion_percent:.0f}%) | "
            f"Failed: {snap.failed} | "
            f"Time: {snap.elapsed_seconds:.1f}s"
        )
