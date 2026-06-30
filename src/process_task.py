#!/usr/bin/env python3
"""
Process pending tasks — with self-correction, learning, multi-file, and context.
"""

import os
import sys
import json
import time
import re

sys.path.insert(0, os.path.dirname(__file__))

from llm.provider import OpenCodeZenProvider
from agent.self_correction import SelfCorrectionLoop
from agent.learning import LearningSystem
from agent.cross_session import CrossSessionLearning
from agent.project_builder import ProjectBuilder
from agent.context import ContextReader
from agent.error_analyzer import ErrorAnalyzer
from verification.syntax import SyntaxChecker
from memory.store import MemoryStore


TASKS_DIR = ".agent-tasks"


def log(msg):
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}")


def process_pending_tasks():
    """Process all pending tasks with full features."""
    api_key = os.environ.get("ZEN_API_KEY")
    if not api_key:
        print("ERROR: Set ZEN_API_KEY")
        return

    # Initialize components
    provider = OpenCodeZenProvider(api_key=api_key, model="big-pickle")
    memory = MemoryStore()
    learning = LearningSystem()
    cross_session = CrossSessionLearning()
    context_reader = ContextReader(provider)
    project_builder = ProjectBuilder(provider)
    error_analyzer = ErrorAnalyzer()
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

        # Step 1: Read project context (if exists)
        log("Step 1: Reading project context...")
        context = context_reader.read_project(project_path)
        context_prompt = context_reader.get_context_prompt(context)
        log(f"  Found {len(context.files)} files, tech: {context.tech_stack}")

        # Step 2: Get cross-session lessons
        log("Step 2: Loading learned lessons...")
        project_id = task["id"]
        lessons = cross_session.apply_before_generation(
            task["request"],
            task.get("language", "python"),
            project_id
        )
        log(f"  Applying {len(lessons)} lessons")

        # Step 3: Build project structure (multi-file)
        log("Step 3: Planning project structure...")
        files = project_builder.build(
            task["request"],
            project_path,
            task.get("language", "python")
        )
        log(f"  Planned {len(files)} files:")
        for f in files:
            log(f"    - {f.path} ({len(f.content)} chars)")

        # Step 4: Write all files
        log("Step 4: Writing files...")
        project_builder.write_files(files, project_path)

        # Step 5: Verify syntax
        log("Step 5: Verifying syntax...")
        all_valid = True
        for f in files:
            if f.path.endswith('.py'):
                result = checker.check(f.content, "python")
                status = "PASS" if result.valid else "FAIL"
                log(f"  {f.path}: {status}")
                if not result.valid:
                    all_valid = False

        # Step 6: Run tests
        log("Step 6: Running tests...")
        import subprocess
        test_files = [f for f in files if 'test' in f.path.lower()]

        tests_passed = False
        for tf in test_files:
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest",
                     os.path.join(project_path, tf.path), "-v", "--tb=short"],
                    capture_output=True,
                    text=True,
                    cwd=project_path,
                    timeout=60
                )

                output = result.stdout + "\n" + result.stderr

                # Use error analyzer
                if result.returncode != 0:
                    analysis = error_analyzer.analyze(output)
                    log(f"  {tf.path}: FAIL ({analysis.category.value})")
                    log(f"    Root cause: {analysis.root_cause}")
                    log(f"    Fix: {analysis.fix_suggestion}")

                    # Try to fix using error analysis
                    log("  Attempting auto-fix...")
                    for f in files:
                        if f.path.endswith('.py') and not f.path.startswith('test'):
                            fixed_content = corrector._fix_code(
                                f.content, output,
                                task.get("language", "python"), lessons
                            )[0]
                            if fixed_content and len(fixed_content) > 100:
                                f.content = fixed_content
                                # Rewrite the file
                                import os as os_mod
                                full_path = os_mod.path.join(project_path, f.path)
                                with open(full_path, 'w') as file:
                                    file.write(fixed_content.encode('ascii', 'ignore').decode('ascii'))
                                log(f"    Fixed {f.path}")
                else:
                    tests_passed = True
                    log(f"  {tf.path}: PASS")

            except Exception as e:
                log(f"  Could not run tests: {e}")

        # Store lessons
        log("Step 7: Storing lessons...")
        if tests_passed:
            cross_session.learn(
                task["request"],
                "Successful generation",
                task.get("language", "python"),
                project_id
            )

        # Mark complete
        task["status"] = "completed" if tests_passed else "failed"
        task["result"] = {
            "success": tests_passed,
            "files": [f.path for f in files],
            "lessons": lessons
        }
        task["confidence"] = 1.0 if tests_passed else 0.5
        task["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        # Move to appropriate directory
        dest_dir = os.path.join(TASKS_DIR, "completed" if tests_passed else "failed")
        dest_path = os.path.join(dest_dir, task_file)
        with open(dest_path, 'w') as f:
            json.dump(task, f, indent=2)
        os.remove(task_path)

        # Summary
        print(f"\n{'='*60}")
        print(f"RESULT: {'SUCCESS' if tests_passed else 'PARTIAL'}")
        print(f"Files: {[f.path for f in files]}")
        print(f"Tests: {'PASS' if tests_passed else 'FAIL'}")
        print(f"Lessons: {cross_session.get_stats()}")
        print(f"{'='*60}")


if __name__ == "__main__":
    process_pending_tasks()
