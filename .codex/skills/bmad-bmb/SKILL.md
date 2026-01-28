---
name: bmad-bmb
description: "Use for BMAD BMB (builder module) tasks: creating/editing BMAD agents, workflows, or modules. Trigger on BMAD builder, agent builder, workflow builder, or module creation requests." 
---

# BMAD BMB (Builder Module)

## Overview
Use BMB when the user wants to create or modify BMAD agents, workflows, or full modules. Execute all BMAD actions in the worker terminal.

## Non-negotiable execution rules
- Run all BMB workflows in the worker or dedicated BMAD window, never locally in the controller session.
- If a BMAD window exists, send commands there (use `send.sh --label bmad`). Otherwise use the worker terminal.
- Do not manually craft BMAD agents or workflows in the controller when the BMB workflow can generate them.
- Always load the BMB agent persona and follow its menu items before running workflows.
- Do not forward the user's request verbatim to the worker. First read the relevant files locally, then translate the request into concrete BMAD menu steps and commands for the worker.
- Use BMAD commands with a single leading slash (e.g. `/bmad-help`). Never send `//bmad-help`.
- If the BMB workflow requires it, start by loading the **SM agent**.

## Workflow

1) Confirm module presence
- Ensure `_bmad/bmb/` exists in the repo.
- If missing, install BMB via `npx bmad-method install` and select the module.

2) Discover builder workflows
- Run `/bmad-help` in the worker to list BMB commands.
- Inspect `_bmad/bmb/agents/` and `_bmad/bmb/workflows/` for available builders.

3) Execute in worker
- Send the chosen workflow command to the worker with `send.sh`.
- Let the workflow guide creation/editing.

## References
- `references/locators.md`
