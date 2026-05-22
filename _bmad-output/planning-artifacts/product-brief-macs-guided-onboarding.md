---
title: "Product Brief: MACS Guided Onboarding"
status: "complete"
created: "2026-04-14T11:00:57+01:00"
updated: "2026-04-14T11:00:57+01:00"
inputs:
  - "/home/codexuser/macs_dev/_bmad-output/brainstorming/brainstorming-session-2026-04-14-11-00-57.md"
  - "/home/codexuser/macs_dev/README.md"
  - "/home/codexuser/macs_dev/docs/getting-started.md"
  - "/home/codexuser/macs_dev/docs/user-guide.md"
  - "/home/codexuser/macs_dev/docs/how-tos.md"
  - "/home/codexuser/macs_dev/docs/architecture.md"
  - "/home/codexuser/macs_dev/_bmad-output/planning-artifacts/ux-design-specification.md"
  - "/home/codexuser/macs_dev/_bmad-output/planning-artifacts/operator-cli-contract.md"
  - "/home/codexuser/macs_dev/_bmad-output/implementation-artifacts/stories/7-2-deliver-mixed-runtime-setup-and-validation-flow.md"
  - "/home/codexuser/macs_dev/_bmad-output/release-evidence/setup-validation-report.md"
---

# Product Brief: MACS Guided Onboarding

## Executive Summary

MACS already ships the core onboarding ingredients: a controller-first CLI, repo-local setup and validation commands, canonical docs, and release-evidence reporting. What it still lacks is a guided path that turns those ingredients into a confident first-run experience. Today, technically capable adopters can bootstrap the repo, but they still have to infer too much: what MACS is actually governing, which command comes next, how to interpret `PARTIAL` or `BLOCKED` states, and when a repo is merely configured versus truly safe-ready.

This initiative should create a controller-owned guided onboarding layer for the existing MACS surface. The first version should be a terminal-guided setup assistant, backed by refreshed docs, that explains the model, inspects the repo's real controller state, and gives precise next-step guidance without introducing a second authority surface or a web dashboard. That direction is the safest highest-leverage choice because it solves the actual adoption problem while staying faithful to the implemented CLI/tmux architecture and Phase 1 guardrails.

## The Problem

MACS is conceptually strong but cognitively front-loaded. New adopters encounter multiple valid entry points: `start-worker.sh`, `start-controller.sh`, `macs setup init`, `macs setup check`, `macs setup dry-run`, `macs worker discover`, `macs worker register`, and `macs setup validate`. The system does expose the conservative order and readiness facts, but those pieces are distributed across docs and command outputs rather than presented as one coherent guided journey.

That distribution creates four kinds of friction:

- operators must assemble the mental model of controller-owned truth, workers, tasks, leases, locks, and recovery from several docs
- they must translate static guidance into the next safe action for the current repo state
- they can see outcomes like `PARTIAL`, but still need to decide whether the blocker is missing bootstrap, missing runtime binaries, missing worker registration, or missing ready-state evidence
- they can start MACS, but still fail to feel confident that the system is configured correctly enough to run real work

The current cost is not lack of features. It is avoidable inference. That inference slows adoption, increases setup abandonment, and makes the product feel more bespoke than the implemented control plane actually is.

## The Solution

Build **MACS Guided Onboarding** as a thin terminal-guided setup assistant layered on the existing `macs setup` and inspection surfaces.

The experience should begin from controller-owned facts, not tutorial fiction. The operator runs a guided onboarding command in the terminal and sees:

- a short explanation of what MACS is governing and why controller truth matters
- the current repo state: bootstrapped or not, configured or not, workers discovered or not, ready or not
- the conservative next step based on actual conditions
- explanation of why that step matters
- interpretation of important outcomes such as `BLOCKED`, `PARTIAL`, `PASS`, missing runtime availability, and no ready workers
- direct pointers to the relevant canonical docs when deeper explanation is needed

The guide should feel like an operator-oriented control-room assistant, not a chat wizard. It should clarify and sequence the real product, not invent a second hidden workflow. Docs remain canonical. The onboarding assistant becomes the contextual layer that helps the operator move through them safely.

## What Makes This Different

This initiative is deliberately not a generic setup wizard and not a lightweight dashboard for its own sake.

Its differentiators are:

- **Controller-truth-first guidance:** every recommendation comes from the same repo-local state and setup read models MACS already treats as authoritative.
- **Safe interpretation, not hidden automation:** the product explains what to do next without auto-installing runtimes, auto-registering workers, or mutating controller state behind the operator's back.
- **CLI/tmux-native delivery:** it fits the actual MACS operator environment instead of forcing a second UI surface that current artifacts do not require.
- **Built on implemented seams:** the initiative extends `tools/orchestration/setup.py`, `tools/orchestration/cli/main.py`, and current docs instead of bypassing them.
- **Future-proof path:** if MACS eventually needs a richer local console, the guided onboarding model can feed it later from the same controller-owned read models.

## Who This Serves

**Primary users:** technical adopters and maintainers bringing MACS into a real repository. They are comfortable in the shell, but they want the shortest path from "I cloned this" to "I know exactly what the system is doing and what I should run next."

**Secondary users:** existing MACS maintainers and contributors validating new repo-local setups, reproducing onboarding issues, or checking why a repo is still not ready after bootstrap.

**Tertiary users:** future contributors extending onboarding and docs. They need a single, authoritative onboarding model that stays aligned with controller-owned behavior rather than duplicating logic in docs, examples, and new UI surfaces.

The "aha" moment is when an operator sees the current repo state, understands why it is or is not safe-ready, and can move forward with confidence from one exact next command rather than cross-referencing several files and guessing.

## Success Criteria

This initiative succeeds when:

- a first-time adopter can move from bootstrap to a correctly interpreted readiness result without undocumented glue or reverse-engineering
- operators can reliably tell the difference between bootstrap completion, configuration visibility, worker registration, and safe-ready-state
- the guided experience reduces context-switching between CLI output and multiple docs during first-run setup
- onboarding guidance remains fully aligned with current command behavior and controller-owned state
- setup-related regressions are still covered through the existing setup-family test surfaces, not an ungoverned parallel workflow
- MACS can later reuse the same onboarding read model for overview or lightweight console work without rewriting the guidance logic

## Scope

### In Scope for the First Version

- A new controller-owned guided onboarding command or mode on the existing `macs setup` surface
- Narrative explanation of the MACS control model, focused on what new operators need to understand to operate safely
- Current-state interpretation driven by existing setup snapshot, dry-run, validation, and inspection data
- Exact next-step recommendations based on real repo conditions
- Better explanation of `BLOCKED`, `PARTIAL`, `PASS`, missing runtime binaries, missing registered workers, and no-ready-worker states
- Links or references back to canonical docs for deeper context
- Documentation refresh so README and docs stay aligned with the guided flow
- Regression coverage that keeps the guide aligned with setup-family command behavior

### Explicitly Out of Scope for the First Version

- A browser-based onboarding dashboard
- A full-screen TUI requirement
- Automatic runtime installation, credential setup, or worker registration
- Hidden state mutation or shortcutting operator-confirmed actions
- A second control-plane store, alternate routing model, or duplicate readiness engine
- Broad redesign of daily operations outside onboarding and immediate setup interpretation

## Technical Approach

The safest implementation path is to extend the setup-family read model that already exists.

The initiative should:

- reuse `tools/orchestration/setup.py` as the source for bootstrap status, dry-run guidance, validation results, and readiness gaps
- add the guided onboarding surface in `tools/orchestration/cli/main.py`, keeping CLI family structure and JSON stability intact
- use existing human-readable rendering patterns so the experience remains narrow-terminal and `NO_COLOR` friendly
- point into the canonical docs for reference depth rather than duplicating long-form documentation inline
- keep all state-affecting actions explicit and operator-confirmed

The product should behave like a guided interpreter over existing controller truth. That keeps implementation disciplined and leaves open a later optional lightweight console built on the same data contract, if real usage proves one is needed.

## Vision

If this initiative succeeds, MACS onboarding stops feeling like a bundle of powerful but separate pieces and starts feeling like one coherent operating model. New adopters will learn the controller-owned mental model through use, not by reconstructing it from fragments.

In the next phase, the same guided-read-model approach can expand beyond first-run setup into adjacent help surfaces such as readiness diagnosis, recovery suggestions, and eventually a lightweight local overview console. But the durable win is earlier: make the existing MACS system legible, conservative, and confidently operable before adding a richer UI layer.
