"""
Tests for Phase 3: Planning Engine
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from planning.parser import IntentParser
from planning.decomposer import TaskDecomposer, Task
from planning.scheduler import TaskScheduler
from planning.replanner import Replanner


class TestIntentParser:
    def setup(self):
        self.parser = IntentParser()

    def test_parse_create_api(self):
        intent = self.parser.parse("Build me a REST API for users")
        assert intent.action == "create"
        assert intent.target == "api"

    def test_parse_fix_bug(self):
        intent = self.parser.parse("Fix the login error")
        assert intent.action == "fix"

    def test_parse_refactor(self):
        intent = self.parser.parse("Refactor the database code")
        assert intent.action == "refactor"

    def test_parse_research(self):
        intent = self.parser.parse("Research authentication options")
        assert intent.action == "research"

    def test_constraints_detection(self):
        intent = self.parser.parse("Build a Python API with React frontend")
        assert "language:python" in intent.constraints
        assert "framework:react" in intent.constraints

    def test_needs_clarification(self):
        intent = self.parser.parse("do something")
        assert self.parser.needs_clarification(intent)


class TestTaskDecomposer:
    def setup(self):
        self.decomposer = TaskDecomposer()

    def test_decompose_create_api(self):
        tasks = self.decomposer.decompose("create", "api", [])
        assert len(tasks) >= 3
        assert tasks[0].description.startswith("Plan")
        assert any("implement" in t.description.lower() for t in tasks)

    def test_decompose_fix(self):
        tasks = self.decomposer.decompose("fix", "bug", [])
        assert len(tasks) == 4
        assert tasks[0].description == "Reproduce the issue"

    def test_decompose_refactor(self):
        tasks = self.decomposer.decompose("refactor", "code", [])
        assert len(tasks) == 4

    def test_task_has_id(self):
        tasks = self.decomposer.decompose("create", "api", [])
        for task in tasks:
            assert task.id.startswith("T")

    def test_dependencies_exist(self):
        tasks = self.decomposer.decompose("create", "api", [])
        for task in tasks:
            for dep in task.dependencies:
                assert any(t.id == dep for t in tasks)


class TestTaskScheduler:
    def setup(self):
        self.scheduler = TaskScheduler()

    def test_schedule_linear(self):
        tasks = [
            Task(id="T1", description="Step 1", dependencies=[]),
            Task(id="T2", description="Step 2", dependencies=["T1"]),
            Task(id="T3", description="Step 3", dependencies=["T2"]),
        ]
        waves = self.scheduler.schedule(tasks)
        assert len(waves) == 3
        assert waves[0][0].id == "T1"
        assert waves[1][0].id == "T2"

    def test_schedule_parallel(self):
        tasks = [
            Task(id="T1", description="Independent 1", dependencies=[]),
            Task(id="T2", description="Independent 2", dependencies=[]),
        ]
        waves = self.scheduler.schedule(tasks)
        assert len(waves) == 1
        assert len(waves[0]) == 2

    def test_get_next_tasks(self):
        tasks = [
            Task(id="T1", description="Step 1", dependencies=[]),
            Task(id="T2", description="Step 2", dependencies=["T1"]),
        ]
        next_tasks = self.scheduler.get_next_tasks(tasks, set())
        assert len(next_tasks) == 1
        assert next_tasks[0].id == "T1"

    def test_estimate_total_time(self):
        tasks = [
            Task(id="T1", description="Fast", dependencies=[], estimated_minutes=5),
            Task(id="T2", description="Slow", dependencies=["T1"], estimated_minutes=10),
        ]
        total = self.scheduler.estimate_total_time(tasks)
        assert total == 15


class TestReplanner:
    def setup(self):
        self.replanner = Replanner()

    def test_replan_on_failure(self):
        tasks = [
            Task(id="T1", description="Do something", status="completed"),
            Task(id="T2", description="Failed task", status="failed"),
            Task(id="T3", description="Depends on T2", dependencies=["T2"]),
        ]
        new_tasks = self.replanner.replan_on_failure(tasks, tasks[1], "Error")
        assert len(new_tasks) == 2  # T1 + investigation
        assert any("investigate" in t.description.lower() for t in new_tasks)

    def test_simplify(self):
        tasks = [
            Task(id="T1", description="Done", status="completed"),
            Task(id="T2", description="Pending", status="pending"),
        ]
        simplified = self.replanner.simplify(tasks)
        assert len(simplified) == 1
        assert simplified[0].id == "T2"


if __name__ == "__main__":
    import traceback

    tests = [
        TestIntentParser,
        TestTaskDecomposer,
        TestTaskScheduler,
        TestReplanner,
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
