---
name: gemini-runtime
description: "Gemini CLI runtime/session control: use Gemini CLI slash commands and CLI flags to manage sessions, models, and restarts in a worker terminal. Trigger when the controller needs to operate the Gemini CLI like a human."
---

# Gemini Runtime

## Overview
Operate the Gemini CLI safely: manage session state, model selection, and restarts from a worker terminal.

## Session Safety

1) Confirm idle state
- Snapshot and/or `status` the worker; do not intervene mid-run.
- Only proceed when the worker is at a prompt or explicitly idle.

2) Prefer in-session resets
- Use `/clear` to reset the current conversation.
- Use `/rewind` to go back to a previous step.
- Use `/stats` or `/context` to confirm state.

3) Full reset (only between tasks)
- Use `/quit` (or `/exit`) to leave the CLI.
- Relaunch with appropriate flags when a fresh context is needed.

## Core Slash Commands (Gemini CLI)

Use `/help` to see the full list. Common commands:
- `/model` select a model.
- `/resume` resume a saved session.
- `/restore` restore a previous state.
- `/chat` manage chat sessions.
- `/clear` reset the current conversation.
- `/context` show current context.
- `/stats` show session stats.
- `/settings` open settings.
- `/privacy` view privacy info.
- `/policies` view policies.
- `/bug` file a bug.
- `/vim` toggle vim mode.
- `/rewind` step backward in the session.
- `/quit` or `/exit` exit the CLI.

## Resume / Continue (Shell)

- `gemini --resume <SESSION_ID>` or `gemini -r <SESSION_ID>` resume a session.
- `gemini --list-sessions` list available sessions.
- `gemini --delete-session <SESSION_ID>` delete a session by index.

## Guardrails

- Do not restart mid-run.
- Prefer `/clear` or `/rewind` over full restarts when possible.
- Use `/stats` or `/context` after model changes to confirm state.
- If the worker is not Gemini CLI, switch to the model-specific runtime skill instead.
