#!/usr/bin/env python3
"""
REAL WORLD TEST — Simulates actual agent usage.

Task: Build a complete URL shortener API
- FastAPI backend
- In-memory storage
- Create short URL, redirect, get stats
- Unit tests
- Full working project
"""

import os
import sys
import json
import time
import subprocess
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm.provider import OpenCodeZenProvider
from llm.planner import LLMPlanner
from llm.coder import LLMCoder
from tools.base import create_default_registry
from execution.executor import TaskExecutor
from verification.syntax import SyntaxChecker
from verification.security import SecurityScanner
from verification.confidence import ConfidenceScorer
from memory.store import MemoryStore
from memory.errors import ErrorTracker
from memory.session import SessionMemory


PROJECT_DIR = "E:\\89P13\\real-world-test"
API_KEY = os.environ.get("ZEN_API_KEY")


def setup_project():
    """Create clean project directory."""
    if os.path.exists(PROJECT_DIR):
        shutil.rmtree(PROJECT_DIR)
    os.makedirs(PROJECT_DIR)
    os.makedirs(os.path.join(PROJECT_DIR, "app"))
    os.makedirs(os.path.join(PROJECT_DIR, "tests"))
    print(f"Project directory: {PROJECT_DIR}")


def log(msg):
    """Print with timestamp."""
    print(f"  [{time.strftime('%H:%M:%S')}] {msg}")


def run_real_world_test():
    """Full real-world agent test."""
    print("=" * 70)
    print("  REAL WORLD TEST — Building a URL Shortener API")
    print("=" * 70)
    print()

    if not API_KEY:
        print("ERROR: Set ZEN_API_KEY environment variable")
        return False

    # Initialize
    provider = OpenCodeZenProvider(api_key=API_KEY, model="big-pickle")
    planner = LLMPlanner(provider)
    coder = LLMCoder(provider)
    tools = create_default_registry()
    executor = TaskExecutor(tools)
    syntax_checker = SyntaxChecker()
    security_scanner = SecurityScanner()
    confidence_scorer = ConfidenceScorer()
    memory = MemoryStore()
    errors = ErrorTracker()
    session = SessionMemory()

    setup_project()

    # ============================================
    # PHASE 1: PLANNING
    # ============================================
    print("\n" + "=" * 70)
    print("  PHASE 1: PLANNING")
    print("=" * 70)

    log("Asking LLM to plan the project...")
    session.log_action("Planning URL shortener project")

    tasks = planner.plan(
        "Build a URL shortener API with FastAPI. Include: "
        "1) POST /shorten - create short URL from long URL "
        "2) GET /{short_id} - redirect to original URL "
        "3) GET /stats/{short_id} - get click stats "
        "Use in-memory storage. Include unit tests.",
        project_path=PROJECT_DIR,
        language="python"
    )

    log(f"Planned {len(tasks)} tasks:")
    for t in tasks:
        log(f"  {t.id}: {t.description[:70]}")

    time.sleep(8)  # Rate limit

    # ============================================
    # PHASE 2: GENERATE CODE
    # ============================================
    print("\n" + "=" * 70)
    print("  PHASE 2: GENERATING CODE")
    print("=" * 70)

    # Task 1: Generate main app
    log("Generating main application...")
    session.start_task("T1", "Generate main app")

    app_code = coder.generate_file(
        "Create a FastAPI URL shortener with these endpoints: "
        "POST /shorten (takes url, returns short_url), "
        "GET /{short_id} (redirects to original url), "
        "GET /stats/{short_id} (returns click count and original url). "
        "Use in-memory dictionary storage. Include proper error handling.",
        os.path.join(PROJECT_DIR, "app", "main.py"),
        "python"
    )

    if not app_code or len(app_code) < 50:
        log(f"FAILED to generate app code: {app_code}")
        return False

    with open(os.path.join(PROJECT_DIR, "app", "main.py"), 'w') as f:
        f.write(app_code)
    session.complete_task("T1", "App generated")
    log(f"App generated: {len(app_code)} chars")

    time.sleep(10)

    # Task 2: Generate __init__.py
    log("Generating __init__.py...")
    init_code = coder.generate_file(
        "Create a simple __init__.py for a FastAPI app package",
        os.path.join(PROJECT_DIR, "app", "__init__.py"),
        "python"
    )
    with open(os.path.join(PROJECT_DIR, "app", "__init__.py"), 'w') as f:
        f.write(init_code or "# App package")
    log("__init__.py created")

    time.sleep(10)

    # Task 3: Generate tests
    log("Generating tests...")
    session.start_task("T2", "Generate tests")

    test_code = coder.generate_file(
        "Write pytest tests for a FastAPI URL shortener. Test: "
        "1) POST /shorten creates short url "
        "2) GET /{short_id} redirects correctly "
        "3) GET /stats/{short_id} returns stats "
        "4) GET /nonexistent returns 404 "
        "Use TestClient from fastapi.testclient.",
        os.path.join(PROJECT_DIR, "tests", "test_api.py"),
        "python"
    )

    if test_code:
        # Strip markdown if present
        import re
        test_code = re.sub(r'```python\s*', '', test_code)
        test_code = re.sub(r'```\s*$', '', test_code, flags=re.MULTILINE)
        test_code = test_code.strip()

        with open(os.path.join(PROJECT_DIR, "tests", "test_api.py"), 'w') as f:
            f.write(test_code)
        session.complete_task("T2", "Tests generated")
        log(f"Tests generated: {len(test_code)} chars")
    else:
        log("FAILED to generate tests")

    time.sleep(10)

    # Task 3: Generate requirements.txt
    log("Generating requirements.txt...")
    with open(os.path.join(PROJECT_DIR, "requirements.txt"), 'w') as f:
        f.write("fastapi>=0.100.0\nuvicorn>=0.23.0\nhttpx>=0.24.0\npytest>=7.0.0\n")
    log("requirements.txt created")

    # ============================================
    # PHASE 3: VERIFY
    # ============================================
    print("\n" + "=" * 70)
    print("  PHASE 3: VERIFICATION")
    print("=" * 70)

    # Syntax check
    log("Checking syntax...")
    app_syntax = syntax_checker.check(app_code, "python")
    log(f"  App syntax: {'PASS' if app_syntax.valid else 'FAIL'}")
    if app_syntax.errors:
        for e in app_syntax.errors:
            log(f"    - {e}")

    if test_code:
        test_syntax = syntax_checker.check(test_code, "python")
        log(f"  Test syntax: {'PASS' if test_syntax.valid else 'FAIL'}")
        if test_syntax.errors:
            for e in test_syntax.errors:
                log(f"    - {e}")

    # Security scan
    log("Running security scan...")
    app_security = security_scanner.scan(app_code, "python")
    log(f"  App security: {app_security.score:.2f} ({'PASS' if app_security.passed else 'FAIL'})")

    # Confidence
    log("Calculating confidence...")
    confidence = confidence_scorer.score(
        app_code,
        "python",
        tests_passed=app_syntax.valid
    )
    log(f"  Confidence: {confidence.overall:.0%}")

    # ============================================
    # PHASE 4: RUN
    # ============================================
    print("\n" + "=" * 70)
    print("  PHASE 4: EXECUTION")
    print("=" * 70)

    # Install dependencies
    log("Installing dependencies...")
    try:
        result = subprocess.run(
            ["pip", "install", "fastapi", "uvicorn", "httpx", "pytest", "-q"],
            capture_output=True,
            text=True,
            timeout=60
        )
        log(f"  Dependencies installed")
    except Exception as e:
        log(f"  Could not install: {e}")

    time.sleep(10)

    # Run tests
    log("Running tests...")
    session.start_task("T3", "Run tests")

    try:
        result = subprocess.run(
            ["python", "-m", "pytest", os.path.join(PROJECT_DIR, "tests", "test_api.py"), "-v"],
            capture_output=True,
            text=True,
            cwd=PROJECT_DIR,
            timeout=30
        )

        if result.returncode == 0:
            session.complete_task("T3", "Tests passed")
            log("  ALL TESTS PASSED!")
            # Show test results
            for line in result.stdout.split('\n'):
                if 'PASSED' in line or 'FAILED' in line:
                    log(f"  {line.strip()}")
        else:
            session.fail_task("T3", result.stderr[-200:] if result.stderr else "Unknown error")
            log("  TESTS FAILED")
            log(f"  Error: {result.stderr[-300:]}")

            # Try to fix and re-run
            log("  Attempting auto-fix...")
            if test_code and "import" in test_code:
                # Fix common import issues
                fixed_test = test_code.replace(
                    "from app.main",
                    "import sys; sys.path.insert(0, '.'); from app.main"
                )
                with open(os.path.join(PROJECT_DIR, "tests", "test_api.py"), 'w') as f:
                    f.write(fixed_test)

                time.sleep(8)
                result2 = subprocess.run(
                    ["python", "-m", "pytest", os.path.join(PROJECT_DIR, "tests", "test_api.py"), "-v"],
                    capture_output=True,
                    text=True,
                    cwd=PROJECT_DIR,
                    timeout=30
                )
                if result2.returncode == 0:
                    log("  AUTO-FIX SUCCEEDED!")
                    session.complete_task("T3", "Tests passed after fix")
                else:
                    log(f"  Auto-fix failed: {result2.stderr[-200:]}")

    except Exception as e:
        log(f"  Could not run tests: {e}")

    # ============================================
    # PHASE 5: LEARN
    # ============================================
    print("\n" + "=" * 70)
    print("  PHASE 5: LEARNING")
    print("=" * 70)

    log("Storing in memory...")
    memory.store("url_shortener_pattern", "FastAPI + in-memory dict", "decision", "url-shortener")
    memory.store("test_pattern", "Use TestClient from fastapi.testclient", "pattern")
    log(f"  Memory entries: {memory.get_stats()['total_entries']}")

    # ============================================
    # SUMMARY
    # ============================================
    print("\n" + "=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)

    progress = session.get_progress_summary()
    print(f"  Tasks completed: {progress['completed']}/{progress['total_tasks']}")
    print(f"  Tasks failed: {progress['failed']}")
    print(f"  Confidence: {confidence.overall:.0%}")
    print(f"  Syntax valid: {'YES' if app_syntax.valid else 'NO'}")
    print(f"  Security clean: {'YES' if app_security.passed else 'NO'}")
    print(f"  Memory stored: YES")
    print()
    print(f"  Project at: {PROJECT_DIR}")
    print()
    print(f"  Files created:")
    for root, dirs, files in os.walk(PROJECT_DIR):
        for f in files:
            path = os.path.join(root, f)
            size = os.path.getsize(path)
            print(f"    {os.path.relpath(path, PROJECT_DIR)} ({size} bytes)")

    print("=" * 70)
    return progress['failed'] == 0


if __name__ == "__main__":
    success = run_real_world_test()
    print(f"\nResult: {'SUCCESS' if success else 'PARTIAL'}")
    sys.exit(0 if success else 1)
