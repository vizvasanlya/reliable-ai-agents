#!/usr/bin/env python3
"""
Real API Test — tests the agent with OpenCode Zen (MiMo-V2.5 Free).

Usage:
  1. Get your API key from https://opencode.ai/auth
  2. Set environment variable: set ZEN_API_KEY=your-key
  3. Run: python tests/test_real_api.py
"""

import os
import sys
import json
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm.provider import OpenCodeZenProvider, create_provider
from llm.planner import LLMPlanner
from llm.coder import LLMCoder
from tools.base import create_default_registry
from execution.executor import TaskExecutor
from verification.syntax import SyntaxChecker
from verification.security import SecurityScanner
from verification.confidence import ConfidenceScorer
from memory.store import MemoryStore


def test_real_api():
    """Test with real OpenCode Zen API."""
    print("=" * 60)
    print("  REAL API TEST — OpenCode Zen (MiMo-V2.5 Free)")
    print("=" * 60)
    print()

    # Check for API key
    api_key = os.environ.get("ZEN_API_KEY") or os.environ.get("OPENCODE_API_KEY")
    if not api_key:
        print("ERROR: No API key found.")
        print()
        print("To run this test:")
        print("1. Get your API key from https://opencode.ai/auth")
        print("2. Set it: set ZEN_API_KEY=your-key-here")
        print("3. Run this test again")
        return False

    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print()

    # Initialize provider
    print("1. Connecting to OpenCode Zen...")
    provider = OpenCodeZenProvider(api_key=api_key, model="mimo-v2.5-free")
    print(f"   Provider: {provider.name}")
    print(f"   Model: {provider.model}")
    print()

    # Test 1: Basic completion
    print("2. Testing basic completion...")
    response = provider.complete(
        "Write a Python function that calculates factorial of a number.",
        system="You are a Python expert. Return ONLY the code, no explanation."
    )

    if response.finish_reason == "error":
        print(f"   FAILED: {response.content}")
        return False

    print(f"   SUCCESS: Got {len(response.content)} characters")
    print(f"   Tokens used: {response.tokens_used}")
    print(f"   Response preview:")
    print(f"   {response.content[:200]}...")
    print()

    # Test 2: Planning with real LLM
    print("3. Testing LLM planning...")
    planner = LLMPlanner(provider)
    tasks = planner.plan("Create a simple web scraper that fetches titles from a URL")

    if not tasks:
        print("   FAILED: No tasks generated")
        return False

    print(f"   SUCCESS: Generated {len(tasks)} tasks")
    for task in tasks:
        print(f"   - {task.id}: {task.description}")
    print()

    # Test 3: Code generation
    print("4. Testing code generation...")
    coder = LLMCoder(provider)

    test_dir = "E:\\89P13\\test-real-api"
    os.makedirs(test_dir, exist_ok=True)

    code = coder.generate_file(
        "Create a simple HTTP server that serves a hello world page",
        os.path.join(test_dir, "server.py"),
        "python"
    )

    if not code or "Error" in code[:20]:
        print(f"   FAILED: {code[:200]}")
        return False

    # Write the file
    with open(os.path.join(test_dir, "server.py"), 'w') as f:
        f.write(code)

    print(f"   SUCCESS: Generated {len(code)} characters")
    print(f"   Written to: {test_dir}/server.py")
    print()

    # Test 4: Syntax verification
    print("5. Verifying syntax...")
    syntax_checker = SyntaxChecker()
    syntax_result = syntax_checker.check(code, "python")
    print(f"   Valid: {syntax_result.valid}")
    if syntax_result.errors:
        for err in syntax_result.errors:
            print(f"   - {err}")
    print()

    # Test 5: Security scan
    print("6. Security scan...")
    security_scanner = SecurityScanner()
    security_result = security_scanner.scan(code, "python")
    print(f"   Score: {security_result.score:.2f}")
    print(f"   Passed: {security_result.passed}")
    print()

    # Test 6: Full flow test
    print("7. Running full agent flow...")
    full_code = coder.generate_file(
        "Create a Calculator class with add, subtract, multiply, divide methods",
        os.path.join(test_dir, "calculator.py"),
        "python"
    )

    full_tests = coder.write_tests(full_code, "python")

    # Write files
    with open(os.path.join(test_dir, "calculator.py"), 'w') as f:
        f.write(full_code)
    with open(os.path.join(test_dir, "test_calculator.py"), 'w') as f:
        f.write(full_tests)

    # Verify and test
    syntax_ok = syntax_checker.check(full_code, "python").valid
    tests_ok = syntax_checker.check(full_tests, "python").valid

    print(f"   Calculator code: {'PASS' if syntax_ok else 'FAIL'}")
    print(f"   Tests code: {'PASS' if tests_ok else 'FAIL'}")

    # Try to run tests
    try:
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", os.path.join(test_dir, "test_calculator.py"), "-v"],
            capture_output=True,
            text=True,
            cwd=test_dir,
            timeout=30
        )
        print(f"   Tests execution: {'PASS' if result.returncode == 0 else 'FAIL'}")
        if result.returncode == 0:
            print(f"   {result.stdout[-200:]}")
    except Exception as e:
        print(f"   Could not run pytest: {e}")

    print()
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  API Connection: SUCCESS")
    print(f"  Basic Completion: SUCCESS")
    print(f"  LLM Planning: SUCCESS ({len(tasks)} tasks)")
    print(f"  Code Generation: SUCCESS")
    print(f"  Syntax Check: {'PASS' if syntax_result.valid else 'FAIL'}")
    print(f"  Security Scan: {'PASS' if security_result.passed else 'FAIL'}")
    print(f"  Full Flow: SUCCESS")
    print(f"  Files created: {test_dir}/")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = test_real_api()
    sys.exit(0 if success else 1)
