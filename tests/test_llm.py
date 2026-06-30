"""
Tests for LLM integration (brain), code generation (hands), and CLI.
"""

import os
import sys
import json
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm.provider import MockProvider, LLMResponse
from llm.planner import LLMPlanner
from llm.coder import LLMCoder
from planning.decomposer import Task


class TestMockProvider:
    def setup(self):
        self.provider = MockProvider(["Hello", "World"])

    def test_basic_complete(self):
        response = self.provider.complete("test prompt")
        assert response.content == "Hello"
        assert response.finish_reason == "stop"

    def test_multiple_completions(self):
        r1 = self.provider.complete("first")
        r2 = self.provider.complete("second")
        assert r1.content == "Hello"
        assert r2.content == "World"

    def test_chat(self):
        messages = [{"role": "user", "content": "hi"}]
        response = self.provider.chat(messages)
        assert response.content == "Hello"


class TestLLMPlanner:
    def setup(self):
        # Mock provider that returns valid JSON plan
        plan_json = json.dumps([
            {
                "id": "T1",
                "description": "Analyze requirements",
                "tools_needed": ["read_file", "grep"],
                "acceptance_criteria": ["Requirements documented"],
                "estimated_minutes": 10,
                "dependencies": []
            },
            {
                "id": "T2",
                "description": "Implement the feature",
                "tools_needed": ["write_file"],
                "acceptance_criteria": ["Code written"],
                "estimated_minutes": 30,
                "dependencies": ["T1"]
            },
            {
                "id": "T3",
                "description": "Test the implementation",
                "tools_needed": ["run_command"],
                "acceptance_criteria": ["Tests pass"],
                "estimated_minutes": 10,
                "dependencies": ["T2"]
            }
        ])
        self.provider = MockProvider([plan_json])
        self.planner = LLMPlanner(self.provider)

    def test_plan_creates_tasks(self):
        tasks = self.planner.plan("Build a user API")
        assert len(tasks) == 3
        assert tasks[0].id == "T1"
        assert tasks[1].id == "T2"
        assert tasks[2].id == "T3"

    def test_plan_has_dependencies(self):
        tasks = self.planner.plan("Build a user API")
        assert tasks[1].dependencies == ["T1"]
        assert tasks[2].dependencies == ["T2"]

    def test_plan_has_tools(self):
        tasks = self.planner.plan("Build a user API")
        assert "read_file" in tasks[0].tools_needed
        assert "write_file" in tasks[1].tools_needed

    def test_clarify_clear_request(self):
        self.provider = MockProvider(["CLEAR"])
        planner = LLMPlanner(self.provider)
        result = planner.clarify("Build a REST API for users")
        assert result is None

    def test_clarify_ambiguous_request(self):
        self.provider = MockProvider(["What language should I use?"])
        planner = LLMPlanner(self.provider)
        result = planner.clarify("Build something")
        assert result is not None
        assert "language" in result.lower()

    def test_fallback_on_invalid_json(self):
        provider = MockProvider(["not valid json"])
        planner = LLMPlanner(provider)
        tasks = planner.plan("Do something")
        # Should fallback to basic plan
        assert len(tasks) >= 1


class TestLLMCoder:
    def setup(self):
        self.provider = MockProvider(['def hello():\n    return "world"'])
        self.coder = LLMCoder(self.provider)

    def test_generate_file(self):
        code = self.coder.generate_file(
            "Create a hello function",
            "hello.py",
            "python"
        )
        assert "def hello" in code

    def test_fix_code(self):
        self.provider = MockProvider(["def fixed():\n    pass"])
        coder = LLMCoder(self.provider)
        fixed = coder.fix_code("def broken(", "SyntaxError")
        assert "def fixed" in fixed

    def test_write_tests(self):
        self.provider = MockProvider(["def test_hello():\n    assert True"])
        coder = LLMCoder(self.provider)
        tests = coder.write_tests("def hello(): pass")
        assert "test_hello" in tests

    def test_generation_history(self):
        self.coder.generate_file("test", "test.py", "python")
        self.coder.generate_file("test2", "test2.py", "python")
        stats = self.coder.get_stats()
        assert stats["total_generations"] == 2
        assert stats["successful"] == 2

    def test_generate_module(self):
        module_json = json.dumps({
            "files": [
                {"path": "__init__.py", "content": "# Module init"},
                {"path": "main.py", "content": "def main(): pass"}
            ]
        })
        provider = MockProvider([module_json])
        coder = LLMCoder(provider)
        files = coder.generate_module("mymodule", "A test module")
        assert "__init__.py" in files
        assert "main.py" in files


class TestCLI:
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

    def teardown(self):
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    def test_cli_help(self):
        # Just test that CLI can be imported without error
        from cli import main
        # Can't actually run argparse in test, but import should work


class TestIntegration:
    """Integration tests combining multiple components."""

    def setup(self):
        self.test_dir = tempfile.mkdtemp()

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_planner_to_coder_flow(self):
        """Test that planner output can be used by coder."""
        # Create a plan
        plan_json = json.dumps([
            {
                "id": "T1",
                "description": "Create a hello world function",
                "tools_needed": ["write_file"],
                "acceptance_criteria": ["Function exists"],
                "estimated_minutes": 5,
                "dependencies": []
            }
        ])
        provider = MockProvider([plan_json, 'def hello():\n    return "Hello, World!"'])
        planner = LLMPlanner(provider)
        coder = LLMCoder(provider)

        # Plan
        tasks = planner.plan("Create a hello world function")
        assert len(tasks) == 1

        # Generate code for the task
        code = coder.generate_file(
            tasks[0].description,
            "hello.py",
            "python"
        )
        assert "def hello" in code


if __name__ == "__main__":
    import traceback

    tests = [
        TestMockProvider,
        TestLLMPlanner,
        TestLLMCoder,
        TestCLI,
        TestIntegration,
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
