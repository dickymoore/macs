---
name: claude-runtime
description: "Claude Code runtime/session control: use Claude Code slash commands and CLI flags to manage sessions, permissions, model selection, and restarts in a worker terminal. Trigger when the controller needs to operate the Claude Code CLI like a human."
---

# Claude Runtime

## Overview
Operate the Claude Code CLI safely: manage session state, permissions, models, and restarts from a worker terminal.

## Session Safety

1) Confirm idle state
- Snapshot and/or `status` the worker; do not intervene mid-run.
- Only proceed when the worker is at a prompt or explicitly idle.

2) Prefer in-session resets
- Use `/clear` to reset the current conversation.
- Use `/compact` to summarize and shrink context.

3) Full reset (only between tasks)
- Exit the CLI with `Ctrl+D` (EOF) when permitted by controller rules/human request.
- Relaunch with appropriate flags when a fresh context is needed.

## Core Slash Commands (Claude Code)

Use `/help` to see the full list. Common commands:
- `/model` change the active model.
- `/permissions` edit tool permissions.
- `/clear` reset the current conversation.
- `/compact` summarize the conversation.
- `/add-dir` add a working directory.
- `/agents` view or manage agents.
- `/config` update configuration.
- `/memory` edit memory files.
- `/mcp` manage MCP servers/tools.
- `/cost` show usage cost.
- `/doctor` check installation health.
- `/login` and `/logout` manage auth.
- `/init` initialize in the current repo.
- `/bug` submit a bug report.
- `/pr_comments` read PR comments in the repo.

## Resume / Continue (Shell)

- `claude -c` / `claude --continue` continue the most recent conversation.
- `claude -r <SESSION_ID>` / `claude --resume <SESSION_ID>` resume a specific session.

## Launch Flags (Shell)

Use these when starting Claude from the shell (not inside the CLI):
- `--model` choose a model at launch.
- `--permission-mode` set tool permission mode.
- `--add-dir` grant additional directories.
- `--dangerously-skip-permissions` bypass permission prompts (use only when explicitly allowed).

## Guardrails

- Do not restart mid-run.
- Prefer `/clear` or `/compact` over full restarts when possible.
- Use `Ctrl+D` only when allowed by controller rules or explicitly requested by the human.
- If the worker is not Claude Code, switch to the model-specific runtime skill instead.
