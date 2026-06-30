"""
Tests for final features: prompts, git, queue, test generation.
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent.prompts import PromptBuilder, SYSTEM_PROMPTS
from agent.git_integration import GitIntegration
from agent.queue import TaskQueue, SimpleQueue, TaskPriority
from agent.test_generator import TestGenerator
from llm.provider import MockProvider


class TestPromptBuilder:
    def setup(self):
        self.builder = PromptBuilder()

    def test_build_code_prompt(self):
        prompt = self.builder.build_code_prompt(
            "Build a REST API",
            "python",
            context="Existing FastAPI app",
            tech_stack=["fastapi", "sqlalchemy"]
        )
        assert "REST API" in prompt
        assert "fastapi" in prompt.lower() or "FastAPI" in prompt
        assert "IMPORTANT RULES" in prompt

    def test_build_test_prompt(self):
        prompt = self.builder.build_test_prompt("def hello(): return 'hi'")
        assert "hello" in prompt
        assert "pytest" in prompt.lower()
        assert "edge cases" in prompt.lower()

    def test_build_fix_prompt(self):
        prompt = self.builder.build_fix_prompt(
            "def add(a,b): return a+b",
            "TypeError: unsupported operand"
        )
        assert "Fix" in prompt
        assert "TypeError" in prompt

    def test_get_system_prompt(self):
        prompt = self.builder.get_system_prompt("code")
        assert "expert" in prompt.lower()
        assert "placeholder" in prompt.lower()

    def test_prevention_rules(self):
        rules = self.builder._get_prevention_rules(["fastapi", "sqlalchemy"])
        assert len(rules) > 0
        assert any("RedirectResponse" in r for r in rules)


class TestGitIntegration:
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        self.git = GitIntegration(self.test_dir)

    def teardown(self):
        try:
            shutil.rmtree(self.test_dir, ignore_errors=True)
        except:
            pass

    def test_init(self):
        result = self.git.init_if_needed()
        assert result.success
        assert os.path.exists(os.path.join(self.test_dir, '.git'))

    def test_commit(self):
        self.git.init_if_needed()
        # Create a file
        with open(os.path.join(self.test_dir, 'test.py'), 'w') as f:
            f.write("print('hello')")

        result = self.git.commit("Add test file")
        assert result.success
        assert result.commit_hash is not None

    def test_auto_commit(self):
        self.git.init_if_needed()
        with open(os.path.join(self.test_dir, 'main.py'), 'w') as f:
            f.write("def hello(): pass")

        result = self.git.auto_commit(['main.py'], "Build hello function")
        assert result.success
        assert "hello" in result.message.lower() or "Build" in result.message

    def test_get_status(self):
        self.git.init_if_needed()
        status = self.git.get_status()
        assert "clean" in status
        assert "modified" in status


class TestQueue:
    def setup(self):
        self.test_dir = tempfile.mkdtemp()

    def teardown(self):
        try:
            shutil.rmtree(self.test_dir, ignore_errors=True)
        except:
            pass

    def test_simple_queue_add(self):
        queue = SimpleQueue(storage_dir=self.test_dir)
        task_id = queue.add("t1", "Build API", "/tmp/project")
        pending = queue.get_pending()
        assert len(pending) == 1
        assert pending[0]["id"] == "t1"

    def test_simple_queue_complete(self):
        queue = SimpleQueue(storage_dir=self.test_dir)
        queue.add("t1", "Build API", "/tmp/project")
        queue.complete("t1", "Done")
        pending = queue.get_pending()
        assert len(pending) == 0

    def test_task_priority(self):
        low = TaskPriority.LOW
        high = TaskPriority.HIGH
        assert high.value < low.value


class TestTestGenerator:
    def setup(self):
        self.provider = MockProvider([
            '''def test_add():
    assert 1 + 1 == 2

def test_subtract():
    assert 5 - 3 == 2

def test_multiply():
    assert 2 * 3 == 6

def test_divide():
    assert 10 / 2 == 5.0

def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        1 / 0
'''
        ])
        self.generator = TestGenerator(self.provider)

    def test_generate(self):
        code = "def add(a, b): return a + b"
        suite = self.generator.generate(code)
        assert suite.test_count >= 5
        assert not suite.has_placeholders
        assert "test_add" in suite.coverage_areas

    def test_validate_no_placeholders(self):
        good_tests = """
def test_add():
    assert 1 + 1 == 2

def test_empty():
    assert [] == []
"""
        assert self.generator.validate_no_placeholders(good_tests)

    def test_detect_placeholders(self):
        bad_tests = """
def test_something():
    assert True

def test_pass():
    pass
"""
        assert not self.generator.validate_no_placeholders(bad_tests)


if __name__ == "__main__":
    import traceback

    tests = [
        TestPromptBuilder,
        TestGitIntegration,
        TestQueue,
        TestTestGenerator,
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
