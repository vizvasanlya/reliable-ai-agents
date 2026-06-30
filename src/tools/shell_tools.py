"""
Shell tools — run commands on the system.
"""

import subprocess
import os
from typing import Any, Dict

from .base import Tool, ToolResult, ToolStatus


class RunCommandTool(Tool):
    """Run a shell command and return its output."""

    @property
    def name(self) -> str:
        return "run_command"

    @property
    def description(self) -> str:
        return "Run a shell command and return stdout/stderr"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to execute"
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory (optional)"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 30)"
                }
            },
            "required": ["command"]
        }

    def execute(self, command: str, cwd: str = None, timeout: int = 30, **kwargs) -> ToolResult:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )

            output = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }

            if result.returncode == 0:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=result.stdout,
                    metadata=output
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Command failed (exit code {result.returncode}): {result.stderr}",
                    output=result.stdout,
                    metadata=output
                )

        except subprocess.TimeoutExpired:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Command timed out after {timeout}s: {command}"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Failed to run command: {e}"
            )
