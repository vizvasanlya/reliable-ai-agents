"""
Queue System — handles multiple concurrent tasks.

Features:
1. Priority queue (urgent tasks first)
2. Concurrent processing (configurable workers)
3. Task dependencies
4. Progress tracking
"""

import os
import json
import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from queue import Queue, PriorityQueue


class TaskPriority(Enum):
    LOW = 3
    MEDIUM = 2
    HIGH = 1
    URGENT = 0


@dataclass
class QueuedTask:
    id: str
    request: str
    project_path: str
    priority: TaskPriority
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def __lt__(self, other):
        return self.priority.value < other.priority.value


class TaskQueue:
    """
    Priority-based task queue with concurrent processing.
    """

    def __init__(self, max_workers: int = 2, storage_dir: str = ".agent-tasks"):
        self.max_workers = max_workers
        self.storage_dir = storage_dir
        self.queue = PriorityQueue()
        self.tasks: Dict[str, QueuedTask] = {}
        self.workers: List[threading.Thread] = []
        self.running = False
        self._lock = threading.Lock()

        # Ensure directories exist
        for subdir in ['pending', 'running', 'completed', 'failed', 'queue']:
            os.makedirs(os.path.join(storage_dir, subdir), exist_ok=True)

    def add(self, task_id: str, request: str, project_path: str,
            priority: TaskPriority = TaskPriority.MEDIUM) -> QueuedTask:
        """Add a task to the queue."""
        task = QueuedTask(
            id=task_id,
            request=request,
            project_path=project_path,
            priority=priority
        )

        with self._lock:
            self.tasks[task_id] = task
            self.queue.put(task)

        # Save to disk
        self._save_task(task, "queue")

        return task

    def start(self, processor: Callable):
        """Start processing tasks with workers."""
        self.running = True

        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(processor, i),
                daemon=True
            )
            worker.start()
            self.workers.append(worker)

    def stop(self):
        """Stop all workers."""
        self.running = False
        for worker in self.workers:
            worker.join(timeout=5)
        self.workers.clear()

    def get_status(self) -> Dict:
        """Get queue status."""
        with self._lock:
            return {
                "pending": sum(1 for t in self.tasks.values() if t.status == "pending"),
                "running": sum(1 for t in self.tasks.values() if t.status == "running"),
                "completed": sum(1 for t in self.tasks.values() if t.status == "completed"),
                "failed": sum(1 for t in self.tasks.values() if t.status == "failed"),
                "total": len(self.tasks),
                "queue_size": self.queue.qsize()
            }

    def get_task(self, task_id: str) -> Optional[QueuedTask]:
        """Get a specific task."""
        return self.tasks.get(task_id)

    def _worker_loop(self, processor: Callable, worker_id: int):
        """Worker thread that processes tasks."""
        while self.running:
            try:
                # Get next task from queue (non-blocking)
                try:
                    task = self.queue.get(timeout=1)
                except:
                    continue

                # Process the task
                with self._lock:
                    task.status = "running"
                    task.started_at = datetime.now().isoformat()

                self._save_task(task, "running")

                try:
                    result = processor(task)
                    task.status = "completed"
                    task.result = result
                    task.completed_at = datetime.now().isoformat()
                    self._save_task(task, "completed")
                except Exception as e:
                    task.status = "failed"
                    task.error = str(e)
                    self._save_task(task, "failed")

                self.queue.task_done()

            except Exception as e:
                time.sleep(1)

    def _save_task(self, task: QueuedTask, subdir: str):
        """Save task to disk."""
        task_file = os.path.join(self.storage_dir, subdir, f"{task.id}.json")
        with open(task_file, 'w') as f:
            json.dump({
                "id": task.id,
                "request": task.request,
                "project_path": task.project_path,
                "priority": task.priority.name,
                "status": task.status,
                "result": task.result,
                "error": task.error,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at
            }, f, indent=2)


class SimpleQueue:
    """
    Simple file-based queue for single-worker processing.
    """

    def __init__(self, storage_dir: str = ".agent-tasks"):
        self.storage_dir = storage_dir
        for subdir in ['pending', 'completed', 'failed']:
            os.makedirs(os.path.join(storage_dir, subdir), exist_ok=True)

    def add(self, task_id: str, request: str, project_path: str) -> str:
        """Add a task to the queue."""
        task_file = os.path.join(self.storage_dir, "pending", f"{task_id}.json")
        with open(task_file, 'w') as f:
            json.dump({
                "id": task_id,
                "request": request,
                "project_path": project_path,
                "status": "pending",
                "created_at": datetime.now().isoformat()
            }, f, indent=2)
        return task_id

    def get_pending(self) -> List[Dict]:
        """Get all pending tasks."""
        pending_dir = os.path.join(self.storage_dir, "pending")
        tasks = []
        for f in os.listdir(pending_dir):
            if f.endswith('.json'):
                with open(os.path.join(pending_dir, f)) as file:
                    tasks.append(json.load(file))
        return sorted(tasks, key=lambda x: x.get('created_at', ''))

    def complete(self, task_id: str, result: str):
        """Mark task as completed."""
        src = os.path.join(self.storage_dir, "pending", f"{task_id}.json")
        dst = os.path.join(self.storage_dir, "completed", f"{task_id}.json")
        if os.path.exists(src):
            with open(src) as f:
                task = json.load(f)
            task["status"] = "completed"
            task["result"] = result
            task["completed_at"] = datetime.now().isoformat()
            with open(dst, 'w') as f:
                json.dump(task, f, indent=2)
            os.remove(src)

    def fail(self, task_id: str, error: str):
        """Mark task as failed."""
        src = os.path.join(self.storage_dir, "pending", f"{task_id}.json")
        dst = os.path.join(self.storage_dir, "failed", f"{task_id}.json")
        if os.path.exists(src):
            with open(src) as f:
                task = json.load(f)
            task["status"] = "failed"
            task["error"] = error
            with open(dst, 'w') as f:
                json.dump(task, f, indent=2)
            os.remove(src)
