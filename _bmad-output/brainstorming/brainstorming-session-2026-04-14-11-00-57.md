---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - "/home/codexuser/macs_dev/README.md"
  - "/home/codexuser/macs_dev/docs/index.md"
  - "/home/codexuser/macs_dev/docs/getting-started.md"
  - "/home/codexuser/macs_dev/docs/user-guide.md"
  - "/home/codexuser/macs_dev/docs/how-tos.md"
  - "/home/codexuser/macs_dev/docs/architecture.md"
  - "/home/codexuser/macs_dev/_bmad-output/planning-artifacts/ux-design-specification.md"
  - "/home/codexuser/macs_dev/_bmad-output/planning-artifacts/operator-cli-contract.md"
  - "/home/codexuser/macs_dev/_bmad-output/implementation-artifacts/stories/7-2-deliver-mixed-runtime-setup-and-validation-flow.md"
  - "/home/codexuser/macs_dev/_bmad-output/release-evidence/setup-validation-report.md"
session_topic: "MACS guided walkthrough and onboarding initiative"
session_goals: "Evaluate documentation-first walkthrough, terminal-guided setup assistant, and local controller UI/onboarding console; recommend the safest highest-leverage direction grounded in implemented MACS; preserve authoritative next-step guidance for a downstream product brief."
selected_approach: "ai-recommended"
techniques_used:
  - "First Principles Thinking"
  - "Constraint Mapping"
  - "Solution Matrix"
ideas_generated:
  - "Documentation-first guided walkthrough"
  - "Terminal-guided setup assistant"
  - "Local controller UI/onboarding console"
context_file: ""
session_active: false
workflow_completed: true
---

# Brainstorming Session Results

**Facilitator:** Dicky  
**Date:** 2026-04-14T11:00:57+01:00

## Session Overview

**Topic:** MACS needs a guided walkthrough or onboarding experience that explains how the system works, how to configure it, how to run it, what to watch for, and what the next safe step should be.

**Goals:** Compare three concrete product directions against the implemented MACS system and converge on the safest highest-leverage direction without drifting into speculative UX that contradicts current architecture.

### Context Guidance

- The implemented product is controller-first, CLI/tmux-native, and treats controller state as authoritative.
- Current onboarding already exists in several forms: `README.md`, `docs/getting-started.md`, `docs/how-tos.md`, `macs setup dry-run`, `macs setup check`, and `macs setup validate`.
- Phase 1 artifacts explicitly state there is no requirement for a web UI and no requirement for a full-screen TUI.
- Current readiness evidence shows the main adopter problem is not missing bootstrap commands. It is understanding the conservative sequence, interpreting `PARTIAL` or `BLOCKED` states, and knowing the next corrective action.

## Technique Selection

**Approach:** AI-Recommended Techniques

**Recommended Techniques:**

- **First Principles Thinking:** Separate the real onboarding problem from interface preference. The core need is authoritative understanding and safe next steps from controller-owned truth.
- **Constraint Mapping:** Evaluate each option against implemented constraints: CLI/tmux-native workflow, repo-local state, no duplicate authority surface, no hidden mutation, and current setup-family command contracts.
- **Solution Matrix:** Score the three options on leverage, safety, implementation fit, operator adoption, and future extensibility.

**AI Rationale:** This initiative is not asking for open-ended ideation. It needs disciplined convergence around implemented seams and Phase 1 constraints, so structured evaluation is the right fit.

## Idea Exploration

### First Principles Framing

The onboarding problem is not primarily "we need prettier setup." The implemented repo already contains setup commands, validation, and docs. The deeper problem is that the operator must mentally stitch together:

- what MACS is doing conceptually
- which command to run next
- how to interpret controller-owned results
- when a repo is merely bootstrapped versus truly safe-ready
- which gaps are environmental versus orchestration-state gaps

Any solution that does not reduce that mental stitching cost is only partial onboarding.

### Constraint Map

**Implemented constraints that matter:**

- Onboarding should extend the existing `macs setup` family before inventing a second operator surface.
- Output must remain compatible with terminal, tmux, SSH, and script-first use.
- The controller remains authoritative; any onboarding surface must read controller truth rather than create a shadow state model.
- Dangerous or state-mutating actions must remain explicit and confirmed.
- Existing docs remain canonical descriptions of implemented behavior.

### Option 1

**[Category #1]**: Documentation-First Guided Walkthrough  
_Concept_: Rework the docs into a clearer onboarding path with a step-by-step narrative, stronger explanation of controller concepts, more explicit "what good looks like" guidance, and decision support for `BLOCKED`, `PARTIAL`, and `PASS` states.  
_Novelty_: Treat docs less like reference pages and more like an operator walkthrough layered over the existing setup-family commands.

**Strengths**

- Lowest implementation risk.
- Keeps authority aligned with existing docs and CLI.
- Can clarify the real migration boundary and safe-ready-state logic immediately.

**Weaknesses**

- Static and not repo-aware.
- Still forces operators to translate docs into current next actions.
- Does not fully solve the "what should I do right now in this repo?" problem.

### Option 2

**[Category #2]**: Terminal-Guided Setup Assistant  
_Concept_: Add a controller-owned onboarding command, likely in the `macs setup` family, that explains the model, reads current repo-local facts, walks the operator through the conservative sequence, interprets current readiness state, and recommends the next exact command without auto-installing or silently mutating state.  
_Novelty_: Combines documentation intent with live controller-state guidance, using the already-implemented setup read model instead of a second control plane.

**Strengths**

- Highest leverage against the actual problem: contextual next-step guidance.
- Reuses existing setup commands, JSON envelopes, config snapshots, and rendering primitives.
- Aligns with current UX direction: CLI/tmux-native, operator-dense, controller-first.
- Can point back to canonical docs instead of replacing them.

**Weaknesses**

- Requires careful boundary-setting so it does not become a magical wizard.
- Needs disciplined copywriting to stay precise rather than chatty.
- Must avoid creating a second set of onboarding rules separate from docs and tests.

### Option 3

**[Category #3]**: Local Controller UI / Onboarding Console  
_Concept_: Build a lightweight local UI, likely browser-based or TUI-like, that visualizes onboarding progress, readiness state, and next steps through a richer console experience.  
_Novelty_: Introduces a new visual operator surface dedicated to onboarding and perhaps later overview or monitoring.

**Strengths**

- Highest glanceability potential.
- Could eventually unify setup, overview, and recovery flows visually.
- Might help later if MACS grows beyond highly shell-native adopters.

**Weaknesses**

- Weakest alignment with current Phase 1 assumptions and explicit non-goals.
- Highest chance of duplicating operator surfaces and creating drift from CLI truth.
- More engineering and maintenance burden than the current onboarding problem justifies.
- Risks solving "presentation" before solving authoritative guidance and interpretation.

## Solution Matrix

| Option | Safety / Architecture Fit | Leverage Against Current Problem | Implementation Risk | Smart Next-Step Guidance | Recommendation |
| --- | --- | --- | --- | --- | --- |
| Documentation-first walkthrough | High | Medium | Low | Low | Keep as supporting layer, not primary bet |
| Terminal-guided setup assistant | High | High | Medium | High | Choose now |
| Local controller UI / onboarding console | Low-Medium | Medium | High | High | Defer until CLI guidance proves insufficient |

## Convergence

### What the evidence says

- `macs setup dry-run` already contains the conservative step order operators need.
- `macs setup validate` already contains the readiness facts operators need.
- `README.md`, `docs/getting-started.md`, and `docs/how-tos.md` already contain most of the narrative pieces, but they are static.
- The UX spec and operator contract both explicitly prefer CLI/tmux guidance over a new web surface at this stage.
- Story 7.2 explicitly says onboarding improvements should extend the setup-family CLI rather than invent a second onboarding surface.

### Recommendation

Choose **Option 2: Terminal-Guided Setup Assistant**, delivered as a thin controller-owned onboarding layer over the existing setup read model and backed by a documentation refresh.

This is the safest highest-leverage direction because it:

- solves the contextual next-step problem the current docs cannot solve alone
- stays inside the authoritative CLI/tmux surface MACS already ships
- reuses implemented seams in `tools/orchestration/setup.py` and `tools/orchestration/cli/main.py`
- preserves a clean path to a future lightweight console if the CLI guide later proves insufficient

### Scope Guardrails

- Documentation improvements are part of the chosen direction, but not the whole product.
- The first version should not be a browser UI.
- The first version should not auto-install runtimes, auto-register workers, or hide controller-owned commands.
- The first version should explain and sequence existing truths, then add a small amount of guided interpretation where the operator currently has to infer too much.

## Action Planning

### Top Priority Direction

**Terminal-guided setup assistant backed by refreshed canonical docs**

**Immediate next steps:**

1. Define the onboarding command surface and narrative scope on the existing `macs setup` family.
2. Reuse the current setup snapshot, dry-run, and validation read models as the source for guidance.
3. Add guidance output for "what MACS is," "where the operator is now," "why the current state matters," and "what exact command should come next."
4. Refresh docs so the guide and written walkthrough share one authoritative model.
5. Defer any local UI or console until the CLI guidance layer has proven where richer visualization is actually needed.

### Rejected / Deferred Directions

- **Docs-only as the primary bet:** too static to deliver contextual next-step help.
- **Local UI as the primary bet:** too early, too risky, and too likely to drift from controller-owned truth.

## Session Summary and Insights

**Key Achievements**

- Reduced the problem from "pick an interface" to "reduce onboarding inference while preserving controller authority."
- Grounded the comparison in implemented commands, release evidence, and frozen Phase 1 constraints.
- Identified a concrete product direction that advances onboarding without reopening architecture debates already settled in current artifacts.

**Breakthrough Insight**

MACS does not need a new authority surface for onboarding. It needs a more guided explanation layer on top of the authority surface it already has.

**Completion**

This brainstorming session converged on a clear recommendation: pursue a controller-owned terminal-guided onboarding assistant, backed by documentation improvements, and defer any local UI until the CLI-guided experience proves its limits.
