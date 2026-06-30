"""
Task Executor — actually does the work.

Executes individual tasks by:
1. Determining what tool to use
2. Running the tool with appropriate parameters
3. Handling errors
4. Returning results
"""

from typing import Any, Dict, Optional

from tools.base import ToolRegistry, ToolResult, ToolStatus
from planning.decomposer import Task


class TaskExecutor:
    """
    Executes individual tasks using the available tools.

    This is the bridge between planning and action.
    """

    def __init__(self, tools: ToolRegistry):
        self.tools = tools
        self.execution_log: list = []

    def execute(self, task: Task, context: Optional[Dict] = None) -> ToolResult:
        """
        Execute a single task.

        This is a simplified version — the real implementation would
        use LLM reasoning to determine the exact tool calls needed.
        """
        context = context or {}

        # Log the execution attempt
        self.execution_log.append({
            "task_id": task.id,
            "description": task.description,
            "status": "started"
        })

        # Determine which tool to use based on task description
        tool_name = self._select_tool(task)
        if not tool_name:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"No suitable tool found for: {task.description}"
            )

        # Build parameters based on task and context
        params = self._build_params(task, tool_name, context)

        # Execute the tool
        result = self.tools.execute(tool_name, **params)

        # Update log
        self.execution_log[-1]["status"] = "completed" if result.success else "failed"
        self.execution_log[-1]["result"] = result.output if result.success else result.error

        return result

    def _select_tool(self, task: Task) -> Optional[str]:
        """Select the best tool for a task based on its description."""
        desc = task.description.lower()

        # Map task descriptions to tools
        if "read" in desc or "inspect" in desc or "analyze" in desc:
            return "read_file"
        elif "write" in desc or "create" in desc or "implement" in desc:
            return "write_file"
        elif "edit" in desc or "modify" in desc or "update" in desc:
            return "edit_file"
        elif "run" in desc or "execute" in desc or "test" in desc:
            return "run_command"
        elif "search" in desc or "find" in desc:
            return "grep"
        elif "list" in desc or "explore" in desc:
            return "glob"
        else:
            # Default to read_file for investigation tasks
            return "read_file"

    def _build_params(self, task: Task, tool_name: str,
                      context: Dict) -> Dict[str, Any]:
        """Build parameters for the tool based on task and context."""
        project_path = context.get("project_path", ".")

        if tool_name == "read_file":
            # For read tasks, try to find relevant files
            return {"path": context.get("target_file", f"{project_path}/README.md")}
        elif tool_name == "write_file":
            return {
                "path": context.get("target_file", f"{project_path}/output.txt"),
                "content": f"# {task.description}\n\nImplementation placeholder"
            }
        elif tool_name == "run_command":
            return {"command": context.get("command", "echo 'Task executed'"), "cwd": project_path}
        elif tool_name == "grep":
            return {"pattern": context.get("pattern", ".*"), "path": project_path}
        elif tool_name == "glob":
            return {"pattern": context.get("pattern", "**/*"), "path": project_path}
        else:
            return {}

    def get_log(self) -> list:
        """Get the execution log."""
        return self.execution_log
