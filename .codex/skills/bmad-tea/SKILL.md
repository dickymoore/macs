---
name: bmad-tea
description: "Use for BMAD TEA (Test Architect) workflows: test-design, atdd, automate, test-review, nfr-assess, trace, and test framework/CI setup. Trigger on TEA, Test Architect, or BMAD testing/quality gates." 
---

# BMAD TEA (Test Architect)

## Overview
Run TEA workflows in the worker terminal. TEA integrates with BMM and provides testing strategy, automation, and quality gates across the lifecycle.

## Non-negotiable execution rules
- Run all TEA workflows in the worker or dedicated BMAD window, never locally in the controller session.
- If a BMAD window exists, send commands there (use `send.sh --label bmad`). Otherwise use the worker terminal.
- Do not manually create TEA artifacts (test design, traceability, reviews) in the controller when the workflow can generate them.
- Always load the TEA agent persona and follow its menu items before running workflows.
- Do not forward the user's request verbatim to the worker. First read the relevant files locally, then translate the request into concrete BMAD menu steps and commands for the worker.
- Use BMAD commands with a single leading slash (e.g. `/bmad-help`). Never send `//bmad-help`.
- If the TEA workflow requires it, start by loading the **SM agent**.

## Workflow

1) Confirm TEA availability
- Check `_bmad/bmm/config.yaml` for TEA settings if needed.
- If unsure, have the worker run `/bmad-help` and select a TEA workflow.

2) Pick the TEA workflow
- Use `framework` or `ci` once per project.
- Use `test-design` (system-level or per-epic).
- Use `atdd` before implementation (red phase).
- Use `automate` after implementation.
- Use `test-review`, `nfr-assess`, or `trace` for quality gates.

3) Execute in worker
- Send the exact TEA workflow command to the worker.
- Wait for outputs and artifacts before proceeding.

## References
- `references/commands.md`
- `references/configuration.md`
