"""
Tests for new features: daemon, multi-file, context, cross-session, error analysis.
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent.cross_session import CrossSessionLearning
from agent.context import ContextReader
from agent.error_analyzer import ErrorAnalyzer, ErrorCategory
from llm.provider import MockProvider


class TestCrossSessionLearning:
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        self.learning = CrossSessionLearning(storage_dir=self.test_dir)

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_learn_and_retrieve(self):
        self.learning.learn(
            "ImportError: cannot import X",
            "Import X from correct module",
            "python",
            "project1"
        )
        rules = self.learning.apply_before_generation("test", "python", "project1")
        assert len(rules) > 0
        assert "Import X from correct module" in rules

    def test_persistence(self):
        self.learning.learn("E1", "F1", "python")
        learning2 = CrossSessionLearning(storage_dir=self.test_dir)
        assert len(learning2.lessons) == 1

    def test_project_association(self):
        self.learning.learn("E1", "F1", "python", "proj1")
        self.learning.learn("E2", "F2", "python", "proj2")
        rules = self.learning.apply_before_generation("test", "python", "proj1")
        assert "F1" in rules

    def test_stats(self):
        self.learning.learn("E1", "F1", "python")
        stats = self.learning.get_stats()
        assert stats["total_lessons"] == 1


class TestContextReader:
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        # Create test project
        with open(os.path.join(self.test_dir, "main.py"), 'w') as f:
            f.write("from fastapi import FastAPI\napp = FastAPI()")
        with open(os.path.join(self.test_dir, "requirements.txt"), 'w') as f:
            f.write("fastapi>=0.100.0\nuvicorn>=0.23.0")

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_read_project(self):
        reader = ContextReader()
        context = reader.read_project(self.test_dir)
        assert len(context.files) > 0
        assert "python" in context.tech_stack
        assert "fastapi" in context.dependencies

    def test_context_prompt(self):
        reader = ContextReader()
        context = reader.read_project(self.test_dir)
        prompt = reader.get_context_prompt(context)
        assert "fastapi" in prompt.lower()


class TestErrorAnalyzer:
    def setup(self):
        self.analyzer = ErrorAnalyzer()

    def test_analyze_import_error(self):
        error = "ImportError: cannot import name 'RedirectResponse' from 'fastapi'"
        analysis = self.analyzer.analyze(error)
        assert analysis.category == ErrorCategory.IMPORT
        assert "RedirectResponse" in analysis.root_cause

    def test_analyze_syntax_error(self):
        error = "SyntaxError: '(' was never closed, line 51"
        analysis = self.analyzer.analyze(error)
        assert analysis.category == ErrorCategory.SYNTAX
        assert "unclosed" in analysis.fix_suggestion.lower() or "close" in analysis.fix_suggestion.lower()

    def test_analyze_module_error(self):
        error = "ModuleNotFoundError: No module named 'sqlalchemy'"
        analysis = self.analyzer.analyze(error)
        assert analysis.category == ErrorCategory.DEPENDENCY
        assert "install" in analysis.fix_suggestion.lower() or "pip" in analysis.fix_suggestion.lower()

    def test_analyze_type_error(self):
        error = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        analysis = self.analyzer.analyze(error)
        assert analysis.category == ErrorCategory.TYPE

    def test_analyze_attribute_error(self):
        error = "AttributeError: 'dict' object has no attribute 'items'"
        analysis = self.analyzer.analyze(error)
        assert analysis.category == ErrorCategory.ATTRIBUTE

    def test_fix_prompt(self):
        error = "ImportError: cannot import name 'X'"
        analysis = self.analyzer.analyze(error, "import X from fastapi")
        prompt = self.analyzer.get_fix_prompt(analysis, "import X")
        assert "ImportError" in prompt
        assert "FIX" in prompt.upper()


class TestDaemon:
    def setup(self):
        pass

    def teardown(self):
        pass

    def test_daemon_import(self):
        # Just test that daemon module can be imported
        import daemon
        assert hasattr(daemon, 'start')
        assert hasattr(daemon, 'stop')
        assert hasattr(daemon, 'status')


class TestProjectBuilder:
    def setup(self):
        self.provider = MockProvider([
            '[{"path": "main.py", "description": "Main app"}, {"path": "test_main.py", "description": "Tests"}]',
            'def hello(): return "world"',
            'def test_hello(): assert hello() == "world"'
        ])

    def test_build_project(self):
        from agent.project_builder import ProjectBuilder
        builder = ProjectBuilder(self.provider)
        files = builder.build("Create a hello world app", "/tmp/test")
        assert len(files) >= 2
        assert any(f.path == "main.py" for f in files)


if __name__ == "__main__":
    import traceback

    tests = [
        TestCrossSessionLearning,
        TestContextReader,
        TestErrorAnalyzer,
        TestDaemon,
        TestProjectBuilder,
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
