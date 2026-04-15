# MACS Phase 1 Sprint Plan

**Date:** 2026-04-09
**Project:** macs_dev
**Planning basis:** `prd.md`, `architecture.md`, `ux-design-specification.md`, `epics.md`, `implementation-readiness-report-2026-04-09.md`, `operator-cli-contract.md`, `release-readiness-evidence-matrix.md`, and the templates under `evidence-templates/`

## Planning Intent

This sprint plan sequences Phase 1 implementation for the current brownfield MACS repo. It deliberately front-loads controller authority, durable state, adapter normalization, and protected-surface safety before substantial controller-surface polish, adoption flows, and release qualification.

The implementation-readiness report concluded that Epic 4, Epic 7, and Epic 8 required supporting artifacts before efficient execution. Those prerequisites are now available and are treated as binding inputs:

- `operator-cli-contract.md` freezes the canonical Phase 1 command surface for Epic 4 and removes naming and output-shape drift.
- `release-readiness-evidence-matrix.md` converts soft NFRs into concrete proof obligations for Epic 7 and Epic 8.
- `evidence-templates/` provides execution-ready scaffolding for setup validation, adapter qualification, failure drills, and dogfood evidence so those stories can ship with concrete evidence outputs instead of ad hoc reporting.

## Brownfield Sequencing Principles

- Preserve current `tools/tmux_bridge/` launchers, repo-local `.codex/` state conventions, and legacy target-pane compatibility while the new control plane is introduced.
- Build controller-owned truth first: session lock, persistence, lease invariants, restart recovery, worker registration, and adapter evidence normalization.
- Introduce routing and locking before rich operator workflows so assignment and inspection are grounded in real authority semantics.
- Treat auditability, intervention, and recovery as core behavior, not post-MVP polish.
- Start Epic 4 only after the frozen CLI contract is accepted as the implementation baseline.
- Start Epic 7 and Epic 8 only when the new evidence matrix and evidence templates are used as the deliverable contract.

## Recommended Sprint Sequence

### Sprint 1: Control-plane bootstrap and authority foundation

**Primary goal:** make the controller authoritative and restart-safe in the existing repo shape.

Stories:

- `1.1` Start a single-controller orchestration session
- `1.2` Persist authoritative control-plane entities
- `1.3` Enforce task and lease state invariants
- `1.4` Restore controller state safely on restart

Brownfield focus:

- reuse current repo-local `.codex/` conventions
- preserve current `start-controller` and tmux detection flows
- keep the initial persistence layer compatible with existing single-worker assumptions where feasible

Exit criteria:

- `.codex/orchestration/` layout exists
- single-controller lock is enforced
- `state.db` and `events.ndjson` become authoritative
- boot sequence restores persisted state before new assignment

### Sprint 2: Worker registration and adapter contract foundation

**Primary goal:** make heterogeneous workers visible through one skeptical contract, starting with the repo's primary runtime.

Stories:

- `2.1` Register and inspect tmux-backed workers
- `2.2` Implement the shared adapter contract and evidence envelope
- `2.3` Deliver the Codex adapter as the reference worker

Brownfield focus:

- keep tmux-backed worker discovery aligned with existing bridge behavior
- expose required worker metadata without trusting adapters as authority
- dogfood Codex first because it is the current repo default runtime

Exit criteria:

- worker roster is controller-owned
- required adapter signals are normalized
- Codex worker registration is operational without weakening controller authority

### Sprint 3: Complete adapter baseline and safe routing core

**Primary goal:** finish the adapter layer and establish explainable routing.

Stories:

- `2.4` Deliver Claude and Gemini adapters as governed workers
- `2.5` Deliver the local adapter and first-class qualification checks
- `3.1` Configure workflow-aware routing policy
- `3.2` Record explainable assignment decisions

Brownfield focus:

- keep runtime-specific differences behind the adapter contract
- make workflow-class defaults repo-local and inspectable
- persist enough routing rationale to support later Epic 4 inspection work

Exit criteria:

- supported runtimes can be represented through one contract
- first-class qualification path exists
- routing policy and rationale are durable and inspectable

### Sprint 4: Protected surfaces, conflict prevention, and early recovery/audit hooks

**Primary goal:** make assignment safe before building richer operator flows.

Stories:

- `3.3` Reserve protected surfaces with coarse default locks
- `3.4` Block conflicts and duplicate ownership claims
- `5.1` Classify worker health and surface warnings promptly
- `6.1` Persist a durable event trail and history inspectors

Brownfield focus:

- use coarse file, directory, and logical-surface locks first
- preserve tmux-oriented operational workflows while moving truth into controller records
- keep history durable enough for later recovery and release evidence

Exit criteria:

- lock reservation precedes risky assignment
- split-brain and duplicate-claim cases are blocked or frozen
- degraded workers are visible quickly
- history inspection no longer depends on raw pane archaeology

### Sprint 5: Recovery engine before controller-surface expansion

**Primary goal:** make degraded and ambiguous situations safe to manage before broadening the CLI operating surface.

Stories:

- `5.2` Freeze risky work through intervention hold and lease suspension
- `5.3` Reconcile ambiguous ownership and reroute safely
- `5.4` Resume interrupted recovery from persisted recovery runs
- `6.2` Preserve intervention rationale across recovery and reassignment

Brownfield focus:

- keep risky work frozen by default when live evidence and persisted truth diverge
- persist recovery context explicitly so restart behavior remains trustworthy

Exit criteria:

- recovery runs survive restart
- reroute and reconciliation cannot create dual current owners
- intervention rationale is part of the durable audit trail

### Sprint 6: Controller-first operator surface on the frozen CLI contract

**Primary goal:** deliver the Phase 1 authority surface only after state, routing, locking, and recovery semantics are real.

Stories:

- `4.1` Provide compact list and inspect commands for control-plane objects
- `4.2` Assign and manage task lifecycle actions from one command path
- `4.3` Inspect degraded evidence and open the right worker pane from context
- `4.4` Support in-place pause controls and terminal accessibility modes

Gating inputs now required:

- `operator-cli-contract.md` is the source of truth for family names, verbs, selectors, JSON envelope, and terminology
- prior sprints must already expose authoritative records for workers, tasks, leases, locks, events, routing rationale, and degraded state

Exit criteria:

- operators can inspect and act from the controller pane without normal-flow tmux surgery
- CLI terms and JSON outputs follow the frozen contract
- degraded evidence is inspectable from the same surface as task and worker actions

### Sprint 7: Governance hardening and repository adoption

**Primary goal:** make the product configurable, governable, and adoptable in real repositories.

Stories:

- `6.3` Enforce explicit decision rights and guarded actions
- `6.4` Govern external surfaces, privacy-sensitive routing, and audit content
- `7.1` Separate controller, adapter, policy, and state configuration
- `7.2` Deliver mixed-runtime setup and validation flow
- `7.3` Preserve and document single-worker compatibility boundaries
- `7.4` Publish contributor-facing adapter guidance

Gating inputs now required:

- `release-readiness-evidence-matrix.md` defines the proof obligations for NFR7-NFR22 that adoption and governance work must satisfy
- `evidence-templates/setup-validation-template.md`
- `evidence-templates/adapter-qualification-template.md`

Exit criteria:

- config domains are clearly separated and documented
- setup and migration flows are runnable against a real repo
- single-worker compatibility claims are explicit and evidence-backed
- contributor guidance matches the actual adapter contract and qualification path

### Sprint 8: Release qualification, failure drills, and dogfooding

**Primary goal:** prove the Phase 1 release is shippable under the reference mixed-runtime operating model.

Stories:

- `8.1` Build unit and contract test coverage for controller and adapter invariants
- `8.2` Build integration and failure-drill coverage for mandatory failure classes
- `8.3` Validate the four-worker reference dogfood scenario
- `8.4` Ship a release-gate command and report for Phase 1 readiness

Gating inputs now required:

- `release-readiness-evidence-matrix.md` is the release proof contract
- `evidence-templates/failure-drill-report-template.md`
- `evidence-templates/dogfood-evidence-template.md`
- `evidence-templates/setup-validation-template.md`
- `evidence-templates/adapter-qualification-template.md`

Exit criteria:

- unit, contract, integration, failure-drill, and dogfood coverage are wired into one release gate
- first-class adapter claims are backed by qualification evidence
- release decision is traceable to human-readable and `--json` outputs

## Dependency Notes

- Epic 1 is the hard prerequisite for all later epics because it establishes controller-owned state and restart safety.
- Epic 2 Story `2.2` is the contract pivot for the rest of Epic 2 and for all mixed-runtime work in Epic 7 and Epic 8.
- Epic 3 must precede broad Epic 4 lifecycle flows so task assignment and lock inspection are authoritative rather than decorative.
- Epic 5 should land before heavy operator-surface polish because degraded-path behavior is one of the product's differentiators and highest-risk failure areas.
- Epic 6.1 and 6.2 are intentionally pulled earlier than the rest of Epic 6 because durable history and intervention rationale are needed to support recovery, inspection, and release evidence.
- Epic 4 is unblocked by the new CLI contract artifact, but it should still wait until controller entities, routing rationale, locks, and degraded-state classification exist.
- Epic 7 and Epic 8 are unblocked by the new evidence matrix and templates, but they should not move ahead of the core control-plane and adapter work that those artifacts are meant to validate.

## Parallelization Guidance

- Within Sprint 2 and Sprint 3, adapter work can proceed in parallel only after Story `2.2` freezes the shared contract and evidence envelope.
- Within Sprint 4 and Sprint 5, audit/history work can proceed alongside recovery work because the durable event model is a direct dependency for reconciliation evidence.
- Within Sprint 7, configuration separation, setup docs, and contributor guidance can overlap, but migration compatibility validation should trail actual config and CLI behavior.
- Within Sprint 8, evidence generation can be parallelized by test layer, but release gating should remain centralized so the final report reflects one authoritative decision.

## Recommended First Story Queue

Create and execute stories in this order unless implementation discoveries force a correction:

1. `1.1` Start a single-controller orchestration session
2. `1.2` Persist authoritative control-plane entities
3. `1.3` Enforce task and lease state invariants
4. `1.4` Restore controller state safely on restart
5. `2.1` Register and inspect tmux-backed workers
6. `2.2` Implement the shared adapter contract and evidence envelope

That queue keeps early work anchored in authority, persistence, and adapter normalization before the more interpretation-sensitive operator and release surfaces.
