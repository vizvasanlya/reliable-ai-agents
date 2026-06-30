"""
Tests for Phase 2: Memory System
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from memory.store import MemoryStore
from memory.errors import ErrorTracker
from memory.session import SessionMemory
from memory.retrieval import MemoryRetriever


class TestMemoryStore:
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        self.store = MemoryStore(storage_dir=self.test_dir)

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_store_and_retrieve(self):
        self.store.store("key1", "value1", "test")
        result = self.store.get_value("key1")
        assert result == "value1"

    def test_store_overwrites(self):
        self.store.store("key1", "old", "test")
        self.store.store("key1", "new", "test")
        result = self.store.get_value("key1")
        assert result == "new"

    def test_delete(self):
        self.store.store("key1", "value1", "test")
        assert self.store.delete("key1")
        assert self.store.get_value("key1") is None

    def test_search(self):
        self.store.store("auth architecture", "Use JWT", "decision")
        self.store.store("code style", "Use snake_case", "preference")
        results = self.store.search("auth")
        assert len(results) == 1
        assert results[0].key == "auth architecture"

    def test_search_with_category_filter(self):
        self.store.store("decision1", "val1", "decision")
        self.store.store("pattern1", "val2", "pattern")
        results = self.store.search("1", category="decision")
        assert len(results) == 1

    def test_persistence(self):
        self.store.store("persistent", "data", "test")
        # Create new store instance
        store2 = MemoryStore(storage_dir=self.test_dir)
        assert store2.get_value("persistent") == "data"

    def test_stats(self):
        self.store.store("k1", "v1", "decision")
        self.store.store("k2", "v2", "preference")
        stats = self.store.get_stats()
        assert stats["total_entries"] == 2
        assert stats["by_category"]["decision"] == 1


class TestErrorTracker:
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        self.tracker = ErrorTracker(storage_dir=self.test_dir)

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_record_and_find(self):
        self.tracker.record(
            "TypeError", "Missing argument", "No default", "Add default value"
        )
        pattern = self.tracker.find("TypeError: missing argument")
        assert pattern is not None
        assert pattern.solution == "Add default value"

    def test_find_no_match(self):
        pattern = self.tracker.find("SomeUnknownError")
        assert pattern is None

    def test_occurrence_count(self):
        self.tracker.record("E1", "desc", "cause", "fix")
        self.tracker.record("E1", "desc", "cause", "better fix")
        pattern = self.tracker.find("E1")
        assert pattern.occurrences == 2
        assert pattern.solution == "better fix"  # Updated with longer solution

    def test_get_solution(self):
        self.tracker.record("CORS", "CORS error", "Missing header", "Add middleware")
        solution = self.tracker.get_solution("CORS error on /api")
        assert solution == "Add middleware"

    def test_most_common(self):
        self.tracker.record("E1", "d", "c", "s")
        self.tracker.record("E1", "d", "c", "s")
        self.tracker.record("E1", "d", "c", "s")
        self.tracker.record("E2", "d", "c", "s")
        common = self.tracker.get_most_common(1)
        assert common[0].error_type == "E1"
        assert common[0].occurrences == 3

    def test_persistence(self):
        self.tracker.record("Persistent", "d", "c", "s")
        tracker2 = ErrorTracker(storage_dir=self.test_dir)
        assert tracker2.find("Persistent") is not None


class TestSessionMemory:
    def setup(self):
        self.session = SessionMemory(session_id="test-session")

    def test_log_events(self):
        self.session.log_action("read file")
        self.session.log_result("read file", "content")
        self.session.log_error("write file", "permission denied")
        self.session.log_decision("use JWT", "industry standard")
        assert len(self.session.events) == 4

    def test_task_tracking(self):
        self.session.start_task("T1", "Read file")
        assert self.session.get_task("T1").status == "in_progress"

        self.session.complete_task("T1", "content")
        assert self.session.get_task("T1").status == "completed"

    def test_task_failure(self):
        self.session.start_task("T1", "Write file")
        self.session.fail_task("T1", "Permission denied")
        task = self.session.get_task("T1")
        assert task.status == "failed"
        assert task.attempts == 1

    def test_context(self):
        self.session.set_context("project_path", "/my/project")
        assert self.session.get_context("project_path") == "/my/project"
        assert self.session.get_context("missing", "default") == "default"

    def test_progress_summary(self):
        self.session.start_task("T1", "Task 1")
        self.session.start_task("T2", "Task 2")
        self.session.complete_task("T1")
        summary = self.session.get_progress_summary()
        assert summary["total_tasks"] == 2
        assert summary["completed"] == 1

    def test_save_and_load(self):
        self.session.log_action("test action")
        self.session.set_context("key", "value")
        path = os.path.join(tempfile.mkdtemp(), "session.json")
        self.session.save(path)

        new_session = SessionMemory()
        new_session.load(path)
        assert new_session.session_id == "test-session"
        assert new_session.get_context("key") == "value"


class TestMemoryRetriever:
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        self.store = MemoryStore(storage_dir=self.test_dir)
        self.errors = ErrorTracker(storage_dir=self.test_dir)
        self.session = SessionMemory()
        self.retriever = MemoryRetriever(self.store, self.errors, self.session)

        # Add some test data
        self.store.store("auth approach", "Use OAuth2", "decision", "my-project")
        self.store.store("coding style", "Use TypeScript", "preference")
        self.errors.record("TypeError", "Missing arg", "No default", "Add default")

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_for_task(self):
        result = self.retriever.for_task("auth approach")
        assert len(result["relevant_decisions"]) == 1
        assert result["relevant_decisions"][0].value == "Use OAuth2"

    def test_for_error(self):
        pattern = self.retriever.for_error("TypeError: missing argument")
        assert pattern is not None
        assert pattern.solution == "Add default"

    def test_for_project(self):
        result = self.retriever.for_project("my-project")
        assert len(result["decisions"]) == 1

    def test_summary(self):
        summary = self.retriever.summary()
        assert "store_stats" in summary
        assert "error_stats" in summary
        assert "session_progress" in summary


if __name__ == "__main__":
    import traceback

    tests = [
        TestMemoryStore,
        TestErrorTracker,
        TestSessionMemory,
        TestMemoryRetriever,
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
