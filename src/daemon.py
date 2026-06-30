#!/usr/bin/env python3
"""
Background Daemon — runs continuously, processes tasks from queue.

Usage:
  python daemon.py start     # Start daemon
  python daemon.py stop      # Stop daemon
  python daemon.py status    # Check if running
"""

import os
import sys
import json
import time
import signal
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

TASKS_DIR = ".agent-tasks"
PID_FILE = os.path.join(TASKS_DIR, "daemon.pid")
LOG_FILE = os.path.join(TASKS_DIR, "daemon.log")


def log(msg):
    """Write to log file and print."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    os.makedirs(TASKS_DIR, exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + "\n")


def is_running():
    """Check if daemon is running."""
    if not os.path.exists(PID_FILE):
        return False
    with open(PID_FILE) as f:
        pid = int(f.read().strip())
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start():
    """Start the daemon."""
    if is_running():
        print("Daemon already running")
        return

    os.makedirs(TASKS_DIR, exist_ok=True)
    os.makedirs(os.path.join(TASKS_DIR, "pending"), exist_ok=True)
    os.makedirs(os.path.join(TASKS_DIR, "completed"), exist_ok=True)
    os.makedirs(os.path.join(TASKS_DIR, "failed"), exist_ok=True)

    # Write PID
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    log("Daemon started")
    print("Daemon running. Use 'python daemon.py stop' to stop.")

    # Run the main loop
    try:
        run_loop()
    except KeyboardInterrupt:
        log("Daemon stopped by user")
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)


def stop():
    """Stop the daemon."""
    if not os.path.exists(PID_FILE):
        print("No daemon running")
        return

    with open(PID_FILE) as f:
        pid = int(f.read().strip())

    try:
        os.kill(pid, signal.SIGTERM)
        log(f"Daemon stopped (PID {pid})")
        print(f"Daemon stopped (PID {pid})")
    except OSError:
        print("Daemon not running (stale PID)")
        os.remove(PID_FILE)


def status():
    """Check daemon status."""
    if is_running():
        with open(PID_FILE) as f:
            pid = f.read().strip()
        print(f"Daemon running (PID {pid})")

        # Show queue
        pending = os.path.join(TASKS_DIR, "pending")
        if os.path.exists(pending):
            tasks = [f for f in os.listdir(pending) if f.endswith('.json')]
            print(f"Pending tasks: {len(tasks)}")
    else:
        print("Daemon not running")


def run_loop():
    """Main daemon loop."""
    from process_task import process_pending_tasks

    while True:
        pending_dir = os.path.join(TASKS_DIR, "pending")
        if os.path.exists(pending_dir):
            tasks = [f for f in os.listdir(pending_dir) if f.endswith('.json')]
            if tasks:
                log(f"Processing {len(tasks)} task(s)...")
                try:
                    process_pending_tasks()
                except Exception as e:
                    log(f"Error processing tasks: {e}")

        time.sleep(5)  # Check every 5 seconds


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python daemon.py [start|stop|status]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "start":
        start()
    elif cmd == "stop":
        stop()
    elif cmd == "status":
        status()
    else:
        print(f"Unknown command: {cmd}")
