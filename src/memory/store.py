"""
Memory Store — persistent key-value storage with metadata.

Memories survive across sessions. Each entry has:
- A key (for lookup)
- A value (the actual memory)
- A category (decision, error, pattern, preference, context)
- A timestamp
- Optional project association
- A confidence score (decreases if contradicted)
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MemoryEntry:
    key: str
    value: Any
    category: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    project_id: Optional[str] = None
    confidence: float = 1.0
    tags: List[str] = field(default_factory=list)


class MemoryStore:
    """
    Persistent memory storage backed by JSON files.

    Memories are organized by category and can be searched,
    updated, and retrieved across sessions.
    """

    def __init__(self, storage_dir: str = ".agent-memory"):
        self.storage_dir = storage_dir
        self.entries: Dict[str, MemoryEntry] = {}
        self._load()

    def _load(self):
        """Load memories from disk."""
        os.makedirs(self.storage_dir, exist_ok=True)
        path = os.path.join(self.storage_dir, "memories.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for key, val in data.items():
                    self.entries[key] = MemoryEntry(**val)

    def _save(self):
        """Persist memories to disk."""
        os.makedirs(self.storage_dir, exist_ok=True)
        path = os.path.join(self.storage_dir, "memories.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(
                {k: asdict(v) for k, v in self.entries.items()},
                f, indent=2
            )

    def store(self, key: str, value: Any, category: str,
              project_id: Optional[str] = None,
              tags: Optional[List[str]] = None,
              confidence: float = 1.0) -> MemoryEntry:
        """
        Store a memory entry.

        If the key already exists, the new entry overwrites it
        with a timestamp update.
        """
        entry = MemoryEntry(
            key=key,
            value=value,
            category=category,
            project_id=project_id,
            tags=tags or [],
            confidence=confidence
        )
        self.entries[key] = entry
        self._save()
        return entry

    def get(self, key: str) -> Optional[MemoryEntry]:
        """Retrieve a memory by key."""
        return self.entries.get(key)

    def get_value(self, key: str) -> Optional[Any]:
        """Retrieve just the value of a memory."""
        entry = self.entries.get(key)
        return entry.value if entry else None

    def delete(self, key: str) -> bool:
        """Delete a memory entry."""
        if key in self.entries:
            del self.entries[key]
            self._save()
            return True
        return False

    def search(self, query: str, category: Optional[str] = None,
               project_id: Optional[str] = None,
               tags: Optional[List[str]] = None,
               min_confidence: float = 0.0) -> List[MemoryEntry]:
        """
        Search memories by keyword and filters.

        Simple substring matching across key, value, and tags.
        """
        results = []
        query_lower = query.lower()

        for entry in self.entries.values():
            # Apply filters
            if category and entry.category != category:
                continue
            if project_id and entry.project_id != project_id:
                continue
            if tags and not any(t in entry.tags for t in tags):
                continue
            if entry.confidence < min_confidence:
                continue

            # Check if query matches
            searchable = f"{entry.key} {str(entry.value)} {' '.join(entry.tags)}".lower()
            if query_lower in searchable:
                results.append(entry)

        return results

    def list_by_category(self, category: str) -> List[MemoryEntry]:
        """List all memories in a category."""
        return [e for e in self.entries.values() if e.category == category]

    def list_by_project(self, project_id: str) -> List[MemoryEntry]:
        """List all memories for a project."""
        return [e for e in self.entries.values() if e.project_id == project_id]

    def update_confidence(self, key: str, new_confidence: float) -> bool:
        """Update the confidence score of a memory."""
        entry = self.entries.get(key)
        if entry:
            entry.confidence = max(0.0, min(1.0, new_confidence))
            self._save()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        categories = {}
        projects = {}
        for entry in self.entries.values():
            categories[entry.category] = categories.get(entry.category, 0) + 1
            if entry.project_id:
                projects[entry.project_id] = projects.get(entry.project_id, 0) + 1

        return {
            "total_entries": len(self.entries),
            "by_category": categories,
            "by_project": projects,
            "avg_confidence": (
                sum(e.confidence for e in self.entries.values()) / len(self.entries)
                if self.entries else 0
            )
        }
