"""
Agent Loop — the main control flow for autonomous agent operation.

Cycle: Plan → Execute → Verify → Learn

This is the heart of the reliable AI agent system.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from tools.base import ToolRegistry, ToolResult, ToolStatus, create_default_registry
from tools.file_tools import ReadFileTool, WriteFileTool, EditFileTool
from tools.shell_tools import RunCommandTool
from tools.search_tools import GrepTool, GlobTool
from memory.store import MemoryStore
from memory.errors import ErrorTracker
from memory.session import SessionMemory
from memory.retrieval import MemoryRetriever
from planning.parser import IntentParser
from planning.decomposer import TaskDecomposer, Task
from planning.scheduler import TaskScheduler
from planning.replanner import Replanner
from execution.executor import TaskExecutor
from execution.error_handler import ErrorHandler, RecoveryAction
from execution.progress import ProgressTracker
from verification.syntax import SyntaxChecker
from verification.security import SecurityScanner
from verification.confidence import ConfidenceScorer


@dataclass
class AgentConfig:
    """Configuration for the agent loop."""
    max_retries: int = 3
    auto_verify: bool = True
    learn_from_errors: bool = True
    confidence_threshold: float = 0.7
    project_path: str = "."


@dataclass
class AgentResult:
    """Result of an agent session."""
    success: bool
    tasks_completed: int
    tasks_failed: int
    message: str
    confidence: float
    history: List[Dict[str, Any]] = field(default_factory=list)


class AgentLoop:
    """
    The main agent control loop.

    Implements: Plan → Execute → Verify → Learn

    This is the integration layer that connects all components.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()

        # Initialize components
        self.tools = self._init_tools()
        self.memory = MemoryStore()
        self.errors = ErrorTracker()
        self.session = SessionMemory()
        self.retriever = MemoryRetriever(self.memory, self.errors, self.session)

        # Planning
        self.parser = IntentParser()
        self.decomposer = TaskDecomposer()
        self.scheduler = TaskScheduler()
        self.replanner = Replanner()

        # Execution
        self.executor = TaskExecutor(self.tools)
        self.error_handler = ErrorHandler(self.errors)
        self.progress = ProgressTracker()

        # Verification
        self.syntax_checker = SyntaxChecker()
        self.security_scanner = SecurityScanner()
        self.confidence_scorer = ConfidenceScorer()

    def _init_tools(self) -> ToolRegistry:
        """Initialize the tool registry with all available tools."""
        registry = ToolRegistry()
        registry.register(ReadFileTool())
        registry.register(WriteFileTool())
        registry.register(EditFileTool())
        registry.register(RunCommandTool())
        registry.register(GrepTool())
        registry.register(GlobTool())
        return registry

    def run(self, request: str) -> AgentResult:
        """
        Execute a user request from start to finish.

        This is the main entry point for agent operation.
        """
        self.session.log_action(f"Received request: {request}")

        # Phase 1: Parse intent
        intent = self.parser.parse(request)
        self.session.log_decision(
            f"Parsed intent: action={intent.action}, target={intent.target}",
            f"Confidence: {intent.confidence}"
        )

        # Check if we need clarification
        if self.parser.needs_clarification(intent):
            return AgentResult(
                success=False,
                tasks_completed=0,
                tasks_failed=0,
                message=f"Need more information: {', '.join(intent.missing_info)}",
                confidence=0.0
            )

        # Phase 2: Create plan
        tasks = self.decomposer.decompose(
            intent.action,
            intent.target,
            intent.constraints
        )
        self.session.log_action(f"Created plan with {len(tasks)} tasks")

        # Phase 3: Execute tasks
        self.progress.start()
        completed_ids = set()

        while not self.progress.is_complete(tasks):
            # Get tasks ready to execute
            ready_tasks = self.scheduler.get_next_tasks(tasks, completed_ids)

            if not ready_tasks:
                # No tasks ready — might be a dependency issue
                self.session.log_error("No tasks ready", "Possible circular dependency")
                break

            # Execute the first ready task
            task = ready_tasks[0]
            self.session.start_task(task.id, task.description)

            # Check memory for known solutions
            known_error = self.retriever.for_error(task.description)

            # Execute
            result = self.executor.execute(task, {
                "project_path": self.config.project_path
            })

            if result.success:
                task.status = "completed"
                task.result = str(result.output)
                completed_ids.add(task.id)
                self.session.complete_task(task.id, result.output)
                self.session.log_result(f"Completed {task.id}", result.output)

                # Verify if enabled
                if self.config.auto_verify:
                    self._verify_output(task, result)
            else:
                task.attempts += 1
                task.error = result.error
                self.session.fail_task(task.id, result.error)

                # Handle error
                analysis = self.error_handler.analyze(
                    result.error,
                    task.attempts
                )

                self.session.log_error(
                    f"Failed {task.id}: {result.error}",
                    f"Severity: {analysis.severity.value}, Action: {analysis.action.value}"
                )

                if analysis.action == RecoveryAction.RETRY and task.attempts < self.config.max_retries:
                    # Will retry on next loop iteration
                    pass
                elif analysis.action == RecoveryAction.REPLAN:
                    tasks = self.replanner.replan_on_failure(tasks, task, result.error)
                    completed_ids = {t.id for t in tasks if t.status == "completed"}
                elif analysis.action == RecoveryAction.ESCALATE:
                    return AgentResult(
                        success=False,
                        tasks_completed=len([t for t in tasks if t.status == "completed"]),
                        tasks_failed=1,
                        message=f"Escalating: {result.error}",
                        confidence=0.0
                    )
                else:
                    # Skip this task
                    task.status = "failed"
                    completed_ids.add(task.id)

        # Phase 4: Summary
        completed = sum(1 for t in tasks if t.status == "completed")
        failed = sum(1 for t in tasks if t.status == "failed")

        # Calculate confidence
        confidence_report = self.confidence_scorer.score(
            "# Generated code placeholder",
            tests_passed=(failed == 0)
        )

        # Learn from session
        if self.config.learn_from_errors:
            self._learn_from_session()

        return AgentResult(
            success=failed == 0,
            tasks_completed=completed,
            tasks_failed=failed,
            message=self.progress.summary(tasks),
            confidence=confidence_report.overall,
            history=self.session.events
        )

    def _verify_output(self, task: Task, result: ToolResult):
        """Verify the output of a completed task."""
        if not result.output:
            return

        # Check syntax if it looks like code
        output_str = str(result.output)
        if any(kw in output_str for kw in ['def ', 'function ', 'class ', '{', 'import ']):
            syntax_result = self.syntax_checker.check(output_str)
            if not syntax_result.valid:
                self.session.log_error(
                    f"Syntax error in {task.id}",
                    str(syntax_result.errors)
                )

    def _learn_from_session(self):
        """Extract lessons from the current session."""
        for event in self.session.events:
            if event.event_type == "error":
                # Could extract and record new error patterns here
                pass

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the agent's memory."""
        return self.retriever.summary()
