"""
Syntax Checker — validates code syntax.
"""

import ast
import json
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SyntaxResult:
    valid: bool
    language: str
    errors: List[str]
    line_numbers: List[int]


class SyntaxChecker:
    """
    Checks code syntax for common languages.

    Supports: Python, JSON, JavaScript (basic)
    """

    def check(self, code: str, language: str = "auto") -> SyntaxResult:
        """Check syntax of code."""
        if language == "auto":
            language = self._detect_language(code)

        if language == "python":
            return self._check_python(code)
        elif language == "json":
            return self._check_json(code)
        elif language == "javascript":
            return self._check_javascript(code)
        else:
            return SyntaxResult(
                valid=True,
                language=language,
                errors=["No syntax checker for this language"],
                line_numbers=[]
            )

    def _detect_language(self, code: str) -> str:
        """Auto-detect language from code content."""
        code_stripped = code.strip()
        if code_stripped.startswith('{') or code_stripped.startswith('['):
            return "json"
        if 'def ' in code or 'import ' in code or 'class ' in code:
            return "python"
        if 'function ' in code or 'const ' in code or 'let ' in code:
            return "javascript"
        return "unknown"

    def _check_python(self, code: str) -> SyntaxResult:
        """Check Python syntax."""
        try:
            ast.parse(code)
            return SyntaxResult(
                valid=True,
                language="python",
                errors=[],
                line_numbers=[]
            )
        except SyntaxError as e:
            return SyntaxResult(
                valid=False,
                language="python",
                errors=[f"Line {e.lineno}: {e.msg}"],
                line_numbers=[e.lineno] if e.lineno else []
            )

    def _check_json(self, code: str) -> SyntaxResult:
        """Check JSON syntax."""
        try:
            json.loads(code)
            return SyntaxResult(
                valid=True,
                language="json",
                errors=[],
                line_numbers=[]
            )
        except json.JSONDecodeError as e:
            return SyntaxResult(
                valid=False,
                language="json",
                errors=[f"Line {e.lineno}: {e.msg}"],
                line_numbers=[e.lineno] if e.lineno else []
            )

    def _check_javascript(self, code: str) -> SyntaxResult:
        """
        Basic JavaScript syntax check.

        Limited — checks for common issues like unbalanced brackets.
        """
        errors = []
        line_numbers = []

        # Check balanced brackets
        pairs = {'(': ')', '[': ']', '{': '}'}
        stack = []
        lines = code.split('\n')

        for line_num, line in enumerate(lines, 1):
            for char in line:
                if char in pairs:
                    stack.append((char, line_num))
                elif char in pairs.values():
                    if not stack:
                        errors.append(f"Line {line_num}: Unmatched closing '{char}'")
                        line_numbers.append(line_num)
                    else:
                        open_char, _ = stack.pop()
                        if pairs[open_char] != char:
                            errors.append(f"Line {line_num}: Mismatched brackets")
                            line_numbers.append(line_num)

        # Check for unclosed brackets
        for open_char, line_num in stack:
            errors.append(f"Line {line_num}: Unclosed '{open_char}'")
            line_numbers.append(line_num)

        return SyntaxResult(
            valid=len(errors) == 0,
            language="javascript",
            errors=errors,
            line_numbers=line_numbers
        )
