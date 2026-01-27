# MACS - Multi Agent Control System

A tmux-based orchestration framework for controlling AI coding agents across multiple terminals. Enables a "controller" agent to oversee and direct a "worker" agent through structured request/response protocols.

## Overview

MACS provides infrastructure for multi-agent AI workflows where:
- **Controller Terminal** - Runs a supervisory agent that makes decisions and provides oversight
- **Worker Terminal** - Runs a task-execution agent that performs the actual work
- **Bridge** - Monitors communication between terminals, extracts requests, and routes responses

```
┌─────────────────────┐     ┌─────────────────────┐
│  Controller (A)     │     │    Worker (B)       │
│  - Makes decisions  │◄───►│  - Executes tasks   │
│  - Reviews output   │     │  - Reports status   │
│  - Provides guidance│     │  - Asks questions   │
└─────────────────────┘     └─────────────────────┘
         │                           │
         └───────────┬───────────────┘
                     │
              ┌──────▼──────┐
              │   Bridge    │
              │  (Python)   │
              └─────────────┘
```

## Quick Start

### Prerequisites
- tmux
- Python 3.8+
- Codex CLI

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_ORG/macs.git
cd macs

# Copy prompts to your project (or use as reference)
cp -r .codex/prompts/* ~/.codex/prompts/
```

### Basic Usage

1. **Start tmux with two panes**:
```bash
tmux new-session -s macs
# Split: Ctrl+b %
```

2. **In the worker pane**, start Codex:
```bash
codex
```

3. **In the controller pane**, load the controller prompt:
```bash
codex
/prompts:controller
```

4. **Start the bridge** (from a third terminal or background):
```bash
./tools/tmux_bridge/bridge.py --session macs
```

The bridge will monitor the worker terminal for `<<CONTROLLER_REQUEST>>` blocks and route them to the controller.

## Architecture

### Request/Response Protocol

The worker agent can request controller input using delimited blocks:

```
<<CONTROLLER_REQUEST>>
Question or status update here.
Options or context if needed.
<<CONTROLLER_REQUEST_END>>
```

The controller responds with:

```
<<CONTROLLER_RESPONSE>>
WORKER INSTRUCTIONS:
Step-by-step guidance here.

NOTES:
Context or rationale (not sent to worker).
<<CONTROLLER_RESPONSE_END>>
```

### Bridge Modes

- **auto** (default) - Bridge invokes controller agent automatically
- **manual** - Bridge writes requests to inbox, waits for response files
- **codex-interactive** - Bridge sends requests to a live Codex session

### Helper Scripts

| Script | Purpose |
|--------|---------|
| `snapshot.sh` | Capture recent output from worker terminal |
| `send.sh` | Send text/commands to worker terminal |
| `status.sh` | Check if worker is busy (running) or idle |
| `set_target.sh` | Pin the worker pane for subsequent commands |

## Configuration

### Codex Config (`.codex/config.toml`)

```toml
model = "your-preferred-model"

[features]
unified_exec = true
shell_snapshot = true
```

### Customizing the Controller Prompt

Copy `.codex/prompts/controller.md` to your project and customize:
- Decision priorities
- Security invariants
- Project-specific rules
- Communication protocols

See `examples/project-rules/` for examples.

## Documentation

- [Getting Started](docs/getting-started.md) - Detailed setup guide
- [Architecture](docs/architecture.md) - How MACS works
- [Customization](docs/customization.md) - Adapting for your project

## License

MIT License - see [LICENSE](LICENSE) for details.
