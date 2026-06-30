"""
Task Scheduler — orders tasks and detects parallelism.

Determines:
- Which tasks can run in parallel
- Which tasks must wait for others
- The optimal execution order
"""

from typing import Dict, List, Set, Tuple

from .decomposer import Task


class TaskScheduler:
    """
    Schedules tasks based on dependencies.

    Tasks with no dependencies can run immediately.
    Tasks with dependencies wait until their prerequisites complete.
    Independent tasks can run in parallel.
    """

    def schedule(self, tasks: List[Task]) -> List[List[Task]]:
        """
        Group tasks into execution waves.

        Each wave contains tasks that can run in parallel.
        Waves are ordered so dependencies are satisfied.
        """
        task_map = {t.id: t for t in tasks}
        completed: Set[str] = set()
        waves: List[List[Task]] = []

        while len(completed) < len(tasks):
            # Find tasks whose dependencies are all completed
            ready = []
            for task in tasks:
                if task.id in completed:
                    continue
                deps_met = all(d in completed for d in task.dependencies)
                if deps_met:
                    ready.append(task)

            if not ready:
                # Circular dependency or error — break the deadlock
                # by taking the next uncompleted task
                for task in tasks:
                    if task.id not in completed:
                        ready.append(task)
                        break

            if not ready:
                break

            waves.append(ready)
            for task in ready:
                completed.add(task.id)

        return waves

    def get_next_tasks(self, tasks: List[Task],
                       completed_ids: Set[str]) -> List[Task]:
        """
        Get tasks that are ready to execute now.

        A task is ready if:
        - It hasn't been completed or failed
        - All its dependencies are completed
        """
        ready = []
        for task in tasks:
            if task.id in completed_ids:
                continue
            if task.status == "failed":
                continue
            deps_met = all(d in completed_ids for d in task.dependencies)
            if deps_met:
                ready.append(task)
        return ready

    def get_critical_path(self, tasks: List[Task]) -> List[Task]:
        """
        Find the longest path through the task graph.

        This is the minimum time to complete all tasks
        (assuming unlimited parallelism).
        """
        task_map = {t.id: t for t in tasks}
        earliest_finish: Dict[str, int] = {}

        def compute_finish(task_id: str) -> int:
            if task_id in earliest_finish:
                return earliest_finish[task_id]

            task = task_map.get(task_id)
            if not task:
                return 0

            if not task.dependencies:
                earliest_finish[task_id] = task.estimated_minutes
            else:
                max_dep_finish = max(
                    compute_finish(d) for d in task.dependencies
                )
                earliest_finish[task_id] = max_dep_finish + task.estimated_minutes

            return earliest_finish[task_id]

        # Compute for all tasks
        for task in tasks:
            compute_finish(task.id)

        # Find the critical path (tasks that affect the total time)
        if not tasks:
            return []

        # Start from the task with the latest finish time
        max_finish_task = max(tasks, key=lambda t: earliest_finish.get(t.id, 0))

        # Trace back the critical path
        critical = [max_finish_task]
        current = max_finish_task

        while current.dependencies:
            # Find the dependency with the latest finish time
            dep_finishes = {
                d: earliest_finish.get(d, 0)
                for d in current.dependencies
            }
            latest_dep_id = max(dep_finishes, key=dep_finishes.get)
            latest_dep = task_map[latest_dep_id]
            critical.insert(0, latest_dep)
            current = latest_dep

        return critical

    def estimate_total_time(self, tasks: List[Task]) -> int:
        """
        Estimate total time considering parallelism.

        Returns the sum of wave durations (longest task in each wave).
        """
        waves = self.schedule(tasks)
        return sum(
            max(t.estimated_minutes for t in wave)
            for wave in waves
        )
