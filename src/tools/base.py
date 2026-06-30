"""
Base tool abstraction — every agent action goes through a Tool.

Tools are the agent's hands. They read files, write code, run commands,
search codebases, and interact with the outside world.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class ToolStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    BLOCKED = "blocked"


@dataclass
class ToolResult:
    """Result of a tool execution."""
    status: ToolStatus
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == ToolStatus.SUCCESS

    def __repr__(self):
        if self.success:
            return f"ToolResult(SUCCESS, output={repr(self.output)[:100]})"
        return f"ToolResult({self.status.value}, error={self.error})"


class Tool(ABC):
    """
    Base class for all tools.

    Every tool has:
    - A name (for discovery)
    - A description (for the agent to understand when to use it)
    - Parameters schema (what inputs it accepts)
    - An execute method (does the actual work)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """What this tool does, for the agent to understand."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON Schema describing expected parameters."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def validate_params(self, params: Dict) -> List[str]:
        """
        Validate parameters against the schema.
        Returns list of error messages (empty if valid).
        """
        errors = []
        required = self.parameters.get("required", [])
        properties = self.parameters.get("properties", {})

        for param in required:
            if param not in params:
                errors.append(f"Missing required parameter: {param}")

        for key, value in params.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type == "string" and not isinstance(value, str):
                    errors.append(f"Parameter '{key}' must be a string")
                elif expected_type == "integer" and not isinstance(value, int):
                    errors.append(f"Parameter '{key}' must be an integer")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Parameter '{key}' must be a boolean")

        return errors

    def safe_execute(self, **kwargs) -> ToolResult:
        """
        Execute with validation and error handling.
        Use this instead of execute() for production use.
        """
        errors = self.validate_params(kwargs)
        if errors:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Validation errors: {'; '.join(errors)}"
            )

        try:
            return self.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"{type(e).__name__}: {str(e)}"
            )


class ToolRegistry:
    """
    Registry of available tools.

    Agents discover tools at runtime and choose which to use
    based on the task at hand.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with their schemas."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in self._tools.values()
        ]

    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unknown tool: {tool_name}"
            )
        return tool.safe_execute(**kwargs)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


def create_default_registry() -> ToolRegistry:
    """Create a registry with all default tools registered."""
    from .file_tools import ReadFileTool, WriteFileTool, EditFileTool
    from .shell_tools import RunCommandTool
    from .search_tools import GrepTool, GlobTool

    registry = ToolRegistry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(EditFileTool())
    registry.register(RunCommandTool())
    registry.register(GrepTool())
    registry.register(GlobTool())

    return registry
