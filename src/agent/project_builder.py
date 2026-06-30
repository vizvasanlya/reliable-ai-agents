"""
Project Builder — generates complete multi-file project structures.

Instead of one file, creates:
- Proper directory structure
- Multiple source files
- Configuration files
- Tests directory
- Requirements file
"""

import os
import re
import json
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ProjectFile:
    path: str
    content: str
    description: str


class ProjectBuilder:
    """
    Generates complete project structures using LLM.
    """

    def __init__(self, llm_provider):
        self.llm = llm_provider

    def build(self, request: str, project_path: str,
              language: str = "python") -> List[ProjectFile]:
        """
        Generate a complete project structure.
        """
        # Step 1: Plan the project structure
        structure = self._plan_structure(request, language)

        # Step 2: Generate each file
        files = []
        for file_info in structure:
            content = self._generate_file(
                request,
                file_info["path"],
                file_info["description"],
                language
            )

            if content:
                files.append(ProjectFile(
                    path=file_info["path"],
                    content=content,
                    description=file_info["description"]
                ))

        return files

    def write_files(self, files: List[ProjectFile], project_path: str):
        """Write all project files to disk."""
        for f in files:
            full_path = os.path.join(project_path, f.path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            # Strip non-ASCII
            content = f.content.encode('ascii', 'ignore').decode('ascii')
            with open(full_path, 'w', encoding='utf-8') as file:
                file.write(content)

    def _plan_structure(self, request: str, language: str) -> List[Dict]:
        """Plan the project file structure."""
        prompt = f"""Plan a {language} project for this request:

"{request}"

Return a JSON array of files to create. Each file has:
- path: relative file path (e.g., "src/main.py")
- description: what this file should contain

Example:
[
  {{"path": "main.py", "description": "Main application entry point with FastAPI app"}},
  {{"path": "models.py", "description": "SQLAlchemy models"}},
  {{"path": "schemas.py", "description": "Pydantic schemas for API"}},
  {{"path": "database.py", "description": "Database connection setup"}},
  {{"path": "test_main.py", "description": "Pytest tests for all endpoints"}}
]

Return ONLY the JSON array."""

        response = self.llm.complete(
            prompt=prompt,
            system="You are a software architect. Plan clean project structures.",
            temperature=0.3,
            max_tokens=1000
        )

        # Parse response
        content = response.content.strip()

        # Strip markdown
        content = re.sub(r'```(?:json)?\s*\n?', '', content)
        content = re.sub(r'```\s*$', '', content, flags=re.MULTILINE)
        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON array
            start = content.find('[')
            end = content.rfind(']') + 1
            if start != -1 and end > start:
                try:
                    return json.loads(content[start:end])
                except json.JSONDecodeError:
                    pass

            # Fallback structure
            return [
                {"path": "main.py", "description": f"Main implementation for: {request[:100]}"},
                {"path": "test_main.py", "description": "Unit tests"},
            ]

    def _generate_file(self, request: str, file_path: str,
                       description: str, language: str) -> Optional[str]:
        """Generate a single file's content."""
        prompt = f"""Write the complete content for this file:

Project requirement: {request}
File: {file_path}
Purpose: {description}

Return ONLY the complete file content. No explanations, no markdown."""

        response = self.llm.complete(
            prompt=prompt,
            system=f"You are an expert {language} developer. Write clean, complete code.",
            temperature=0.2,
            max_tokens=4096
        )

        # Clean the response
        content = response.content
        content = re.sub(r'```(?:python|javascript|json|bash)?\s*\n?', '', content)
        content = re.sub(r'```\s*$', '', content, flags=re.MULTILINE)
        content = content.strip()

        # Remove common prefixes
        for prefix in ["Here is", "Here's", "This is", "The following"]:
            if content.startswith(prefix):
                content = content.split('\n', 1)[-1] if '\n' in content else ""

        return content.strip() if content else None
