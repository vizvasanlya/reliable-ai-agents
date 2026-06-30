"""
Tests for Phase 4: Execution Engine
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tools.base import create_default_registry
from execution.executor import TaskExecutor
from execution.error_handler import ErrorHandler, ErrorSeverity, RecoveryAction
from execution.progress import ProgressTracker
from memory.errors import ErrorTracker
from planning.decomposer import Task


class TestTaskExecutor:
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        self.tools = create_default_registry()
        self.executor = TaskExecutor(self.tools)

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_execute_read_task(self):
        # Create a test file
        test_file = os.path.join(self.test_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("hello")

        task = Task(id="T1", description="Read the file")
        result = self.executor.execute(task, {
            "project_path": self.test_dir,
            "target_file": test_file
        })
        assert result.success
        assert "hello" in str(result.output)

    def test_execute_write_task(self):
        task = Task(id="T1", description="Write a file")
        result = self.executor.execute(task, {
            "project_path": self.test_dir,
            "target_file": os.path.join(self.test_dir, "output.txt")
        })
        assert result.success

    def test_execution_log(self):
        task = Task(id="T1", description="Read file")
        self.executor.execute(task, {"project_path": self.test_dir})
        log = self.executor.get_log()
        assert len(log) == 1
        assert log[0]["task_id"] == "T1"


class TestErrorHandler:
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        self.tracker = ErrorTracker(storage_dir=self.test_dir)
        self.handler = ErrorHandler(self.tracker)

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_analyze_low_severity(self):
        analysis = self.handler.analyze("minor warning", 1)
        assert analysis.severity == ErrorSeverity.LOW
        assert analysis.action == RecoveryAction.RETRY

    def test_analyze_high_severity(self):
        analysis = self.handler.analyze("Permission denied", 1)
        assert analysis.severity == ErrorSeverity.CRITICAL
        assert analysis.action == RecoveryAction.ESCALATE

    def test_analyze_with_known_solution(self):
        self.tracker.record("CORS", "CORS error", "Missing header", "Add middleware")
        analysis = self.handler.analyze("CORS error", 1)
        assert analysis.known_solution == "Add middleware"
        assert analysis.action == RecoveryAction.RETRY

    def test_retry_limit(self):
        analysis = self.handler.analyze("some error", 3)
        assert analysis.action in (RecoveryAction.REPLAN, RecoveryAction.ESCALATE, RecoveryAction.SKIP)


class TestProgressTracker:
    def setup(self):
        self.tracker = ProgressTracker()

    def test_snapshot(self):
        tasks = [
            Task(id="T1", description="Done", status="completed"),
            Task(id="T2", description="Pending", status="pending"),
        ]
        snap = self.tracker.snapshot(tasks)
        assert snap.total_tasks == 2
        assert snap.completed == 1
        assert snap.completion_percent == 50.0

    def test_is_complete(self):
        tasks = [
            Task(id="T1", description="Done", status="completed"),
            Task(id="T2", description="Failed", status="failed"),
        ]
        assert self.tracker.is_complete(tasks)

    def test_summary(self):
        tasks = [
            Task(id="T1", description="Done", status="completed"),
            Task(id="T2", description="Pending", status="pending"),
        ]
        self.tracker.start()
        summary = self.tracker.summary(tasks)
        assert "1/2" in summary


if __name__ == "__main__":
    import traceback

    tests = [
        TestTaskExecutor,
        TestErrorHandler,
        TestProgressTracker,
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
