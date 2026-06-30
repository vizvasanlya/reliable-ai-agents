"""
Intent Parser — understands what the user wants.

Analyzes natural language requests and extracts:
- Action (create, fix, refactor, research, etc.)
- Target (api, ui, database, etc.)
- Constraints (language, framework, style)
- Missing information that should be clarified
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Intent:
    action: str = "unknown"
    target: str = "unknown"
    description: str = ""
    constraints: List[str] = field(default_factory=list)
    missing_info: List[str] = field(default_factory=list)
    confidence: float = 0.0


class IntentParser:
    """
    Parses user intent from natural language.

    Uses keyword matching and heuristics. A production version
    would use an LLM for more nuanced understanding.
    """

    ACTION_KEYWORDS = {
        "create": ["create", "build", "make", "new", "add", "implement", "develop"],
        "fix": ["fix", "repair", "debug", "error", "broken", "issue", "bug"],
        "refactor": ["refactor", "reorganize", "clean", "restructure", "improve"],
        "research": ["research", "investigate", "analyze", "explore", "study"],
        "modify": ["update", "modify", "change", "edit", "adjust", "enhance"],
        "delete": ["delete", "remove", "destroy", "clean up"],
        "test": ["test", "verify", "check", "validate"],
    }

    TARGET_KEYWORDS = {
        "api": ["api", "endpoint", "route", "rest", "graphql", "webhook"],
        "ui": ["ui", "interface", "page", "component", "frontend", "view", "screen"],
        "database": ["database", "db", "schema", "table", "model", "migration"],
        "auth": ["auth", "authentication", "login", "signup", "oauth", "jwt"],
        "tests": ["test", "spec", "testing"],
        "documentation": ["doc", "readme", "documentation", "comment"],
        "config": ["config", "configuration", "setup", "settings"],
        "cli": ["cli", "command line", "terminal"],
    }

    def parse(self, request: str) -> Intent:
        """Parse a user request into an Intent."""
        intent = Intent(description=request)
        request_lower = request.lower()

        # Detect action
        for action, keywords in self.ACTION_KEYWORDS.items():
            if any(kw in request_lower for kw in keywords):
                intent.action = action
                break

        # Detect target
        for target, keywords in self.TARGET_KEYWORDS.items():
            if any(kw in request_lower for kw in keywords):
                intent.target = target
                break

        # Detect constraints
        if "python" in request_lower:
            intent.constraints.append("language:python")
        if "javascript" in request_lower or "js" in request_lower:
            intent.constraints.append("language:javascript")
        if "typescript" in request_lower or "ts" in request_lower:
            intent.constraints.append("language:typescript")
        if "react" in request_lower:
            intent.constraints.append("framework:react")
        if "fastapi" in request_lower or "flask" in request_lower:
            intent.constraints.append("framework:python-web")
        if "simple" in request_lower:
            intent.constraints.append("complexity:low")
        if "production" in request_lower:
            intent.constraints.append("quality:high")

        # Check for missing info
        if intent.action == "unknown":
            intent.missing_info.append("What do you want me to do?")
        if intent.target == "unknown":
            intent.missing_info.append("What component/feature are you working on?")

        # Calculate confidence
        intent.confidence = 0.0
        if intent.action != "unknown":
            intent.confidence += 0.5
        if intent.target != "unknown":
            intent.confidence += 0.3
        if not intent.missing_info:
            intent.confidence += 0.2

        return intent

    def needs_clarification(self, intent: Intent) -> bool:
        """Check if the intent needs more information."""
        return len(intent.missing_info) > 0 or intent.confidence < 0.5
