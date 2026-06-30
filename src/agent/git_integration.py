"""
Git Integration — auto-commits generated code.

Features:
1. Initialize git repo if not exists
2. Auto-commit generated code
3. Create meaningful commit messages
4. Push to remote if configured
"""

import os
import subprocess
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class GitResult:
    success: bool
    message: str
    commit_hash: Optional[str] = None


class GitIntegration:
    """
    Handles git operations for generated code.
    """

    def __init__(self, project_path: str):
        self.project_path = project_path

    def init_if_needed(self) -> GitResult:
        """Initialize git repo if not already initialized."""
        if os.path.exists(os.path.join(self.project_path, '.git')):
            return GitResult(True, "Git repo already exists")

        try:
            result = subprocess.run(
                ['git', 'init'],
                capture_output=True,
                text=True,
                cwd=self.project_path,
                timeout=10
            )

            if result.returncode == 0:
                # Create .gitignore
                self._create_gitignore()
                return GitResult(True, "Git repo initialized")
            else:
                return GitResult(False, f"Git init failed: {result.stderr}")

        except Exception as e:
            return GitResult(False, f"Error: {str(e)}")

    def commit(self, message: str, files: List[str] = None) -> GitResult:
        """Commit changes with a message."""
        try:
            # Stage files
            if files:
                for f in files:
                    subprocess.run(
                        ['git', 'add', f],
                        capture_output=True,
                        cwd=self.project_path,
                        timeout=10
                    )
            else:
                subprocess.run(
                    ['git', 'add', '-A'],
                    capture_output=True,
                    cwd=self.project_path,
                    timeout=10
                )

            # Check if there are changes
            status = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                cwd=self.project_path,
                timeout=10
            )

            if not status.stdout.strip():
                return GitResult(True, "No changes to commit")

            # Commit
            result = subprocess.run(
                ['git', 'commit', '-m', message],
                capture_output=True,
                text=True,
                cwd=self.project_path,
                timeout=10
            )

            if result.returncode == 0:
                # Get commit hash
                hash_result = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    capture_output=True,
                    text=True,
                    cwd=self.project_path,
                    timeout=10
                )
                commit_hash = hash_result.stdout.strip()[:8]
                return GitResult(True, f"Committed: {message}", commit_hash)
            else:
                return GitResult(False, f"Commit failed: {result.stderr}")

        except Exception as e:
            return GitResult(False, f"Error: {str(e)}")

    def push(self, remote: str = "origin", branch: str = "master") -> GitResult:
        """Push to remote repository."""
        try:
            result = subprocess.run(
                ['git', 'push', remote, branch],
                capture_output=True,
                text=True,
                cwd=self.project_path,
                timeout=30
            )

            if result.returncode == 0:
                return GitResult(True, f"Pushed to {remote}/{branch}")
            else:
                return GitResult(False, f"Push failed: {result.stderr}")

        except Exception as e:
            return GitResult(False, f"Error: {str(e)}")

    def auto_commit(self, files: List[str], task_description: str) -> GitResult:
        """Auto-commit with a meaningful message based on the task."""
        # Generate commit message
        message = self._generate_commit_message(task_description, files)

        # Init if needed
        self.init_if_needed()

        # Commit
        return self.commit(message, files)

    def _generate_commit_message(self, task: str, files: List[str]) -> str:
        """Generate a meaningful commit message."""
        # Keep task short
        short_task = task[:50].strip()

        if len(files) == 1:
            return f"feat: {short_task}"
        elif len(files) <= 3:
            return f"feat: {short_task} ({len(files)} files)"
        else:
            return f"feat: {short_task} (project with {len(files)} files)"

    def _create_gitignore(self):
        """Create a .gitignore file."""
        gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/

# IDE
.vscode/
.idea/

# Agent
.agent-memory/
.agent-tasks/
*.db

# OS
.DS_Store
Thumbs.db
"""
        gitignore_path = os.path.join(self.project_path, '.gitignore')
        with open(gitignore_path, 'w') as f:
            f.write(gitignore_content)

    def get_status(self) -> dict:
        """Get git status."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                cwd=self.project_path,
                timeout=10
            )

            lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
            return {
                "clean": len(lines) == 0,
                "modified": len(lines),
                "files": [l.split(' ', 1)[-1] for l in lines if l.strip()]
            }
        except:
            return {"clean": True, "modified": 0, "files": []}
