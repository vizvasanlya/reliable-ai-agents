"""
Tests for Phase 6: Full Agent System
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent.loop import AgentLoop, AgentConfig
from agent.session import AgentSession
from agent.trust import TrustSystem


class TestAgentLoop:
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        self.config = AgentConfig(project_path=self.test_dir)
        self.agent = AgentLoop(self.config)

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_agent_creation(self):
        assert self.agent is not None
        assert len(self.agent.tools) == 6

    def test_simple_request(self):
        result = self.agent.run("Research the codebase")
        assert result is not None
        assert isinstance(result.tasks_completed, int)

    def test_memory_stats(self):
        stats = self.agent.get_memory_stats()
        assert "store_stats" in stats

    def test_intent_parsing(self):
        result = self.agent.run("Create a Python API")
        assert result is not None


class TestAgentSession:
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        self.session = AgentSession(project_path=self.test_dir)

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_chat(self):
        result = self.session.chat("Research authentication")
        assert result is not None
        assert len(self.session.history) == 1

    def test_stats(self):
        self.session.chat("Do something")
        stats = self.session.get_stats()
        assert stats["requests"] == 1

    def test_reset(self):
        self.session.chat("Do something")
        self.session.reset()
        assert len(self.session.history) == 0


class TestTrustSystem:
    def setup(self):
        self.trust = TrustSystem()

    def test_initial_trust(self):
        level = self.trust.get_trust()
        assert level.score == 0.5

    def test_success_increases_trust(self):
        initial = self.trust.get_trust().score
        self.trust.record_success()
        assert self.trust.get_trust().score > initial

    def test_failure_decreases_trust(self):
        initial = self.trust.get_trust().score
        self.trust.record_failure()
        assert self.trust.get_trust().score < initial

    def test_consecutive_failures(self):
        for _ in range(3):
            self.trust.record_failure()
        assert self.trust.needs_supervision()

    def test_auto_execute_check(self):
        for _ in range(10):
            self.trust.record_success()
        assert self.trust.can_auto_execute()

    def test_stats(self):
        self.trust.record_success()
        self.trust.record_failure()
        stats = self.trust.get_stats()
        assert stats["total_successes"] == 1
        assert stats["total_failures"] == 1


if __name__ == "__main__":
    import traceback

    tests = [
        TestAgentLoop,
        TestAgentSession,
        TestTrustSystem,
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
