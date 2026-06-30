"""
Project Context — reads and understands existing code before generating.

Before writing new code, the agent:
1. Scans the project directory
2. Reads key files (requirements, existing code)
3. Understands the tech stack
4. Generates code that fits the existing project
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ProjectContext:
    path: str
    files: List[str]
    tech_stack: List[str]
    dependencies: List[str]
    existing_code: Dict[str, str]  # filename -> content (first 500 chars)
    summary: str


class ContextReader:
    """
    Reads and understands existing project structure.
    """

    def __init__(self, llm_provider=None):
        self.llm = llm_provider

    def read_project(self, project_path: str,
                     max_files: int = 10) -> ProjectContext:
        """
        Read and analyze an existing project.
        """
        files = self._scan_files(project_path)
        tech_stack = self._detect_tech_stack(files, project_path)
        dependencies = self._read_dependencies(project_path)
        existing_code = self._read_key_files(project_path, files, max_files)

        # Generate summary using LLM if available
        summary = self._generate_summary(
            files, tech_stack, dependencies, existing_code
        )

        return ProjectContext(
            path=project_path,
            files=files,
            tech_stack=tech_stack,
            dependencies=dependencies,
            existing_code=existing_code,
            summary=summary
        )

    def get_context_prompt(self, context: ProjectContext) -> str:
        """Generate a context prompt for code generation."""
        prompt = f"EXISTING PROJECT CONTEXT:\n"
        prompt += f"Path: {context.path}\n"
        prompt += f"Tech stack: {', '.join(context.tech_stack)}\n"
        prompt += f"Dependencies: {', '.join(context.dependencies)}\n"
        prompt += f"Files: {', '.join(context.files[:10])}\n"

        if context.existing_code:
            prompt += "\nEXISTING CODE (first 200 chars each):\n"
            for fname, content in list(context.existing_code.items())[:3]:
                prompt += f"\n--- {fname} ---\n"
                prompt += content[:200] + "\n"

        if context.summary:
            prompt += f"\nPROJECT SUMMARY: {context.summary}\n"

        return prompt

    def _scan_files(self, path: str) -> List[str]:
        """Scan project directory for source files."""
        files = []
        ignore = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.agent-memory'}

        for root, dirs, filenames in os.walk(path):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in ignore]

            for f in filenames:
                if f.startswith('.'):
                    continue
                rel_path = os.path.relpath(os.path.join(root, f), path)
                files.append(rel_path)

        return sorted(files)[:50]  # Limit to 50 files

    def _detect_tech_stack(self, files: List[str], path: str) -> List[str]:
        """Detect technology stack from files."""
        tech = set()

        # Check file extensions
        for f in files:
            if f.endswith('.py'):
                tech.add('python')
            elif f.endswith('.js'):
                tech.add('javascript')
            elif f.endswith('.ts'):
                tech.add('typescript')
            elif f.endswith('.go'):
                tech.add('go')
            elif f.endswith('.rs'):
                tech.add('rust')
            elif f.endswith('.java'):
                tech.add('java')

        # Check for config files
        config_files = ['package.json', 'requirements.txt', 'pyproject.toml',
                       'Cargo.toml', 'go.mod', 'pom.xml', 'Makefile', 'Dockerfile']

        for f in files:
            if f in config_files:
                tech.add(f.replace('.txt', '').replace('.toml', '').replace('.json', ''))

        # Check for frameworks
        for f in files:
            if 'fastapi' in f.lower() or 'flask' in f.lower():
                tech.add('fastapi/flask')
            if 'react' in f.lower() or 'jsx' in f:
                tech.add('react')
            if 'vue' in f.lower():
                tech.add('vue')

        return list(tech)

    def _read_dependencies(self, path: str) -> List[str]:
        """Read dependencies from requirements/package files."""
        deps = []

        # Python requirements
        req_file = os.path.join(path, 'requirements.txt')
        if os.path.exists(req_file):
            with open(req_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        deps.append(line.split('==')[0].split('>=')[0])

        # package.json
        pkg_file = os.path.join(path, 'package.json')
        if os.path.exists(pkg_file):
            try:
                with open(pkg_file) as f:
                    pkg = json.load(f)
                deps.extend(list(pkg.get('dependencies', {}).keys()))
            except:
                pass

        return deps[:20]  # Limit

    def _read_key_files(self, path: str, files: List[str],
                        max_files: int) -> Dict[str, str]:
        """Read content of key source files."""
        content = {}

        # Prioritize main files
        priority = ['main.py', 'app.py', 'index.py', 'index.js', 'index.ts',
                    'server.py', 'server.js', 'models.py', 'schema.py']

        key_files = []
        for p in priority:
            for f in files:
                if os.path.basename(f) == p:
                    key_files.append(f)

        # Add other source files
        for f in files:
            if f not in key_files and any(f.endswith(ext) for ext in ['.py', '.js', '.ts', '.go']):
                key_files.append(f)

        # Read files
        for f in key_files[:max_files]:
            full_path = os.path.join(path, f)
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content[f] = file.read()[:500]  # First 500 chars
            except:
                pass

        return content

    def _generate_summary(self, files: List[str], tech: List[str],
                          deps: List[str], code: Dict[str, str]) -> str:
        """Generate a summary of the project."""
        if not self.llm:
            return f"Project with {len(files)} files using {', '.join(tech)}"

        code_snippets = "\n".join([
            f"--- {k} ---\n{v[:200]}"
            for k, v in list(code.items())[:3]
        ])

        prompt = f"""Summarize this project in 2 sentences:

Files: {len(files)}
Tech: {', '.join(tech)}
Dependencies: {', '.join(deps[:10])}

Code snippets:
{code_snippets}

Summary:"""

        response = self.llm.complete(
            prompt=prompt,
            system="Summarize software projects concisely.",
            temperature=0.3,
            max_tokens=200
        )

        return response.content.strip()


# Need json import
import json
