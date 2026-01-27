# MACS - Multi Agent Control System

A tmux-based orchestration framework for controlling AI coding agents across multiple terminals. Enables a "controller" agent to oversee and direct a "worker" agent.

## Overview

MACS provides infrastructure for multi-agent AI workflows where:
- **Controller Terminal** - Runs a supervisory agent that makes decisions and provides oversight
- **Worker Terminal** - Runs a task-execution agent that performs the actual work

```
┌─────────────────────┐     ┌─────────────────────┐
│  Controller (A)     │     │    Worker (B)       │
│  - Makes decisions  │────►│  - Executes tasks   │
│  - Reviews output   │     │  - Reports status   │
│  - Sends commands   │◄────│  - Asks questions   │
└─────────────────────┘     └─────────────────────┘
        │                           │
        │   snapshot.sh ◄───────────┘ (read output)
        │   send.sh ────────────────► (send commands)
        │   status.sh ◄─────────────┘ (check busy/idle)
```

## Quick Start

### Prerequisites
- tmux
- Codex CLI (or Claude Code)

### Installation

```bash
# Clone the repository
git clone https://github.com/dickymoore/macs.git
cd macs

# Copy prompts to your Codex prompts directory
mkdir -p ~/.codex/prompts
cp .codex/prompts/*.md ~/.codex/prompts/

# Make scripts executable
chmod +x tools/tmux_bridge/*.sh
```

### Basic Usage

1. **Start tmux with a worker window**:
```bash
./tools/tmux_bridge/start_worker.sh macs
# start_worker auto-attaches by default; use --no-attach to skip
```

2. **In the worker window** (Ctrl+b n to switch), start Codex:
```bash
codex
```

3. **In a separate controller terminal** (from your project repo root), install the controller prompt + skills and start Codex:
```bash
../macs/tools/tmux_bridge/start_controller.sh
# If you copied the scripts into your repo:
# ./tools/tmux_bridge/start_controller.sh
# Or from anywhere:
# ../macs/tools/tmux_bridge/start_controller.sh --repo /path/to/your-repo
# Skip copying skills:
# ../macs/tools/tmux_bridge/start_controller.sh --skip-skills
#
# If tmux socket auto-detect fails:
# ../macs/tools/tmux_bridge/start_controller.sh --tmux-session macs
# ../macs/tools/tmux_bridge/start_controller.sh --tmux-socket /tmp/tmux-<uid>/default
# To bypass tmux detection (not recommended):
# ../macs/tools/tmux_bridge/start_controller.sh --no-tmux-detect
# If Codex can't access the tmux socket from inside its sandbox:
# ../macs/tools/tmux_bridge/start_controller.sh --codex-args "--sandbox danger-full-access"
# Or set MACS_CODEX_ARGS="--sandbox danger-full-access"
# To only install prompts/skills without launching Codex:
# ../macs/tools/tmux_bridge/start_controller.sh --no-codex
```
This writes `.codex/macs-path.txt` in the repo so the controller can locate `tmux_bridge` tools even when they are not vendored.
It also attempts to record a tmux socket in `.codex/tmux-socket.txt` so controller commands can reach the correct tmux server.
If you pass `--tmux-session`, it records `.codex/tmux-session.txt` so commands can target the right session automatically.

4. **The controller** can now:
   - Read worker output: `./tools/tmux_bridge/snapshot.sh`
   - Send commands: `./tools/tmux_bridge/send.sh "your instruction"`
   - Check status: `./tools/tmux_bridge/status.sh`

## How It Works

The controller agent uses shell scripts to interact with the worker terminal:

### Helper Scripts

| Script | Purpose |
|--------|---------|
| `snapshot.sh` | Capture recent output from worker terminal |
| `send.sh` | Send text/commands to worker terminal |
| `status.sh` | Check if worker is busy (running) or idle |
| `set_target.sh` | Pin the worker pane for subsequent commands |
| `notify.sh` | Play sound to alert human |

### Controller Workflow

1. **Snapshot** - Read worker output to see current state
2. **Decide** - Determine what instruction to give
3. **Send** - Send command to worker via `send.sh`
4. **Wait** - Poll with backoff until worker responds
5. **Repeat** - Continue until task complete or blocked

The controller prompt (`.codex/prompts/controller.md`) contains detailed operating principles including:
- Polling/backoff schedules
- Busy detection rules
- Looping behavior (stay in loop until blocked or complete)
- When to notify the human

## Customization

Copy `.codex/prompts/controller.md` to your project and add project-specific rules at the bottom:
- Repository structure
- CI/CD requirements
- Security policies
- Team conventions

See `examples/project-rules/` for templates.

## Documentation

- [Getting Started](docs/getting-started.md) - Detailed setup guide
- [Architecture](docs/architecture.md) - How MACS works
- [Customization](docs/customization.md) - Adapting for your project

## License

MIT License - see [LICENSE](LICENSE) for details.
