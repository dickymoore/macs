---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
inputDocuments:
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/product-brief-macs-guided-onboarding.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/product-brief-macs-guided-onboarding-distillate.md
  - /home/codexuser/macs_dev/_bmad-output/brainstorming/brainstorming-session-2026-04-14-11-00-57.md
  - /home/codexuser/macs_dev/_bmad-output/project-context.md
  - /home/codexuser/macs_dev/docs/getting-started.md
  - /home/codexuser/macs_dev/docs/user-guide.md
  - /home/codexuser/macs_dev/docs/how-tos.md
  - /home/codexuser/macs_dev/docs/architecture.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/operator-cli-contract.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/ux-design-specification.md
  - /home/codexuser/macs_dev/_bmad-output/implementation-artifacts/stories/7-2-deliver-mixed-runtime-setup-and-validation-flow.md
  - /home/codexuser/macs_dev/_bmad-output/release-evidence/setup-validation-report.md
workflowType: 'prd'
documentCounts:
  briefs: 2
  research: 0
  brainstorming: 1
  projectDocs: 9
classification:
  projectType: cli_tool
  domain: general
  complexity: medium
  projectContext: brownfield
status: complete
---

# Product Requirements Document - MACS Guided Onboarding

**Author:** Dicky  
**Date:** 2026-04-14T11:14:14+01:00

## Executive Summary

MACS already exposes the core mechanics needed for onboarding: a controller-first CLI, repo-local setup commands, readiness validation, dry-run guidance, canonical docs, and evidence reports. The current gap is not missing capability. It is missing guided interpretation. New adopters can bootstrap a repo, but they still have to infer too much about what MACS is governing, which command should come next, how to interpret `BLOCKED` or `PARTIAL`, and when a repository is actually safe-ready rather than merely initialized.

The guided onboarding initiative adds a terminal-guided setup assistant on top of the existing `macs setup` surface and current documentation. It must explain the controller-owned model, inspect the repo's real state, classify readiness clearly, recommend the next safe action, and route the operator to the right canonical docs when deeper explanation is needed. It must do that without creating a second authority surface, without hidden mutation, and without bypassing the existing setup/readiness/sequencing model already implemented in MACS.

### What Makes This Special

This initiative is not a generic setup wizard and not a dashboard project in disguise. Its differentiator is controller-truth-first guidance: onboarding recommendations come from the same repo-local setup read model and command contracts that MACS already treats as authoritative.

The core insight is that MACS does not need a new onboarding subsystem. It needs a better explanation layer over existing setup truths. Operators should choose this experience because it reduces onboarding inference without compromising the product's core governance promise: controller-owned state, explicit operator action, skeptical treatment of runtime signals, and CLI/tmux-native operation.

## Project Classification

- **Project Type:** CLI tool initiative within a broader developer tooling product
- **Domain:** General software tooling focused on local orchestration onboarding and operator guidance
- **Complexity:** Medium, driven by brownfield constraints, controller-authority boundaries, and the need to stay aligned with implemented setup/readiness semantics
- **Project Context:** Brownfield initiative layered over an existing MACS control-plane implementation and documentation set

## Success Criteria

### User Success

The initiative succeeds for primary users when a technically capable operator can start from the current repo state, understand what MACS is governing, and reach the correct next action without reverse-engineering docs or raw command outputs.

User success means operators can:

- understand whether the repo is uninitialized, partially configured, or safe-ready
- distinguish bootstrap, config visibility, worker registration, runtime availability, and ready-state evidence
- follow a conservative onboarding path without guessing which command comes next
- understand why a result is `BLOCKED`, `PARTIAL`, or `PASS`
- find deeper documentation only when they need depth, not because the baseline path is unclear

The "aha" moment is when the operator sees current repo state and immediately understands both what is true now and what to do next.

### Business Success

This is an open-source product initiative, so business success is measured through adoption quality, operator confidence, and planning coherence rather than direct revenue.

At 3 months, success means:

- maintainers can use the guided onboarding path in this repo without bespoke explanation outside the product surface
- the onboarding artifact set clearly explains the initiative and its scope inside the current MACS system
- contributor and adopter conversations can point to one canonical onboarding model instead of stitching together multiple partial explanations

At 6-12 months, success means:

- at least one additional brownfield repo can adopt the same onboarding path with minimal repo-specific explanation
- onboarding work remains aligned with CLI behavior and does not fork into a second product model
- future onboarding enhancements can trace cleanly from PRD to UX, architecture, and stories without reopening the product direction

### Technical Success

The initiative succeeds technically when:

- guided onboarding is layered over existing setup-state and validation logic rather than recreating them
- controller truth remains the only authority for onboarding state and readiness interpretation
- onboarding does not silently install runtimes, register workers, or mutate state beyond explicit operator-confirmed actions
- guidance stays compatible with human-readable and machine-readable command surfaces
- guidance remains valid in narrow terminals, `NO_COLOR` mode, and tmux-native workflows
- onboarding behavior is regression-testable through existing setup-family seams and documentation parity checks

### Measurable Outcomes

- A first-time operator can move from repo bootstrap to a correctly interpreted readiness result using the guided flow and current docs alone.
- The guided experience covers the full conservative onboarding order already exposed by `setup dry-run`: bootstrap, config inspection, worker discovery, worker registration, readiness validation, intervention, and recovery.
- The system can explain every reported readiness gap in terms of controller facts, runtime availability hints, or worker readiness, instead of leaving the operator to infer those distinctions.
- The initiative preserves brownfield compatibility: bridge-era workflows remain understandable, and controller-owned flows remain canonical.

## Product Scope

### MVP - Minimum Viable Product

The MVP is a problem-solving and experience MVP. It must make the existing MACS onboarding model legible and actionable without broadening product scope.

MVP includes:

- a guided onboarding command or mode under the existing `macs setup` family
- orientation copy that explains controller truth, repo-local state, and safe-ready-state
- state-aware next-step recommendations based on current repo conditions
- clear interpretation of `BLOCKED`, `PARTIAL`, and `PASS`
- explanations of common onboarding gaps such as missing runtime binaries, no registered workers, and no ready workers
- explicit links or references to canonical docs for deeper context
- documentation refresh so the guided path and docs remain one model

### Growth Features (Post-MVP)

- resume-oriented onboarding checkpoints for longer setup flows
- richer guided diagnosis for degraded adapter/readiness scenarios
- onboarding summaries that roll into `overview` or related inspection surfaces
- improved contributor guidance for keeping onboarding copy aligned with contract changes

### Vision (Future)

- a shared guidance model reused across onboarding, readiness diagnosis, and recovery suggestions
- a possible lightweight local overview console only if the CLI-guided model proves insufficient
- reusable onboarding patterns for multiple repo profiles without relaxing controller-authority constraints

## User Journeys

### Journey 1: New Adopter Reaches Safe-Ready-State

Nina clones MACS into a brownfield repo because she wants governed multi-agent work without building her own terminal rituals. She can follow the README, but she still feels uncertain about the real order of operations and what "ready" actually means.

She launches guided onboarding from the `setup` surface. The product explains the controller-owned model in plain operational terms, shows her current repo state, and tells her what step comes next. When she reaches validation, the guide makes it clear why runtime binaries on `PATH` are not enough and why ready workers still matter. Instead of reading several docs in parallel, Nina uses one guided path and only opens deeper docs when she wants detail.

The climax is not a splashy wizard completion. It is the moment she sees a readiness result, understands it, and knows exactly how to move forward. Her new reality is a repo that feels governable rather than mysterious.

### Journey 2: Existing Single-Worker Operator Hits a Partial State

Sam already knows the older bridge-era habits. He can start a worker and controller, but his mental model still mixes legacy flow with current control-plane commands. He runs validation and gets `PARTIAL`.

Instead of treating `PARTIAL` as a dead end, guided onboarding explains the migration boundary: what still works unchanged, what is now superseded, and why the repo is not safe-ready yet. Sam can see whether the issue is missing workers, missing runtime binaries, or incomplete readiness. He can move from uncertainty to a concrete next command without digging through history or guessing at hidden prerequisites.

The recovery moment is emotional as much as functional: frustration drops because the system explains the state transition clearly rather than only reporting it.

### Journey 3: Maintainer Diagnoses Another Operator's Onboarding Failure

Priya maintains MACS and gets a report that onboarding "doesn't work." What she actually needs is not generic setup prose but a way to identify which factual layer is failing: bootstrap, config visibility, adapter runtime availability, worker registration, or readiness.

She uses the guided onboarding surface and supporting docs to reproduce the reported state. The guide points back to controller facts and references the exact command family and doc sections that matter. Priya can tell whether the issue is a product bug, a docs mismatch, or an environment gap.

The value moment comes when support and product surfaces stop drifting. The onboarding experience becomes a shared operational language for both adopters and maintainers.

### Journey 4: Contributor Updates Onboarding Without Breaking Canonical Behavior

Alex wants to improve onboarding copy and flow, but the repo already has README guidance, `setup dry-run`, `setup validate`, and contract-level CLI assumptions. A cosmetic rewrite that invents a second model would create damage.

The PRD-driven onboarding system makes the constraints explicit: the guide must reuse setup read models, preserve controller truth, and stay aligned with current command grammar. Alex can extend the onboarding surface by improving explanation and sequencing rather than by adding hidden behavior.

The payoff is maintainability. Contributor work can improve onboarding without destabilizing the broader operator surface.

### Journey 5: Automation-Oriented Operator Needs Structured Readiness Signals

Dana wants to embed onboarding checks into a scripted local validation flow. She does not want a chatty wizard; she wants stable guidance and state interpretation that can be consumed by humans and automation.

The system provides equivalent structured output where relevant, preserves stable command envelopes, and keeps human-readable guidance aligned with controller facts. Dana can use machine-readable results for automation while still relying on canonical human-readable explanations for issue investigation.

### Journey Requirements Summary

These journeys require the product to provide:

- orientation to the controller-owned model
- state-aware onboarding progression
- readiness interpretation and remediation guidance
- brownfield migration guidance
- maintainable alignment between guide, docs, and CLI contracts
- structured output compatibility for operators who automate local checks

## Domain-Specific Requirements

### Compliance & Regulatory

This initiative is not regulated in the external sense, but it operates under internal governance constraints that function like product law for MACS:

- controller-owned truth must remain authoritative
- operator-confirmed actions must remain explicit
- readiness claims must distinguish controller facts from runtime availability hints and worker evidence
- onboarding must not widen audit/governance posture by introducing hidden side effects or shadow state

### Technical Constraints

- The onboarding experience must remain local-host-first and repo-local.
- The initiative must reuse the existing `setup` read model rather than create a second readiness engine.
- Guidance must remain compatible with current command family structure and CLI contracts.
- The product must continue to work in shell, tmux, SSH, narrow-terminal, and `NO_COLOR` contexts.
- Backward-compatible bridge-era workflows remain part of the brownfield environment and must be explained accurately.

### Integration Requirements

- Guided onboarding must integrate with current `macs setup` commands and their outputs.
- It must link cleanly to README and docs surfaces already used by operators.
- It must remain consistent with current project context, UX direction, CLI contract, and release-evidence framing.
- It must not require a browser UI, full-screen TUI, hosted service, or external runtime installation mechanism.

### Risk Mitigations

- **Wizard drift risk:** Mitigate by reusing the existing setup read model and command grammar.
- **Docs drift risk:** Mitigate by treating docs as canonical and using the guide as a contextual layer rather than a replacement.
- **False-readiness risk:** Mitigate by preserving the distinction between runtime availability, registration, and ready-state evidence.
- **Brownfield breakage risk:** Mitigate by keeping compatibility boundaries explicit and avoiding hidden automation.

## Innovation & Novel Patterns

### Detected Innovation Areas

The initiative contains one genuine innovation pattern: onboarding as a state-aware interpreter over controller-owned truth rather than as static documentation or a separate wizard subsystem. That is novel in the MACS context because it turns existing setup/readiness surfaces into an explicit operator guidance model without creating a second authority surface.

### Market Context & Competitive Landscape

Most CLI onboarding experiences fall into one of two weak patterns:

- static docs that describe a path but cannot interpret the user's current state
- opaque wizards that mutate state quickly but hide why a result occurred

MACS should take a third path: explain the current state, preserve explicit operator action, and keep the guidance tied to the actual control plane.

### Validation Approach

- dogfood the flow in the MACS repo against known `BLOCKED`, `PARTIAL`, and `PASS` states
- validate against current setup-family command behavior and docs
- confirm the guide still makes correct recommendations when runtime availability and worker readiness change
- treat supportability as a validation target: maintainers should be able to use the same flow for reproduction and diagnosis

### Risk Mitigation

- if the guided experience becomes too chatty or magical, reduce it back toward command-led explanation
- if guidance diverges from CLI behavior, the CLI behavior wins and the guide must be corrected
- if richer interface needs emerge later, build them on the same read model rather than replacing the CLI-guided layer

## CLI Tool Specific Requirements

### Project-Type Overview

This initiative extends a CLI-first operational product. That means the onboarding surface is not auxiliary documentation; it is part of the operator interface. The initiative must preserve command predictability, output discipline, and script-friendly behavior while still improving learnability.

### Technical Architecture Considerations

- The onboarding command must live under the existing `macs setup` family.
- The exact subcommand name may be finalized later, but it must preserve current command grammar and brownfield expectations.
- Onboarding must behave as a thin interpretive layer over existing setup-state data and documentation references.

### Command Structure

- The onboarding surface must present a conservative sequence that aligns with current setup-family commands.
- The flow must use current canonical nouns and not invent alternative object vocabulary.
- The guide must make clear which steps are read-only and which steps can change controller state.

### Output Formats

- Human-readable output must remain the default.
- Structured output must remain available where it adds concrete value for automation, testing, or evidence capture.
- Warnings, degraded states, and safe-next-action hints must remain readable without color or wide layouts.

### Configuration & State Model

- The guide must operate against current repo-local state paths and configuration domains.
- It must explain controller defaults, adapter settings, routing policy, governance policy, and state layout only to the degree needed for onboarding success.
- It must not introduce a separate onboarding configuration regime.

### Scripting Support

- The guided onboarding flow must coexist with scripted use of setup-family commands.
- Stable envelopes and consistent recommendations matter because some operators will consume readiness and guidance in automated local workflows.
- The initiative must not require interactive-only behavior for core readiness interpretation.

### Implementation Considerations

- Preserve current brownfield compatibility notes and migration boundary guidance.
- Avoid UI-specific commitments that would force a later web or TUI implementation.
- Keep the surface dense, operational, and operator-trustworthy rather than tutorial-like.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-solving and experience MVP.  
The MVP proves that MACS can explain its existing onboarding model in a way that reduces inference and increases operator confidence without broadening product scope.

**Resource Requirements:** A focused cross-functional planning-and-delivery slice is sufficient:

- product/requirements ownership to keep scope narrow
- UX/design ownership for terminal-first copy and flow clarity
- architecture ownership to keep reuse and authority boundaries explicit
- implementation and test capacity for setup-family extensions and docs alignment

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**

- new adopter reaches correct next action from current repo state
- existing operator interprets `PARTIAL` or `BLOCKED` correctly
- maintainer/support user can reproduce and diagnose onboarding state through the same surface

**Must-Have Capabilities:**

- guided onboarding entry on `macs setup`
- controller-truth-first orientation
- state-aware next-step recommendation
- readiness state interpretation and remediation guidance
- canonical doc linkage
- terminal accessibility and structured-output compatibility
- regression-aligned maintainability

### Post-MVP Features

**Phase 2 (Post-MVP):**

- richer resume/checkpoint behavior for longer onboarding sessions
- better degraded-state explanation for adapter-specific gaps
- tighter integration between onboarding guidance and overview/inspection flows
- contributor-facing maintenance guidance for onboarding copy and contract alignment

**Phase 3 (Expansion):**

- shared explanation model across onboarding, readiness diagnosis, and recovery suggestions
- optional lightweight overview console only if CLI evidence shows clear need
- reusable onboarding profiles for multiple repo archetypes while preserving controller-owned semantics

### Risk Mitigation Strategy

**Technical Risks:**  
The main technical risk is drift between guided onboarding and implemented CLI behavior. Mitigation: reuse existing setup read models, preserve stable command grammar, and test the guide through current setup-family seams.

**Market Risks:**  
The main product risk is overbuilding UI around a problem that is mostly interpretive. Mitigation: keep MVP focused on explanation, next-step guidance, and docs alignment rather than richer interface ambitions.

**Resource Risks:**  
The main resource risk is letting the initiative expand into general CLI redesign or broader control-room work. Mitigation: keep the scope tied to onboarding flows, readiness interpretation, and brownfield guidance only.

## Functional Requirements

### Guided Onboarding Entry & Orientation

- FR1: Operators can launch guided onboarding from the existing `macs setup` surface.
- FR2: Operators can receive a concise explanation of the controller-owned MACS model before or during onboarding.
- FR3: Operators can see the current repo onboarding state at the start of the guided flow.
- FR4: Operators can understand whether the current step is read-only guidance or a state-changing command.

### State-Aware Guidance

- FR5: The system can inspect repo-local bootstrap, configuration, runtime availability, worker registration, and worker readiness using current controller-owned sources.
- FR6: The system can classify onboarding state as blocked, partial, pass, or equivalent controller-recognized readiness states.
- FR7: The system can recommend the next safe operator action based on the current repo state.
- FR8: The system can explain why a recommended next action matters and what condition it is intended to resolve.
- FR9: Operators can distinguish auto-detected facts from actions that require explicit operator execution or confirmation.

### Setup Progression & Readiness Interpretation

- FR10: Operators can follow the conservative onboarding order already established by MACS setup guidance.
- FR11: Operators can understand why runtime availability alone does not establish safe-ready-state.
- FR12: Operators can review readiness gaps by adapter, runtime availability, worker registration, and ready-state evidence.
- FR13: Operators can understand the boundary between bridge-era workflows and controller-owned setup workflows.
- FR14: Operators can tell whether a repo is initialized, configured, partially ready, or safe-ready without inspecting raw state files directly.

### Diagnosis & Remediation Guidance

- FR15: Operators can inspect the specific reasons behind a blocked or partial onboarding result.
- FR16: The system can recommend targeted remediation paths for common onboarding failure modes.
- FR17: Operators can access intervention and recovery guidance relevant to onboarding-related readiness problems.
- FR18: Operators can inspect or reference the underlying controller evidence that supports a guidance recommendation.

### Documentation & Learn-More Support

- FR19: Operators can move from guided output to the relevant canonical documentation for deeper explanation.
- FR20: The system can present current, canonical example commands for the onboarding step being discussed.
- FR21: Maintainers can keep onboarding guidance aligned with README and docs without creating a second authoritative product model.

### Output Modes & Accessibility

- FR22: Operators can use guided onboarding successfully in narrow terminals and no-color terminal environments.
- FR23: Operators can interpret warnings, degraded states, and next-step guidance without relying on color alone.
- FR24: Operators can request machine-readable onboarding and readiness signals through stable structured output modes where automation or evidence capture is needed.

### Governance & Safety Boundaries

- FR25: Guided onboarding can provide direction without auto-installing runtimes or auto-registering workers.
- FR26: Guided onboarding can preserve operator-confirmed behavior for any state-changing actions it references.
- FR27: Guided onboarding can preserve controller authority and avoid introducing shadow state, hidden side effects, or alternate readiness engines.

### Maintainability & Validation Support

- FR28: Maintainers can regression-test onboarding behavior through existing setup-family test and documentation surfaces.
- FR29: Contributors can update onboarding flow and copy without changing canonical command grammar unless the underlying contract changes.
- FR30: Planning, UX, and architecture work for guided onboarding can trace back to this PRD without redefining the broader MACS product scope.

## Non-Functional Requirements

### Performance

- NFR1: Read-only guided onboarding state inspection shall complete within 2 seconds for a typical local repo with initialized controller state and no live worker mutations in progress.
- NFR2: Full readiness interpretation that reuses existing setup validation data shall complete within 5 seconds for the current repo-local adapter set under normal local conditions.

### Reliability & Safety

- NFR3: Guided onboarding shall never report a readiness state higher than the result supported by the underlying controller-owned setup and validation surfaces for the same repo state.
- NFR4: Any guided path that references a state-changing action shall preserve existing explicit confirmation requirements and safe-state transitions defined by the MACS control plane.
- NFR5: When guidance depends on incomplete, stale, degraded, or unavailable evidence, the affected output shall label that uncertainty explicitly before recommending the next action.

### Accessibility & Terminal Compatibility

- NFR6: Human-readable onboarding output must remain usable at 80 columns and in half-width tmux panes.
- NFR7: No-color mode shall retain full semantic clarity through textual state labels, warning labels, and structural formatting alone.
- NFR8: Onboarding output pasted into plain-text issues, docs, or chat shall remain understandable without terminal styling or hidden context.

### Consistency & Traceability

- NFR9: Guided onboarding terminology shall match canonical MACS object and command vocabulary across CLI output, docs, UX artifacts, and stories.
- NFR10: All onboarding examples and recommended commands shall match the documented canonical command forms in the maintained docs set at release time.
- NFR11: Changes to onboarding behavior shall be traceable through planning artifacts, docs updates, and regression coverage rather than through copy-only changes.

### Maintainability & Testability

- NFR12: Automated regression coverage shall exercise at least blocked, partial, and pass onboarding/readiness scenarios through the existing setup-family test seams.
- NFR13: The onboarding design shall reuse current setup/readiness read models and documentation sources wherever practical so that readiness logic is defined in one place.

## Final Notes

This PRD defines a bounded onboarding initiative inside MACS, not a replacement for the broader MACS PRD. Downstream UX, architecture, epics, and sprint planning must preserve that boundary: extend the current setup and documentation surfaces, reduce onboarding inference, and do not reopen settled control-plane or surface-model assumptions unless new evidence requires it.
