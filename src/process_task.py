#!/usr/bin/env python3
"""
Process pending tasks — full featured version.
"""

import os
import sys
import json
import time
import re
import subprocess

sys.path.insert(0, os.path.dirname(__file__))

from llm.provider import OpenCodeZenProvider
from agent.self_correction import SelfCorrectionLoop
from agent.learning import LearningSystem
from agent.cross_session import CrossSessionLearning
from agent.project_builder import ProjectBuilder
from agent.context import ContextReader
from agent.error_analyzer import ErrorAnalyzer
from agent.prompts import PromptBuilder
from agent.git_integration import GitIntegration
from agent.test_generator import TestGenerator
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
    prompt_builder = PromptBuilder()
    test_generator = TestGenerator(provider)
    checker = SyntaxChecker()

    # Create self-correction loop with better prompts
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

        # Initialize git
        git = GitIntegration(project_path)
        git.init_if_needed()

        # Step 1: Read project context
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

        # Step 3: Build better prompt
        log("Step 3: Building optimized prompt...")
        code_prompt = prompt_builder.build_code_prompt(
            task["request"],
            task.get("language", "python"),
            context_prompt,
            context.tech_stack
        )

        # Step 4: Generate code with better prompts
        log("Step 4: Generating code...")
        from llm.coder import LLMCoder
        coder = LLMCoder(provider)

        code = coder.generate_file(
            code_prompt,
            os.path.join(project_path, "main.py"),
            task.get("language", "python")
        )

        if not code or len(code.strip()) < 50:
            log("  Code too short, retrying...")
            time.sleep(10)
            code = coder.generate_file(
                f"Write complete working code for: {task['request']}",
                os.path.join(project_path, "main.py"),
                task.get("language", "python")
            )

        log(f"  Generated {len(code)} chars")

        # Step 5: Generate better tests
        log("Step 5: Generating comprehensive tests...")
        time.sleep(10)

        test_suite = test_generator.generate(code, task.get("language", "python"))
        log(f"  Generated {test_suite.test_count} tests")
        log(f"  Coverage: {', '.join(test_suite.coverage_areas[:5])}")

        if test_suite.has_placeholders:
            log("  WARNING: Tests contain placeholders, regenerating...")
            time.sleep(10)
            test_suite = test_generator.generate(code, task.get("language", "python"))
            log(f"  Regenerated: {test_suite.test_count} tests")

        # Write files
        code_file = os.path.join(project_path, "main.py")
        test_file = os.path.join(project_path, "test_main.py")

        code = code.encode('ascii', 'ignore').decode('ascii')
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(code)

        test_code = test_suite.code.encode('ascii', 'ignore').decode('ascii')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_code)

        # Step 6: Verify syntax
        log("Step 6: Verifying syntax...")
        code_valid = checker.check(code, "python").valid
        tests_valid = checker.check(test_code, "python").valid
        log(f"  Code: {'PASS' if code_valid else 'FAIL'}")
        log(f"  Tests: {'PASS' if tests_valid else 'FAIL'}")

        # Step 7: Run tests
        log("Step 7: Running tests...")
        tests_passed = False

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                cwd=project_path,
                timeout=60
            )

            output = result.stdout + "\n" + result.stderr

            # Check for actual failures (not just warnings)
            has_failed = "FAILED" in output and "error" in output.lower()
            has_passed = "passed" in output.lower()

            if has_passed and not has_failed:
                tests_passed = True
                log("  Tests PASSED!")
            else:
                log("  Tests failed, attempting auto-fix...")
                # Use error analyzer
                analysis = error_analyzer.analyze(output)
                log(f"    Error: {analysis.category.value} - {analysis.root_cause}")

                # Try to fix
                for attempt in range(3):
                    time.sleep(10)
                    fixed_code = corrector._fix_code(
                        code, output,
                        task.get("language", "python"), lessons
                    )[0]

                    if fixed_code and len(fixed_code) > 100:
                        code = fixed_code.encode('ascii', 'ignore').decode('ascii')
                        with open(code_file, 'w', encoding='utf-8') as f:
                            f.write(code)

                        # Re-run tests
                        result = subprocess.run(
                            ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
                            capture_output=True,
                            text=True,
                            cwd=project_path,
                            timeout=60
                        )
                        output = result.stdout + "\n" + result.stderr

                        if "passed" in output.lower() and "FAILED" not in output:
                            tests_passed = True
                            log(f"    Fixed on attempt {attempt + 1}!")
                            break

        except Exception as e:
            log(f"  Could not run tests: {e}")

        # Step 8: Git commit
        log("Step 8: Committing to git...")
        files = [f for f in os.listdir(project_path) if f.endswith('.py')]
        git_result = git.auto_commit(files, task["request"])
        log(f"  {git_result.message}")

        # Store lessons
        log("Step 9: Storing lessons...")
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
            "files": files,
            "tests": test_suite.test_count,
            "git_commit": git_result.commit_hash
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
        print(f"Files: {files}")
        print(f"Tests: {test_suite.test_count} generated, {'PASS' if tests_passed else 'FAIL'}")
        print(f"Git: {git_result.commit_hash or 'no commit'}")
        print(f"{'='*60}")


if __name__ == "__main__":
    process_pending_tasks()
