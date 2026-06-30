"""
LLM Coder — generates real code using language models.

Takes task descriptions and produces working code.
"""

import json
import os
from typing import Dict, List, Optional

from .provider import LLMProvider, LLMResponse


CODEGEN_SYSTEM = """You are an expert software developer. Generate clean, working code.

Rules:
1. Write complete, runnable code — no placeholders
2. Follow language best practices and conventions
3. Include error handling where appropriate
4. Add brief comments only for non-obvious logic
5. Use meaningful variable and function names
6. If the task is unclear, make reasonable assumptions and note them

Output format: Return ONLY the code, no explanations unless asked."""


class LLMCoder:
    """
    Generates real code using LLM.
    """

    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.generation_history: List[Dict] = []

    def generate_file(self, task_description: str,
                      file_path: str,
                      language: str = "python",
                      context: str = "",
                      existing_code: str = "") -> str:
        """
        Generate code for a single file.
        """
        prompt_parts = [f"Task: {task_description}"]
        prompt_parts.append(f"File: {file_path}")
        prompt_parts.append(f"Language: {language}")

        if context:
            prompt_parts.append(f"\nProject context:\n{context}")
        if existing_code:
            prompt_parts.append(f"\nExisting code to modify:\n{existing_code}")

        prompt = "\n".join(prompt_parts)

        response = self.provider.complete(
            prompt=prompt,
            system=CODEGEN_SYSTEM,
            temperature=0.3,
            max_tokens=4096
        )

        # Store generation history
        self.generation_history.append({
            "task": task_description,
            "file": file_path,
            "language": language,
            "success": response.finish_reason != "error"
        })

        return self._strip_markdown(response.content)

    def _strip_markdown(self, content: str) -> str:
        """Strip markdown code block formatting from LLM response."""
        import re
        # Remove ```language ... ``` blocks
        content = re.sub(r'```(?:python|javascript|typescript|json|bash|shell)?\s*\n?', '', content)
        content = re.sub(r'```\s*$', '', content, flags=re.MULTILINE)
        # Remove **bold** markers
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
        # Remove # headers
        content = re.sub(r'^#+\s+', '', content, flags=re.MULTILINE)
        return content.strip()

    def generate_module(self, module_name: str,
                        description: str,
                        language: str = "python",
                        files_needed: List[str] = None) -> Dict[str, str]:
        """
        Generate a complete module with multiple files.
        """
        files = {}

        prompt = f"""Generate a complete module called "{module_name}".

Description: {description}
Language: {language}
Files needed: {files_needed or ['main file']}

For each file, respond with JSON:
{{
  "files": [
    {{"path": "filename", "content": "full code"}}
  ]
}}"""

        response = self.provider.complete(
            prompt=prompt,
            system=CODEGEN_SYSTEM + "\n\nYou MUST respond with valid JSON containing a 'files' array.",
            temperature=0.3,
            max_tokens=8192
        )

        try:
            data = json.loads(response.content)
            for file_data in data.get("files", []):
                files[file_data["path"]] = file_data["content"]
        except (json.JSONDecodeError, KeyError):
            # Fallback: treat entire response as single file
            if files_needed:
                files[files_needed[0]] = response.content
            else:
                files[f"{module_name}.py"] = response.content

        return files

    def fix_code(self, code: str, error_message: str,
                 language: str = "python") -> str:
        """
        Fix code based on an error message.
        """
        prompt = f"""Fix this code that has an error.

Error: {error_message}

Code:
```{language}
{code}
```

Return the fixed code only."""

        response = self.provider.complete(
            prompt=prompt,
            system=CODEGEN_SYSTEM,
            temperature=0.2,
            max_tokens=4096
        )

        return response.content

    def explain_code(self, code: str, language: str = "python") -> str:
        """Explain what code does."""
        prompt = f"""Explain this {language} code concisely:

```{language}
{code}
```"""

        response = self.provider.complete(
            prompt=prompt,
            system="Explain code clearly and concisely.",
            temperature=0.3,
            max_tokens=1000
        )

        return response.content

    def write_tests(self, code: str, language: str = "python") -> str:
        """Generate tests for given code."""
        prompt = f"""Write unit tests for this {language} code:

```{language}
{code}
```

Return complete, runnable test code."""

        response = self.provider.complete(
            prompt=prompt,
            system="Write thorough unit tests using standard test frameworks.",
            temperature=0.3,
            max_tokens=4096
        )

        return response.content

    def refactor_code(self, code: str, instructions: str,
                      language: str = "python") -> str:
        """Refactor code based on instructions."""
        prompt = f"""Refactor this {language} code.

Instructions: {instructions}

Code:
```{language}
{code}
```

Return the refactored code."""

        response = self.provider.complete(
            prompt=prompt,
            system=CODEGEN_SYSTEM,
            temperature=0.3,
            max_tokens=4096
        )

        return response.content

    def get_stats(self) -> Dict:
        """Get generation statistics."""
        total = len(self.generation_history)
        successful = sum(1 for g in self.generation_history if g["success"])
        return {
            "total_generations": total,
            "successful": successful,
            "success_rate": f"{(successful/total)*100:.0f}%" if total > 0 else "N/A"
        }
