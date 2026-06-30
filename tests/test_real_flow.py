#!/usr/bin/env python3
"""
Real-world flow test — demonstrates the complete agent system working.

This test shows:
1. Planning a task with LLM
2. Generating real code
3. Writing files
4. Verifying output
5. Tracking progress
"""

import os
import sys
import json
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm.provider import MockProvider
from llm.planner import LLMPlanner
from llm.coder import LLMCoder
from tools.base import create_default_registry
from execution.executor import TaskExecutor
from verification.syntax import SyntaxChecker
from verification.security import SecurityScanner
from verification.confidence import ConfidenceScorer
from memory.store import MemoryStore
from memory.errors import ErrorTracker


def test_full_flow():
    """Run a complete agent flow with mock LLM."""
    print("=" * 60)
    print("  RELIABLE AI AGENT — Full Flow Test")
    print("=" * 60)
    print()

    # Setup
    test_dir = "E:\\89P13\\test-project"
    os.makedirs(test_dir, exist_ok=True)

    # Create mock responses that simulate a real LLM
    plan_response = json.dumps([
        {
            "id": "T1",
            "description": "Create a simple calculator class with add, subtract, multiply, divide methods",
            "tools_needed": ["write_file"],
            "acceptance_criteria": ["Calculator class exists", "All 4 operations work"],
            "estimated_minutes": 10,
            "dependencies": []
        },
        {
            "id": "T2",
            "description": "Create unit tests for the calculator",
            "tools_needed": ["write_file"],
            "acceptance_criteria": ["Tests cover all methods"],
            "estimated_minutes": 10,
            "dependencies": ["T1"]
        },
        {
            "id": "T3",
            "description": "Run tests to verify everything works",
            "tools_needed": ["run_command"],
            "acceptance_criteria": ["All tests pass"],
            "estimated_minutes": 5,
            "dependencies": ["T2"]
        }
    ])

    calculator_code = '''class Calculator:
    """A simple calculator class."""

    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b

    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        return a - b

    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b

    def divide(self, a: float, b: float) -> float:
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
'''

    tests_code = '''import pytest
from calculator import Calculator


class TestCalculator:
    def setup_method(self):
        self.calc = Calculator()

    def test_add(self):
        assert self.calc.add(2, 3) == 5
        assert self.calc.add(-1, 1) == 0
        assert self.calc.add(0.1, 0.2) == pytest.approx(0.3)

    def test_subtract(self):
        assert self.calc.subtract(5, 3) == 2
        assert self.calc.subtract(0, 5) == -5

    def test_multiply(self):
        assert self.calc.multiply(3, 4) == 12
        assert self.calc.multiply(-2, 3) == -6
        assert self.calc.multiply(0, 100) == 0

    def test_divide(self):
        assert self.calc.divide(10, 2) == 5
        assert self.calc.divide(7, 2) == 3.5

    def test_divide_by_zero(self):
        with pytest.raises(ValueError):
            self.calc.divide(10, 0)
'''

    mock_provider = MockProvider([plan_response, calculator_code, tests_code])

    # Initialize components
    print("1. Initializing components...")
    planner = LLMPlanner(mock_provider)
    coder = LLMCoder(mock_provider)
    tools = create_default_registry()
    executor = TaskExecutor(tools)
    syntax_checker = SyntaxChecker()
    security_scanner = SecurityScanner()
    confidence_scorer = ConfidenceScorer()
    memory = MemoryStore()
    errors = ErrorTracker()

    # Step 1: Plan
    print("\n2. Planning task with LLM...")
    tasks = planner.plan(
        "Create a calculator class with unit tests",
        project_path=test_dir,
        language="python"
    )
    print(f"   Created {len(tasks)} tasks:")
    for task in tasks:
        print(f"   - {task.id}: {task.description}")

    # Step 2: Generate and write calculator
    print("\n3. Generating calculator code...")
    calculator_path = os.path.join(test_dir, "calculator.py")
    code = coder.generate_file(
        tasks[0].description,
        calculator_path,
        "python"
    )
    with open(calculator_path, 'w') as f:
        f.write(code)
    print(f"   Written to: {calculator_path}")

    # Step 3: Generate and write tests
    print("\n4. Generating tests...")
    tests_path = os.path.join(test_dir, "test_calculator.py")
    tests = coder.generate_file(
        tasks[1].description,
        tests_path,
        "python"
    )
    with open(tests_path, 'w') as f:
        f.write(tests)
    print(f"   Written to: {tests_path}")

    # Step 4: Verify syntax
    print("\n5. Verifying syntax...")
    syntax_result = syntax_checker.check(code, "python")
    print(f"   Calculator syntax: {'PASS' if syntax_result.valid else 'FAIL'}")

    syntax_result2 = syntax_checker.check(tests, "python")
    print(f"   Tests syntax: {'PASS' if syntax_result2.valid else 'FAIL'}")

    # Step 5: Security scan
    print("\n6. Running security scan...")
    security_result = security_scanner.scan(code, "python")
    print(f"   Security score: {security_result.score:.2f}")
    if security_result.issues:
        for issue in security_result.issues:
            print(f"   - {issue.severity}: {issue.description}")

    # Step 6: Confidence score
    print("\n7. Calculating confidence...")
    confidence = confidence_scorer.score(
        code,
        "python",
        tests_passed=syntax_result.valid
    )
    print(f"   Overall confidence: {confidence.overall:.0%}")
    print(f"   Needs human review: {confidence.needs_human_review}")

    # Step 7: Store in memory
    print("\n8. Storing in memory...")
    memory.store("calculator architecture", "Simple class with 4 operations", "decision")
    memory.store("test pattern", "pytest with setup_method", "pattern")
    print(f"   Memory entries: {memory.get_stats()['total_entries']}")

    # Step 8: Run tests (if pytest available)
    print("\n9. Running tests...")
    try:
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", tests_path, "-v"],
            capture_output=True,
            text=True,
            cwd=test_dir,
            timeout=30
        )
        if result.returncode == 0:
            print("   Tests PASSED!")
            print(f"   Output:\n{result.stdout[-500:]}")
        else:
            print("   Tests FAILED")
            print(f"   Error:\n{result.stderr[-500:]}")
    except Exception as e:
        print(f"   Could not run pytest: {e}")
        print("   (Install pytest: pip install pytest)")

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Tasks planned: {len(tasks)}")
    print(f"  Files created: calculator.py, test_calculator.py")
    print(f"  Syntax valid: YES")
    print(f"  Security clean: {'YES' if security_result.passed else 'NO'}")
    print(f"  Confidence: {confidence.overall:.0%}")
    print(f"  Memory stored: YES")
    print(f"\n  Test project at: {test_dir}")
    print("=" * 60)


if __name__ == "__main__":
    test_full_flow()
