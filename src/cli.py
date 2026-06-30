#!/usr/bin/env python3
"""
CLI Interface — interact with the agent from the command line.

Commands:
  submit <task>      Submit a new task
  status <task_id>   Check task status
  result <task_id>   Get task result
  history            Show task history
  memory             Show memory stats
  trust              Show trust level
  daemon start       Start background daemon
  daemon stop        Stop background daemon
"""

import sys
import os
import json
import time
import signal
import argparse
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from agent.loop import AgentLoop, AgentConfig
from llm.provider import create_provider


TASKS_DIR = ".agent-tasks"
DAEMON_PID_FILE = os.path.join(TASKS_DIR, "daemon.pid")


def ensure_dirs():
    """Ensure task directories exist."""
    os.makedirs(TASKS_DIR, exist_ok=True)
    os.makedirs(os.path.join(TASKS_DIR, "pending"), exist_ok=True)
    os.makedirs(os.path.join(TASKS_DIR, "completed"), exist_ok=True)
    os.makedirs(os.path.join(TASKS_DIR, "failed"), exist_ok=True)


def submit_task(args):
    """Submit a new task to the agent."""
    ensure_dirs()

    task_id = f"task_{int(time.time()*1000)}"
    task_data = {
        "id": task_id,
        "request": args.task,
        "project_path": args.project or ".",
        "status": "pending",
        "submitted_at": datetime.now().isoformat(),
        "language": args.language or "python"
    }

    # Save task file
    task_file = os.path.join(TASKS_DIR, "pending", f"{task_id}.json")
    with open(task_file, 'w') as f:
        json.dump(task_data, f, indent=2)

    print(f"Task submitted: {task_id}")
    print(f"Request: {args.task}")
    print(f"Project: {os.path.abspath(args.project or '.')}")
    print(f"\nTo check status: python cli.py status {task_id}")

    # If daemon is running, wake it up
    wake_daemon()


def check_status(args):
    """Check task status."""
    task_file = find_task_file(args.task_id)
    if not task_file:
        print(f"Task not found: {args.task_id}")
        return

    with open(task_file) as f:
        task = json.load(f)

    print(f"Task: {task['id']}")
    print(f"Status: {task['status']}")
    print(f"Request: {task['request']}")
    print(f"Submitted: {task.get('submitted_at', 'unknown')}")

    if task['status'] == 'completed':
        print(f"Completed: {task.get('completed_at', 'unknown')}")
        print(f"Result: {task.get('result', 'no result')}")
        print(f"Confidence: {task.get('confidence', 0):.0%}")
    elif task['status'] == 'failed':
        print(f"Error: {task.get('error', 'unknown error')}")
    elif task['status'] == 'in_progress':
        print(f"Progress: {task.get('progress', 'unknown')}")


def get_result(args):
    """Get task result."""
    task_file = find_task_file(args.task_id)
    if not task_file:
        print(f"Task not found: {args.task_id}")
        return

    with open(task_file) as f:
        task = json.load(f)

    if task['status'] != 'completed':
        print(f"Task not completed. Status: {task['status']}")
        return

    print(f"Result for {task['id']}:")
    print(f"{'='*50}")
    print(task.get('result', 'No result'))
    print(f"{'='*50}")
    print(f"Confidence: {task.get('confidence', 0):.0%}")


def show_history(args):
    """Show task history."""
    ensure_dirs()

    print("Task History:")
    print(f"{'='*60}")

    for status in ['completed', 'failed']:
        dir_path = os.path.join(TASKS_DIR, status)
        if os.path.exists(dir_path):
            for filename in sorted(os.listdir(dir_path)):
                if filename.endswith('.json'):
                    with open(os.path.join(dir_path, filename)) as f:
                        task = json.load(f)
                    print(f"{task['id']} | {task['status']} | {task['request'][:40]}")


def show_memory(args):
    """Show memory statistics."""
    from memory.store import MemoryStore
    from memory.errors import ErrorTracker

    store = MemoryStore()
    errors = ErrorTracker()

    print("Memory Statistics:")
    print(f"{'='*40}")
    stats = store.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print(f"\nError Patterns:")
    error_stats = errors.get_stats()
    for key, value in error_stats.items():
        if key != "most_common":
            print(f"  {key}: {value}")


def show_trust(args):
    """Show trust level."""
    from agent.trust import TrustSystem
    import shelve

    trust_file = os.path.join(TASKS_DIR, "trust")
    trust = TrustSystem()

    # Load existing trust if available
    if os.path.exists(trust_file):
        try:
            with open(trust_file + ".json") as f:
                data = json.load(f)
                # Restore trust data
                pass
        except:
            pass

    print("Trust Level:")
    print(f"{'='*40}")
    level = trust.get_trust()
    print(f"  Score: {level.score:.2f}")
    print(f"  Grade: {level.reliability_grade}")
    print(f"  Successes: {level.successful_tasks}")
    print(f"  Failures: {level.failed_tasks}")
    print(f"  Success Rate: {level.success_rate:.0%}")


def start_daemon(args):
    """Start the background daemon."""
    ensure_dirs()

    # Check if already running
    if os.path.exists(DAEMON_PID_FILE):
        with open(DAEMON_PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)
            print(f"Daemon already running (PID: {pid})")
            return
        except OSError:
            # PID file exists but process is dead
            os.remove(DAEMON_PID_FILE)

    print("Starting daemon...")
    print("The daemon will process tasks in the background.")
    print("Use 'python cli.py submit <task>' to add tasks.")
    print("Use 'python cli.py daemon stop' to stop.")

    # Write PID file
    with open(DAEMON_PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    # Start processing loop
    try:
        run_daemon_loop()
    except KeyboardInterrupt:
        print("\nStopping daemon...")
    finally:
        if os.path.exists(DAEMON_PID_FILE):
            os.remove(DAEMON_PID_FILE)


def stop_daemon(args):
    """Stop the background daemon."""
    if not os.path.exists(DAEMON_PID_FILE):
        print("No daemon running.")
        return

    with open(DAEMON_PID_FILE) as f:
        pid = int(f.read().strip())

    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Daemon stopped (PID: {pid})")
    except OSError:
        print("Daemon not running (stale PID file)")
        os.remove(DAEMON_PID_FILE)


def run_daemon_loop():
    """Main daemon processing loop."""
    from memory.errors import ErrorTracker
    from llm.provider import create_provider

    # Initialize components
    provider = create_provider("auto")
    error_tracker = ErrorTracker()

    print(f"Daemon started with LLM: {provider.name}")

    while True:
        # Check for pending tasks
        pending_dir = os.path.join(TASKS_DIR, "pending")
        tasks = [f for f in os.listdir(pending_dir) if f.endswith('.json')]

        for task_file in tasks:
            task_path = os.path.join(pending_dir, task_file)
            process_task(task_path, provider, error_tracker)

        # Sleep before checking again
        time.sleep(5)


def process_task(task_file: str, provider, error_tracker):
    """Process a single task."""
    from llm.planner import LLMPlanner
    from llm.coder import LLMCoder
    from execution.executor import TaskExecutor
    from tools.base import create_default_registry

    # Load task
    with open(task_file) as f:
        task = json.load(f)

    print(f"\nProcessing: {task['id']}")
    task["status"] = "in_progress"
    save_task(task)

    try:
        # Initialize components
        planner = LLMPlanner(provider)
        coder = LLMCoder(provider)
        tools = create_default_registry()
        executor = TaskExecutor(tools)

        # Create plan
        print(f"  Planning...")
        tasks = planner.plan(
            task["request"],
            project_path=task.get("project_path", "."),
            language=task.get("language", "python")
        )
        print(f"  Created {len(tasks)} tasks")

        # Execute tasks
        completed_tasks = []
        for t in tasks:
            print(f"  Executing: {t.description}")

            # Generate code for each task
            code = coder.generate_file(
                t.description,
                file_path=f"{task.get('project_path', '.')}/output.py",
                language=task.get("language", "python")
            )

            # Write the file
            result = executor.execute(t, {
                "project_path": task.get("project_path", "."),
                "code": code
            })

            if result.success:
                completed_tasks.append(t.id)
                t.status = "completed"
            else:
                print(f"  Failed: {result.error}")
                break

        # Mark task complete
        task["status"] = "completed"
        task["result"] = f"Completed {len(completed_tasks)}/{len(tasks)} tasks"
        task["confidence"] = len(completed_tasks) / len(tasks) if tasks else 0
        task["completed_at"] = datetime.now().isoformat()

        # Move to completed
        completed_file = os.path.join(TASKS_DIR, "completed", os.path.basename(task_file))
        save_task(task, completed_file)

        # Remove from pending
        os.remove(task_file)

        print(f"  Done: {task['id']}")

    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)

        # Move to failed
        failed_file = os.path.join(TASKS_DIR, "failed", os.path.basename(task_file))
        save_task(task, failed_file)

        # Remove from pending
        os.remove(task_file)

        print(f"  Failed: {task['id']} - {e}")


def save_task(task: dict, path: str = None):
    """Save task data."""
    if path is None:
        path = os.path.join(TASKS_DIR, task["status"], f"{task['id']}.json")
    with open(path, 'w') as f:
        json.dump(task, f, indent=2)


def find_task_file(task_id: str) -> str:
    """Find a task file by ID."""
    for status in ['pending', 'in_progress', 'completed', 'failed']:
        dir_path = os.path.join(TASKS_DIR, status)
        if os.path.exists(dir_path):
            for filename in os.listdir(dir_path):
                if filename.endswith('.json'):
                    with open(os.path.join(dir_path, filename)) as f:
                        task = json.load(f)
                    if task['id'] == task_id:
                        return os.path.join(dir_path, filename)
    return None


def wake_daemon():
    """Signal the daemon to wake up."""
    # The daemon checks for tasks every 5 seconds
    pass


def main():
    parser = argparse.ArgumentParser(
        description="Reliable AI Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # submit
    submit_parser = subparsers.add_parser("submit", help="Submit a new task")
    submit_parser.add_argument("task", help="Task description")
    submit_parser.add_argument("-p", "--project", help="Project path")
    submit_parser.add_argument("-l", "--language", help="Programming language")

    # status
    status_parser = subparsers.add_parser("status", help="Check task status")
    status_parser.add_argument("task_id", help="Task ID")

    # result
    result_parser = subparsers.add_parser("result", help="Get task result")
    result_parser.add_argument("task_id", help="Task ID")

    # history
    subparsers.add_parser("history", help="Show task history")

    # memory
    subparsers.add_parser("memory", help="Show memory statistics")

    # trust
    subparsers.add_parser("trust", help="Show trust level")

    # daemon
    daemon_parser = subparsers.add_parser("daemon", help="Manage daemon")
    daemon_parser.add_argument("action", choices=["start", "stop"],
                               help="Start or stop daemon")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "submit": submit_task,
        "status": check_status,
        "result": get_result,
        "history": show_history,
        "memory": show_memory,
        "trust": show_trust,
    }

    if args.command == "daemon":
        if args.action == "start":
            start_daemon(args)
        elif args.action == "stop":
            stop_daemon(args)
    elif args.command in commands:
        commands[args.command](args)


if __name__ == "__main__":
    main()
