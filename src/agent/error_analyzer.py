"""
Better Error Analysis — understands errors deeply and fixes them intelligently.

Unlike basic error extraction, this system:
1. Parses full traceback to find root cause
2. Categorizes errors (import, syntax, logic, runtime)
3. Maps errors to known fix patterns
4. Provides specific fix instructions to LLM
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ErrorCategory(Enum):
    IMPORT = "import"           # Missing/wrong imports
    SYNTAX = "syntax"           # Syntax errors
    TYPE = "type"               # Type errors
    ATTRIBUTE = "attribute"     # Missing attributes
    LOGIC = "logic"             # Logic errors (assertion failures)
    RUNTIME = "runtime"         # Runtime errors
    DEPENDENCY = "dependency"   # Missing packages
    UNKNOWN = "unknown"


@dataclass
class ErrorAnalysis:
    category: ErrorCategory
    message: str
    file: str
    line: int
    root_cause: str
    fix_suggestion: str
    confidence: float


class ErrorAnalyzer:
    """
    Deep error analysis for better auto-fixing.
    """

    # Common error patterns and their fixes
    FIX_PATTERNS = {
        "ImportError: cannot import name": {
            "category": ErrorCategory.IMPORT,
            "fix": "Check the correct import path. The name may be in a submodule."
        },
        "ModuleNotFoundError": {
            "category": ErrorCategory.DEPENDENCY,
            "fix": "Install the missing package with pip install <package_name>"
        },
        "SyntaxError: invalid syntax": {
            "category": ErrorCategory.SYNTAX,
            "fix": "Check for missing colons, parentheses, or quotes"
        },
        "SyntaxError: '(' was never closed": {
            "category": ErrorCategory.SYNTAX,
            "fix": "Find the unclosed parenthesis and close it"
        },
        "IndentationError": {
            "category": ErrorCategory.SYNTAX,
            "fix": "Fix indentation - use consistent spaces (4 recommended)"
        },
        "TypeError: unsupported operand": {
            "category": ErrorCategory.TYPE,
            "fix": "Check variable types before operations"
        },
        "AttributeError: object has no attribute": {
            "category": ErrorCategory.ATTRIBUTE,
            "fix": "Check the object type and available methods"
        },
        "NameError: name 'X' is not defined": {
            "category": ErrorCategory.IMPORT,
            "fix": "Variable or function not defined. Check spelling and scope."
        },
        "FileNotFoundError": {
            "category": ErrorCategory.RUNTIME,
            "fix": "Check file path exists and is correct"
        },
        "AssertionError": {
            "category": ErrorCategory.LOGIC,
            "fix": "The code logic is wrong. Check expected vs actual values."
        },
    }

    def analyze(self, error_output: str, code: str = "") -> ErrorAnalysis:
        """
        Deeply analyze an error and suggest a fix.
        """
        # Extract key error info
        error_lines = error_output.split('\n')

        # Find the main error line
        error_msg = ""
        error_file = ""
        error_line = 0

        for line in error_lines:
            # Match Python traceback format
            match = re.search(r'File "(.+?)", line (\d+)', line)
            if match:
                error_file = match.group(1)
                error_line = int(match.group(2))

            # Match error message
            if 'Error:' in line or 'Exception:' in line:
                error_msg = line.strip()

        if not error_msg:
            # Try to find error in last lines
            for line in reversed(error_lines[-10:]):
                if line.strip() and ('error' in line.lower() or 'failed' in line.lower()):
                    error_msg = line.strip()
                    break

        # Categorize error
        category = self._categorize(error_msg)

        # Get root cause
        root_cause = self._find_root_cause(error_msg, code)

        # Get fix suggestion
        fix = self._suggest_fix(error_msg, category)

        # Calculate confidence
        confidence = self._calculate_confidence(error_msg, category)

        return ErrorAnalysis(
            category=category,
            message=error_msg,
            file=error_file,
            line=error_line,
            root_cause=root_cause,
            fix_suggestion=fix,
            confidence=confidence
        )

    def get_fix_prompt(self, analysis: ErrorAnalysis, code: str) -> str:
        """Generate a detailed fix prompt for the LLM."""
        return f"""Fix this {analysis.category.value} error.

ERROR: {analysis.message}
FILE: {analysis.file}
LINE: {analysis.line}
ROOT CAUSE: {analysis.root_cause}

SUGGESTED FIX: {analysis.fix_suggestion}

CURRENT CODE:
```python
{code[:3000]}
```

INSTRUCTIONS:
1. Fix the specific error at line {analysis.line}
2. The root cause is: {analysis.root_cause}
3. Apply this fix: {analysis.fix_suggestion}
4. Make sure all imports are correct
5. Return ONLY the complete fixed code"""

    def _categorize(self, error_msg: str) -> ErrorCategory:
        """Categorize the error type."""
        error_lower = error_msg.lower()

        for pattern, info in self.FIX_PATTERNS.items():
            if pattern.lower() in error_lower:
                return info["category"]

        # Default categorization
        if 'import' in error_lower:
            return ErrorCategory.IMPORT
        elif 'syntax' in error_lower:
            return ErrorCategory.SYNTAX
        elif 'type' in error_lower:
            return ErrorCategory.TYPE
        elif 'attribute' in error_lower:
            return ErrorCategory.ATTRIBUTE
        elif 'assert' in error_lower or 'expected' in error_lower:
            return ErrorCategory.LOGIC
        elif 'error' in error_lower:
            return ErrorCategory.RUNTIME

        return ErrorCategory.UNKNOWN

    def _find_root_cause(self, error_msg: str, code: str) -> str:
        """Determine the root cause of the error."""
        if not error_msg:
            return "Unknown error"

        # Check for common patterns
        if "cannot import name" in error_msg:
            # Extract the name being imported
            match = re.search(r"cannot import name '(\w+)'", error_msg)
            if match:
                return f"Module doesn't have '{match.group(1)}'. Check the correct import path."

        if "No module named" in error_msg:
            match = re.search(r"No module named '(\w+)'", error_msg)
            if match:
                return f"Package '{match.group(1)}' not installed. Run: pip install {match.group(1)}"

        if "was never closed" in error_msg:
            return "Missing closing bracket, parenthesis, or quote"

        if "invalid syntax" in error_msg:
            return "Python syntax error - check for missing colons, quotes, or parentheses"

        if "not defined" in error_msg:
            match = re.search(r"name '(\w+)' is not defined", error_msg)
            if match:
                return f"Variable '{match.group(1)}' not defined. Check spelling and scope."

        if "has no attribute" in error_msg:
            match = re.search(r"has no attribute '(\w+)'", error_msg)
            if match:
                return f"Object doesn't have method/attribute '{match.group(1)}'"

        return error_msg[:200]

    def _suggest_fix(self, error_msg: str, category: ErrorCategory) -> str:
        """Suggest a specific fix based on the error."""
        # Check known patterns
        for pattern, info in self.FIX_PATTERNS.items():
            if pattern.lower() in error_msg.lower():
                return info["fix"]

        # Category-based fixes
        fixes = {
            ErrorCategory.IMPORT: "Check import paths and ensure package is installed",
            ErrorCategory.SYNTAX: "Fix syntax errors - check brackets, colons, quotes",
            ErrorCategory.TYPE: "Check variable types before operations",
            ErrorCategory.ATTRIBUTE: "Verify object has the expected method/attribute",
            ErrorCategory.LOGIC: "Check expected vs actual values in assertions",
            ErrorCategory.RUNTIME: "Check file paths, network connections, permissions",
            ErrorCategory.DEPENDENCY: "Install missing packages with pip",
        }

        return fixes.get(category, "Analyze the error and fix the root cause")

    def _calculate_confidence(self, error_msg: str, category: ErrorCategory) -> float:
        """Calculate confidence in the analysis."""
        # Higher confidence for common, well-understood errors
        if category in (ErrorCategory.IMPORT, ErrorCategory.SYNTAX, ErrorCategory.DEPENDENCY):
            return 0.9
        elif category in (ErrorCategory.TYPE, ErrorCategory.ATTRIBUTE):
            return 0.7
        elif category == ErrorCategory.LOGIC:
            return 0.5
        else:
            return 0.3
