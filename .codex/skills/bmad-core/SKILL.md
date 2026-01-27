---
name: bmad-core
description: "Use when a user says 'use BMAD', 'follow BMAD', or wants the BMAD Method run in a repo. Routes BMAD work to the worker terminal, verifies install, and selects the right BMAD module/track."
---

# BMAD Core

## Overview
Route BMAD execution to the worker terminal. Verify BMAD is installed, then use `/bmad-help` (or tool equivalent) to pick the right module and workflow. Do not run BMAD workflows in the controller session.

## Non-negotiable execution rules
- Run all BMAD commands in the worker or a dedicated BMAD window, never in the controller session.
- If a BMAD window exists, send commands there (use `send.sh --label bmad`). Otherwise use the worker terminal.
- Do not manually author BMAD outputs in the controller when a BMAD workflow or agent can generate them.
- Always load the BMAD agent persona, follow its menu items, and run BMAD workflows as instructed.

## Workflow

1) Verify BMAD installation
- Check for `_bmad/` and `_bmad-output/` in the target repo.
- If missing, ask the user whether to install, then tell the worker to run `npx bmad-method install`.
- If present, proceed to help/track selection.

2) Always execute in worker
- Use `./tools/tmux_bridge/send.sh` to send BMAD commands to the worker terminal.
- Wait for worker output before deciding the next BMAD step.

3) Select module + track
- If the user just says "use BMAD" or "follow BMAD", instruct the worker to run `/bmad-help` to see the recommended next action and available modules.
- Use repo cues to disambiguate:
  - `_bmad/bmm` -> BMM (software dev lifecycle)
  - `_bmad/bmgd` -> BMGD (game dev)
  - `_bmad/cis` -> CIS (creative/ideation)
  - `_bmad/bmb` -> BMB (builder: agents/workflows/modules)
- If the user explicitly names a module, switch to that module's skill.

4) Hand off to module skill
- BMM lifecycle -> `bmad-bmm`
- Testing/quality -> `bmad-tea`
- Game dev -> `bmad-bmgd`
- Creative suite -> `bmad-cis`
- Builder module -> `bmad-bmb`

## Worker Command Pattern
- Send the exact BMAD command to the worker (e.g., `/bmad-help`).
- Do not inline long explanations; let BMAD workflows drive the process.

## References
- `references/core.md`
