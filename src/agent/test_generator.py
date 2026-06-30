"""
Better Test Generation — never generates placeholder tests.

Generates comprehensive, real tests that:
1. Actually test the code functionality
2. Cover edge cases
3. Have descriptive names
4. Are independent (no shared state)
5. Never use "assert True"
"""

from typing import List, Optional
from dataclasses import dataclass


@dataclass
class TestSuite:
    code: str
    test_count: int
    coverage_areas: List[str]
    has_placeholders: bool


class TestGenerator:
    """
    Generates real, comprehensive tests.
    """

    def __init__(self, llm_provider):
        self.llm = llm_provider

    def generate(self, code: str, language: str = "python") -> TestSuite:
        """
        Generate comprehensive tests for the given code.
        """
        prompt = self._build_prompt(code, language)

        response = self.llm.complete(
            prompt=prompt,
            system=self._get_system_prompt(),
            temperature=0.2,
            max_tokens=4096
        )

        test_code = self._clean_code(response.content)

        # Validate the tests
        validation = self._validate_tests(test_code)

        return TestSuite(
            code=test_code,
            test_count=validation["count"],
            coverage_areas=validation["coverage"],
            has_placeholders=validation["has_placeholders"]
        )

    def _build_prompt(self, code: str, language: str) -> str:
        """Build the test generation prompt."""
        return f"""Write comprehensive pytest tests for this code:

```{language}
{code[:3000]}
```

REQUIREMENTS:
1. Test ALL public functions and classes
2. Test happy path (normal usage)
3. Test edge cases:
   - Empty inputs
   - None/null values
   - Boundary values (0, max, min)
   - Invalid inputs
4. Test error handling (should raise exceptions)
5. Use descriptive test names: test_<function>_<scenario>_<expected>
6. Each test must be independent (no shared state)
7. Use fixtures for setup if needed
8. NO placeholder tests (forbidden: "assert True", "pass", "...")
9. Include at least 5-10 test cases
10. Add docstrings explaining what each test verifies

FORBIDDEN PATTERNS:
- def test_*: ... (empty tests)
- assert True (placeholder)
- pass (no-op)
- # TODO (incomplete)

Return ONLY the test code."""

    def _get_system_prompt(self) -> str:
        """Get the system prompt for test generation."""
        return """You are an expert test engineer. Write thorough, production-quality tests.

RULES:
1. Every test MUST assert something meaningful
2. Never use "assert True" or "pass" as test body
3. Test both success and failure cases
4. Use clear, descriptive test names
5. Each test should test ONE specific behavior
6. Use pytest fixtures for setup/teardown
7. Mock external dependencies
8. Test edge cases and boundary conditions

Your tests should catch real bugs, not just pass."""

    def _clean_code(self, content: str) -> str:
        """Clean the generated test code."""
        # Remove markdown code blocks
        lines = content.split('\n')
        cleaned = []
        in_block = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('`' * 3):
                in_block = not in_block
                continue
            if not in_block:
                cleaned.append(line)

        return '\n'.join(cleaned).strip()

    def _validate_tests(self, test_code: str) -> dict:
        """Validate the generated tests."""
        lines = test_code.split('\n')

        # Count test functions
        test_count = 0
        coverage = []
        has_placeholders = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Count test functions
            if stripped.startswith('def test_'):
                test_count += 1

                # Get function name for coverage
                func_name = stripped.split('(')[0].replace('def ', '')
                coverage.append(func_name)

            # Check for placeholder tests
            if stripped in ['assert True', 'pass', '...', '# TODO']:
                has_placeholders = True

            # Check for empty test bodies
            if stripped.startswith('def test_') and i + 1 < len(lines):
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if next_line in ['pass', '...', '']:
                    has_placeholders = True

        return {
            "count": test_count,
            "coverage": coverage[:10],  # First 10 test names
            "has_placeholders": has_placeholders
        }

    def validate_no_placeholders(self, test_code: str) -> bool:
        """Check that tests don't contain placeholders."""
        forbidden = [
            'assert True',
            'assert False',
            'pass',
            '# TODO',
            '# FIXME',
            '...',
        ]

        for pattern in forbidden:
            if pattern in test_code:
                return False

        # Check for empty test functions
        lines = test_code.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('def test_'):
                # Check next few lines for meaningful content
                has_assertion = False
                for j in range(i + 1, min(i + 5, len(lines))):
                    if 'assert' in lines[j] or 'with pytest' in lines[j]:
                        has_assertion = True
                        break
                if not has_assertion:
                    return False

        return True
