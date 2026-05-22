---
title: "Product Brief Distillate: MACS Guided Onboarding"
type: llm-distillate
source: "product-brief-macs-guided-onboarding.md"
created: "2026-04-14T11:00:57+01:00"
purpose: "Token-efficient context for downstream PRD creation"
---

# Product Brief Distillate: MACS Guided Onboarding

## Chosen Direction

- Chosen product direction: terminal-guided onboarding assistant on the existing `macs setup` family, backed by refreshed canonical docs.
- Working framing: a guided interpreter over controller-owned setup truth, not a new authority surface.
- Core user need: explain how MACS works, where the repo currently stands, what to look for, and what exact command should come next.
- Why this won: it solves contextual next-step guidance while matching the implemented CLI/tmux-native Phase 1 model.

## Option Triage

- Rejected as primary direction: documentation-first walkthrough.
- Reason rejected: safest and useful, but too static to answer "what should I do next in this repo right now?"
- Deferred direction: local controller UI / onboarding console.
- Reason deferred: current artifacts explicitly do not require a web UI or full-screen TUI; too much risk of duplicate operator surfaces and drift from controller truth.
- Keep from rejected options:
  - docs refresh is still part of the chosen direction
  - future lightweight console can be revisited later, but only on top of the same controller-owned read model

## Implemented-System Evidence

- Current onboarding building blocks already exist:
  - `README.md`
  - `docs/getting-started.md`
  - `docs/how-tos.md`
  - `macs setup check`
  - `macs setup dry-run`
  - `macs setup validate`
- Current code seam for reuse:
  - `tools/orchestration/setup.py` already builds setup snapshot, dry-run guidance, and readiness validation
  - `tools/orchestration/cli/main.py` already owns `setup` command routing and output envelopes
  - `tools/orchestration/cli/rendering.py` already supports narrow-terminal human-readable output
- Current UX/planning constraint:
  - controller-first, CLI/tmux-native surface is intentional
  - no requirement for a web UI in Phase 1
  - no requirement for a full-screen TUI
  - onboarding improvements should extend the setup-family CLI before inventing a second surface

## Problem Signals to Preserve

- Adopters must currently infer too much across multiple docs and command outputs.
- Main confusion is not "how do I bootstrap at all?" but:
  - what MACS is actually governing
  - whether the repo is merely bootstrapped or actually safe-ready
  - whether a `PARTIAL` result comes from runtime availability, worker registration, or readiness state
  - what exact next command should be run
- Release evidence in this repo state shows the real gap well:
  - repo-local bootstrap is present
  - routing defaults are visible
  - no workers are registered
  - no ready workers are available
  - overall outcome remains `PARTIAL`

## Requirements Hints

- Add a guided onboarding command or mode under `macs setup`.
- The guide should explain the control model briefly:
  - controller owns truth
  - adapters provide evidence
  - safe-ready-state requires more than runtime availability
- The guide should show current repo state and classify it clearly.
- The guide should recommend one exact next action at a time.
- The guide should interpret important setup outcomes:
  - `BLOCKED`
  - `PARTIAL`
  - `PASS`
  - missing binaries on `PATH`
  - missing registered workers
  - no ready workers
- The guide should point to canonical docs for deeper detail rather than re-hosting full reference text inline.
- The guide should preserve scriptability and existing JSON contracts where practical.

## Technical Context

- Preferred implementation seam:
  - read from the existing setup read model instead of recreating state logic
  - extend setup-family CLI rather than adding a separate service or background process
- Strong constraints:
  - no auto-installation
  - no silent worker registration
  - no hidden mutations
  - no second control-plane store
  - no browser dependency for first release
  - no full-screen TUI requirement
- Delivery style should remain:
  - terminal-first
  - tmux-compatible
  - SSH-friendly
  - narrow-width readable
  - `NO_COLOR` tolerant

## Review Insights Applied

- Skeptic lens:
  - biggest risk is building a magical wizard that drifts from real CLI behavior
  - mitigation: make the guide a thin explanatory layer over existing setup outputs and test it through the current setup-family surfaces
- Opportunity lens:
  - the same guidance model can later support readiness diagnosis, recovery suggestions, or a lightweight local console
  - avoid building those now; keep first release tightly scoped to onboarding
- Contextual lens: operator adoption friction
  - the highest-value copy is not generic installation prose
  - the highest-value copy explains state transitions and next actions from actual repo conditions

## Scope Signals

- In for first release:
  - guided onboarding command or mode
  - state-aware next-step guidance
  - explanation of readiness outcomes
  - docs refresh aligned to the guide
- Out for first release:
  - web UI
  - full-screen TUI
  - automated installers
  - automated worker registration
  - broader redesign of daily operations

## Open Questions

- Best command shape:
  - `macs setup guide`
  - `macs setup walkthrough`
  - `macs setup explain`
- How interactive should first release be:
  - purely read-only narrative with recommended next commands
  - or minimally interactive with explicit operator confirmation before mutating steps
- How much onboarding content belongs inline versus in docs:
  - keep inline copy short and state-aware
  - keep deeper explanation canonical in docs

## Downstream PRD Guidance

- Treat this as an initiative within MACS, not a replacement for the broader MACS product brief.
- Preserve the parent-product posture: controller authority, evidence-backed operation, operator-confirmed actions, and repo-local CLI/tmux delivery.
- Write the PRD so the first milestone delivers guidance over existing truths, not a new onboarding subsystem.
