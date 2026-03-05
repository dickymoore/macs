---
name: aider-runtime
description: "Aider runtime/session control: use Aider CLI slash commands and flags to manage files, models, and sessions in a worker terminal. Trigger when the controller needs to operate the Aider CLI like a human."
---

# Aider Runtime

## Overview
Operate the Aider CLI safely: manage tracked files, chat modes, and session control from a worker terminal.

## Session Safety

1) Confirm idle state
- Snapshot and/or `status` the worker; do not intervene mid-run.
- Only proceed when the worker is at a prompt or explicitly idle.

2) Prefer in-session resets
- Use `/clear` to reset the chat context.
- Use `/reset` to reset to a clean conversation state.

## Core Slash Commands (Aider)

Use `/help` to see the full list. Common commands:
- `/add` add files to the chat context.
- `/drop` remove files from the chat context.
- `/ls` list tracked files.
- `/read` read a file into the context.
- `/diff` show current diffs.
- `/git` run git commands.
- `/commit` create a commit.
- `/lint` run linting.
- `/test` run tests.
- `/run` run a shell command.
- `/map` and `/map-refresh` manage repo maps.
- `/tokens` show token usage.
- `/settings` show or change settings.
- `/clear`, `/reset`, `/undo` manage conversation state.
- `/exit` or `/quit` exit Aider.

## Launch Flags (Shell)

Use these when starting Aider from the shell (not inside the CLI):
- `--model` choose a model at launch.
- `--edit-format` set edit format.
- `--message` send a one-shot prompt.
- `--file` add a file at startup.
- `--git` enable git integration.

## Guardrails

- Do not restart mid-run.
- Prefer `/clear` or `/reset` over full restarts when possible.
- If the worker is not Aider, switch to the model-specific runtime skill instead.
