---
name: bmad-bmm
description: "Use for BMAD BMM (BMad Method) software-dev workflows: PRD, architecture, epics/stories, sprint planning, quick-spec/quick-dev, and lifecycle tracking. Trigger on 'BMM', 'BMad Method', or when users want structured planning/implementation via BMAD.'"
---

# BMAD BMM (BMad Method)

## Overview
Drive the BMM lifecycle (analysis -> planning -> solutioning -> implementation) via the worker terminal. Use `/bmad-help` or workflow-status to determine the next workflow, then run the appropriate `/bmad:bmm:workflows:<id>` (or tool-equivalent) command in the worker.

## Non-negotiable execution rules
- Run all BMAD BMM workflows in the worker or dedicated BMAD window, never locally in the controller session.
- If a BMAD window exists, send commands there (use `send.sh --label bmad`). Otherwise use the worker terminal.
- Do not manually draft PRD, architecture, epics, or stories in the controller when a BMAD workflow can generate them.
- Always load the BMAD agent persona and follow its menu items before running workflows.
- Do not forward the user's request verbatim to the worker. First read the relevant files locally, then translate the request into concrete BMAD menu steps and commands for the worker.
- Use BMAD commands with a single leading slash (e.g. `/bmad-help`). Never send `//bmad-help`.
- If the BMM workflow requires it, start by loading the **SM agent**.

## Workflow

1) Determine track
- Quick Flow: small changes, bug fixes, refactors.
- BMad Method: product work that needs PRD + architecture.
- Enterprise: extended planning (security, DevOps, testing strategy).
- If unsure, tell the worker to run `/bmad-help` and follow its recommendation.

2) Use the workflow map
- Select the workflow that matches the phase and artifact needs.
- Run the workflow in the worker terminal and wait for output.

3) Brownfield support
- If the repo lacks documentation or is an existing codebase, run `document-project` before Phase 4 workflows.

4) Quick Flow
- For small tasks, run `quick-spec` then `quick-dev`.

5) Track progress
- If available, use `workflow-status` to see what is complete and what's next.

## Worker Command Pattern
- Always send BMAD commands to the worker via `send.sh`.
- Example: `/bmad-help` -> choose next workflow -> `/bmad:bmm:workflows:create-prd`.

## References
- `references/workflow-map.md`
- `references/track-selection.md`
