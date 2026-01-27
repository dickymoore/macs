---
name: bmad-cis
description: "Use for BMAD CIS (Creative Intelligence Suite) tasks like brainstorming, innovation strategy, problem solving, or storytelling. Trigger on CIS, creative suite, brainstorming coach, or storytelling workflows." 
---

# BMAD CIS (Creative Intelligence Suite)

## Overview
Use CIS for creative/ideation workflows (brainstorming, innovation, storytelling, problem solving). Execute CIS workflows in the worker terminal.

## Non-negotiable execution rules
- Run all CIS workflows in the worker or dedicated BMAD window, never locally in the controller session.
- If a BMAD window exists, send commands there (use `send.sh --label bmad`). Otherwise use the worker terminal.
- Do not manually run CIS exercises in the controller when the CIS workflow can run them.
- Always load the CIS agent persona and follow its menu items before running workflows.

## Workflow

1) Confirm module presence
- Ensure `_bmad/cis/` exists in the repo.
- If missing, install CIS via `npx bmad-method install` and select the module.

2) Discover CIS workflows
- Run `/bmad-help` in the worker to list CIS commands.
- Inspect `_bmad/cis/agents/` and `_bmad/cis/workflows/` for available options.

3) Execute in worker
- Send the workflow command to the worker with `send.sh`.
- Wait for outputs in `_bmad-output/`.

## References
- `references/locators.md`
