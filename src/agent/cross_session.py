"""
Cross-Session Learning — persists and applies lessons across sessions.

Unlike basic memory, this system:
1. Tracks which lessons actually work
2. Applies lessons BEFORE generating code
3. Improves over time automatically
"""

import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CrossSessionLesson:
    id: str
    trigger: str          # When to apply this lesson
    rule: str             # What to do
    language: str
    times_applied: int = 0
    times_helped: int = 0
    last_applied: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class CrossSessionLearning:
    """
    Learning that persists and improves across sessions.
    """

    def __init__(self, storage_dir: str = ".agent-memory"):
        self.storage_dir = storage_dir
        self.lessons: Dict[str, CrossSessionLesson] = {}
        self.project_lessons: Dict[str, List[str]] = {}  # project -> lesson_ids
        self._load()

    def _load(self):
        """Load lessons from disk."""
        os.makedirs(self.storage_dir, exist_ok=True)

        lessons_file = os.path.join(self.storage_dir, "cross_session_lessons.json")
        if os.path.exists(lessons_file):
            with open(lessons_file, 'r') as f:
                data = json.load(f)
                for key, val in data.items():
                    self.lessons[key] = CrossSessionLesson(**val)

        projects_file = os.path.join(self.storage_dir, "project_lessons.json")
        if os.path.exists(projects_file):
            with open(projects_file, 'r') as f:
                self.project_lessons = json.load(f)

    def _save(self):
        """Persist lessons to disk."""
        os.makedirs(self.storage_dir, exist_ok=True)

        lessons_file = os.path.join(self.storage_dir, "cross_session_lessons.json")
        with open(lessons_file, 'w') as f:
            json.dump(
                {k: vars(v) for k, v in self.lessons.items()},
                f, indent=2
            )

        projects_file = os.path.join(self.storage_dir, "project_lessons.json")
        with open(projects_file, 'w') as f:
            json.dump(self.project_lessons, f, indent=2)

    def learn(self, error: str, fix: str, language: str,
              project_id: Optional[str] = None):
        """Record a new lesson."""
        # Check if similar lesson exists
        for lesson in self.lessons.values():
            if lesson.rule == fix:
                lesson.times_applied += 1
                self._save()
                return

        # Create new lesson
        lesson_id = f"lesson_{len(self.lessons) + 1}"
        lesson = CrossSessionLesson(
            id=lesson_id,
            trigger=error[:100],
            rule=fix,
            language=language
        )

        self.lessons[lesson_id] = lesson

        # Associate with project
        if project_id:
            if project_id not in self.project_lessons:
                self.project_lessons[project_id] = []
            if lesson_id not in self.project_lessons[project_id]:
                self.project_lessons[project_id].append(lesson_id)

        self._save()

    def apply_before_generation(self, request: str, language: str,
                                 project_id: Optional[str] = None) -> List[str]:
        """
        Get lessons to apply BEFORE generating code.

        Returns list of rules to include in the prompt.
        """
        rules = []

        # Get language-specific lessons
        for lesson in self.lessons.values():
            if lesson.language == language and lesson.times_helped > 0:
                rules.append(lesson.rule)

        # Get project-specific lessons
        if project_id and project_id in self.project_lessons:
            for lid in self.project_lessons[project_id]:
                if lid in self.lessons:
                    lesson = self.lessons[lid]
                    if lesson.rule not in rules:
                        rules.append(lesson.rule)

        # Sort by effectiveness
        rules.sort(key=lambda r: self._get_help_count(r), reverse=True)

        return rules[:10]  # Top 10 rules

    def record_success(self, lesson_id: str):
        """Record that a lesson helped."""
        if lesson_id in self.lessons:
            self.lessons[lesson_id].times_helped += 1
            self.lessons[lesson_id].last_applied = datetime.now().isoformat()
            self._save()

    def get_stats(self) -> Dict:
        """Get learning statistics."""
        total = len(self.lessons)
        effective = sum(1 for l in self.lessons.values() if l.times_helped > 0)

        return {
            "total_lessons": total,
            "effective_lessons": effective,
            "effectiveness_rate": f"{(effective/total*100):.0f}%" if total > 0 else "N/A",
            "projects_tracked": len(self.project_lessons)
        }

    def _get_help_count(self, rule: str) -> int:
        """Count how many times a rule has helped."""
        count = 0
        for lesson in self.lessons.values():
            if lesson.rule == rule:
                count += lesson.times_helped
        return count
