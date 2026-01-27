# MACS Architecture

This document explains how MACS (Multi Agent Control System) works internally.

## Overview

MACS enables a supervisory "controller" agent to oversee and direct a "worker" agent across separate terminals. The system uses tmux for terminal multiplexing and a Python bridge for communication routing.

```
┌─────────────────────────────────────────────────────────────┐
│                      TMux Session                            │
│  ┌──────────────────┐       ┌──────────────────┐            │
│  │  Controller (A)  │       │   Worker (B)     │            │
│  │                  │       │                  │            │
│  │  - Codex         │       │  - Codex         │            │
│  │  - /controller   │       │  - Task agent    │            │
│  │  - Oversight     │       │  - Execution     │            │
│  └────────┬─────────┘       └────────┬─────────┘            │
│           │                          │                       │
│           │    pipe-pane logging     │                       │
│           ▼                          ▼                       │
│  ┌────────────────────────────────────────────┐             │
│  │              Bridge (Python)                │             │
│  │  - Monitors worker log                     │             │
│  │  - Detects request blocks                  │             │
│  │  - Routes to controller                    │             │
│  │  - Injects responses                       │             │
│  └────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Controller Terminal

The controller runs a Codex session with the controller prompt loaded. It:
- Makes high-level decisions
- Reviews worker output
- Provides guidance and instructions
- Enforces security invariants

### 2. Worker Terminal

The worker runs a Codex session (or any AI agent) that:
- Executes tasks
- Reports progress
- Asks questions
- Requests guidance when needed

### 3. Bridge

The Python bridge (`bridge.py`) orchestrates communication:
- Uses tmux `pipe-pane` to log terminal output
- Parses logs for request delimiters
- Routes requests to controller (various backends)
- Injects responses back into worker terminal

## Communication Protocol

### Request Format

Workers signal requests using delimited blocks:

```
<<CONTROLLER_REQUEST>>
Request content here.
Context and options.
<<CONTROLLER_REQUEST_END>>
```

Optional attributes:
```
<<CONTROLLER_REQUEST id=abc123 type=question>>
```

### Response Format

Controllers respond with structured output:

```
<<CONTROLLER_RESPONSE>>
WORKER INSTRUCTIONS:
Step-by-step guidance.

NOTES:
Context for human (not sent to worker).
<<CONTROLLER_RESPONSE_END>>
```

### Heuristic Triggers

When enabled, the bridge also triggers on natural language patterns:
- Questions ending with `?`
- Phrases: "what would you like", "should i", "ready to proceed"
- Completion: "done", "complete", "finished"

## Bridge Operation Modes

### 1. Codex Interactive (Default)

```
Worker ──request──> Bridge ──> Controller Codex ──response──> Bridge ──> Worker
```

The bridge sends requests to a live Codex session in the controller terminal and waits for the response.

### 2. Codex Exec

```
Worker ──request──> Bridge ──> codex exec ──response──> Bridge ──> Worker
```

The bridge invokes `codex exec` for one-shot responses without maintaining a session.

### 3. Manual Mode

```
Worker ──request──> Bridge ──> inbox/*.txt
                                    │
                                    ▼ (human writes response)
                               outbox/*.txt ──> Bridge ──> Worker
```

Requests are written to files; humans (or other systems) write responses.

## TMux Integration

### Pane Discovery

The bridge discovers panes by searching for:
1. Explicit pane ID (`--worker-pane %3`)
2. Pinned pane (`target_pane.txt`)
3. Window/pane name containing label
4. Process command containing "codex"

### Output Capture

```bash
tmux pipe-pane -o -t %3 "cat >> /tmp/macs-worker.log"
```

This streams all pane output to a log file that the bridge monitors.

### Input Injection

```bash
# Short messages
tmux send-keys -t %3 "message" Enter

# Long messages (>1000 chars)
tmux load-buffer -b buf - <<< "message"
tmux paste-buffer -t %3 -b buf
tmux send-keys -t %3 Enter
```

### Busy Detection

The bridge checks for "esc to interrupt" in recent output to determine if the worker is still processing:

```bash
tmux capture-pane -p -t %3 -S -40 | grep -qi "esc to interrupt"
```

## File Structure

```
tools/tmux_bridge/
├── bridge.py           # Main orchestration
├── snapshot.sh         # Capture pane output
├── send.sh            # Send input to pane
├── status.sh          # Check busy/idle
├── set_target.sh      # Pin target pane
├── start_*.sh         # Session setup
├── controller_prompt.txt  # System prompt
├── target_pane.txt    # Pinned pane (runtime)
├── inbox/             # Incoming requests
├── outbox/            # Outgoing responses
└── archive/           # Historical data
```

## Request Deduplication

Requests are deduplicated using SHA1 hashes to prevent processing the same request twice (e.g., if it appears in scrollback).

## Response Splitting

By default, responses are split:
- `WORKER INSTRUCTIONS:` - Sent to worker terminal
- `NOTES:` - Printed locally (not sent to worker)

This allows the controller to communicate privately with the human operator.

## Security Considerations

1. **Isolation**: Controller and worker run in separate terminals
2. **Audit Trail**: All requests/responses archived
3. **Guard Rails**: Controller prompt enforces security invariants
4. **Busy Protection**: Won't send to busy worker by default

## Extending MACS

### Custom Backends

Implement a new backend by:
1. Adding a choice to `--controller-backend`
2. Implementing `run_<backend>_controller(block_text, args)`
3. Returning response text

### Custom Triggers

Modify `is_heuristic_trigger()` and related regexes to detect additional patterns.

### Multiple Workers

Run multiple bridges with different `--worker-pane` and `--log` values to supervise multiple workers from one controller.
