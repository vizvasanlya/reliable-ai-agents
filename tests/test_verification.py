"""
Tests for Phase 5: Verification Layer
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from verification.syntax import SyntaxChecker
from verification.security import SecurityScanner
from verification.confidence import ConfidenceScorer


class TestSyntaxChecker:
    def setup(self):
        self.checker = SyntaxChecker()

    def test_valid_python(self):
        result = self.checker.check("def hello():\n    pass", "python")
        assert result.valid

    def test_invalid_python(self):
        result = self.checker.check("def hello(\n    pass", "python")
        assert not result.valid
        assert len(result.errors) > 0

    def test_valid_json(self):
        result = self.checker.check('{"key": "value"}', "json")
        assert result.valid

    def test_invalid_json(self):
        result = self.checker.check('{"key": }', "json")
        assert not result.valid

    def test_auto_detect_python(self):
        result = self.checker.check("import os\ndef main(): pass")
        assert result.language == "python"
        assert result.valid

    def test_auto_detect_json(self):
        result = self.checker.check('{"name": "test"}')
        assert result.language == "json"
        assert result.valid


class TestSecurityScanner:
    def setup(self):
        self.scanner = SecurityScanner()

    def test_clean_code(self):
        code = "x = 1\nprint(x)"
        report = self.scanner.scan(code)
        assert report.passed
        assert report.score > 0.9

    def test_sql_injection(self):
        code = 'execute("SELECT * FROM users WHERE id=" + user_id)'
        report = self.scanner.scan(code)
        assert not report.passed
        assert any(i.issue_type == "sql_injection" for i in report.issues)

    def test_hardcoded_secret(self):
        code = 'password = "secret123"'
        report = self.scanner.scan(code)
        assert not report.passed
        assert any(i.issue_type == "hardcoded_secret" for i in report.issues)

    def test_xss_vulnerability(self):
        code = 'element.innerHTML = userInput'
        report = self.scanner.scan(code)
        assert any(i.issue_type == "xss" for i in report.issues)

    def test_safe_password(self):
        code = 'password = os.environ.get("PASSWORD")'
        report = self.scanner.scan(code)
        assert not any(i.issue_type == "hardcoded_secret" for i in report.issues)


class TestConfidenceScorer:
    def setup(self):
        self.scorer = ConfidenceScorer()

    def test_high_confidence(self):
        code = 'def hello():\n    return "world"'
        report = self.scorer.score(code, "python", tests_passed=True)
        assert report.overall > 0.8
        assert not report.needs_human_review

    def test_low_confidence_syntax_error(self):
        code = 'def hello(\n    pass'
        report = self.scorer.score(code, "python")
        # Syntax error reduces confidence and triggers human review
        assert report.syntax_score < 1.0
        assert report.needs_human_review

    def test_low_confidence_security_issue(self):
        code = 'password = "secret123"'
        report = self.scorer.score(code, "python")
        assert report.security_score < 1.0

    def test_trend(self):
        # Score a few things to build history
        self.scorer.score("def ok(): pass", "python", True)
        self.scorer.score("def ok(): pass", "python", True)
        trend = self.scorer.get_trend()
        assert trend in ("stable", "improving", "insufficient_data")


if __name__ == "__main__":
    import traceback

    tests = [
        TestSyntaxChecker,
        TestSecurityScanner,
        TestConfidenceScorer,
    ]

    passed = 0
    failed = 0

    for test_class in tests:
        suite = test_class()
        for method_name in dir(suite):
            if method_name.startswith("test_"):
                suite.setup()
                try:
                    getattr(suite, method_name)()
                    print(f"  PASS: {test_class.__name__}.{method_name}")
                    passed += 1
                except Exception as e:
                    print(f"  FAIL: {test_class.__name__}.{method_name}: {e}")
                    traceback.print_exc()
                    failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
