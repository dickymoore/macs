---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/prd.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/architecture.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/ux-design-specification.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/prd-advanced-elicitation-note-2026-04-09.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/prd-validation-report.md
---

# macs_dev - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for macs_dev, decomposing the requirements from the PRD, UX Design, Architecture, and refinement notes into implementable stories for the control-plane MVP.

## Requirements Inventory

### Functional Requirements

FR1: Operators can start and manage a local-host orchestration session that supervises multiple worker windows under one controller.
FR2: Operators can create, assign, reassign, pause, resume, abort, reconcile, close, and archive tasks through the MACS orchestration surface.
FR3: The controller can maintain exactly one current owner for each active task at any given time.
FR4: The controller can create, renew, expire, revoke, and transfer leases associated with task ownership.
FR5: Operators can inspect the current lifecycle state of any task, including owner, lease, intervention state, and recent events.
FR6: The system can prevent conflicting task progression when a task enters intervention hold, reconciliation, or failure review.
FR6a: The system can represent lease states that distinguish active, paused or suspended, revoked, expired, completed, and historical records.
FR6b: The system can enforce that a task has zero or one active leases, allowing zero active leases during reconciliation or interrupted reassignment but never more than one.
FR7: Operators can discover, register, enable, disable, and inspect workers available on the local host.
FR8: The system can represent workers from Codex CLI, Claude Code, Gemini CLI, and one local/runtime-neutral adapter as first-class workers.
FR9: Operators can view worker identity, runtime type, availability, interruptibility, freshness, and capability metadata.
FR10: The system can distinguish required adapter signals from optional runtime-specific enrichment signals.
FR11: The system can mark workers as healthy, degraded, unavailable, quarantined, or otherwise not eligible for new work based on controller-evaluated evidence.
FR12: Contributors can add or update runtime adapters against a defined minimum adapter contract without changing controller authority semantics.
FR12a: The system can classify an adapter as first-class only after required contract support, degraded-mode behavior, intervention support, routing-evidence support, and validation coverage are demonstrated.
FR13: The controller can evaluate eligible workers for a task using policy, capability fit, freshness, health evidence, and current lock state.
FR14: Operators can define or apply workflow-class-aware runtime defaults for documentation/context, planning docs, solutioning, implementation, review, and privacy-sensitive/offline work.
FR15: The system can record the routing rationale and evidence associated with each assignment decision.
FR16: The system can degrade routing behavior safely when some worker signals are unavailable, stale, or untrusted.
FR17: The system can prevent task assignment to workers that do not satisfy required capabilities, trust boundaries, or governance policy.
FR18: The controller can create, inspect, update, and release protected-surface locks associated with active work.
FR19: Operators can view which protected surfaces are currently reserved, blocked, conflicted, or released.
FR20: The system can prevent unsafe concurrent work when two tasks or workers target the same protected surface.
FR21: The system can detect duplicate task claims, competing ownership assertions, and split-brain conditions.
FR22: The system can force reconciliation before conflicting ownership or lock state is allowed to continue.
FR23: The system can preserve ownership and lock history for audit and post-failure analysis.
FR23a: The system can support the MVP minimum lock model of file, directory, and policy-defined logical work-surface targets with coarse default granularity.
FR23b: The system can treat concurrent write-impacting work on the same protected surface as conflicting by default unless explicit policy permits otherwise.
FR24: The system can monitor worker liveness, session freshness, adapter health, and token or session-limit signals where available.
FR25: The system can raise visible warnings when worker evidence indicates degraded or unsafe execution conditions.
FR26: Operators can inspect degraded workers and the evidence supporting the degraded classification.
FR27: Operators can pause risky work without requiring direct tmux manipulation as the normal control path.
FR28: Operators can reroute or recover a task from controller-owned state after degradation, failure, or interruption.
FR29: The system can preserve event history and intervention rationale across recovery and reassignment flows.
FR30: The system can classify failure conditions such as worker disconnect, stale lease divergence, lock collision, misleading health evidence, and interrupted recovery.
FR31: The system can maintain an auditable event trail for assignments, lease changes, lock changes, interventions, recoveries, and task closure.
FR32: Operators can inspect task, worker, lease, lock, and event state without reconstructing orchestration state from raw terminal panes.
FR33: The system can enforce governance defaults such as skeptical adapter boundaries, bounded-permission execution, and no-auto-push / no-remote-ops style safeguards where relevant.
FR34: The system can allowlist or pin governed integration surfaces such as MCP-backed tool access where relevant to runtime operation.
FR35: The system can keep privacy-sensitive or offline-capable workflows routable to appropriate local/runtime-neutral worker options when configured.
FR35a: The system can apply a decision-rights model that distinguishes automatic controller actions, policy-automatic but operator-visible actions, operator-confirmed actions, and actions forbidden in MVP.
FR35b: The system can persist audit metadata separately from optional rich content capture and apply policy-based redaction or omission for sensitive content.
FR36: Technically capable adopters can install and configure MACS for mixed-runtime local-host orchestration in a real repository without bespoke per-repo glue code beyond documented extension points.
FR37: Operators can configure controller defaults, worker/runtime adapter settings, orchestration policy settings, safety/governance settings, and repo-local state separately.
FR38: The product can provide documented setup, onboarding, and migration guidance from current single-controller/single-worker usage to multi-worker orchestration.
FR39: The product can provide reference examples for mixed-runtime orchestration, intervention and recovery, and adapter registration/configuration.
FR39a: The product can preserve or clearly document compatibility boundaries for current single-worker usage, including whether state migration or command-surface changes are required.
FR40: Contributors can validate adapters and orchestration behavior against a regression suite before runtime support is treated as first-class.
FR41: The system can expose the minimum adapter contract, declared capabilities, degradation behavior, and validation expectations needed for contributor work.
FR42: Maintainers can run release-gated orchestration tests covering required happy-path and failure/recovery behaviors.

### NonFunctional Requirements

NFR1: Worker discovery, task inspection, ownership inspection, and lock inspection actions must return operator-visible results within 2 seconds in the reference local-host environment under a 4-worker session.
NFR2: Normal task assignment, including worker selection, lease creation, lock reservation, and event persistence, must complete within 5 seconds in the reference local-host environment when required worker evidence is available.
NFR3: Degraded-worker warnings must become visible to the operator within 10 seconds of the controller receiving sufficient evidence to classify the worker as degraded or unsafe.
NFR4: The system must preserve controller-authoritative state for `worker`, `task`, `lease`, `lock`, and `event` across normal orchestration flows, controller restarts, and recoverable worker failures.
NFR5: The release-gate suite must pass the full mandatory failure-mode matrix for worker disconnect, stale lease/session divergence, duplicate task claim, split-brain ownership, lock collision, misleading health evidence, surfaced budget/session exhaustion, and interrupted recovery before Phase 1 release.
NFR6: Recovery workflows must preserve audit history and ownership clarity such that no active task can appear to have more than one current owner after reconciliation completes.
NFR6a: Restart recovery must restore persisted controller state before new assignments, then reconcile live worker/session evidence before risky work is resumed.
NFR7: The controller must treat adapter outputs as bounded evidence rather than trusted truth and must not permit adapters to become the source of truth for ownership, routing, or recovery state.
NFR8: Product defaults must not initiate autonomous remote operations, automatic pushes, or unapproved external actions as part of normal orchestration behavior.
NFR9: Governed integration surfaces, including MCP-backed tool access where used, must support allowlisting or equivalent explicit trust controls before being enabled in a production-oriented configuration.
NFR10: Where runtimes expose approval, sandbox, or permission controls, MACS must preserve and surface those controls rather than bypassing them.
NFR11: Every assignment, lease mutation, lock mutation, intervention, recovery action, and task closure must create an audit event with enough context to reconstruct the operator-visible orchestration history.
NFR12: Event, lease, and lock history must remain inspectable after task completion or failure so maintainers can perform post-run analysis without depending on raw tmux pane history.
NFR13: Routing decisions must retain enough evidence context that maintainers can understand why a worker was selected, rejected, degraded, or quarantined.
NFR13a: MVP audit storage must default to local-host retention, capture event metadata by default, and bound or redact rich content capture according to documented local policy.
NFR14: The intended MVP control surface must support normal orchestration workflows without requiring direct raw tmux manipulation as the primary operating path.
NFR15: A technically capable adopter must be able to complete documented mixed-runtime local-host setup in a real repository using the supplied configuration and migration guidance, without undocumented repository-specific glue.
NFR16: The CLI/tmux-native operator experience must preserve clear, consistent terminology for `worker`, `task`, `lease`, `lock`, and `event` across commands, views, and documentation.
NFR17: The MVP must remain local-host-first and must not require hosted backend infrastructure to deliver the Phase 1 orchestration experience.
NFR18: The product must preserve repo-local state and targeting conventions already used by MACS, including compatibility with existing repository-local orchestration metadata patterns.
NFR19: Runtime-specific capability differences must degrade gracefully so the absence of optional signals does not break orchestration flows or silently weaken safety semantics.
NFR20: Orchestration logic must remain organized around explicit control-plane entities and state transitions so routing, locking, intervention, and recovery behavior can be tested directly.
NFR21: Documentation, reference examples, and regression coverage for new orchestration behavior are part of the deliverable and must ship with Phase 1 changes rather than being deferred.
NFR22: Adapter extension points must remain explicit enough that contributors can implement or update runtime support without reverse-engineering hidden controller assumptions.

### Additional Requirements

- Use a durable repo-local control-plane store under `.codex/orchestration/`, with transactional canonical state in `state.db` and append-friendly audit export in `events.ndjson`.
- Enforce a single-controller session lock and recover authoritative state before permitting new assignments.
- Model `worker`, `task`, `lease`, `lock`, and `event` explicitly, including zero-or-one live lease invariants and coarse `exclusive_write` locks for file, directory, and logical work-surface targets.
- Reuse `tools/tmux_bridge/` as the low-level pane transport while keeping orchestration state, policy, routing, and recovery logic in a separate controller module set.
- Persist routing decisions, evidence records, recovery runs, and policy snapshots strongly enough to support restart reconciliation and post-run audit.
- Implement restart boot sequencing that loads persisted state, probes live tmux and adapter evidence, marks ambiguous tasks for hold or reconciliation, and blocks risky work until alignment is restored.
- Separate automatic, policy-automatic, operator-confirmed, and forbidden actions as an explicit decision-rights model.
- Default audit retention to local-host metadata capture, with policy-controlled redaction and bounded rich-content retention.
- Preserve compatibility with current single-worker usage as a degenerate one-worker orchestration session and keep existing tmux targeting metadata readable during migration.
- Ship unit, contract, integration, failure-drill, and four-worker dogfood test layers as release gates rather than post-MVP cleanup.

### UX Design Requirements

UX-DR1: Provide a controller-first worker roster view that ranks workers by readiness and risk, showing identity, runtime, availability, interruptibility, freshness, and capability metadata without forcing pane hopping.
UX-DR2: Provide task inspection views where current owner, lease state, lock state, intervention state, and recent events are primary fields rather than secondary drill-down data.
UX-DR3: Expose evidence stacks that clearly separate controller facts, adapter signals, and untrusted claims, including freshness or uncertainty markers when evidence is stale or partial.
UX-DR4: Keep assignment, pause, abort, reroute, reconcile, and pane-open actions in the same inspection flow so operators can move from alert to evidence to action without context switching.
UX-DR5: Present recovery and degraded-session summaries procedurally, with explicit freeze semantics, recommended next actions, and preserved ownership history.
UX-DR6: Maintain dense but calm terminal layouts with canonical nouns (`worker`, `task`, `lease`, `lock`, `event`, `adapter`), predictable command verbs, and stable table or inspector patterns.
UX-DR7: Support standard color and reduced-color or high-contrast terminal modes, plus narrow and wide layouts, without changing control-plane meaning.
UX-DR8: Provide machine-readable output modes and validation-oriented command output for setup, adapter qualification, and release-gate workflows.

### FR Coverage Map

FR1: Epic 1 - Stand Up a Trustworthy Orchestration Session
FR2: Epic 4 - Operate Tasks from a Controller-First Surface
FR3: Epic 1 - Stand Up a Trustworthy Orchestration Session
FR4: Epic 1 - Stand Up a Trustworthy Orchestration Session
FR5: Epic 4 - Operate Tasks from a Controller-First Surface
FR6: Epic 5 - Recover from Degradation Without Losing Ownership Truth
FR6a: Epic 1 - Stand Up a Trustworthy Orchestration Session
FR6b: Epic 1 - Stand Up a Trustworthy Orchestration Session
FR7: Epic 2 - Govern Heterogeneous Workers Through Explicit Adapters
FR8: Epic 2 - Govern Heterogeneous Workers Through Explicit Adapters
FR9: Epic 2 - Govern Heterogeneous Workers Through Explicit Adapters
FR10: Epic 2 - Govern Heterogeneous Workers Through Explicit Adapters
FR11: Epic 5 - Recover from Degradation Without Losing Ownership Truth
FR12: Epic 2 - Govern Heterogeneous Workers Through Explicit Adapters
FR12a: Epic 2 - Govern Heterogeneous Workers Through Explicit Adapters
FR13: Epic 3 - Route Work Safely and Reserve Protected Surfaces
FR14: Epic 7 - Adopt, Configure, and Migrate MACS in Real Repositories
FR15: Epic 3 - Route Work Safely and Reserve Protected Surfaces
FR16: Epic 3 - Route Work Safely and Reserve Protected Surfaces
FR17: Epic 3 - Route Work Safely and Reserve Protected Surfaces
FR18: Epic 3 - Route Work Safely and Reserve Protected Surfaces
FR19: Epic 4 - Operate Tasks from a Controller-First Surface
FR20: Epic 3 - Route Work Safely and Reserve Protected Surfaces
FR21: Epic 3 - Route Work Safely and Reserve Protected Surfaces
FR22: Epic 5 - Recover from Degradation Without Losing Ownership Truth
FR23: Epic 6 - Preserve Auditability and Governance Boundaries
FR23a: Epic 3 - Route Work Safely and Reserve Protected Surfaces
FR23b: Epic 3 - Route Work Safely and Reserve Protected Surfaces
FR24: Epic 5 - Recover from Degradation Without Losing Ownership Truth
FR25: Epic 5 - Recover from Degradation Without Losing Ownership Truth
FR26: Epic 4 - Operate Tasks from a Controller-First Surface
FR27: Epic 4 - Operate Tasks from a Controller-First Surface
FR28: Epic 5 - Recover from Degradation Without Losing Ownership Truth
FR29: Epic 6 - Preserve Auditability and Governance Boundaries
FR30: Epic 5 - Recover from Degradation Without Losing Ownership Truth
FR31: Epic 6 - Preserve Auditability and Governance Boundaries
FR32: Epic 4 - Operate Tasks from a Controller-First Surface
FR33: Epic 6 - Preserve Auditability and Governance Boundaries
FR34: Epic 6 - Preserve Auditability and Governance Boundaries
FR35: Epic 6 - Preserve Auditability and Governance Boundaries
FR35a: Epic 6 - Preserve Auditability and Governance Boundaries
FR35b: Epic 6 - Preserve Auditability and Governance Boundaries
FR36: Epic 7 - Adopt, Configure, and Migrate MACS in Real Repositories
FR37: Epic 7 - Adopt, Configure, and Migrate MACS in Real Repositories
FR38: Epic 7 - Adopt, Configure, and Migrate MACS in Real Repositories
FR39: Epic 7 - Adopt, Configure, and Migrate MACS in Real Repositories
FR39a: Epic 7 - Adopt, Configure, and Migrate MACS in Real Repositories
FR40: Epic 8 - Qualify the Release with Failure Drills and Dogfooding
FR41: Epic 8 - Qualify the Release with Failure Drills and Dogfooding
FR42: Epic 8 - Qualify the Release with Failure Drills and Dogfooding

## Epic List

### Epic 1: Stand Up a Trustworthy Orchestration Session
Operators can run a controller-owned local orchestration session with durable state, explicit task and lease semantics, and restart-safe authority before mixed-runtime coordination begins.
**FRs covered:** FR1, FR3, FR4, FR6a, FR6b

### Epic 2: Govern Heterogeneous Workers Through Explicit Adapters
Operators and contributors can register local workers through a skeptical adapter model that exposes mixed runtimes without weakening controller authority.
**FRs covered:** FR7, FR8, FR9, FR10, FR12, FR12a

### Epic 3: Route Work Safely and Reserve Protected Surfaces
Operators can assign work confidently because the controller evaluates policy and evidence, records routing rationale, and blocks conflicting write-impacting work.
**FRs covered:** FR13, FR15, FR16, FR17, FR18, FR20, FR21, FR23a, FR23b

### Epic 4: Operate Tasks from a Controller-First Surface
Operators can inspect, assign, pause, and navigate live work from one MACS-native surface without reconstructing orchestration truth from raw tmux panes.
**FRs covered:** FR2, FR5, FR19, FR26, FR27, FR32

### Epic 5: Recover from Degradation Without Losing Ownership Truth
Operators can detect degraded conditions, freeze unsafe progression, reconcile ambiguous ownership, and reroute work without creating split-brain state.
**FRs covered:** FR6, FR11, FR22, FR24, FR25, FR28, FR30

### Epic 6: Preserve Auditability and Governance Boundaries
Maintainers can trust what happened because MACS records durable history, enforces decision rights, protects sensitive surfaces, and keeps governance defaults explicit.
**FRs covered:** FR23, FR29, FR31, FR33, FR34, FR35, FR35a, FR35b

### Epic 7: Adopt, Configure, and Migrate MACS in Real Repositories
Technical adopters can configure workflow defaults, install the control plane, and move from current single-worker usage to mixed-runtime orchestration without bespoke glue.
**FRs covered:** FR14, FR36, FR37, FR38, FR39, FR39a

### Epic 8: Qualify the Release with Failure Drills and Dogfooding
Maintainers and contributors can prove the control-plane MVP is shippable by validating adapters, exercising failure containment, and passing the reference four-worker release gate.
**FRs covered:** FR40, FR41, FR42

## Epic 1: Stand Up a Trustworthy Orchestration Session

Operators can run a controller-owned local orchestration session with durable state, explicit task and lease semantics, and restart-safe authority before mixed-runtime coordination begins.

### Story 1.1: Start a single-controller orchestration session

As a maintainer,
I want to launch a repo-local orchestration session with an exclusive controller lock,
So that only one authoritative controller can govern local worker state at a time.

**Requirements:** FR1; NFR4, NFR17, NFR18

**Acceptance Criteria:**

**Given** a repository with MACS installed
**When** I start an orchestration session
**Then** MACS creates or verifies the repo-local `.codex/orchestration/` layout and acquires a single-controller lock
**And** a second controller start attempt fails with an operator-visible message that points to the active session

### Story 1.2: Persist authoritative control-plane entities

As a maintainer,
I want durable storage for `worker`, `task`, `lease`, `lock`, and `event` records,
So that controller truth survives process restarts and normal orchestration activity.

**Requirements:** FR1, FR3, FR4; NFR4, NFR11, NFR20

**Acceptance Criteria:**

**Given** an active orchestration session
**When** the controller creates or mutates control-plane entities
**Then** the canonical entity state is committed transactionally in `state.db`
**And** each material transition is also emitted to `events.ndjson` as an append-friendly audit record

### Story 1.3: Enforce task and lease state invariants

As a maintainer,
I want explicit task and lease state machines with zero-or-one live lease enforcement,
So that ownership never becomes ambiguous during normal progression.

**Requirements:** FR3, FR4, FR6a, FR6b; NFR6, NFR20

**Acceptance Criteria:**

**Given** a task with an existing live lease
**When** the controller evaluates a lease mutation or ownership transfer
**Then** it allows only one live lease state for that task at any time
**And** it records revoked, expired, completed, and replaced leases as historical records rather than active ownership

### Story 1.4: Restore controller state safely on restart

As a maintainer,
I want controller startup to restore persisted state before any new routing occurs,
So that recovery begins from authoritative records rather than runtime guesswork.

**Requirements:** FR1, FR4, FR6b; NFR4, NFR6a

**Acceptance Criteria:**

**Given** a prior session with persisted tasks, leases, and locks
**When** the controller restarts
**Then** it reloads the persisted state and marks any previously live ownership as pending reconciliation before accepting new assignments
**And** the operator can see a startup summary of restored entities and unresolved anomalies

## Epic 2: Govern Heterogeneous Workers Through Explicit Adapters

Operators and contributors can register local workers through a skeptical adapter model that exposes mixed runtimes without weakening controller authority.

### Story 2.1: Register and inspect tmux-backed workers

As an operator,
I want to discover, register, enable, disable, and inspect local workers,
So that the controller knows which execution endpoints are available for governed work.

**Requirements:** FR7, FR9; NFR1, NFR18

**Acceptance Criteria:**

**Given** one or more tmux-backed runtime sessions on the local host
**When** I run worker discovery or registration commands
**Then** MACS records stable worker identities with runtime, pane, and availability metadata
**And** I can enable, disable, or inspect a worker without editing state files manually

### Story 2.2: Implement the shared adapter contract and evidence envelope

As a contributor,
I want a base adapter contract that normalizes identity, capability, health, and intervention signals,
So that new runtimes can integrate without changing controller authority rules.

**Requirements:** FR10, FR12; NFR7, NFR19, NFR22

**Acceptance Criteria:**

**Given** an adapter implementation
**When** it reports worker evidence to the controller
**Then** the evidence is normalized into required signals, optional enrichment, timestamps, and confidence or freshness metadata
**And** the adapter cannot mutate authoritative task, lease, lock, or routing state directly

### Story 2.3: Deliver the Codex adapter as the reference worker

As a maintainer,
I want Codex CLI to be a first-class default worker in this repository,
So that the reference repo dogfoods the control plane with its primary runtime.

**Requirements:** FR8, FR9, FR10; NFR10, NFR19

**Acceptance Criteria:**

**Given** a valid Codex CLI environment
**When** I register or discover a Codex worker
**Then** the worker exposes required identity, capability, freshness, interruptibility, and supported permission-surface signals through the adapter contract
**And** missing optional telemetry degrades safely instead of blocking worker registration

### Story 2.4: Deliver Claude and Gemini adapters as governed workers

As a maintainer,
I want Claude Code and Gemini CLI workers to integrate through the same skeptical contract,
So that mixed-runtime orchestration is a product behavior rather than a special-case hack.

**Requirements:** FR8, FR9, FR10; NFR10, NFR19

**Acceptance Criteria:**

**Given** valid Claude Code or Gemini CLI environments
**When** I register the workers with MACS
**Then** each worker is represented through the shared adapter contract with explicit support or degradation for optional signals
**And** runtime-specific differences do not bypass controller-owned eligibility and health classification

### Story 2.5: Deliver the local adapter and first-class qualification checks

As a contributor,
I want a runtime-neutral local adapter and a qualification path for first-class support,
So that contributors can extend MACS without weakening the trust boundary.

**Requirements:** FR8, FR12a; NFR5, NFR22

**Acceptance Criteria:**

**Given** a local/runtime-neutral worker implementation
**When** it is validated for first-class support
**Then** it must satisfy required contract surfaces, degraded-mode behavior, intervention support, routing-evidence support, and validation coverage
**And** MACS marks it as non-first-class until those qualification checks pass

## Epic 3: Route Work Safely and Reserve Protected Surfaces

Operators can assign work confidently because the controller evaluates policy and evidence, records routing rationale, and blocks conflicting write-impacting work.

### Story 3.1: Configure workflow-aware routing policy

As an operator,
I want workflow-class defaults and capability rules for routing,
So that documentation, planning, implementation, review, and privacy-sensitive work can target the right runtimes.

**Requirements:** FR13, FR14, FR17; NFR13, NFR19

**Acceptance Criteria:**

**Given** repo-local routing policy configuration
**When** I create a task with workflow class and required capabilities
**Then** the controller evaluates workers against capability fit, trust boundaries, health, and policy defaults
**And** workers that fail required policy or capability checks are excluded from assignment

### Story 3.2: Record explainable assignment decisions

As an operator,
I want each task assignment to include a visible routing rationale,
So that I can understand why a worker was selected or rejected.

**Requirements:** FR13, FR15, FR16; NFR2, NFR13

**Acceptance Criteria:**

**Given** a task ready for assignment
**When** the controller ranks and selects eligible workers
**Then** it stores the selection outcome with evidence, rejections, and freshness context
**And** the operator can inspect the rationale without reading raw worker panes

### Story 3.3: Reserve protected surfaces with coarse default locks

As an operator,
I want the controller to reserve protected work surfaces before dispatch,
So that concurrent write-impacting work does not silently overlap.

**Requirements:** FR18, FR20, FR23a, FR23b; NFR2, NFR20

**Acceptance Criteria:**

**Given** a task that declares file, directory, or logical work-surface targets
**When** the controller prepares assignment
**Then** it acquires coarse `exclusive_write` locks for the protected surfaces before activating the lease
**And** lock state is stored durably with task, lease, and policy-origin metadata

### Story 3.4: Block conflicts and duplicate ownership claims

As a maintainer,
I want the controller to reject unsafe overlaps and duplicate claims,
So that split-brain coordination cannot progress as normal work.

**Requirements:** FR20, FR21; NFR5, NFR20

**Acceptance Criteria:**

**Given** a new assignment or claim that conflicts with an active lock or live task ownership
**When** the controller validates the request
**Then** it rejects or freezes the conflicting progression instead of activating a second owner
**And** it emits conflict evidence that later recovery and audit flows can inspect

## Epic 4: Operate Tasks from a Controller-First Surface

Operators can inspect, assign, pause, and navigate live work from one MACS-native surface without reconstructing orchestration truth from raw tmux panes.

### Story 4.1: Provide compact list and inspect commands for control-plane objects

As an operator,
I want stable CLI views for workers, tasks, leases, locks, and events,
So that I can answer common orchestration questions from the controller pane in seconds.

**Requirements:** FR5, FR19, FR32; NFR1, NFR14, NFR16

**Acceptance Criteria:**

**Given** an active orchestration session
**When** I run list or inspect commands for control-plane objects
**Then** MACS shows dense, stable layouts using canonical control-plane terminology
**And** the same commands support machine-readable output for scripting and test automation

### Story 4.2: Assign and manage task lifecycle actions from one command path

As an operator,
I want to create, assign, reassign, close, and archive tasks through MACS-native commands,
So that normal orchestration never depends on manual tmux surgery.

**Requirements:** FR2, FR5, FR32; NFR14, NFR16

**Acceptance Criteria:**

**Given** a task in draft, pending, active, or completed state
**When** I invoke a supported lifecycle command through the controller surface
**Then** the requested transition is validated against authoritative state and applied through one MACS command path
**And** the resulting owner, lease, lock, and event changes are immediately inspectable

### Story 4.3: Inspect degraded evidence and open the right worker pane from context

As an operator,
I want to move from a task or worker record to the relevant evidence and pane,
So that I can investigate live behavior without losing the controller’s state context.

**Requirements:** FR26, FR32; UX-DR3, UX-DR4

**Acceptance Criteria:**

**Given** a worker or task flagged as degraded or under review
**When** I inspect the record
**Then** MACS shows controller facts, adapter signals, and untrusted claims as distinct evidence layers
**And** I can open the associated tmux pane from that same context without losing the task or worker reference

### Story 4.4: Support in-place pause controls and terminal accessibility modes

As an operator,
I want pause controls, narrow layouts, and reduced-color modes in the same controller surface,
So that intervention stays accessible in varied terminal conditions.

**Requirements:** FR27; NFR14, NFR16; UX-DR6, UX-DR7

**Acceptance Criteria:**

**Given** an active task in a terminal with standard or reduced-color settings
**When** I use pause or inspection flows
**Then** the CLI offers the same control semantics in narrow and wide layouts with consistent terminology
**And** pause remains available from the controller surface without requiring raw pane commands as the primary path

## Epic 5: Recover from Degradation Without Losing Ownership Truth

Operators can detect degraded conditions, freeze unsafe progression, reconcile ambiguous ownership, and reroute work without creating split-brain state.

### Story 5.1: Classify worker health and surface warnings promptly

As an operator,
I want worker health, freshness, and budget evidence to drive visible warnings,
So that risky sessions are identified before they corrupt coordination state.

**Requirements:** FR11, FR24, FR25; NFR3, NFR19

**Acceptance Criteria:**

**Given** worker evidence indicating stale heartbeat, degraded adapter health, or surfaced quota or session risk
**When** the controller classification threshold is met
**Then** MACS updates the worker state to the appropriate health class and raises an operator-visible warning within the defined timing window
**And** new routing respects the degraded classification automatically

### Story 5.2: Freeze risky work through intervention hold and lease suspension

As an operator,
I want degraded tasks to enter an explicit hold state before unsafe work continues,
So that the controller prevents conflicting progression during investigation.

**Requirements:** FR6, FR24, FR27; NFR6, NFR20

**Acceptance Criteria:**

**Given** a task attached to degraded or uncertain worker evidence
**When** I pause the task or the controller places it into intervention hold by policy
**Then** the task transitions into a non-progressing state and the live lease is suspended or paused without creating a successor lease
**And** conflicting reassignment is blocked until the hold is resolved

### Story 5.3: Reconcile ambiguous ownership and reroute safely

As an operator,
I want reroute and recovery flows to revoke or replace unsafe ownership explicitly,
So that a task can move forward without ever appearing to have two active owners.

**Requirements:** FR22, FR28, FR30; NFR6, NFR6a

**Acceptance Criteria:**

**Given** a task in reconciliation due to disconnect, duplicate claim, lock collision, or misleading health evidence
**When** I confirm reroute or recovery
**Then** the controller resolves the predecessor live lease before activating a successor lease
**And** the task remains blocked from risky progression until ownership ambiguity is cleared

### Story 5.4: Resume interrupted recovery from persisted recovery runs

As a maintainer,
I want recovery actions and anomalies to persist as resumable recovery runs,
So that controller restart or operator interruption does not erase recovery context.

**Requirements:** FR28, FR30; NFR4, NFR5, NFR6a

**Acceptance Criteria:**

**Given** a recovery flow that is interrupted by restart or operator exit
**When** the controller comes back online
**Then** it restores the pending recovery run, detected anomalies, evidence references, and recommended actions
**And** no successor routing proceeds until the interrupted recovery is either completed or explicitly abandoned with audit

## Epic 6: Preserve Auditability and Governance Boundaries

Maintainers can trust what happened because MACS records durable history, enforces decision rights, protects sensitive surfaces, and keeps governance defaults explicit.

### Story 6.1: Persist a durable event trail and history inspectors

As a maintainer,
I want event, lease, and lock history to remain inspectable after work completes or fails,
So that post-run analysis does not depend on raw pane logs.

**Requirements:** FR23, FR31; NFR11, NFR12

**Acceptance Criteria:**

**Given** assignments, lock mutations, interventions, recoveries, and task closure events
**When** I inspect historical state for a task or worker
**Then** MACS shows a durable timeline that reconstructs operator-visible orchestration history
**And** completed or failed work retains inspectable ownership and lock history

### Story 6.2: Preserve intervention rationale across recovery and reassignment

As a maintainer,
I want recovery decisions to carry operator rationale and causation links,
So that ownership changes remain explainable after degraded workflows.

**Requirements:** FR29, FR31; NFR11, NFR13

**Acceptance Criteria:**

**Given** a pause, reroute, abort, or reconciliation decision
**When** the controller records the intervention
**Then** it stores actor identity, rationale, causation, and resulting transitions in the event trail
**And** later inspection can connect the recovery decision to the affected task, lease, and worker records

### Story 6.3: Enforce explicit decision rights and guarded actions

As an operator,
I want automatic, policy-automatic, operator-confirmed, and forbidden actions to be explicit,
So that MACS moves quickly where safe and stops where human authorization is required.

**Requirements:** FR33, FR35a; NFR7, NFR8, NFR10

**Acceptance Criteria:**

**Given** an action such as normal routing, quarantine, reroute, abort, or conflict override
**When** the controller evaluates the requested behavior
**Then** it applies the configured decision-rights class and requires confirmation for operator-confirmed actions
**And** forbidden MVP actions are rejected with a clear explanation instead of being silently attempted

### Story 6.4: Govern external surfaces, privacy-sensitive routing, and audit content

As a maintainer,
I want MCP or similar integrations, privacy-sensitive workflows, and rich audit capture to be policy-controlled,
So that governance defaults remain conservative and inspectable.

**Requirements:** FR34, FR35, FR35b; NFR9, NFR13a

**Acceptance Criteria:**

**Given** governed integration settings, local-only workflow classes, and optional rich-content capture
**When** I configure or inspect governance policy
**Then** MACS supports allowlisting or pinning of governed surfaces, local-routing rules for privacy-sensitive work, and separate metadata versus rich-content audit policy
**And** redaction or omission policy is applied before optional rich content is retained

## Epic 7: Adopt, Configure, and Migrate MACS in Real Repositories

Technical adopters can configure workflow defaults, install the control plane, and move from current single-worker usage to mixed-runtime orchestration without bespoke glue.

### Story 7.1: Separate controller, adapter, policy, and state configuration

As an operator,
I want repo-local configuration domains for controller defaults, adapters, routing policy, governance, and state,
So that I can change orchestration behavior without editing code paths directly.

**Requirements:** FR14, FR37; NFR15, NFR18

**Acceptance Criteria:**

**Given** a fresh or existing repository
**When** I inspect or edit MACS configuration
**Then** controller defaults, runtime adapter settings, routing policy, governance policy, and repo-local state locations are separately documented and configurable
**And** workflow-class defaults can be applied without bespoke repository glue code

### Story 7.2: Deliver mixed-runtime setup and validation flow

As a technical adopter,
I want a documented setup path that registers and validates mixed runtimes on one local host,
So that I can reach a safe ready state in a real repository without reverse-engineering MACS internals.

**Requirements:** FR36, FR38, FR39; NFR15, NFR21

**Acceptance Criteria:**

**Given** a repository adopting the control-plane MVP
**When** I follow the documented setup flow
**Then** I can install or configure MACS, register supported runtimes, validate worker readiness, and inspect routing defaults end to end
**And** the flow includes reference examples for registration, intervention, and recovery

### Story 7.3: Preserve and document single-worker compatibility boundaries

As an existing MACS user,
I want single-worker usage to remain supported with clear compatibility notes,
So that I can migrate incrementally instead of taking a hard workflow break.

**Requirements:** FR38, FR39a; NFR18

**Acceptance Criteria:**

**Given** an existing single-controller or single-worker MACS setup
**When** I migrate to the new control-plane commands
**Then** MACS documents which legacy metadata and workflows remain readable, which commands are superseded, and whether state migration is required
**And** one-worker orchestration remains a supported specialization of the same control-plane model

### Story 7.4: Publish contributor-facing adapter guidance

As a contributor,
I want clear docs for adapter extension, declared capabilities, and validation expectations,
So that I can add or update runtime support without tribal knowledge.

**Requirements:** FR39, FR41; NFR21, NFR22

**Acceptance Criteria:**

**Given** the adapter extension surface
**When** I read the contributor documentation
**Then** I can find the minimum adapter contract, declared capability model, degraded-mode expectations, and qualification steps in one place
**And** the docs align with the shared contract tests and release-gate criteria

## Epic 8: Qualify the Release with Failure Drills and Dogfooding

Maintainers and contributors can prove the control-plane MVP is shippable by validating adapters, exercising failure containment, and passing the reference four-worker release gate.

### Story 8.1: Build unit and contract test coverage for controller and adapter invariants

As a maintainer,
I want deterministic unit and contract suites around state transitions and adapter behavior,
So that core orchestration semantics can be validated without relying only on live sessions.

**Requirements:** FR40, FR41; NFR20, NFR22

**Acceptance Criteria:**

**Given** the controller domain model and shared adapter contract
**When** the automated test suite runs
**Then** unit tests cover task, lease, lock, routing, and recovery invariants while contract tests cover adapter normalization and unsupported-feature declarations
**And** an adapter cannot qualify as first-class if its shared contract checks fail

### Story 8.2: Build integration and failure-drill coverage for mandatory failure classes

As a maintainer,
I want tmux-backed integration tests and failure drills for required recovery scenarios,
So that release readiness is based on catastrophe-grade orchestration behavior rather than happy paths alone.

**Requirements:** FR40, FR42; NFR5, NFR20

**Acceptance Criteria:**

**Given** isolated tmux sockets and fixture work surfaces
**When** the integration and failure-drill suites run
**Then** they exercise worker disconnect, stale lease divergence, duplicate claim, split-brain ownership, lock collision, misleading health evidence, surfaced budget exhaustion, and interrupted recovery
**And** each mandatory failure class produces assertions against authoritative state and event traces

### Story 8.3: Validate the four-worker reference dogfood scenario

As a maintainer,
I want a repeatable four-worker orchestration scenario in the MACS repo,
So that the Phase 1 release proves real mixed-runtime value under its reference conditions.

**Requirements:** FR42; NFR1, NFR2, NFR3, NFR5

**Acceptance Criteria:**

**Given** Codex, Claude, Gemini, and local workers in the reference repository
**When** the dogfood scenario is executed
**Then** MACS completes the defined mixed-runtime orchestration flow with visible ownership, locks, routing rationale, and intervention support under the reference timing envelope
**And** the scenario records enough artifacts to support release review and repeatability

### Story 8.4: Ship a release-gate command and report for Phase 1 readiness

As a maintainer,
I want one command that summarizes contract, integration, failure-drill, and dogfood readiness,
So that the MVP can be evaluated against explicit release criteria before shipping.

**Requirements:** FR42; NFR5, NFR21

**Acceptance Criteria:**

**Given** the Phase 1 validation suites and reference scenario outputs
**When** I run the release-gate command
**Then** MACS reports pass or fail status for first-class adapters, mandatory failure classes, restart recovery invariants, and the four-worker reference scenario
**And** the release decision can be traced to machine-readable and human-readable evidence rather than ad hoc judgment
