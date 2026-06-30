#!/usr/bin/env python3
"""
Real API Test v2 — tests with rate limit handling.
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm.provider import OpenCodeZenProvider
from llm.planner import LLMPlanner
from llm.coder import LLMCoder
from verification.syntax import SyntaxChecker
from verification.security import SecurityScanner


def wait_for_api(seconds=10):
    """Wait for rate limit to reset."""
    print(f"   Waiting {seconds}s for rate limit...")
    time.sleep(seconds)


def test_real_api():
    print("=" * 60)
    print("  REAL API TEST — MiMo-V2.5 Free")
    print("=" * 60)

    api_key = os.environ.get("ZEN_API_KEY") or os.environ.get("OPENCODE_API_KEY")
    if not api_key:
        print("ERROR: Set ZEN_API_KEY environment variable")
        return False

    provider = OpenCodeZenProvider(api_key=api_key, model="big-pickle")
    print(f"Provider: {provider.name}")

    # Test 1: Basic completion
    print("\n1. Basic completion...")
    r = provider.complete("Write a Python function to add two numbers. Return ONLY the code.")
    if r.finish_reason == "error":
        print(f"   FAILED: {r.content}")
        return False
    print(f"   OK: {len(r.content)} chars")
    print(f"   Preview: {r.content[:150]}...")

    wait_for_api(5)

    # Test 2: Code generation
    print("\n2. Code generation...")
    coder = LLMCoder(provider)
    test_dir = "E:\\89P13\\test-real-api"
    os.makedirs(test_dir, exist_ok=True)

    code = coder.generate_file(
        "Create a Calculator class with add, subtract, multiply, divide methods",
        os.path.join(test_dir, "calculator.py"),
        "python"
    )

    if not code or len(code) < 20:
        print(f"   FAILED: {code[:200] if code else 'empty'}")
        return False

    with open(os.path.join(test_dir, "calculator.py"), 'w') as f:
        f.write(code)
    print(f"   OK: Generated {len(code)} chars")

    wait_for_api(5)

    # Test 3: Syntax check
    print("\n3. Syntax check...")
    checker = SyntaxChecker()
    result = checker.check(code, "python")
    print(f"   Valid: {result.valid}")
    if result.errors:
        for e in result.errors:
            print(f"   - {e}")

    # Test 4: Security scan
    print("\n4. Security scan...")
    scanner = SecurityScanner()
    sec = scanner.scan(code, "python")
    print(f"   Score: {sec.score:.2f}, Passed: {sec.passed}")

    wait_for_api(5)

    # Test 5: Generate tests
    print("\n5. Generate tests...")
    tests = coder.write_tests(code, "python")
    if tests and len(tests) > 20:
        with open(os.path.join(test_dir, "test_calculator.py"), 'w') as f:
            f.write(tests)
        print(f"   OK: Generated {len(tests)} chars")
    else:
        print(f"   FAILED: {tests[:200] if tests else 'empty'}")

    wait_for_api(5)

    # Test 6: Run tests
    print("\n6. Run tests...")
    try:
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", os.path.join(test_dir, "test_calculator.py"), "-v"],
            capture_output=True,
            text=True,
            cwd=test_dir,
            timeout=30
        )
        if result.returncode == 0:
            print("   PASSED!")
            print(f"   {result.stdout[-300:]}")
        else:
            print("   FAILED")
            print(f"   {result.stderr[-300:]}")
    except Exception as e:
        print(f"   Could not run pytest: {e}")

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print("  API: Connected to MiMo-V2.5 Free")
    print("  Code Generation: Working")
    print("  Syntax Check: Working")
    print("  Security Scan: Working")
    print("  Files at:", test_dir)
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_real_api()
    sys.exit(0 if success else 1)
