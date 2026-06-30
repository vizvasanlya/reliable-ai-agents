"""
Memory Retriever — finds relevant memories for the current task.

Combines MemoryStore, ErrorTracker, and SessionMemory to
provide a unified interface for memory retrieval.
"""

from typing import Dict, List, Optional, Any

from .store import MemoryStore, MemoryEntry
from .errors import ErrorTracker, ErrorPattern
from .session import SessionMemory


class MemoryRetriever:
    """
    Unified interface for retrieving relevant memories.

    Given a current task or error, this retrieves:
    - Past decisions about similar tasks
    - Known error patterns and solutions
    - Relevant project context
    - User preferences
    """

    def __init__(self, store: MemoryStore, errors: ErrorTracker,
                 session: SessionMemory):
        self.store = store
        self.errors = errors
        self.session = session

    def for_task(self, task_description: str,
                 project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve all relevant memories for a given task.

        Returns a dict with:
        - relevant_decisions: past decisions about similar work
        - known_errors: errors that might occur
        - preferences: user preferences that apply
        - context: session context
        """
        query = task_description.lower()

        # Find relevant decisions
        relevant_decisions = self.store.search(
            query,
            category="decision",
            project_id=project_id
        )

        # Find relevant patterns
        relevant_patterns = self.store.search(
            query,
            category="pattern",
            project_id=project_id
        )

        # Find user preferences
        preferences = self.store.search(query, category="preference")

        # Find project context
        context = []
        if project_id:
            context = self.store.list_by_project(project_id)

        return {
            "relevant_decisions": relevant_decisions,
            "relevant_patterns": relevant_patterns,
            "preferences": preferences,
            "context": context,
            "session_history": self.session.events[-10:]  # Last 10 events
        }

    def for_error(self, error_message: str) -> Optional[ErrorPattern]:
        """
        Check if an error matches a known pattern.

        Returns the pattern with solution if found, None otherwise.
        """
        return self.errors.find(error_message)

    def for_project(self, project_id: str) -> Dict[str, List]:
        """
        Get all memories for a specific project.
        """
        return {
            "decisions": self.store.list_by_project(project_id),
            "all": self.store.list_by_project(project_id)
        }

    def recent_decisions(self, limit: int = 5) -> List[MemoryEntry]:
        """Get the most recent decisions."""
        decisions = self.store.list_by_category("decision")
        return sorted(
            decisions,
            key=lambda x: x.timestamp,
            reverse=True
        )[:limit]

    def recent_errors(self, limit: int = 5) -> List[ErrorPattern]:
        """Get the most recent error patterns."""
        errors = self.errors.get_all()
        return sorted(
            errors,
            key=lambda x: x.last_seen,
            reverse=True
        )[:limit]

    def summary(self) -> Dict[str, Any]:
        """Get a summary of all available memories."""
        return {
            "store_stats": self.store.get_stats(),
            "error_stats": self.errors.get_stats(),
            "session_progress": self.session.get_progress_summary()
        }
