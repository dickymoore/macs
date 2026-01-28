---
name: bmad-bmgd
description: "Use for BMAD BMGD (game development) workflows, game briefs/GDDs, and game-specific planning. Trigger on BMGD, game design, GDD, or game architecture requests." 
---

# BMAD BMGD (Game Dev)

## Overview
Run BMGD workflows in the worker terminal to produce game briefs, GDDs, and game-specific architecture. Use `/bmad-help` to discover available BMGD workflows and the recommended next step.

## Non-negotiable execution rules
- Run all BMGD workflows in the worker or dedicated BMAD window, never locally in the controller session.
- If a BMAD window exists, send commands there (use `send.sh --label bmad`). Otherwise use the worker terminal.
- Do not manually author game briefs or GDDs in the controller when the workflow can generate them.
- Always load the BMGD agent persona and follow its menu items before running workflows.
- Do not forward the user's request verbatim to the worker. First read the relevant files locally, then translate the request into concrete BMAD menu steps and commands for the worker.
- Use BMAD commands with a single leading slash (e.g. `/bmad-help`). Never send `//bmad-help`.
- If the BMGD workflow requires it, start by loading the **SM agent**.

## Workflow

1) Confirm module presence
- Ensure `_bmad/bmgd/` exists in the repo.
- If missing, ask whether to install BMGD via `npx bmad-method install` and select the module.

2) Discover available workflows
- In the worker terminal, run `/bmad-help` and pick a BMGD workflow.
- Optionally inspect `_bmad/bmgd/workflows/` to see available workflow IDs.

3) Execute in worker
- Send the workflow command to the worker with `send.sh`.
- Wait for output artifacts before proceeding.

## References
- `references/locators.md`
- `references/game-terms.md`
