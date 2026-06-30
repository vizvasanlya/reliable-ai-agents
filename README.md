# Reliable AI Agents

**Goal:** Build AI systems that can be trusted to work autonomously on real-world projects.

## Vision

Today's AI is powerful but unreliable. This project builds the missing pieces to make AI agents trustworthy collaborators — not just tools.

**Target:** An AI system that can independently complete multi-day, real-world projects with <5% error rate, without human course-correction.

## What This Is

A **background agent daemon** that:
1. Accepts natural language tasks via CLI
2. Plans the work using LLM reasoning
3. Generates real code using language models
4. Verifies output (syntax, security, tests)
5. Self-corrects when errors occur
6. Learns from mistakes across sessions
7. Reads existing project context before generating

## Project Structure

```
reliable-ai-agents/
├── src/
│   ├── agent/
│   │   ├── self_correction.py   # Auto-fix loop (up to 5 attempts)
│   │   ├── learning.py          # Real-time learning from errors
│   │   ├── cross_session.py     # Persistent learning across sessions
│   │   ├── context.py           # Read existing project before generating
│   │   ├── project_builder.py   # Multi-file project generation
│   │   ├── error_analyzer.py    # Deep error analysis and fix suggestions
│   │   ├── loop.py              # Main agent control loop
│   │   ├── session.py           # Session management
│   │   └── trust.py             # Trust tracking
│   ├── llm/
│   │   ├── provider.py          # OpenCode Zen (Big Pickle, MiMo)
│   │   ├── planner.py           # LLM-powered task planning
│   │   └── coder.py             # Real code generation
│   ├── tools/                   # File ops, shell, search
│   ├── memory/                  # Persistent storage
│   ├── planning/                # Task decomposition
│   ├── execution/               # Task runner, error handler
│   ├── verification/            # Syntax, security, confidence
│   ├── cli.py                   # CLI interface
│   ├── daemon.py                # Background daemon
│   └── process_task.py          # Task processor
├── tests/                       # 136 tests
└── docs/                        # Vision and development plan
```

## How To Use

### Submit a task
```bash
python src/cli.py submit "Build a REST API for user management" -p ./my-project
```

### Check status
```bash
python src/cli.py status <task_id>
```

### Start daemon (background processing)
```bash
python src/daemon.py start
```

### View history
```bash
python src/cli.py history
```

## Features

| Feature | Status | Description |
|---------|--------|-------------|
| CLI Interface | Done | Submit tasks, check status, view history |
| LLM Integration | Done | Big Pickle via OpenCode Zen (free) |
| Code Generation | Done | Real code from natural language |
| Self-Correction | Done | Auto-fix up to 5 attempts |
| Learning | Done | Learn from every error |
| Cross-Session Learning | Done | Persist lessons across sessions |
| Project Context | Done | Read existing code before generating |
| Multi-File Projects | Done | Generate complete project structures |
| Error Analysis | Done | Deep error analysis with fix suggestions |
| Background Daemon | Done | Run as background service |
| Syntax Checking | Done | Validate Python/JSON/JS |
| Security Scanning | Done | Detect vulnerabilities |
| Trust System | Done | Track reliability over time |

## Test Results

```
Tools:        18/18 passing
Memory:       23/23 passing
Planning:     17/17 passing
LLM:          16/16 passing
Execution:    10/10 passing
Verification: 15/15 passing
Agent Loop:   13/13 passing
Self-Correction: 10/10 passing
New Features: 14/14 passing
─────────────────────────────
Total:       136/136 passing
```

## Real-World Demo

```
$ python src/cli.py submit "Build a Book Library API with SQLAlchemy..."

Processing...
  Step 1: Reading project context...
  Step 2: Loading learned lessons... (applying 3 lessons)
  Step 3: Planning project structure... (5 files)
  Step 4: Writing files...
  Step 5: Verifying syntax... (PASS)
  Step 6: Running tests... (25/25 PASS)

RESULT: SUCCESS
```

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/vizvasanlya/reliable-ai-agents.git
cd reliable-ai-agents

# 2. Set your API key (free from opencode.ai)
set ZEN_API_KEY=your-key-here

# 3. Submit a task
python src/cli.py submit "Build me a REST API" -p ./my-project

# 4. Or start the daemon
python src/daemon.py start
```

## Architecture

```
Request → Context Reader → Learning System → Project Builder
    ↓                                               ↓
Error Analyzer ← Self-Correction Loop ← Code Generator
    ↓                                               ↓
Verification Layer → Tests → Fix? → Retry → Done
```

## License

MIT
