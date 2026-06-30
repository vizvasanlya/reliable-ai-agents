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
5. Reports results when done
6. Learns from mistakes across sessions

## Project Structure

```
reliable-ai-agents/
├── docs/
│   ├── VISION.md              # What we're building and why
│   └── DEVELOPMENT_PLAN.md    # Phased implementation plan
├── src/
│   ├── tools/                 # Agent's hands (file ops, shell, search)
│   ├── memory/                # Agent's brain (persistent learning)
│   ├── planning/              # Agent's strategy (task decomposition)
│   ├── llm/                   # LLM integration (brain)
│   ├── execution/             # Agent's action (running tasks)
│   ├── verification/          # Agent's quality control
│   ├── agent/                 # Integration (loop, session, trust)
│   └── cli.py                 # CLI entry point + daemon
├── tests/                     # 112 tests
└── examples/                  # Working examples
```

## Implementation Status

| Module | Status | Tests | What It Does |
|--------|--------|-------|--------------|
| Tools | Complete | 18/18 | Read/write/edit files, run commands, search |
| Memory | Complete | 23/23 | Persistent storage, error tracking, sessions |
| Planning | Complete | 17/17 | Intent parsing, task decomposition, scheduling |
| LLM Planner | Complete | 9/9 | LLM-powered smart task planning |
| LLM Coder | Complete | 7/7 | Real code generation using language models |
| Execution | Complete | 10/10 | Task execution, error handling, progress |
| Verification | Complete | 15/15 | Syntax checking, security scanning, confidence |
| Agent Loop | Complete | 13/13 | Main control: Plan → Execute → Verify → Learn |
| **Total** | **Complete** | **112/112** | |

## How To Use

### Submit a task
```bash
python src/cli.py submit "Build a REST API for user management"
```

### Check status
```bash
python src/cli.py status <task_id>
```

### Get result
```bash
python src/cli.py result <task_id>
```

### View history
```bash
python src/cli.py history
```

### Start daemon (background processing)
```bash
python src/cli.py daemon start
```

### Stop daemon
```bash
python src/cli.py daemon stop
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `submit <task>` | Submit a new task |
| `status <id>` | Check task status |
| `result <id>` | Get task result |
| `history` | Show all tasks |
| `memory` | Show memory stats |
| `trust` | Show trust level |
| `daemon start` | Start background worker |
| `daemon stop` | Stop background worker |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    USER SUBMITS TASK                 │
│         python cli.py submit "Build auth API"       │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│                  AGENT DAEMON                        │
│                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│  │   LLM    │   │  Tools   │   │  Memory  │        │
│  │  (Brain) │   │  (Hands) │   │ (Learn)  │        │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘        │
│       │              │              │                │
│       ▼              ▼              ▼                │
│  ┌──────────────────────────────────────────┐      │
│  │            Agent Loop                     │      │
│  │  Plan → Execute → Verify → Learn         │      │
│  └──────────────────────────────────────────┘      │
│                                                      │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│                 RESULT DELIVERED                     │
│  "Done. 5/5 tasks completed. Confidence: 94%"       │
└─────────────────────────────────────────────────────┘
```

## What Each Component Does

### LLM Brain
- `LLMProvider` — Interface to OpenAI, Anthropic, or mock
- `LLMPlanner` — Uses LLM to break down tasks intelligently
- `LLMCoder` — Generates real code, fixes bugs, writes tests

### Tools (Hands)
- `read_file` / `write_file` / `edit_file` — File operations
- `run_command` — Execute shell commands
- `grep` / `glob` — Search codebases

### Memory (Learning)
- `MemoryStore` — Persistent key-value storage
- `ErrorTracker` — Record and retrieve error patterns
- `SessionMemory` — Track current session

### Verification (Quality)
- `SyntaxChecker` — Validate code syntax
- `SecurityScanner` — Detect vulnerabilities
- `ConfidenceScorer` — Rate output quality

## Quick Start

```python
from src.llm.provider import create_provider
from src.llm.planner import LLMPlanner
from src.llm.coder import LLMCoder

# Create LLM provider (auto-detects API keys)
provider = create_provider("auto")

# Plan a task
planner = LLMPlanner(provider)
tasks = planner.plan("Build a user authentication system")
print(f"Created {len(tasks)} tasks")

# Generate code
coder = LLMCoder(provider)
code = coder.generate_file("Implement login function", "auth.py", "python")
print(code)
```

## Tests

```bash
python tests/test_tools.py        # 18 tests
python tests/test_memory.py       # 23 tests
python tests/test_planning.py     # 17 tests
python tests/test_llm.py          # 16 tests
python tests/test_execution.py    # 10 tests
python tests/test_verification.py # 15 tests
python tests/test_agent.py        # 13 tests
```

## What's Next

1. **Package as installable CLI** — `pip install reliable-agent`
2. **Web dashboard** — Monitor tasks in browser
3. **Multi-project support** — Handle concurrent projects
4. **Plugin system** — Extend with custom tools
5. **Team collaboration** — Multiple agents working together
