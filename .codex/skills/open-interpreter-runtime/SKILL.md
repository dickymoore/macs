---
name: open-interpreter-runtime
description: "Open Interpreter runtime/session control: use Open Interpreter CLI % commands and shell flags to manage sessions and context in a worker terminal. Trigger when the controller needs to operate Open Interpreter like a human."
---

# Open Interpreter Runtime

## Overview
Operate the Open Interpreter CLI safely: manage session state, verbosity, and context from a worker terminal.

## Session Safety

1) Confirm idle state
- Snapshot and/or `status` the worker; do not intervene mid-run.
- Only proceed when the worker is at a prompt or explicitly idle.

2) Prefer in-session resets
- Use `%reset` to reset the conversation state.
- Use `%undo` to revert the last step.
- Use `%retry` to rerun the last step.

## Core % Commands (Open Interpreter)

Use `%help` to see the full list. Common commands:
- `%reset` reset the conversation.
- `%undo` undo the last action.
- `%retry` retry the last action.
- `%verbose` toggle verbose output.
- `%tokens` show token usage.
- `%editor` open the editor for the current session.
- `%history` / `%messages` view conversation history.
- `%logs` / `%debug` show logs and debug info.
- `%multi_line` / `%paste` handle multi-line input.
- `%profiles` / `%profile` manage profiles.
- `%list` list available commands.
- `%clear` clear the screen.

## Launch (Shell)

- `interpreter` starts the CLI.
- `interpreter --help` shows available flags and options.

## Guardrails

- Do not restart mid-run.
- Prefer `%reset` or `%undo` over full restarts when possible.
- If the worker is not Open Interpreter, switch to the model-specific runtime skill instead.
