"""
Tests for self-correction loop and learning system.
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent.learning import LearningSystem, Lesson
from llm.provider import MockProvider


class TestLearningSystem:
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        self.learning = LearningSystem(storage_dir=self.test_dir)

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_learn_from_error(self):
        lesson = self.learning.learn_from_error(
            "ImportError: cannot import name 'RedirectResponse'",
            "Import RedirectResponse from fastapi.responses instead of fastapi",
            "python"
        )
        assert lesson.id.startswith("lesson_")
        assert "RedirectResponse" in lesson.rule

    def test_get_relevant_fixes(self):
        self.learning.learn_from_error(
            "ImportError: cannot import name 'RedirectResponse'",
            "Import from fastapi.responses",
            "python"
        )
        fixes = self.learning.get_relevant_fixes(
            "ImportError: cannot import name 'RedirectResponse'"
        )
        assert len(fixes) > 0
        assert any("fastapi.responses" in f for f in fixes)

    def test_get_pre_generation_rules(self):
        self.learning.learn_from_error(
            "ImportError: cannot import name 'RedirectResponse'",
            "Import from fastapi.responses",
            "python"
        )
        # Mark as helpful
        for lesson in self.learning.lessons.values():
            lesson.times_helped = 1

        rules = self.learning.get_pre_generation_rules("python")
        assert len(rules) > 0

    def test_persistence(self):
        self.learning.learn_from_error(
            "SomeError",
            "SomeFix",
            "python"
        )
        # Create new instance
        learning2 = LearningSystem(storage_dir=self.test_dir)
        assert len(learning2.lessons) == 1

    def test_stats(self):
        self.learning.learn_from_error("E1", "F1", "python")
        self.learning.learn_from_error("E2", "F2", "python")
        stats = self.learning.get_stats()
        assert stats["total_lessons"] == 2
        assert stats["total_patterns"] == 2

    def test_extract_pattern(self):
        pattern = self.learning._extract_pattern(
            "ImportError: cannot import name 'RedirectResponse'"
        )
        assert "redirect" in pattern.lower() or "import" in pattern.lower()

    def test_record_fix_result(self):
        lesson = self.learning.learn_from_error("E1", "F1", "python")
        self.learning.record_fix_result(lesson.id, worked=True)
        assert self.learning.lessons[lesson.id].times_helped == 1


class TestSelfCorrectionLoop:
    def setup(self):
        self.test_dir = tempfile.mkdtemp()

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_clean_code(self):
        from agent.self_correction import SelfCorrectionLoop
        loop = SelfCorrectionLoop(llm_provider=MockProvider())

        # Test markdown stripping
        code = "```python\ndef hello():\n    pass\n```"
        cleaned = loop._clean_code(code)
        assert "```" not in cleaned
        assert "def hello" in cleaned

    def test_verify_syntax_valid(self):
        from agent.self_correction import SelfCorrectionLoop
        loop = SelfCorrectionLoop(llm_provider=MockProvider())

        ok, err = loop._verify_syntax("def hello(): pass", "python")
        assert ok
        assert err == ""

    def test_verify_syntax_invalid(self):
        from agent.self_correction import SelfCorrectionLoop
        loop = SelfCorrectionLoop(llm_provider=MockProvider())

        ok, err = loop._verify_syntax("def hello(", "python")
        assert not ok
        assert "Line" in err or "SyntaxError" in err


if __name__ == "__main__":
    import traceback

    tests = [
        TestLearningSystem,
        TestSelfCorrectionLoop,
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
                finally:
                    if hasattr(suite, 'teardown'):
                        suite.teardown()

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
