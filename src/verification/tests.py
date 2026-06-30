"""
Test Runner — executes tests and evaluates results.
"""

import subprocess
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TestResult:
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    output: str
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class TestRunner:
    """
    Runs tests and interprets results.

    Supports: pytest, unittest, and basic shell commands.
    """

    def run(self, command: str, cwd: Optional[str] = None,
            timeout: int = 60) -> TestResult:
        """
        Run a test command and parse results.
        """
        import time
        start = time.time()

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )

            duration = time.time() - start
            output = result.stdout + result.stderr

            # Parse pytest output
            if "pytest" in command or "passed" in output:
                return self._parse_pytest(output, duration)

            # Parse unittest output
            if "Ran " in output and "OK" in output:
                return self._parse_unittest(output, duration)

            # Generic: check exit code
            return TestResult(
                passed=result.returncode == 0,
                total_tests=1,
                passed_tests=1 if result.returncode == 0 else 0,
                failed_tests=0 if result.returncode == 0 else 1,
                skipped_tests=0,
                output=output,
                duration_seconds=duration
            )

        except subprocess.TimeoutExpired:
            return TestResult(
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                output="",
                errors=[f"Test timed out after {timeout}s"],
                duration_seconds=timeout
            )
        except Exception as e:
            return TestResult(
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                output="",
                errors=[str(e)],
                duration_seconds=time.time() - start
            )

    def _parse_pytest(self, output: str, duration: float) -> TestResult:
        """Parse pytest output."""
        import re

        # Look for summary line like "5 passed, 2 failed in 1.23s"
        match = re.search(
            r'(\d+) passed.*?(\d+) failed',
            output
        )
        if match:
            passed = int(match.group(1))
            failed = int(match.group(2))
            return TestResult(
                passed=failed == 0,
                total_tests=passed + failed,
                passed_tests=passed,
                failed_tests=failed,
                skipped_tests=0,
                output=output,
                duration_seconds=duration
            )

        # Look for all passed
        match = re.search(r'(\d+) passed', output)
        if match:
            passed = int(match.group(1))
            return TestResult(
                passed=True,
                total_tests=passed,
                passed_tests=passed,
                failed_tests=0,
                skipped_tests=0,
                output=output,
                duration_seconds=duration
            )

        # Unknown format
        return TestResult(
            passed="error" not in output.lower(),
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            output=output,
            duration_seconds=duration
        )

    def _parse_unittest(self, output: str, duration: float) -> TestResult:
        """Parse unittest output."""
        import re

        match = re.search(r'Ran (\d+) tests? in [\d.]+s', output)
        total = int(match.group(1)) if match else 0

        passed = "OK" in output

        return TestResult(
            passed=passed,
            total_tests=total,
            passed_tests=total if passed else 0,
            failed_tests=0 if passed else total,
            skipped_tests=0,
            output=output,
            duration_seconds=duration
        )
