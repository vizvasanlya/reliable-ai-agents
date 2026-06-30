"""
LLM Planner — uses language models for intelligent task decomposition.

Unlike the keyword-based parser, this uses LLM reasoning to:
- Understand ambiguous requests
- Generate better task breakdowns
- Estimate effort more accurately
- Ask clarifying questions when needed
"""

import json
from typing import Dict, List, Optional

from llm.provider import LLMProvider, LLMResponse
from planning.decomposer import Task


PLANNING_SYSTEM = """You are a software project planner. Break down user requests into executable tasks.

CRITICAL RULE: Output ONLY valid JSON. No explanation, no markdown, no code blocks.
Your entire response must be a JSON array like this example:

[{"id": "T1", "description": "task description", "tools_needed": ["write_file"], "acceptance_criteria": ["criteria"], "estimated_minutes": 10, "dependencies": []}]

Rules:
1. Each task should be small enough to complete in one step
2. Tasks should have clear acceptance criteria
3. Identify dependencies between tasks
4. Estimate time in minutes for each task
5. Be specific — "implement user auth" is better than "build feature"

Fields for each task:
- id: string (T1, T2, etc.)
- description: what to do
- tools_needed: list of tools (read_file, write_file, run_command, grep, glob)
- acceptance_criteria: list of strings
- estimated_minutes: integer
- dependencies: list of task IDs that must complete first
"""

PLANNING_PROMPT = """Break down this request into executable tasks:

"{request}"

Context:
- Project path: {project_path}
- Language: {language}
- Framework: {framework}

Respond with ONLY a JSON array of tasks. No explanation."""


class LLMPlanner:
    """
    Uses LLM to create intelligent task plans.
    """

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def plan(self, request: str, project_path: str = ".",
             language: str = "python",
             framework: str = None) -> List[Task]:
        """
        Create a plan using LLM reasoning.
        """
        prompt = PLANNING_PROMPT.format(
            request=request,
            project_path=project_path,
            language=language,
            framework=framework or "none"
        )

        response = self.provider.complete(
            prompt=prompt,
            system=PLANNING_SYSTEM,
            temperature=0.3,  # Lower temperature for structured output
            max_tokens=2048
        )

        if response.finish_reason == "error":
            # Fallback to basic decomposition
            return self._fallback_plan(request)

        # Strip markdown code blocks
        import re
        content = response.content
        content = re.sub(r'```(?:json)?\s*\n?', '', content)
        content = re.sub(r'```\s*$', '', content, flags=re.MULTILINE)
        content = content.strip()

        try:
            # Parse JSON response
            tasks_data = json.loads(content)
            return self._parse_tasks(tasks_data)
        except (json.JSONDecodeError, KeyError):
            # Try to extract JSON from response
            return self._extract_and_parse(content)

    def clarify(self, request: str) -> Optional[str]:
        """
        Ask clarifying questions if the request is ambiguous.
        """
        prompt = f"""The user said: "{request}"

Is this request clear enough to plan? If not, what questions should we ask?

Respond with:
- "CLEAR" if the request is unambiguous
- Or a single clarifying question if more info is needed."""

        response = self.provider.complete(
            prompt=prompt,
            system="You are a helpful assistant that clarifies requirements.",
            temperature=0.3,
            max_tokens=200
        )

        content = response.content.strip()
        if content.upper() == "CLEAR":
            return None
        return content

    def estimate_effort(self, tasks: List[Task]) -> Dict[str, int]:
        """
        Use LLM to estimate effort for each task.
        """
        task_descriptions = "\n".join([
            f"- {t.id}: {t.description}" for t in tasks
        ])

        prompt = f"""Estimate the time (in minutes) for each task:

{task_descriptions}

Respond with JSON: {{"T1": minutes, "T2": minutes, ...}}"""

        response = self.provider.complete(
            prompt=prompt,
            system="Estimate software task durations realistically.",
            temperature=0.3,
            max_tokens=500
        )

        try:
            estimates = json.loads(response.content)
            return estimates
        except json.JSONDecodeError:
            return {}

    def _parse_tasks(self, tasks_data: List[Dict]) -> List[Task]:
        """Parse LLM response into Task objects."""
        tasks = []
        for item in tasks_data:
            task = Task(
                id=item.get("id", f"T{len(tasks)+1}"),
                description=item.get("description", ""),
                tools_needed=item.get("tools_needed", []),
                acceptance_criteria=item.get("acceptance_criteria", []),
                estimated_minutes=item.get("estimated_minutes", 10),
                dependencies=item.get("dependencies", [])
            )
            tasks.append(task)
        return tasks

    def _extract_and_parse(self, content: str) -> List[Task]:
        """Try to extract JSON from LLM response."""
        # Strip markdown code blocks if present
        import re
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*$', '', content)
        content = content.strip()

        # Look for JSON array in the response
        start = content.find('[')
        end = content.rfind(']') + 1

        if start != -1 and end > start:
            try:
                tasks_data = json.loads(content[start:end])
                return self._parse_tasks(tasks_data)
            except json.JSONDecodeError:
                pass

        return self._fallback_plan(content)

    def _fallback_plan(self, request: str) -> List[Task]:
        """Basic fallback when LLM fails to parse JSON."""
        # Create clean, actionable tasks from the request
        return [
            Task(
                id="T1",
                description=f"Implement the main code for: {request[:100]}",
                tools_needed=["write_file"],
                acceptance_criteria=["Code implemented"],
                estimated_minutes=20
            ),
            Task(
                id="T2",
                description="Write unit tests for the implementation",
                dependencies=["T1"],
                tools_needed=["write_file"],
                acceptance_criteria=["Tests written"],
                estimated_minutes=15
            ),
            Task(
                id="T3",
                description="Verify code runs without errors",
                dependencies=["T2"],
                tools_needed=["run_command"],
                acceptance_criteria=["Code runs successfully"],
                estimated_minutes=10
            ),
        ]
