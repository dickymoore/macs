# Getting Started with MACS

This guide walks you through setting up MACS (Multi Agent Control System) for your project.

## Prerequisites

- **tmux** - Terminal multiplexer
- **Python 3.8+** - For the bridge script
- **Codex CLI** - AI coding assistant

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_ORG/macs.git
cd macs
```

### 2. Copy Prompts to Codex

Copy the prompts to your global Codex prompts directory:

```bash
mkdir -p ~/.codex/prompts
cp .codex/prompts/*.md ~/.codex/prompts/
```

Or copy to your project's `.codex/prompts/` for project-specific use.

### 3. Make Scripts Executable

```bash
chmod +x tools/tmux_bridge/*.sh
chmod +x tools/tmux_bridge/*.py
```

## Basic Usage

### Step 1: Start a TMux Session

```bash
# Create session with controller and worker windows
./tools/tmux_bridge/start_controller.sh macs
./tools/tmux_bridge/start_worker.sh macs

# Attach to the session
tmux attach -t macs
```

### Step 2: Start Codex in Both Windows

In the **worker** window (`Ctrl+b` then `n` to switch):
```bash
codex
```

In the **controller** window:
```bash
codex
/prompts:controller
```

### Step 3: Start the Bridge

From a separate terminal (or tmux pane):
```bash
./tools/tmux_bridge/bridge.py --session macs
```

The bridge will now monitor the worker terminal for requests and route them to the controller.

## Manual Workflow (Without Bridge)

You can also use MACS manually without the bridge:

1. **Worker** performs tasks and asks questions
2. **You** read worker output with `snapshot.sh`
3. **You** provide guidance via `send.sh`
4. Repeat

```bash
# Read recent worker output
./tools/tmux_bridge/snapshot.sh

# Send instructions to worker
./tools/tmux_bridge/send.sh "Proceed with the implementation"

# Check if worker is busy
./tools/tmux_bridge/status.sh
```

## Customizing for Your Project

### 1. Create Project-Specific Rules

Copy the controller prompt to your project and customize:

```bash
cp .codex/prompts/controller.md your-project/.codex/prompts/controller.md
```

Add your project-specific rules at the bottom:
- Repository structure
- CI/CD requirements
- Security policies
- Team conventions

See `examples/project-rules/` for examples.

### 2. Configure the Bridge

Common bridge options:

```bash
# Use a specific controller model
./tools/tmux_bridge/bridge.py --controller-model gpt-4

# Disable heuristic triggers
./tools/tmux_bridge/bridge.py --no-heuristic

# Increase context sent to controller
./tools/tmux_bridge/bridge.py --worker-context-lines 100
```

## Troubleshooting

### Bridge can't find panes

Ensure your tmux windows/panes have identifiable names:
```bash
# Set pane title manually
printf '\033]2;worker\033\\'
```

Or pin the pane explicitly:
```bash
./tools/tmux_bridge/set_target.sh --pane %3
```

### Worker appears busy when idle

The busy detection looks for "esc to interrupt" in recent output. If this persists in scrollback:
```bash
# Increase busy detection window
TARGET_PANE_BUSY_LINES=60 ./tools/tmux_bridge/status.sh
```

### Responses not being sent

Check if the worker is busy:
```bash
./tools/tmux_bridge/status.sh
```

Force send if needed:
```bash
./tools/tmux_bridge/send.sh --force "your message"
```

## Next Steps

- Read the [Architecture Guide](architecture.md) to understand how MACS works
- See [Customization Guide](customization.md) for advanced configuration
- Check `examples/` for project-specific rule examples
