---
name: codex-runtime
description: "Codex runtime/session control: use Codex CLI slash commands and CLI flags to manage sessions, approvals, models, resumes/forks, and safe restarts in a worker terminal. Trigger when the controller needs to operate the Codex CLI like a human."
---

# Codex Runtime

## Overview
Operate the Codex CLI safely: manage session state, approvals, models, resume/fork, and clean restarts from a worker terminal.

## Session Safety

1) Confirm idle state
- Snapshot and/or `status` the worker; do not intervene mid-run.
- Only proceed when the worker is at a prompt or explicitly idle.

2) Prefer in-session resets
- Use `/new` for a fresh conversation without leaving the CLI.
- Use `/compact` to summarize after long runs.
- Use `/status` to confirm model, approvals, and sandbox before new work.

3) Full reset (only between tasks)
- Use `/exit` (or `/quit`) to leave the CLI.
- Relaunch with the appropriate flags only when a fresh context is materially helpful.

## Core Slash Commands (Codex CLI)

Use `/help` (or `/`) to see the full list. Common commands:
- `/model` change the active model.
- `/status` show current model, approvals, and sandbox.
- `/permissions` manage approvals (alias `/approvals`).
- `/new` start a fresh conversation.
- `/compact` summarize the conversation.
- `/diff` view Git diff.
- `/review` request a review of the working tree.
- `/mcp` list or manage MCP servers/tools.
- `/resume` resume a saved conversation.
- `/fork` fork a saved conversation.
- `/apps`, `/ps`, `/personality`, `/mention` for additional session controls.
- `/init`, `/logout`, `/feedback`, `/undo` for setup/cleanup.
- `/exit` or `/quit` to exit the CLI.

## Resume / Fork (Shell)

- `codex resume` open the interactive resume picker.
- `codex resume --last` resume the most recent session.
- `codex resume --all` list sessions across projects.
- `codex resume <SESSION_ID>` resume a specific session.
- `codex exec resume --last "..."` resume and immediately send a prompt.
- `codex fork <SESSION_ID>` fork an existing session.

## Launch Flags (Shell)

Use these when starting Codex from the shell (not inside the CLI):
- `--model` choose a model at launch.
- `--profile` select a saved profile.
- `--oss` use the open-source instructions mode.
- `--ask-for-approval` set approval behavior.
- `--sandbox` choose sandbox mode.
- `--full-auto` low-friction local work (approval on-request + workspace-write).
- `--yolo` (aka `--dangerously-bypass-approvals-and-sandbox`) disables approvals and sandboxing. Use only when explicitly allowed.
- `--search` enable live web search instead of cached.
- `--cd` set working directory before the session starts.
- `--add-dir` grant additional writable directories.
- `--config` use a custom config file.
- `--image` include images with the first prompt.
- `--enable` / `--disable` toggle specific Codex features.

## Guardrails

- Do not send Ctrl+C or Ctrl+D to exit; use `/exit`.
- Never restart mid-run.
- Use `/status` after model or approval changes to confirm settings.
- If the worker is not Codex, switch to the model-specific runtime skill instead.
