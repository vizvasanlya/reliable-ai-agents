"""
Session Memory — tracks what happens in the current session.

Unlike persistent memory, session memory is temporary and
covers only the current interaction. It's used for:
- Tracking progress within a session
- Maintaining context for multi-step tasks
- Storing intermediate results
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SessionEvent:
    event_type: str  # "action", "result", "error", "decision"
    description: str
    data: Any = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskProgress:
    task_id: str
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Any = None
    error: Optional[str] = None
    attempts: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class SessionMemory:
    """
    Tracks the current session's state and history.

    This is volatile — it resets when a new session starts.
    Use MemoryStore for persistent cross-session data.
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.events: List[SessionEvent] = []
        self.tasks: Dict[str, TaskProgress] = {}
        self.context: Dict[str, Any] = {}
        self.started_at = datetime.now().isoformat()

    def log_event(self, event_type: str, description: str, data: Any = None):
        """Log an event in the session."""
        self.events.append(SessionEvent(
            event_type=event_type,
            description=description,
            data=data
        ))

    def log_action(self, action: str, details: Any = None):
        """Log an action taken by the agent."""
        self.log_event("action", action, details)

    def log_result(self, action: str, result: Any):
        """Log the result of an action."""
        self.log_event("result", action, result)

    def log_error(self, action: str, error: str):
        """Log an error that occurred."""
        self.log_event("error", action, {"error": error})

    def log_decision(self, decision: str, reason: str):
        """Log a decision made by the agent."""
        self.log_event("decision", decision, {"reason": reason})

    def start_task(self, task_id: str, description: str) -> TaskProgress:
        """Start tracking a task."""
        task = TaskProgress(
            task_id=task_id,
            description=description,
            status="in_progress",
            started_at=datetime.now().isoformat()
        )
        self.tasks[task_id] = task
        self.log_action(f"Started task {task_id}: {description}")
        return task

    def complete_task(self, task_id: str, result: Any = None):
        """Mark a task as completed."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.now().isoformat()
            self.log_result(f"Completed task {task_id}", result)

    def fail_task(self, task_id: str, error: str):
        """Mark a task as failed."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = "failed"
            task.error = error
            task.attempts += 1
            self.log_error(f"Failed task {task_id}", error)

    def get_task(self, task_id: str) -> Optional[TaskProgress]:
        """Get progress of a specific task."""
        return self.tasks.get(task_id)

    def get_pending_tasks(self) -> List[TaskProgress]:
        """Get all pending tasks."""
        return [t for t in self.tasks.values() if t.status == "pending"]

    def get_completed_tasks(self) -> List[TaskProgress]:
        """Get all completed tasks."""
        return [t for t in self.tasks.values() if t.status == "completed"]

    def get_failed_tasks(self) -> List[TaskProgress]:
        """Get all failed tasks."""
        return [t for t in self.tasks.values() if t.status == "failed"]

    def set_context(self, key: str, value: Any):
        """Set a context value for the session."""
        self.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        return self.context.get(key, default)

    def get_progress_summary(self) -> Dict[str, Any]:
        """Get a summary of session progress."""
        total = len(self.tasks)
        completed = len(self.get_completed_tasks())
        failed = len(self.get_failed_tasks())
        pending = total - completed - failed

        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "progress_percent": (completed / total * 100) if total > 0 else 0,
            "events_count": len(self.events)
        }

    def save(self, path: Optional[str] = None):
        """Save session state to file."""
        if path is None:
            path = f".agent-memory/sessions/{self.session_id}.json"

        os.makedirs(os.path.dirname(path), exist_ok=True)

        data = {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "context": self.context,
            "tasks": {k: asdict(v) for k, v in self.tasks.items()},
            "events": [asdict(e) for e in self.events[-100:]]  # Keep last 100 events
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load(self, path: str):
        """Load session state from file."""
        if not os.path.exists(path):
            return

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.session_id = data["session_id"]
        self.started_at = data["started_at"]
        self.context = data.get("context", {})

        for task_id, task_data in data.get("tasks", {}).items():
            self.tasks[task_id] = TaskProgress(**task_data)

        for event_data in data.get("events", []):
            self.events.append(SessionEvent(**event_data))
