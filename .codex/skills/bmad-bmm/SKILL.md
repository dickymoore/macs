---
name: bmad-bmm
description: "Use for BMAD BMM (BMad Method) software-dev workflows: PRD, architecture, epics/stories, sprint planning, quick-spec/quick-dev, and lifecycle tracking. Trigger on 'BMM', 'BMad Method', or when users want structured planning/implementation via BMAD."
---

# BMAD BMM (BMad Method)

## Overview
Drive the BMM lifecycle (analysis -> planning -> solutioning -> implementation) via the worker terminal. Use `/bmad-help` or `workflow-status` to determine the next workflow, then run the appropriate `/bmad:bmm:workflows:<id>` (or tool-equivalent) command in the worker.

**Default mode is EXHAUSTIVE.** Unless the user explicitly asks for a lighter path, run the BMM workflows exhaustively: consult every BMAD persona, run every workflow in the map, and ensure all optional stages execute.

## Non-negotiable execution rules
- Run all BMAD BMM workflows in the worker or dedicated BMAD window, never locally in the controller session.
- If a BMAD window exists, send commands there (use `send.sh --label bmad`). Otherwise use the worker terminal.
- Do not manually draft PRD, architecture, epics, or stories in the controller when a BMAD workflow can generate them.
- Always load the BMAD agent persona and follow its menu items before running workflows.
- Do not forward the user's request verbatim to the worker. First read the relevant files locally, then translate the request into concrete BMAD menu steps and commands for the worker.
- Use BMAD commands with a single leading slash (e.g. `/bmad-help`). Never send `//bmad-help`.
- If the BMM workflow requires it, start by loading the **SM agent**.
- Default to **EXHAUSTIVE** unless the user explicitly opts out.
- **EXHAUSTIVE =** consult **every** available BMAD persona/agent, and run **every** workflow in the BMM map, including all optional stages.
- If a workflow is optional or conditional and its applicability is unclear, **run it anyway** and note assumptions in the artifacts.
- Do not stop after any single stage; continue until all workflows are complete.
- **Advanced Elicitation is mandatory.** If prompted for elicitation depth or mode, always choose **Advanced Elicitation**. If a standalone "Advanced Elicitation" workflow/menu item exists, run it before Phase 1 and again at each major gate (post-PRD, post-architecture, pre-implementation).

## Workflow

1) Determine execution mode (default: **EXHAUSTIVE**)
- If the user explicitly requests quick/small scope, follow that request.
- Otherwise run **EXHAUSTIVE** and do not short-circuit on scope.

2) Enumerate personas and workflows
- In the worker, run `/bmad-help` and list **all** available personas/agents and **all** BMM workflows.
- Consult **every** persona before Phase 1, and again at key gates (post-PRD, post-architecture, pre-implementation).
- Use the persona order shown by `/bmad-help` (top-to-bottom); if it changes, follow the latest list.
- When elicitation depth/mode is offered, select **Advanced Elicitation** every time.

3) Run the full workflow map (EXHAUSTIVE)
- **Phase 1 (optional by default):** `brainstorm` -> `research` -> `create-product-brief`.
- **Phase 2:** `create-prd` -> `create-ux-design`.
- **Phase 3:** `create-architecture` -> `create-epics-and-stories` -> `check-implementation-readiness`.
- **Phase 4:** `sprint-planning` -> `create-story` -> `dev-story` -> `code-review` -> `correct-course` -> `retrospective`.
- **Quick Flow:** also run `quick-spec` -> `quick-dev` as a supplemental sanity pass (unless user opts out).
- **Brownfield:** if the repo is existing or docs are missing, run `document-project` before Phase 4 (if uncertain, run it anyway).
- **Enterprise extensions:** if the menu exposes security, DevOps, or test-strategy workflows, run them as well.

4) Track progress
- After each workflow, run `workflow-status` (or equivalent) to confirm completion and next steps.

## Exhaustive Checklist (default)
1) Run `/bmad-help` and capture the full persona list and workflow list.
2) Consult every persona once in the order shown.
3) Run **Advanced Elicitation** (if offered as a workflow or mode).
4) Phase 1: `brainstorm`, `research`, `create-product-brief`.
5) Consult every persona again (same order).
6) Run **Advanced Elicitation** again if offered.
7) Phase 2: `create-prd`, `create-ux-design`.
8) Consult every persona again (same order).
9) Run **Advanced Elicitation** again if offered.
10) Phase 3: `create-architecture`, `create-epics-and-stories`, `check-implementation-readiness`.
11) Consult every persona again (same order).
12) Run **Advanced Elicitation** again if offered.
13) Brownfield: `document-project` (if uncertain, run it).
14) Phase 4: `sprint-planning`, `create-story`, `dev-story`, `code-review`, `correct-course`, `retrospective`.
15) Quick Flow sanity pass: `quick-spec`, `quick-dev` (unless user opts out).
16) Enterprise extensions: run any security, DevOps, or test-strategy workflows exposed in the menu.
17) After each workflow, run `workflow-status`.

## Worker Command Pattern
- Always send BMAD commands to the worker via `send.sh`.
- Example: `/bmad-help` -> choose next workflow -> `/bmad:bmm:workflows:create-prd`.

## References
- `references/workflow-map.md`
- `references/track-selection.md`
