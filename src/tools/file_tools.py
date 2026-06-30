"""
File tools — read, write, and edit files on disk.
"""

import os
from typing import Any, Dict

from .base import Tool, ToolResult, ToolStatus


class ReadFileTool(Tool):
    """Read the contents of a file."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file at the given path"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file"
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (0-indexed)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read"
                }
            },
            "required": ["path"]
        }

    def execute(self, path: str, offset: int = 0, limit: int = 0, **kwargs) -> ToolResult:
        if not os.path.exists(path):
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"File not found: {path}"
            )

        if not os.path.isfile(path):
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Not a file: {path}"
            )

        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

            total_lines = len(lines)

            if offset > 0:
                lines = lines[offset:]

            if limit > 0:
                lines = lines[:limit]

            content = ''.join(lines)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=content,
                metadata={
                    "path": path,
                    "total_lines": total_lines,
                    "lines_read": len(lines),
                    "offset": offset
                }
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Failed to read {path}: {e}"
            )


class WriteFileTool(Tool):
    """Write content to a file, creating directories if needed."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file, creating parent directories if needed"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to write to"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write"
                }
            },
            "required": ["path", "content"]
        }

    def execute(self, path: str, content: str, **kwargs) -> ToolResult:
        try:
            # Create parent directories if needed
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"Written {len(content)} bytes to {path}",
                metadata={
                    "path": path,
                    "bytes_written": len(content)
                }
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Failed to write {path}: {e}"
            )


class EditFileTool(Tool):
    """Edit a file by replacing text."""

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return "Edit a file by replacing a specific text string with new content"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to edit"
                },
                "old_text": {
                    "type": "string",
                    "description": "Exact text to find and replace"
                },
                "new_text": {
                    "type": "string",
                    "description": "Text to replace it with"
                }
            },
            "required": ["path", "old_text", "new_text"]
        }

    def execute(self, path: str, old_text: str, new_text: str, **kwargs) -> ToolResult:
        if not os.path.exists(path):
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"File not found: {path}"
            )

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            if old_text not in content:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Text not found in {path}"
                )

            count = content.count(old_text)
            if count > 1:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Found {count} matches for old_text — provide more context to make it unique"
                )

            new_content = content.replace(old_text, new_text, 1)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"Edited {path}",
                metadata={"path": path, "replacement_made": True}
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Failed to edit {path}: {e}"
            )
