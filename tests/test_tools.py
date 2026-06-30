"""
Tests for Phase 1: Tool Interface
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tools.base import ToolRegistry, ToolResult, ToolStatus, create_default_registry
from tools.file_tools import ReadFileTool, WriteFileTool, EditFileTool
from tools.shell_tools import RunCommandTool
from tools.search_tools import GrepTool, GlobTool


class TestReadFileTool:
    def setup(self):
        self.tool = ReadFileTool()
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.txt")
        with open(self.test_file, 'w') as f:
            f.write("line 1\nline 2\nline 3\nline 4\nline 5\n")

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_read_existing_file(self):
        result = self.tool.execute(path=self.test_file)
        assert result.success
        assert "line 1" in result.output
        assert "line 5" in result.output

    def test_read_with_offset(self):
        result = self.tool.execute(path=self.test_file, offset=2)
        assert result.success
        assert "line 1" not in result.output
        assert "line 3" in result.output

    def test_read_with_limit(self):
        result = self.tool.execute(path=self.test_file, limit=2)
        assert result.success
        assert "line 3" not in result.output

    def test_read_nonexistent_file(self):
        result = self.tool.execute(path="/nonexistent/file.txt")
        assert not result.success
        assert "not found" in result.error.lower()


class TestWriteFileTool:
    def setup(self):
        self.tool = WriteFileTool()
        self.test_dir = tempfile.mkdtemp()

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_write_new_file(self):
        path = os.path.join(self.test_dir, "new.txt")
        result = self.tool.execute(path=path, content="hello world")
        assert result.success
        assert os.path.exists(path)
        with open(path) as f:
            assert f.read() == "hello world"

    def test_write_creates_directories(self):
        path = os.path.join(self.test_dir, "sub", "dir", "file.txt")
        result = self.tool.execute(path=path, content="nested")
        assert result.success
        assert os.path.exists(path)


class TestEditFileTool:
    def setup(self):
        self.tool = EditFileTool()
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "edit.txt")
        with open(self.test_file, 'w') as f:
            f.write("hello world\nfoo bar\n")

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_edit_replaces_text(self):
        result = self.tool.execute(
            path=self.test_file,
            old_text="hello",
            new_text="goodbye"
        )
        assert result.success
        with open(self.test_file) as f:
            content = f.read()
        assert "goodbye world" in content
        assert "hello" not in content

    def test_edit_fails_on_nonexistent_text(self):
        result = self.tool.execute(
            path=self.test_file,
            old_text="nonexistent",
            new_text="replacement"
        )
        assert not result.success
        assert "not found" in result.error.lower()


class TestRunCommandTool:
    def setup(self):
        self.tool = RunCommandTool()

    def test_run_echo(self):
        result = self.tool.execute(command="echo hello")
        assert result.success
        assert "hello" in result.output

    def test_run_failing_command(self):
        result = self.tool.execute(command="exit 1")
        assert not result.success
        assert result.metadata["returncode"] == 1


class TestGrepTool:
    def setup(self):
        self.tool = GrepTool()
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "grep_test.txt")
        with open(self.test_file, 'w') as f:
            f.write("def hello():\n    pass\n\ndef world():\n    pass\n")

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_grep_finds_pattern(self):
        result = self.tool.execute(pattern="def \\w+", path=self.test_dir)
        assert result.success
        assert len(result.output) == 2

    def test_grep_no_matches(self):
        result = self.tool.execute(pattern="class \\w+", path=self.test_dir)
        assert result.success
        assert len(result.output) == 0


class TestGlobTool:
    def setup(self):
        self.tool = GlobTool()
        self.test_dir = tempfile.mkdtemp()
        # Create test files
        for name in ["a.py", "b.py", "c.txt"]:
            with open(os.path.join(self.test_dir, name), 'w') as f:
                f.write("content")

    def teardown(self):
        shutil.rmtree(self.test_dir)

    def test_glob_finds_py_files(self):
        result = self.tool.execute(pattern="*.py", path=self.test_dir)
        assert result.success
        assert len(result.output) == 2

    def test_glob_finds_all_files(self):
        result = self.tool.execute(pattern="*", path=self.test_dir)
        assert result.success
        assert len(result.output) == 3


class TestToolRegistry:
    def setup(self):
        self.registry = create_default_registry()

    def test_registry_has_tools(self):
        assert len(self.registry) == 6

    def test_registry_lists_tools(self):
        tools = self.registry.list_tools()
        names = [t["name"] for t in tools]
        assert "read_file" in names
        assert "write_file" in names
        assert "run_command" in names

    def test_registry_executes_tool(self):
        result = self.registry.execute("run_command", command="echo test")
        assert result.success
        assert "test" in result.output

    def test_registry_unknown_tool(self):
        result = self.registry.execute("nonexistent_tool")
        assert not result.success
        assert "Unknown tool" in result.error


if __name__ == "__main__":
    import traceback

    tests = [
        TestReadFileTool,
        TestWriteFileTool,
        TestEditFileTool,
        TestRunCommandTool,
        TestGrepTool,
        TestGlobTool,
        TestToolRegistry,
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
