"""
Better Prompts — improves first-attempt success rate.

Instead of generic prompts, uses:
1. Task-specific templates
2. Example code patterns
3. Common error prevention
4. Structured output format
"""

from typing import List, Dict, Optional


# System prompts that work well
SYSTEM_PROMPTS = {
    "code": """You are an expert Python developer. Write clean, production-ready code.

RULES:
1. Write COMPLETE code - no placeholders, no "TODO", no "..."
2. All imports must be at the top
3. Use type hints where appropriate
4. Include error handling for common cases
5. Follow PEP 8 style
6. Write code that runs without modifications

Return ONLY the code. No explanations, no markdown, no ```python``` blocks.""",

    "tests": """You are an expert test writer. Write thorough pytest tests.

RULES:
1. Every test must be independent (no shared state)
2. Use descriptive test names (test_<what>_<condition>_<expected>)
3. Cover happy path AND edge cases
4. Use fixtures for setup/teardown
5. Test both success and failure cases
6. Each test should test ONE thing
7. Use assert with clear messages

Return ONLY the test code. No explanations.""",

    "fix": """You are a debugger. Fix the code to make tests pass.

RULES:
1. Read the error message carefully
2. Fix ONLY the specific error - don't rewrite everything
3. Keep working code intact
4. Ensure all imports are correct
5. Test your fix mentally before returning

Return ONLY the complete fixed code.""",
}

# Task-specific prompt templates
TASK_TEMPLATES = {
    "api": """Build a {framework} REST API with these endpoints:
{endpoints}

Requirements:
- Proper error handling (400, 404, 500)
- Input validation
- Consistent response format
- Database integration if needed

Return the complete working code.""",

    "cli": """Build a command-line tool that:
{requirements}

Requirements:
- Use argparse for CLI arguments
- Include --help documentation
- Handle errors gracefully
- Return proper exit codes

Return the complete working code.""",

    "algorithm": """Implement this algorithm:
{description}

Requirements:
- Handle edge cases
- Include time complexity as docstring
- Write unit tests
- Optimize for readability

Return the complete working code.""",
}

# Common error prevention rules
PREVENTION_RULES = {
    "fastapi": [
        "Import RedirectResponse from fastapi.responses, not fastapi",
        "Use Depends() for dependency injection",
        "Use async def for I/O-bound endpoints",
        "Define response_model for consistent responses",
    ],
    "sqlalchemy": [
        "Use declarative_base() from sqlalchemy.ext.declarative",
        "Set check_same_thread=False for SQLite",
        "Use SessionLocal for database sessions",
        "Always close sessions in finally blocks",
    ],
    "pytest": [
        "Use fixtures for setup/teardown",
        "Don't share state between tests",
        "Use tmp_path for temporary files",
        "Mock external services",
    ],
}


class PromptBuilder:
    """
    Builds optimized prompts for better first-attempt success.
    """

    def __init__(self):
        self.system_prompts = SYSTEM_PROMPTS
        self.task_templates = TASK_TEMPLATES
        self.prevention_rules = PREVENTION_RULES

    def build_code_prompt(self, request: str, language: str = "python",
                          context: str = "", tech_stack: List[str] = None) -> str:
        """Build an optimized code generation prompt."""
        prompt_parts = []

        # Add context if available
        if context:
            prompt_parts.append(f"EXISTING PROJECT:\n{context[:1000]}\n")

        # Add prevention rules based on tech stack
        if tech_stack:
            rules = self._get_prevention_rules(tech_stack)
            if rules:
                prompt_parts.append("IMPORTANT RULES:")
                for rule in rules:
                    prompt_parts.append(f"- {rule}")
                prompt_parts.append("")

        # Add the main request
        prompt_parts.append(f"TASK: {request}")
        prompt_parts.append("")
        prompt_parts.append("Write the complete, working code. No placeholders.")

        return "\n".join(prompt_parts)

    def build_test_prompt(self, code: str, language: str = "python") -> str:
        """Build an optimized test generation prompt."""
        prompt = f"""Write comprehensive pytest tests for this code:

```python
{code[:3000]}
```

REQUIREMENTS:
1. Test ALL public functions/methods
2. Test happy path (normal usage)
3. Test edge cases (empty input, None, boundary values)
4. Test error cases (invalid input, missing data)
5. Use descriptive test names
6. Each test should be independent
7. NO placeholder tests (no "assert True")
8. Include at least 5 test cases

Return ONLY the test code."""

        return prompt

    def build_fix_prompt(self, code: str, error: str,
                          test_output: str = "") -> str:
        """Build an optimized fix prompt."""
        # Extract key error info
        error_lines = error.split('\n')
        key_errors = [l for l in error_lines if 'Error' in l or 'FAILED' in l]
        error_summary = '\n'.join(key_errors[:5]) if key_errors else error[:500]

        prompt = f"""Fix this code to make tests pass.

ERROR:
{error_summary}

CODE:
```python
{code[:3000]}
```

INSTRUCTIONS:
1. Fix ONLY the specific error shown
2. Don't rewrite working code
3. Ensure all imports are correct
4. Make sure the code runs without errors

Return the complete fixed code."""

        return prompt

    def get_system_prompt(self, task_type: str) -> str:
        """Get the appropriate system prompt."""
        return self.system_prompts.get(task_type, self.system_prompts["code"])

    def _get_prevention_rules(self, tech_stack: List[str]) -> List[str]:
        """Get prevention rules based on tech stack."""
        rules = []
        for tech in tech_stack:
            tech_lower = tech.lower()
            for key, key_rules in self.prevention_rules.items():
                if key in tech_lower:
                    rules.extend(key_rules)
        return list(set(rules))[:10]  # Unique rules, max 10
