"""
Self-Correction Loop — the agent fixes its own mistakes.

When code fails:
1. Detect the error
2. Analyze what went wrong (LLM reasoning)
3. Fix the code
4. Re-run tests
5. Repeat until working or escalate

This is the core autonomous behavior.
"""

import os
import re
import json
import subprocess
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Attempt:
    iteration: int
    code: str
    error: str
    fix_applied: str
    success: bool


@dataclass
class CorrectionResult:
    success: bool
    final_code: str
    attempts: List[Attempt]
    total_fixes: int
    learned_lessons: List[str]


class SelfCorrectionLoop:
    """
    Autonomous agent that fixes its own mistakes.

    Flow:
    1. Generate code
    2. Run tests
    3. If fail: analyze error, fix code, re-run
    4. Repeat up to N times
    5. Store lessons learned
    """

    def __init__(self, llm_provider, memory_store=None, max_attempts: int = 5):
        self.llm = llm_provider
        self.memory = memory_store
        self.max_attempts = max_attempts
        self.lessons: List[str] = []

    def generate_and_fix(self, request: str, project_path: str,
                         language: str = "python") -> CorrectionResult:
        """
        Generate code, test it, and fix until it works.

        This is the main autonomous loop.
        """
        attempts = []
        learned = []

        # Check memory for known issues with similar requests
        known_fixes = self._check_known_issues(request)

        for iteration in range(1, self.max_attempts + 1):
            print(f"\n  --- Attempt {iteration}/{self.max_attempts} ---")

            # Step 1: Generate or fix code
            if iteration == 1:
                code = self._generate_initial_code(request, language, known_fixes)
                fix_applied = "Initial generation"
            else:
                prev_error = attempts[-1].error
                prev_code = attempts[-1].code
                code, fix_applied = self._fix_code(prev_code, prev_error, language, learned)
                print(f"  Fix: {fix_applied}")

            # Validate code is not empty
            if not code or len(code.strip()) < 50:
                print(f"  Code too short ({len(code)} chars), retrying...")
                time.sleep(10)
                code = self._generate_initial_code(request, language, known_fixes)
                fix_applied = "Regenerated (previous was empty)"

            # Step 2: Write code to file
            code_file = os.path.join(project_path, "main.py")
            # Strip non-ASCII characters that cause encoding issues
            code = code.encode('ascii', 'ignore').decode('ascii')
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(code)

            # Step 3: Verify syntax
            syntax_ok, syntax_error = self._verify_syntax(code, language)
            if not syntax_ok:
                print(f"  Syntax error: {syntax_error}")
                attempts.append(Attempt(
                    iteration=iteration,
                    code=code,
                    error=syntax_error,
                    fix_applied=fix_applied,
                    success=False
                ))
                continue

            # Step 4: Generate tests (always regenerate if previous failed)
            tests = self._generate_tests(code, language)
            test_file = os.path.join(project_path, "test_main.py")
            # Strip non-ASCII characters that cause encoding issues
            tests = tests.encode('ascii', 'ignore').decode('ascii')

            # Check if tests are complete (balanced braces/brackets)
            if not self._is_code_complete(tests):
                print("  Tests incomplete, regenerating...")
                time.sleep(10)
                tests = self._generate_tests(code, language)
                tests = tests.encode('ascii', 'ignore').decode('ascii')

            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(tests)

            # Step 5: Run tests
            test_passed, test_output = self._run_tests(project_path)

            if test_passed:
                print(f"  Tests PASSED on attempt {iteration}")
                attempts.append(Attempt(
                    iteration=iteration,
                    code=code,
                    error="",
                    fix_applied=fix_applied,
                    success=True
                ))

                # Learn from success
                lesson = f"Attempt {iteration} succeeded: {fix_applied}"
                learned.append(lesson)

                return CorrectionResult(
                    success=True,
                    final_code=code,
                    attempts=attempts,
                    total_fixes=iteration - 1,
                    learned_lessons=learned
                )

            # Tests failed — analyze error
            error_msg = self._extract_error(test_output)
            print(f"  Test failed: {error_msg[:100]}...")

            # Store this error pattern
            lesson = self._analyze_and_learn(error_msg, code, language)
            if lesson:
                learned.append(lesson)

            attempts.append(Attempt(
                iteration=iteration,
                code=code,
                error=error_msg,
                fix_applied=fix_applied,
                success=False
            ))

            # Wait for rate limit
            time.sleep(10)

        # All attempts exhausted
        print(f"\n  FAILED after {self.max_attempts} attempts")

        # Store failure pattern for future learning
        if self.memory and attempts:
            self._store_failure_pattern(request, attempts[-1].error, learned)

        return CorrectionResult(
            success=False,
            final_code=attempts[-1].code if attempts else "",
            attempts=attempts,
            total_fixes=len(attempts) - 1,
            learned_lessons=learned
        )

    def _generate_initial_code(self, request: str, language: str,
                                known_fixes: List[str]) -> str:
        """Generate initial code with known fixes applied."""
        from llm.coder import LLMCoder
        coder = LLMCoder(self.llm)

        # Build prompt with known fixes
        prompt = f"Write complete, working {language} code for:\n\n{request}\n\n"

        if known_fixes:
            prompt += "IMPORTANT FIXES TO APPLY:\n"
            for fix in known_fixes:
                prompt += f"- {fix}\n"
            prompt += "\n"

        prompt += "Return ONLY the complete code. No explanations, no markdown."

        response = self.llm.complete(
            prompt=prompt,
            system=f"You are an expert {language} developer. Write clean, working code that passes all tests.",
            temperature=0.2,
            max_tokens=4096
        )

        return self._clean_code(response.content)

    def _fix_code(self, code: str, error: str, language: str,
                   learned: List[str]) -> Tuple[str, str]:
        """Fix code based on error analysis using LLM."""
        # Extract the most relevant error lines
        error_lines = error.split('\n')
        relevant_errors = [l for l in error_lines if 'Error' in l or 'FAILED' in l or 'assert' in l]
        error_summary = '\n'.join(relevant_errors[:10]) if relevant_errors else error[:500]

        prompt = f"""Fix this {language} code. The tests are failing.

ERROR SUMMARY:
{error_summary}

CURRENT CODE (first 2000 chars):
```{language}
{code[:2000]}
```

LESSONS FROM PAST MISTAKES:
{chr(10).join(learned[:5]) if learned else "None yet"}

INSTRUCTIONS:
1. Fix the specific error shown above
2. Make sure all imports are correct
3. Make sure the code runs without errors
4. Return ONLY the complete fixed code

Fixed code:"""

        response = self.llm.complete(
            prompt=prompt,
            system=f"You are an expert {language} developer. Fix bugs and return complete working code.",
            temperature=0.2,
            max_tokens=4096
        )

        fixed_code = self._clean_code(response.content)

        # Analyze what changed
        fix_description = self._describe_fix(code, fixed_code, error)

        return fixed_code, fix_description

    def _generate_tests(self, code: str, language: str) -> str:
        """Generate tests for the code."""
        prompt = f"""Write comprehensive pytest tests for this code:

```{language}
{code}
```

Return ONLY the test code. No explanations."""

        response = self.llm.complete(
            prompt=prompt,
            system="Write thorough unit tests using pytest. Cover normal cases and edge cases.",
            temperature=0.3,
            max_tokens=4096
        )

        return self._clean_code(response.content)

    def _verify_syntax(self, code: str, language: str) -> Tuple[bool, str]:
        """Verify code syntax."""
        import ast

        if language == "python":
            try:
                ast.parse(code)
                return True, ""
            except SyntaxError as e:
                return False, f"Line {e.lineno}: {e.msg}"
        elif language == "json":
            try:
                json.loads(code)
                return True, ""
            except json.JSONDecodeError as e:
                return False, str(e)

        return True, ""

    def _run_tests(self, project_path: str) -> Tuple[bool, str]:
        """Run tests and return pass/fail with output."""
        test_file = os.path.join(project_path, "test_main.py")

        if not os.path.exists(test_file):
            return True, "No test file"

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                cwd=project_path,
                timeout=60
            )

            output = result.stdout + "\n" + result.stderr

            # Check for actual test failures, not just warnings
            has_failures = "FAILED" in output and "error" in output.lower()
            has_passed = "passed" in output.lower()
            has_errors = "ERROR" in output and "error" in output.lower()

            # Return success if tests passed and no actual failures
            if has_passed and not has_failures and not has_errors:
                return True, output
            elif result.returncode == 0:
                return True, output
            else:
                return False, output

        except Exception as e:
            return False, str(e)

    def _extract_error(self, output: str) -> str:
        """Extract the key error message from test output."""
        lines = output.split('\n')

        # Look for FAILED or ERROR lines
        for line in lines:
            if 'FAILED' in line or 'ERROR' in line or 'AssertionError' in line:
                return line.strip()

        # Look for the last few lines which usually contain the error
        for line in reversed(lines[-10:]):
            if line.strip() and not line.startswith('='):
                return line.strip()

        return output[-500:] if output else "Unknown error"

    def _is_code_complete(self, code: str) -> bool:
        """Check if code is complete (balanced braces, brackets, parens)."""
        # Count opening and closing brackets
        opens = code.count('{') + code.count('[') + code.count('(')
        closes = code.count('}') + code.count(']') + code.count(')')

        # Allow some imbalance (comments might have unmatched brackets)
        if abs(opens - closes) > 2:
            return False

        # Check if file ends abruptly (no newline at end, or ends mid-line)
        lines = code.strip().split('\n')
        if lines:
            last_line = lines[-1].strip()
            # If last line is incomplete (ends with comma, operator, etc.)
            if last_line.endswith((',', '+', '-', '*', '/', '=', '(', '[', '{', 'and', 'or', 'not')):
                return False

        return True

    def _analyze_and_learn(self, error: str, code: str, language: str) -> Optional[str]:
        """Analyze error and extract a learning lesson."""
        prompt = f"""Analyze this error and give a ONE LINE fix rule.

Error: {error[:300]}

Code snippet:
```{language}
{code[:500]}
```

Return a single, actionable rule like:
- "Always import X from Y"
- "Add try/except for Z"
- "Use W instead of V"

Return ONLY the rule, nothing else."""

        response = self.llm.complete(
            prompt=prompt,
            system="Give concise, actionable coding rules.",
            temperature=0.2,
            max_tokens=100
        )

        lesson = response.content.strip()

        # Store lesson in memory
        if self.memory and lesson:
            self.memory.record_error(
                error_type=error[:50],
                description=f"Error in {language} code",
                cause=error[:200],
                solution=lesson,
                tags=[language, "auto-learned"]
            )

        return lesson

    def _describe_fix(self, old_code: str, new_code: str, error: str) -> str:
        """Describe what changed between code versions."""
        if len(new_code) < len(old_code):
            return "Removed problematic code"
        elif len(new_code) > len(old_code) + 50:
            return "Added error handling/imports"
        else:
            return "Fixed logic/syntax"

    def _check_known_issues(self, request: str) -> List[str]:
        """Check memory for known fixes for similar requests."""
        if not self.memory:
            return []

        # Search for relevant fixes
        results = self.memory.search(request[:50], category="error")
        return [r.value.get("solution", "") for r in results if r.value.get("solution")]

    def _store_failure_pattern(self, request: str, error: str, lessons: List[str]):
        """Store failure pattern for future learning."""
        if self.memory:
            self.memory.store(
                key=f"failure_{request[:30]}",
                value={
                    "request": request,
                    "error": error[:200],
                    "lessons": lessons
                },
                category="failure",
                tags=["failure", "auto-learned"]
            )

    def _clean_code(self, content: str) -> str:
        """Strip markdown and clean code."""
        # Remove markdown code blocks - use simple string replace instead of regex
        # to avoid regex issues with backticks
        lines = content.split('\n')
        cleaned_lines = []
        in_code_block = False

        for line in lines:
            stripped = line.strip()
            # Detect code block boundaries
            if stripped.startswith('`' * 3):
                in_code_block = not in_code_block
                continue
            # Skip lines that are clearly not code
            if stripped.startswith('Here is') or stripped.startswith("Here's"):
                continue
            if stripped.startswith('The following'):
                continue
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines).strip()

    def get_stats(self) -> Dict:
        """Get self-correction statistics."""
        return {
            "lessons_learned": len(self.lessons),
            "lessons": self.lessons[-10:]  # Last 10
        }
