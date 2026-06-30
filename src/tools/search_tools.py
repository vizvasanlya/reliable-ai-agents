"""
Search tools — find files and content in codebases.
"""

import os
import re
from typing import Any, Dict, List

from .base import Tool, ToolResult, ToolStatus


class GrepTool(Tool):
    """Search file contents using regex patterns."""

    @property
    def name(self) -> str:
        return "grep"

    @property
    def description(self) -> str:
        return "Search file contents using regex patterns"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for"
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: current)"
                },
                "include": {
                    "type": "string",
                    "description": "File pattern to include (e.g., '*.py')"
                }
            },
            "required": ["pattern"]
        }

    def execute(self, pattern: str, path: str = ".", include: str = None, **kwargs) -> ToolResult:
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Invalid regex pattern: {e}"
            )

        matches = []
        path = os.path.abspath(path)

        for root, dirs, files in os.walk(path):
            # Skip hidden dirs and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in [
                'node_modules', '__pycache__', 'venv', '.git', 'dist', 'build'
            ]]

            for filename in files:
                if include:
                    import fnmatch
                    if not fnmatch.fnmatch(filename, include):
                        continue

                filepath = os.path.join(root, filename)

                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                matches.append({
                                    "file": filepath,
                                    "line": line_num,
                                    "content": line.strip()
                                })
                except (PermissionError, UnicodeDecodeError):
                    continue

        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=matches,
            metadata={
                "pattern": pattern,
                "matches_found": len(matches),
                "search_path": path
            }
        )


class GlobTool(Tool):
    """Find files matching a glob pattern."""

    @property
    def name(self) -> str:
        return "glob"

    @property
    def description(self) -> str:
        return "Find files matching a glob pattern (e.g., '**/*.py', 'src/**/*.js')"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match files"
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: current)"
                }
            },
            "required": ["pattern"]
        }

    def execute(self, pattern: str, path: str = ".", **kwargs) -> ToolResult:
        import glob as glob_module

        search_path = os.path.join(path, pattern)
        matches = glob_module.glob(search_path, recursive=True)

        # Filter to only files (not directories)
        file_matches = [m for m in matches if os.path.isfile(m)]

        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=sorted(file_matches),
            metadata={
                "pattern": pattern,
                "matches_found": len(file_matches),
                "search_path": os.path.abspath(path)
            }
        )
