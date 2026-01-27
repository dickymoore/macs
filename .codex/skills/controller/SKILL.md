---
name: controller
description: "Load the MACS controller prompt for supervising a worker agent in another terminal."
---

# Controller (MACS)

## Purpose
Launch and use the Controller prompt for multi-agent orchestration.

## Usage
Load the prompt with: `/prompts:controller`

The prompt file lives at `.codex/prompts/controller.md`.

## When to Use
- Use when you want to supervise a worker agent in another terminal
- Use when you need structured oversight with decision priorities and security invariants
- Use with the tmux bridge for automated request/response routing

## Related
- `/prompts:loop` - Keep the controller looping without interruption
