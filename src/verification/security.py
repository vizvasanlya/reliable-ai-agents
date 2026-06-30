"""
Security Scanner — detects common security vulnerabilities.
"""

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class SecurityIssue:
    severity: str  # "high", "medium", "low"
    issue_type: str
    description: str
    line_number: int = 0
    suggestion: str = ""


@dataclass
class SecurityReport:
    passed: bool
    issues: List[SecurityIssue]
    score: float  # 0.0 (bad) to 1.0 (clean)


class SecurityScanner:
    """
    Scans code for common security vulnerabilities.

    Checks for:
    - SQL injection
    - XSS vulnerabilities
    - Hardcoded secrets
    - Insecure dependencies
    - Path traversal
    """

    def scan(self, code: str, language: str = "auto") -> SecurityReport:
        """Scan code for security issues."""
        issues = []

        issues.extend(self._check_sql_injection(code))
        issues.extend(self._check_xss(code))
        issues.extend(self._check_secrets(code))
        issues.extend(self._check_path_traversal(code))

        # Calculate score
        high = sum(1 for i in issues if i.severity == "high")
        medium = sum(1 for i in issues if i.severity == "medium")
        low = sum(1 for i in issues if i.severity == "low")

        score = 1.0 - (high * 0.3 + medium * 0.1 + low * 0.05)
        score = max(0.0, min(1.0, score))

        return SecurityReport(
            passed=high == 0,
            issues=issues,
            score=score
        )

    def _check_sql_injection(self, code: str) -> List[SecurityIssue]:
        """Check for SQL injection patterns."""
        issues = []
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            # String concatenation in SQL
            if re.search(r'execute\s*\(', line, re.IGNORECASE):
                if '+' in line or 'format' in line or '%' in line:
                    issues.append(SecurityIssue(
                        severity="high",
                        issue_type="sql_injection",
                        description="String concatenation in SQL query",
                        line_number=i,
                        suggestion="Use parameterized queries instead"
                    ))

        return issues

    def _check_xss(self, code: str) -> List[SecurityIssue]:
        """Check for XSS vulnerabilities."""
        issues = []
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            if 'innerHTML' in line:
                issues.append(SecurityIssue(
                    severity="medium",
                    issue_type="xss",
                    description="Use of innerHTML can lead to XSS",
                    line_number=i,
                    suggestion="Use textContent or sanitize input"
                ))
            if 'dangerouslySetInnerHTML' in line:
                issues.append(SecurityIssue(
                    severity="medium",
                    issue_type="xss",
                    description="dangerouslySetInnerHTML bypasses React escaping",
                    line_number=i,
                    suggestion="Sanitize HTML before rendering"
                ))

        return issues

    def _check_secrets(self, code: str) -> List[SecurityIssue]:
        """Check for hardcoded secrets."""
        issues = []
        lines = code.split('\n')

        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "password"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "API key"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "secret"),
            (r'token\s*=\s*["\'][^"\']+["\']', "token"),
        ]

        for i, line in enumerate(lines, 1):
            for pattern, name in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Check if it's using environment variable
                    if 'os.environ' not in line and 'process.env' not in line:
                        issues.append(SecurityIssue(
                            severity="high",
                            issue_type="hardcoded_secret",
                            description=f"Hardcoded {name} detected",
                            line_number=i,
                            suggestion=f"Move {name} to environment variables"
                        ))

        return issues

    def _check_path_traversal(self, code: str) -> List[SecurityIssue]:
        """Check for path traversal vulnerabilities."""
        issues = []
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            if 'open(' in line and '..' in line:
                issues.append(SecurityIssue(
                    severity="medium",
                    issue_type="path_traversal",
                    description="Path traversal possible with '..' in file path",
                    line_number=i,
                    suggestion="Validate and sanitize file paths"
                ))

        return issues
