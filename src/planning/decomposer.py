"""
Task Decomposer — breaks goals into atomic, executable tasks.

Each task is:
- Small enough to complete in one step
- Has clear acceptance criteria
- Knows what tools it needs
- Has estimated effort
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Task:
    id: str
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed
    dependencies: List[str] = field(default_factory=list)
    tools_needed: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    estimated_minutes: int = 5
    result: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0


class TaskDecomposer:
    """
    Breaks down goals into concrete, executable tasks.

    Each task follows the SMART principle:
    - Specific (clear description)
    - Measurable (acceptance criteria)
    - Achievable (one step)
    - Relevant (contributes to goal)
    - Time-bound (estimated duration)
    """

    def decompose(self, action: str, target: str,
                  constraints: List[str]) -> List[Task]:
        """
        Create a task list based on the action and target.
        """
        tasks = []
        task_num = [0]

        def next_id():
            task_num[0] += 1
            return f"T{task_num[0]}"

        # Get language/framework from constraints
        language = self._get_constraint(constraints, "language", "python")
        framework = self._get_constraint(constraints, "framework", None)

        if action == "create":
            tasks.extend(self._decompose_create(next_id, target, language, framework))
        elif action == "fix":
            tasks.extend(self._decompose_fix(next_id, target))
        elif action == "refactor":
            tasks.extend(self._decompose_refactor(next_id, target))
        elif action == "research":
            tasks.extend(self._decompose_research(next_id, target))
        elif action == "test":
            tasks.extend(self._decompose_test(next_id, target))
        else:
            tasks.append(Task(
                id=next_id(),
                description=f"Complete the requested task: {target}",
                acceptance_criteria=["Task completed successfully"],
                tools_needed=["read_file", "write_file"]
            ))

        return tasks

    def _decompose_create(self, next_id, target, language, framework):
        """Decompose a creation task."""
        tasks = []

        # Planning phase
        tasks.append(Task(
            id=next_id(),
            description=f"Plan {target} implementation",
            tools_needed=["read_file"],
            acceptance_criteria=[
                "Implementation approach defined",
                "File structure planned"
            ],
            estimated_minutes=5
        ))

        # Implementation phase
        if target == "api":
            tasks.append(Task(
                id=next_id(),
                description=f"Implement {target} endpoints",
                dependencies=[tasks[0].id],
                tools_needed=["write_file", "read_file"],
                acceptance_criteria=[
                    "All endpoints implemented",
                    "Request/response handling working"
                ],
                estimated_minutes=15
            ))
        elif target == "ui":
            tasks.append(Task(
                id=next_id(),
                description=f"Implement {target} components",
                dependencies=[tasks[0].id],
                tools_needed=["write_file"],
                acceptance_criteria=[
                    "All components created",
                    "Components render correctly"
                ],
                estimated_minutes=15
            ))
        else:
            tasks.append(Task(
                id=next_id(),
                description=f"Implement {target}",
                dependencies=[tasks[0].id],
                tools_needed=["write_file", "read_file"],
                acceptance_criteria=["Implementation complete"],
                estimated_minutes=10
            ))

        # Verification phase
        tasks.append(Task(
            id=next_id(),
            description=f"Verify {target} works correctly",
            dependencies=[tasks[1].id],
            tools_needed=["run_command"],
            acceptance_criteria=[
                "Code runs without errors",
                "Basic functionality works"
            ],
            estimated_minutes=5
        ))

        return tasks

    def _decompose_fix(self, next_id, target):
        """Decompose a fix task."""
        return [
            Task(
                id=next_id(),
                description="Reproduce the issue",
                tools_needed=["read_file", "run_command"],
                acceptance_criteria=["Issue is reproducible"],
                estimated_minutes=3
            ),
            Task(
                id=next_id(),
                description="Identify root cause",
                dependencies=["T1"],
                tools_needed=["read_file", "grep"],
                acceptance_criteria=["Root cause identified"],
                estimated_minutes=5
            ),
            Task(
                id=next_id(),
                description="Implement fix",
                dependencies=["T2"],
                tools_needed=["edit_file"],
                acceptance_criteria=["Fix applied"],
                estimated_minutes=5
            ),
            Task(
                id=next_id(),
                description="Verify fix works",
                dependencies=["T3"],
                tools_needed=["run_command"],
                acceptance_criteria=["Issue resolved", "No regressions"],
                estimated_minutes=3
            ),
        ]

    def _decompose_refactor(self, next_id, target):
        """Decompose a refactor task."""
        return [
            Task(
                id=next_id(),
                description="Analyze current structure",
                tools_needed=["read_file", "glob"],
                acceptance_criteria=["Structure understood"],
                estimated_minutes=5
            ),
            Task(
                id=next_id(),
                description="Plan refactoring approach",
                dependencies=["T1"],
                tools_needed=[],
                acceptance_criteria=["Approach defined"],
                estimated_minutes=5
            ),
            Task(
                id=next_id(),
                description="Execute refactoring",
                dependencies=["T2"],
                tools_needed=["edit_file", "read_file"],
                acceptance_criteria=["Code restructured"],
                estimated_minutes=15
            ),
            Task(
                id=next_id(),
                description="Verify no regressions",
                dependencies=["T3"],
                tools_needed=["run_command"],
                acceptance_criteria=["All tests pass"],
                estimated_minutes=5
            ),
        ]

    def _decompose_research(self, next_id, target):
        """Decompose a research task."""
        return [
            Task(
                id=next_id(),
                description=f"Research {target}",
                tools_needed=["read_file", "grep"],
                acceptance_criteria=["Key information gathered"],
                estimated_minutes=10
            ),
            Task(
                id=next_id(),
                description="Document findings",
                dependencies=["T1"],
                tools_needed=["write_file"],
                acceptance_criteria=["Findings documented"],
                estimated_minutes=5
            ),
        ]

    def _decompose_test(self, next_id, target):
        """Decompose a testing task."""
        return [
            Task(
                id=next_id(),
                description=f"Write tests for {target}",
                tools_needed=["read_file", "write_file"],
                acceptance_criteria=["Tests written"],
                estimated_minutes=10
            ),
            Task(
                id=next_id(),
                description="Run tests",
                dependencies=["T1"],
                tools_needed=["run_command"],
                acceptance_criteria=["All tests pass"],
                estimated_minutes=3
            ),
        ]

    def _get_constraint(self, constraints, key, default):
        """Extract a constraint value."""
        for c in constraints:
            if c.startswith(f"{key}:"):
                return c.split(":", 1)[1]
        return default
