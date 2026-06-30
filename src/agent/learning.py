"""
Real Learning System — learns from every mistake and applies lessons.

Unlike simple memory storage, this system:
1. Records errors and their fixes
2. Detects patterns across failures
3. Applies lessons BEFORE generating new code
4. Builds a knowledge base that grows over time
"""

import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Lesson:
    id: str
    trigger: str      # What caused this lesson (error pattern)
    rule: str         # What to do instead
    language: str     # Programming language
    times_applied: int = 0
    times_helped: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class LearningSystem:
    """
    Real learning that grows over time.

    Tracks:
    - Error patterns and their fixes
    - Which fixes actually work
    - Rules to apply before code generation
    """

    def __init__(self, storage_dir: str = ".agent-memory"):
        self.storage_dir = storage_dir
        self.lessons: Dict[str, Lesson] = {}
        self.patterns: Dict[str, List[str]] = {}  # error_pattern -> [fixes]
        self._load()

    def _load(self):
        """Load lessons from disk."""
        os.makedirs(self.storage_dir, exist_ok=True)

        lessons_file = os.path.join(self.storage_dir, "lessons.json")
        if os.path.exists(lessons_file):
            with open(lessons_file, 'r') as f:
                data = json.load(f)
                for key, val in data.items():
                    self.lessons[key] = Lesson(**val)

        patterns_file = os.path.join(self.storage_dir, "patterns.json")
        if os.path.exists(patterns_file):
            with open(patterns_file, 'r') as f:
                self.patterns = json.load(f)

    def _save(self):
        """Persist lessons to disk."""
        os.makedirs(self.storage_dir, exist_ok=True)

        lessons_file = os.path.join(self.storage_dir, "lessons.json")
        with open(lessons_file, 'w') as f:
            json.dump(
                {k: vars(v) for k, v in self.lessons.items()},
                f, indent=2
            )

        patterns_file = os.path.join(self.storage_dir, "patterns.json")
        with open(patterns_file, 'w') as f:
            json.dump(self.patterns, f, indent=2)

    def learn_from_error(self, error_message: str, fix: str,
                         language: str = "python") -> Lesson:
        """
        Record a new lesson from an error and its fix.
        """
        # Create a pattern key from the error
        pattern = self._extract_pattern(error_message)
        lesson_id = f"lesson_{len(self.lessons) + 1}"

        lesson = Lesson(
            id=lesson_id,
            trigger=pattern,
            rule=fix,
            language=language
        )

        self.lessons[lesson_id] = lesson

        # Update pattern index
        if pattern not in self.patterns:
            self.patterns[pattern] = []
        if fix not in self.patterns[pattern]:
            self.patterns[pattern].append(fix)

        self._save()
        return lesson

    def learn_from_success(self, code: str, request: str,
                           language: str = "python"):
        """
        Extract patterns from successful code.
        """
        # Extract import patterns
        import re
        imports = re.findall(r'^(?:from|import)\s+.+', code, re.MULTILINE)

        if imports:
            lesson_id = f"success_{len(self.lessons) + 1}"
            lesson = Lesson(
                id=lesson_id,
                trigger=f"Code for: {request[:50]}",
                rule=f"Common imports: {', '.join(imports[:5])}",
                language=language,
                times_applied=1,
                times_helped=1
            )
            self.lessons[lesson_id] = lesson
            self._save()

    def get_relevant_fixes(self, error_message: str,
                           language: str = "python") -> List[str]:
        """
        Get fixes that are relevant to this error.
        """
        pattern = self._extract_pattern(error_message)

        fixes = []

        # Direct pattern match
        if pattern in self.patterns:
            fixes.extend(self.patterns[pattern])

        # Fuzzy match — check if any known pattern is in the error
        for known_pattern, known_fixes in self.patterns.items():
            if known_pattern in error_message.lower():
                fixes.extend(known_fixes)

        # Language-specific lessons
        for lesson in self.lessons.values():
            if lesson.language == language and lesson.times_helped > 0:
                if lesson.trigger.lower() in error_message.lower():
                    fixes.append(lesson.rule)

        return list(set(fixes))[:5]  # Return top 5 unique fixes

    def get_pre_generation_rules(self, language: str = "python") -> List[str]:
        """
        Get rules to apply BEFORE generating code.

        These are lessons learned from past mistakes that should
        be injected into the code generation prompt.
        """
        rules = []

        for lesson in self.lessons.values():
            if lesson.language == language and lesson.times_helped > 0:
                rules.append(lesson.rule)

        # Sort by effectiveness
        rules.sort(key=lambda r: self._count_helps(r), reverse=True)

        return rules[:10]  # Top 10 rules

    def record_fix_result(self, lesson_id: str, worked: bool):
        """Record whether a fix actually helped."""
        if lesson_id in self.lessons:
            lesson = self.lessons[lesson_id]
            lesson.times_applied += 1
            if worked:
                lesson.times_helped += 1
            self._save()

    def get_stats(self) -> Dict:
        """Get learning statistics."""
        total_lessons = len(self.lessons)
        total_patterns = len(self.patterns)
        effective = sum(1 for l in self.lessons.values() if l.times_helped > 0)

        return {
            "total_lessons": total_lessons,
            "total_patterns": total_patterns,
            "effective_fixes": effective,
            "effectiveness_rate": f"{(effective/total_lessons*100):.0f}%" if total_lessons > 0 else "N/A"
        }

    def _extract_pattern(self, error_message: str) -> str:
        """Extract a reusable pattern from an error message."""
        import re

        # Common patterns - using positional placeholders
        patterns = [
            (r"cannot import name '(\w+)'", "import_{0}"),
            (r"ModuleNotFoundError: No module named '(\w+)'", "missing_{0}"),
            (r"(\w+)Error: (.+)", "error_{0}"),
            (r"Line (\d+): (.+)", "syntax_line_{0}"),
            (r"unexpected EOF", "eof_error"),
            (r"unexpected indent", "indent_error"),
        ]

        for regex, template in patterns:
            match = re.search(regex, error_message)
            if match:
                try:
                    return template.format(*match.groups())
                except (IndexError, KeyError):
                    pass

        # Generic pattern
        return error_message[:50].lower().replace(" ", "_")

    def _count_helps(self, rule: str) -> int:
        """Count how many times a rule has helped."""
        count = 0
        for lesson in self.lessons.values():
            if lesson.rule == rule and lesson.times_helped > 0:
                count += lesson.times_helped
        return count
