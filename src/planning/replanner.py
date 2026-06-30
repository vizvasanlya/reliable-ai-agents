"""
Replanner — adjusts plans when things go wrong.

When a task fails or new information changes the approach,
the replanner creates a new plan that:
- Keeps completed work
- Addresses the failure
- Adjusts remaining tasks
"""

from typing import List, Optional

from .decomposer import Task


class Replanner:
    """
    Adjusts execution plans based on failures and new information.
    """

    def replan_on_failure(self, tasks: List[Task],
                          failed_task: Task,
                          error_message: str) -> List[Task]:
        """
        Create a new plan after a task failure.

        Strategy:
        1. Keep completed tasks as-is
        2. Add an investigation task if needed
        3. Remove tasks that depend on the failed task
        4. Adjust remaining tasks based on the error
        """
        new_tasks = []
        failed_id = failed_task.id

        for task in tasks:
            if task.status == "completed":
                # Keep completed tasks
                new_tasks.append(task)
            elif task.id == failed_id:
                # Replace failed task with investigation
                new_tasks.append(Task(
                    id=f"{failed_id}_investigate",
                    description=f"Investigate failure: {failed_task.description}",
                    tools_needed=["read_file", "grep"],
                    acceptance_criteria=[
                        f"Root cause of '{error_message}' identified"
                    ],
                    estimated_minutes=5
                ))
            elif failed_id in task.dependencies:
                # Task depends on failed task — skip or restructure
                # For now, remove it (will be re-added after investigation)
                pass
            else:
                # Independent task — keep it
                new_tasks.append(task)

        return new_tasks

    def replan_on_discovery(self, tasks: List[Task],
                            new_information: str) -> List[Task]:
        """
        Adjust plan based on new information discovered during execution.

        For example, discovering the project uses a different framework
        than expected.
        """
        # For now, keep existing tasks but note the new information
        # A production version would use LLM reasoning here
        return tasks

    def simplify(self, tasks: List[Task]) -> List[Task]:
        """
        Simplify a plan by removing unnecessary tasks.

        Removes:
        - Tasks that are already completed
        - Tasks with too many failed attempts
        """
        return [
            t for t in tasks
            if t.status != "completed" and t.attempts < 3
        ]
