"""
Agent Session — manages multi-turn interactions.
"""

from typing import Any, Dict, Optional

from .loop import AgentLoop, AgentConfig, AgentResult


class AgentSession:
    """
    Manages a conversation session with the agent.

    Maintains context across multiple requests within a session.
    """

    def __init__(self, project_path: str = "."):
        self.config = AgentConfig(project_path=project_path)
        self.agent = AgentLoop(self.config)
        self.history: list = []

    def chat(self, message: str) -> AgentResult:
        """
        Process a user message and return the result.
        """
        result = self.agent.run(message)

        self.history.append({
            "input": message,
            "output": result.message,
            "success": result.success,
            "confidence": result.confidence
        })

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        if not self.history:
            return {"requests": 0}

        successful = sum(1 for h in self.history if h["success"])
        avg_confidence = (
            sum(h["confidence"] for h in self.history) / len(self.history)
        )

        return {
            "requests": len(self.history),
            "successful": successful,
            "success_rate": f"{(successful/len(self.history))*100:.0f}%",
            "average_confidence": f"{avg_confidence:.2f}"
        }

    def reset(self):
        """Reset the session for a new conversation."""
        self.agent = AgentLoop(self.config)
        self.history = []
