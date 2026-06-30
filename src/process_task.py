#!/usr/bin/env python3
"""
Process pending tasks — with self-correction and real learning.
"""

import os
import sys
import json
import time
import subprocess
import re

sys.path.insert(0, os.path.dirname(__file__))

from llm.provider import OpenCodeZenProvider
from agent.self_correction import SelfCorrectionLoop
from agent.learning import LearningSystem
from verification.syntax import SyntaxChecker
from memory.store import MemoryStore


TASKS_DIR = ".agent-tasks"


def log(msg):
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}")


def process_pending_tasks():
    """Process all pending tasks with self-correction."""
    api_key = os.environ.get("ZEN_API_KEY")
    if not api_key:
        print("ERROR: Set ZEN_API_KEY")
        return

    # Initialize components
    provider = OpenCodeZenProvider(api_key=api_key, model="big-pickle")
    memory = MemoryStore()
    learning = LearningSystem()
    checker = SyntaxChecker()

    # Create self-correction loop
    corrector = SelfCorrectionLoop(
        llm_provider=provider,
        memory_store=memory,
        max_attempts=5
    )

    pending_dir = os.path.join(TASKS_DIR, "pending")
    tasks = [f for f in os.listdir(pending_dir) if f.endswith('.json')]

    for task_file in tasks:
        task_path = os.path.join(pending_dir, task_file)

        with open(task_path) as f:
            task = json.load(f)

        print(f"\n{'='*60}")
        print(f"PROCESSING: {task['id']}")
        print(f"Request: {task['request']}")
        print(f"{'='*60}")

        # Update status
        task["status"] = "in_progress"
        with open(task_path, 'w') as f:
            json.dump(task, f, indent=2)

        project_path = task.get("project_path", ".")
        os.makedirs(project_path, exist_ok=True)

        # Get pre-generation rules from learning
        rules = learning.get_pre_generation_rules(task.get("language", "python"))
        if rules:
            log(f"Applying {len(rules)} learned rules")

        # Run self-correction loop
        log("Starting autonomous generation with self-correction...")
        result = corrector.generate_and_fix(
            request=task["request"],
            project_path=project_path,
            language=task.get("language", "python")
        )

        # Record what worked
        if result.success:
            learning.learn_from_success(
                result.final_code,
                task["request"],
                task.get("language", "python")
            )
            log(f"SUCCESS after {result.total_fixes} fix(es)")
        else:
            log(f"FAILED after {len(result.attempts)} attempts")

        # Record lessons learned
        for lesson in result.learned_lessons:
            learning.learn_from_error(
                error_message=lesson,
                fix=lesson,
                language=task.get("language", "python")
            )

        # Mark task complete
        task["status"] = "completed" if result.success else "failed"
        task["result"] = {
            "success": result.success,
            "attempts": len(result.attempts),
            "fixes": result.total_fixes,
            "lessons": result.learned_lessons
        }
        task["confidence"] = 1.0 if result.success else 0.3
        task["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        # Move to appropriate directory
        if result.success:
            dest_dir = os.path.join(TASKS_DIR, "completed")
        else:
            dest_dir = os.path.join(TASKS_DIR, "failed")

        dest_path = os.path.join(dest_dir, task_file)
        with open(dest_path, 'w') as f:
            json.dump(task, f, indent=2)
        os.remove(task_path)

        # Print summary
        print(f"\n{'='*60}")
        print(f"RESULT: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Attempts: {len(result.attempts)}")
        print(f"Fixes applied: {result.total_fixes}")
        print(f"Lessons learned: {len(result.learned_lessons)}")
        print(f"Learning stats: {learning.get_stats()}")
        print(f"{'='*60}")


if __name__ == "__main__":
    process_pending_tasks()
