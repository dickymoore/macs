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
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/product-brief-macs_dev.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/product-brief-macs_dev-validation-report.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/research/domain-multi-agent-orchestration-and-agent-runtime-orchestration-for-macs-research-2026-04-09.md
  - /home/codexuser/macs_dev/_bmad-output/project-context.md
  - /home/codexuser/macs_dev/.source/deep-research-report.md
  - /home/codexuser/macs_dev/.source/deep-research-report (1).md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/macs-multi-agent-orchestration-diagram-pack-2026-04-09.md
  - /home/codexuser/macs_dev/docs/architecture.md
workflowType: 'prd'
documentCounts:
  briefs: 2
  research: 3
  brainstorming: 0
  projectDocs: 2
classification:
  projectType: developer_tool
  domain: general
  complexity: medium
  projectContext: brownfield
---

# Product Requirements Document - macs_dev

**Author:** Dicky
**Date:** 2026-04-09T19:00:00+01:00

## Executive Summary

MACS currently provides a controller-to-worker supervision model built around tmux and a Python bridge. That model is useful, but it does not yet provide a trustworthy control plane for many heterogeneous agent runtimes working in parallel. The next product phase extends MACS into a controller-owned orchestration system that manages multiple tmux worker windows across mixed runtimes while preserving explicit authority over routing, ownership, locks, intervention, monitoring, and recovery.

The core product problem is not agent launch or terminal multiplexing. It is safe orchestration. Current MACS and ad hoc multi-agent setups do not provide reliable task ownership, bounded context, evidence-backed routing, conflict-aware coordination, or auditable recovery across mixed runtimes. As a result, parallel agent execution can produce hidden divergence, stale-state misrouting, semantic merge conflicts, low operator confidence, and poor reproducibility in failure handling.

Phase 1 of this product defines MACS as a local-host-first orchestration control plane for maintainers and serious technical adopters. The controller remains authoritative for `worker`, `task`, `lease`, `lock`, and `event` state. Worker runtimes are integrated through skeptical, pluggable adapters that expose facts, soft signals, and claims with bounded trust rather than becoming the source of truth themselves. Product defaults should preserve Codex CLI as the default controller/worker runtime in this repository while supporting Claude Code, Gemini CLI, and local adapters as first-class workers.

The MVP focuses on production-grade local orchestration before broader autonomy or distributed execution. It includes one orchestration controller managing multiple tmux worker windows, pluggable runtime adapters, controller-owned routing, explicit ownership and lock management, operator monitoring and intervention across windows, token or session-limit visibility where available, and comprehensive automated testing for orchestration behavior, coordination boundaries, and recovery paths. It explicitly excludes autonomous self-replanning without operator oversight, cross-machine orchestration, deep enterprise IAM packaging, and broad marketplace/ecosystem layers beyond the initial adapter model.

### What Makes This Special

MACS is differentiated by treating orchestration as an operational governance problem instead of an agent-construction problem. The product is not primarily a framework for building agents. It is a control plane for governing mixed-runtime execution under explicit safety and recovery rules.

Its core differentiators are:
- controller-owned orchestration authority rather than runtime-owned implicit coordination
- heterogeneous runtime support across Codex CLI, Claude Code, Gemini CLI, and local/runtime-neutral adapters
- safe parallelisation through explicit ownership, leases, locks, coordination boundaries, and reconciliation gates
- evidence-backed routing that distinguishes authoritative controller state from adapter signals and untrusted claims
- governance defaults including sandboxing and approval controls, skeptical adapter boundaries, MCP allowlisting/pinning, explicit audit trails, and no-auto-push / no-remote-ops style safeguards where relevant
- workflow-aware runtime defaults so documentation/context, planning, solutioning, implementation, review, and privacy-sensitive/offline work can be routed to appropriate runtimes by policy or configuration
- comprehensive automated regression centered on failure containment, including split-brain ownership, stale-state routing, lock collisions, degraded sessions, and interrupted recovery

The core insight behind the product is that the missing capability in current multi-agent coding workflows is not more agent intelligence. It is trustworthy orchestration. Users should choose MACS because it gives them a legible, inspectable, intervention-friendly control plane for parallel heterogeneous agent work without forcing them to trust opaque runtime behavior.

## Project Classification

- **Project Type:** Developer tool with strong CLI/tooling characteristics
- **Domain:** General software tooling focused on multi-agent orchestration and runtime governance
- **Complexity:** Medium, with elevated operational complexity driven by state authority, failure recovery, and mixed-runtime coordination
- **Project Context:** Brownfield project extending an existing single-controller/single-worker architecture into a local-host-first multi-agent orchestration platform

## Success Criteria

### User Success

The product succeeds for primary users when maintainers can run and supervise parallel multi-agent workflows on a single local host without losing ownership clarity, safety boundaries, or recovery control. The user "aha" moment is not that multiple workers are running; it is that multiple heterogeneous workers can run in parallel while the controller still shows a clear current owner, current locks, live worker state, and explicit intervention options.

For maintainers, "done" means they can:
- discover or register workers,
- inspect worker capability and health state,
- assign work through the controller,
- see active ownership and lock state without manual inference,
- intervene in degraded sessions without dropping to ad hoc tmux surgery for core orchestration tasks,
- reconcile or reroute failed work with auditable controller-owned state.

For technical adopters, success means MACS can be applied to real repositories with mixed runtimes and still behave predictably enough to trust for serious parallel work, not just demos.

### Business Success

Because this is an open-source product with a path to production-grade use, business success is primarily adoption, credibility, and contributor momentum rather than direct revenue.

At 3 months, success means:
- a coherent Phase 1 orchestration release exists with documented runtime support and explicit local-host-first positioning,
- maintainers can use the orchestration controller in the MACS repo itself for real multi-agent workflows,
- the release is credible enough to attract serious contributor and adopter interest.

At 6-12 months, success means:
- MACS is seen as a credible open-source foundation for heterogeneous agent orchestration,
- maintainers and early adopters are using it in real repositories,
- contributors can extend runtime adapters and orchestration logic against a stable control-plane model,
- the project has clear evidence that its differentiation is understood: mixed-runtime orchestration with controller-owned authority and testable resilience.

### Technical Success

The product succeeds technically when orchestration authority is explicit, runtime evidence is bounded and interpretable, and failure handling is testable.

Technical success for MVP requires:
- one controller-authoritative source of truth for `worker`, `task`, `lease`, `lock`, and `event` state,
- successful orchestration of multiple tmux worker windows on a single local host,
- first-class worker support for Codex CLI, Claude Code, Gemini CLI, and one runtime-neutral/local adapter,
- explicit ownership and lock handling that prevents unsafe concurrent work on protected surfaces,
- operator interventions for pause, inspect, reroute, reconcile, and abort through the intended MVP surface,
- token/session visibility where a runtime exposes those signals, with graceful degradation where it does not,
- automated regression coverage for routing, locking, ownership, intervention, and recovery behavior,
- mandatory failure-mode coverage for split-brain ownership, stale-state routing, lock collision, degraded session state, false healthy signal, exhausted budget/session state where available, and interrupted recovery flows.

For Phase 1 authority semantics:
- a task may have zero or one active leases, never more than one,
- a task may temporarily have zero active leases during reconciliation, interrupted reassignment, or explicit operator-held recovery,
- paused or suspended work must not create a second active lease; the controller must either preserve the current lease in a non-progressing state or revoke it before replacement,
- expired, revoked, replaced, and completed leases remain historical records and must not be treated as active.

### Measurable Outcomes

The Phase 1 release must meet the following measurable targets:

- **Concurrent-worker target:** support at least **4 concurrent local-host workers** under one orchestration controller in the reference repo.
- **Runtime target:** ship with **4 first-class runtime adapters**:
  - Codex CLI
  - Claude Code
  - Gemini CLI
  - one local/runtime-neutral adapter
- **Authoritative-state target:** every task assignment must create and expose:
  - exactly **1 current owner**
  - at most **1 active lease record**
  - explicit lock state for protected surfaces where applicable
  - an auditable event trail for assignment and intervention actions
- **Lease-semantics target:** the controller must enforce a zero-or-one-active-lease rule per task. A task may temporarily have zero active leases during reconciliation or interrupted reassignment, but it must never have more than one active lease at a time.
- **Operator-visible outcome target:** the MVP surface must allow an operator to complete, without manual direct tmux surgery for normal orchestration flow:
  - inspect worker state
  - assign work
  - view current ownership and locks
  - pause and resume
  - reroute
  - trigger recovery/reconciliation
  - close/archive completed work
  - inspect explicit guarded high-consequence actions such as `abort`, `lock override`, and `lock release`, which remain CLI-visible but blocked in Phase 1
- **Failure/recovery coverage target:** the automated release-gate suite must include and pass **100%** of the mandatory failure-mode matrix for:
  - worker disconnect
  - stale lease/session divergence
  - duplicate task claim / split-brain ownership
  - lock collision
  - stale or misleading health/capability evidence
  - budget/session exhaustion where surfaced by adapters
  - interrupted or partial recovery
- **Adopter-setup target:** a technically capable adopter must be able to configure a mixed-runtime local-host installation in a real repo using documented setup and configuration, without bespoke per-repo glue code beyond documented extension points.
- **Real-use target:** the Phase 1 release must demonstrate repeatable successful parallel workflows in the MACS repo. Early external adopter use in a real repository is a strong validation signal and preferred post-release milestone, but not a hard ship blocker if equivalent internal dogfooding evidence exists by release cutoff.
- **Conflict-prevention target:** 100% of detected write-impacting protected-surface conflicts are blocked before dispatch in passing failure drills, and passing dogfood or release-gate runs show zero silent conflicting assignments.
- **Stale-lease recovery target:** stale or ambiguous live-lease conditions become operator-visible and assignment-blocking within 60 seconds of detection or startup reconciliation in the reference environment.
- **Reroute success target:** at least 90% of operator-confirmed reroute attempts in controlled recovery drills complete without violating zero-or-one-live-lease invariants, and 100% of successful reroutes preserve the decision-event causation chain.
- **Intervention-frequency target:** under the default `primary_plus_fallback` profile, unplanned manual intervention stays below 10% of tasks in reference internal dogfood runs, excluding planned drills and demonstrations.
- **False-safe-routing target:** zero passing release-gate runs may include an assignment later frozen as unsafe without a contemporaneous warning, policy block, or recovery hold.
- **Auditable-passing-run target:** 100% of runs counted as PASS must emit a complete evidence package: release-gate summary, human-readable reports, machine-readable artifacts, and correlated event IDs.

## Product Scope

### MVP - Minimum Viable Product

MVP is the smallest production-grade release that proves MACS can safely orchestrate heterogeneous workers on a single local host.

**Release blockers / must-have:**
- one orchestration controller managing multiple tmux worker windows
- controller-owned source of truth for `worker`, `task`, `lease`, `lock`, and `event`
- explicit operator task lifecycle for assign, inspect, intervene, recover, and close/archive
- first-class runtime adapters for Codex CLI, Claude Code, Gemini CLI, and one local/runtime-neutral adapter
- minimum adapter contract with required signals and defined degradation behavior when signals are unavailable
- explicit BMAD phase-to-runtime policy with shipping-default `primary_plus_fallback` and opt-in `full_hybrid` operating profiles
- controller-owned routing with evidence-aware worker selection
- explicit ownership and coarse protected-surface locks for conflict avoidance
- operator monitoring/intervention across windows
- explicit audit/event logging
- governance defaults:
  - sandboxing/approval controls where supported
  - skeptical adapter boundaries
  - MCP allowlisting/pinning where relevant
  - no-auto-push / no-remote-ops safeguards where relevant
- mandatory orchestration and failure-mode regression tests
- intended MVP interaction surface defined and implemented as a local-host-first operator experience

**MVP non-goals that protect delivery:**
- no distributed or cross-machine orchestration
- no autonomous self-replanning beyond operator-governed recovery flows
- no semantic merge intelligence beyond coarse protected-surface coordination and explicit reconciliation
- no enterprise IAM, hosted control plane, or team-administration layer as a Phase 1 dependency
- no requirement that all runtimes expose identical telemetry depth or intervention richness beyond the minimum first-class adapter contract

**Minimum protected-surface lock model for MVP:**
- lock targets may be declared at the file, directory, or policy-defined logical work-surface level
- the default lock granularity is intentionally coarse: directory or explicitly named work-surface scope, with file-level locks used where scope is already explicit
- MVP lock semantics are write-oriented and conflict-prevention focused; the product does not require a full read/read, read/write, write/write matrix beyond treating concurrent write-impacting work as conflicting unless policy explicitly allows it
- operator override is allowed only through explicit controller-mediated intervention that is logged and forces reconciliation semantics when conflict risk exists

**Should-have for Phase 1 if schedule permits:**
- token/session-limit visibility and warnings where adapters can expose them
- workflow-class-aware runtime/backend defaults as product configuration rules
- hybrid lock behavior beyond coarse default, where it does not threaten MVP delivery
- richer operator diagnostics for degraded workers and stale evidence

### Growth Features (Post-MVP)

These features strengthen competitiveness after the production-grade local-host foundation is proven:

- finer-grained or semantic coordination beyond coarse protected-surface locks
- richer routing policies by workflow class and confidence levels
- stronger replay/reconciliation tooling and workflow visualisation
- expanded adapter ecosystem and broader runtime capability negotiation
- more sophisticated operator surfaces and status views
- more advanced policy tooling for teams and maintainers

### Vision (Future)

The long-term vision is for MACS to become a trusted open-source orchestration control plane for heterogeneous agent runtimes.

Future-state capabilities may include:
- broader interoperability across vendors and local/offline agents
- deeper evidence-backed orchestration policies
- stronger replay, audit, and governance layers
- more mature standards-aligned control-plane semantics
- eventual expansion beyond single-host orchestration, but only after local-host authority and safety are proven

This keeps the product anchored to the core insight: trustworthy orchestration first, broader autonomy later.

## User Journeys

### Journey 1: Maintainer Runs a Successful Parallel Orchestration Session

**Persona:** Maya, core MACS maintainer  
**Situation:** Maya needs to move faster on a real repo task without sacrificing control. She already knows how to run one controller and one worker in MACS, but parallel work today still feels fragile and too dependent on manual coordination.  
**Goal:** Run multiple heterogeneous workers in parallel under one controller and still trust the system’s ownership, routing, and recovery behavior.  
**Obstacle:** Ad hoc multi-agent workflows create ambiguity around who owns what, what runtime is safe to use, and whether a worker is still healthy enough to keep the task.

**Opening Scene**  
Maya opens MACS in a local repo and launches a local-host orchestration session. The system discovers registered workers across tmux windows: Codex CLI, Claude Code, Gemini CLI, and a local adapter. Instead of guessing which worker to use, she sees worker capabilities, freshness, health, interruptibility, and token/session visibility where available.

**Rising Action**  
She creates a task and the controller evaluates routing policy against workflow class, capability fit, and lock state. The controller assigns the task to a worker, creates a visible lease, reserves protected surfaces, and records the decision in the event log. Maya then assigns a second non-conflicting task to another worker and watches both progress in parallel.

**Climax**  
The moment of value arrives when Maya sees that parallelism is no longer opaque: each task has one current owner, locks are visible, the routing decision is explainable, and she can inspect the workers without manually reconstructing state from raw tmux panes.

**Resolution**  
The tasks complete without silent coordination failure. Maya closes the tasks through the controller and sees an auditable event trail of assignment, progress, and completion. Her new reality is that multi-agent parallel work feels governable rather than improvised.

**Capabilities Revealed**
- worker discovery/registration
- worker capability and health display
- workflow-aware routing defaults
- lease creation and ownership visibility
- protected-surface locking
- event logging and task closure

### Journey 2: Maintainer Intervenes in a Degraded Session and Recovers Safely

**Persona:** Maya, core MACS maintainer  
**Situation:** A routed worker begins to degrade mid-task. In today’s workflows, this is where trust collapses: the maintainer has to infer whether the worker is still valid, whether the task should move, and whether ownership is now ambiguous.  
**Goal:** Inspect the issue, pause unsafe progress, and recover or reroute the task without creating split-brain ownership.  
**Obstacle:** Health signals can be stale or incomplete, and a worker may still appear active even when it is unsafe to continue.

**Opening Scene**  
During a parallel session, the controller raises a degraded-state warning: the worker’s session freshness is weak and observed behavior no longer matches prior health confidence. Maya sees the task’s current lease, lock state, and recent events from the controller.

**Rising Action**  
She pauses the affected lease from the intended operator surface. The controller freezes risky progression, records the intervention, and prevents a second worker from silently taking over the same task. Maya inspects the worker’s evidence, compares recent event history, and chooses reroute rather than resume.

**Climax**  
The critical value moment is not just that recovery exists. It is that recovery is legible. Maya can see the current owner, the intervention state, the reasons the worker was downgraded, and the exact reconciliation path before a new worker is allowed to continue.

**Resolution**  
The controller reassigns the task under a new lease, preserves the audit trail, and prevents split-brain ownership. Maya does not need to improvise with manual tmux operations to keep the system safe.

**Capabilities Revealed**
- degraded-state detection
- pause/abort/reroute controls
- reconciliation workflow
- lease and ownership freeze semantics
- evidence-aware health interpretation
- recovery event trail

### Journey 3: Technical Adopter Onboards MACS into a Real Repository

**Persona:** Rowan, early technical adopter  
**Situation:** Rowan wants to use MACS in a serious codebase, but most multi-agent tools still feel like demos or one-off internal stacks.  
**Goal:** Install MACS, configure mixed runtimes, and run a real local-host orchestration workflow without bespoke glue code.  
**Obstacle:** Setup friction is often the hidden killer of open-source adoption. If runtime configuration, adapter semantics, or workflow setup feel too custom, adoption stops before value is proven.

**Opening Scene**  
Rowan installs MACS into a repository and follows documented setup for the Phase 1 orchestration model. The product defaults make Codex CLI the default controller/worker runtime in this repo, while still allowing Rowan to register Claude Code, Gemini CLI, and a local adapter as workers.

**Rising Action**  
He configures the available adapters, verifies worker registration, and reviews the runtime policy defaults by workflow class. He does not need to write repository-specific orchestration glue just to get the system working. The controller exposes a clear local-host-first interaction model and safe defaults around approvals, runtime trust, and no-auto-push / no-remote-ops style protections where applicable.

**Climax**  
The adoption “aha” moment is when Rowan realizes that mixed-runtime orchestration is a first-class product behavior, not a pile of undocumented tweaks. He can route real work, observe state, and understand the controller’s decisions without reverse-engineering the product.

**Resolution**  
Rowan is able to run a real mixed-runtime workflow in his own repo and judge MACS as a credible open-source foundation for serious orchestration work.

**Capabilities Revealed**
- documented installation and repo onboarding
- runtime adapter configuration
- local-host-first defaults
- workflow-class-aware policy defaults
- safe governance defaults
- low-friction mixed-runtime startup path

### Journey 4: Contributor Adds or Improves a Runtime Adapter

**Persona:** Elena, contributor extending MACS  
**Situation:** Elena wants to improve heterogeneous runtime support, but adapter work in orchestration systems often becomes inconsistent because the product has no clear minimum contract.  
**Goal:** Extend MACS with confidence using a stable adapter model and a predictable regression suite.  
**Obstacle:** Without a minimum adapter contract and explicit degradation rules, new runtime support can weaken routing and recovery semantics rather than strengthen them.

**Opening Scene**  
Elena reviews the adapter contract and sees the minimum required surfaces: worker identity, capability metadata, health/freshness signals, interruptibility, and degraded behavior when certain signals are unavailable.

**Rising Action**  
She implements or updates an adapter and runs the regression suite. The tests do not only check happy-path startup. They validate how the adapter behaves when a runtime cannot expose token limits, when health evidence goes stale, or when session continuity is weak.

**Climax**  
The key value moment is that adapter contribution is governed. Elena is not guessing what “supporting a runtime” means. She is implementing against explicit orchestration semantics and release-gate tests.

**Resolution**  
Her adapter changes land without weakening the controller-owned authority model, and contributors can grow the runtime matrix without eroding the product’s trust boundary.

**Capabilities Revealed**
- minimum adapter contract
- optional vs required adapter signals
- graceful degradation rules
- adapter-facing test harness
- contributor-safe extension model

### Journey 5: Maintainer Investigates a Failed or Conflicted Run

**Persona:** Maya, core MACS maintainer  
**Situation:** A workflow fails, or two work surfaces appear to be in conflict. In current ad hoc systems, this kind of event often devolves into manual archaeology.  
**Goal:** Reconstruct what happened, determine whether ownership diverged or locking failed, and decide whether the work can be resumed, reassigned, or aborted.  
**Obstacle:** Hidden failures are the most damaging kind because they make the system look coordinated until the output is already compromised.

**Opening Scene**  
Maya sees an alert indicating a lock collision, stale lease/session divergence, or suspected split-brain ownership. The controller shows her recent events, current lease history, current lock state, and the affected workers.

**Rising Action**  
She traces the failure from the event log instead of reading raw pane output and guessing. The system highlights whether the issue came from stale routing evidence, a recovery interruption, or a conflicting ownership claim.

**Climax**  
The real value arrives when the system explains enough state to support a decision. Maya can determine whether the task should be reconciled, re-run, reassigned, or closed, and the product preserves that outcome in the audit trail.

**Resolution**  
Failure analysis becomes an operator workflow, not an improvised debugging ritual. This raises trust in the platform because failures are not only survivable; they are inspectable.

**Capabilities Revealed**
- audit/event timeline
- failure classification
- lock/lease history visibility
- split-brain detection and reconciliation
- post-failure operator decision support

### Journey Requirements Summary

These journeys reveal the minimum capability areas the MVP must support:

- controller-owned lifecycle management for `worker`, `task`, `lease`, `lock`, and `event`
- a clear operator task lifecycle:
  - discover/register
  - inspect
  - assign
  - monitor
  - intervene
  - recover/reconcile
  - close/archive
- visible worker evidence and graceful degradation when signals are unavailable
- runtime policy defaults by workflow class and runtime/backend suitability
- protected-surface ownership and lock semantics for safe parallelisation
- intervention and recovery paths that are visible and auditable
- adapter extensibility governed by a minimum contract and regression suite
- onboarding and setup flows that make mixed-runtime use practical for real repos

## Domain-Specific Requirements

### Compliance & Regulatory

This product does not start in a formally regulated vertical, but it still operates under meaningful governance expectations because it orchestrates code execution, terminal access, tool invocation, and potentially sensitive repository content across multiple runtimes.

The product must therefore treat the following as baseline domain requirements:
- maintain explicit audit trails for routing, ownership, lease changes, lock changes, interventions, and recovery events
- preserve operator oversight as a first-class control, especially for pause, reroute, abort, and reconciliation actions
- support bounded-permission and approval-oriented execution models where runtimes expose them
- avoid product defaults that imply autonomous remote operations, automatic pushes, or opaque runtime trust
- keep privacy-sensitive and offline-capable execution paths available through local/runtime-neutral adapters where feasible
- treat MCP and other integration surfaces as governed trust boundaries requiring allowlisting/pinning where relevant

Phase 1 product policies turn these expectations into release-blocking rules:
- `POL-1 No Auto Push`: MACS must never perform `git push`, branch publication, PR merge, release publication, or analogous remote publication automatically. These remain forbidden-in-MVP actions.
- `POL-2 No Autonomous Remote Ops`: MACS must not autonomously invoke remote execution, deployment, issue-tracker mutation, SaaS write APIs, or similar network side effects without explicit governed-surface policy and operator-confirmed action.
- `POL-3 Baseline Diff/Review Gate`: before task close/archive or any action that relaxes a safety boundary, the operator workflow must surface a baseline diff/review checkpoint and record the approval event. Phase 1 may satisfy this with repo-native diff evidence and operator attribution; richer semantic review remains post-MVP.
- `POL-4 Operator Approval Classes`: automatic, policy-automatic, operator-confirmed, guarded, and forbidden actions must remain explicit and inspectable. `task pause`, `task resume`, `task reroute`, `recovery retry`, and `recovery reconcile` are operator-confirmed; `task abort`, `lock override`, and `lock release` are intentionally CLI-visible but guarded in Phase 1.
- `POL-5 Governed Surface Control`: MCP, tool, and network-facing surfaces are deny-by-default unless allowlisted. Production-oriented profiles require adapter pins, and may require version pins and scoped secret references for approved surfaces.
- `POL-6 Local-First Sensitive Routing`: `privacy_sensitive_offline` work must route to local/runtime-neutral workers and forbid networked tools unless policy explicitly relaxes that boundary.

For MVP audit, privacy, and retention policy:
- audit capture should default to controller metadata and state transitions first, not full transcript capture
- prompt, terminal, and tool-output content should be persisted only when needed for operator-visible recovery or debugging and should support redaction or omission by policy
- audit and orchestration state should remain local-host stored by default in MVP
- retention should be intentionally bounded by documented local policy, with short operational retention for rich content and longer retention for minimal event metadata
- operator identity for MVP may be local-session identity rather than enterprise IAM identity, but operator-confirmed actions must still be attributable in the audit trail

### Technical Constraints

This domain has unusually strong control-plane constraints even though it is not industry-regulated.

Key technical constraints are:
- the controller must remain the source of truth for `worker`, `task`, `lease`, `lock`, and `event`
- adapters must be skeptical boundaries rather than authority sources
- local-host-first behavior is the default architecture for MVP
- orchestration semantics must work even when worker signals are partial, stale, or unavailable
- token/session visibility must degrade gracefully because runtimes differ in what they expose
- safe parallelisation must be enforced before throughput optimization
- failure handling must assume recovery is not atomically reversible across runtime sessions and side effects
- operator-facing workflows must not depend on raw tmux inspection for normal orchestration actions
- controller state must be durable enough that restart recovery can reconstruct authoritative `worker`, `task`, `lease`, `lock`, and `event` state without trusting workers to restore ownership truth
- restart recovery must assume partial divergence between persisted controller state and live runtime sessions and must reconcile rather than blindly resume

For Phase 1 restart behavior, the controller should:
- restore persisted authoritative state before accepting new assignments
- re-evaluate live worker/session evidence after boot
- mark uncertain ownership or lock state for reconciliation
- avoid automatically resuming risky work until controller state and live evidence are aligned

### Integration Requirements

The product’s domain is defined partly by its mixed-runtime environment, so integration requirements are first-class product requirements.

Required integration capabilities include:
- tmux-based worker window discovery and management on the local host
- first-class worker support for:
  - Codex CLI
  - Claude Code
  - Gemini CLI
  - one local/runtime-neutral adapter
- runtime/backend policy defaults by workflow class, including at minimum:
  - documentation/context
  - planning docs
  - solutioning
  - implementation
  - review
  - privacy-sensitive/offline execution
- explicit adapter contract expectations for capability metadata, health/freshness, interruptibility, and degradation behavior
- compatibility with repo-local state and targeting conventions already used by MACS

An adapter is considered **first-class** in Phase 1 only if it:
- implements the minimum adapter contract for identity, capability declaration, health/freshness reporting, interruptibility signaling, and degraded-mode behavior
- supports controller-mediated assignment and at least one intervention path appropriate to the runtime
- emits enough routing evidence for safe eligibility decisions
- passes the required adapter validation and failure-mode regression coverage for its supported behaviors

### Risk Mitigations

The domain-specific risks that matter most are operational rather than legal.

Required mitigations:
- split-brain ownership must be detectable and force reconciliation before work continues
- stale-but-plausible runtime evidence must not remain routable indefinitely
- lock and ownership semantics must prevent unsafe concurrent work on protected surfaces
- operator override must be auditable and bounded so it does not silently invalidate controller safety semantics
- adapter inconsistency must be contained through a minimum adapter contract and degradation rules
- recovery workflows must preserve event history and ownership clarity even when runtime sessions degrade or disappear
- regression coverage must include mandatory failure/recovery scenarios as release gates, not optional test depth

## Innovation & Novel Patterns

### Detected Innovation Areas

The product introduces a novel combination of ideas that are usually fragmented across different tool categories:

- a **controller-owned orchestration control plane** rather than runtime-owned or informal coordination
- **mixed-runtime orchestration** as a first-class product behavior, not an accidental side effect of supporting many CLIs
- **evidence-backed routing** that distinguishes controller facts, soft signals, and untrusted adapter claims
- **safe parallelisation** through explicit ownership, leases, locks, and reconciliation rather than relying on post hoc merge cleanup
- **workflow-class-aware runtime defaults** so different classes of work can be routed to different runtime types by policy
- **catastrophe-grade release testing** where split-brain ownership, stale-state routing, lock collisions, and recovery failures are treated as mandatory product behaviors to validate

The core innovation is not a new model or a new agent runtime. It is a new orchestration paradigm for coding agents: governance first, automation second.

### Market Context & Competitive Landscape

The market context reinforces that this direction is genuinely differentiated.

Current platforms and frameworks increasingly support:
- durable state
- workflow graphs
- human checkpoints
- interoperability protocols
- observability

But most do **not** center the product around:
- controller authority over heterogeneous runtime workers
- skeptical adapter trust boundaries
- explicit local-host-first orchestration semantics
- operator-driven intervention and recovery as core product behavior
- release-gated orchestration failure drills

This gives MACS a distinct position in the landscape: not another agent framework, and not purely an enterprise automation suite, but a trustworthy orchestration control plane for real mixed-runtime agent work in repositories.

### Validation Approach

The innovative aspects of this product should be validated through operational proof, not messaging.

Validation should answer:
- Can one controller safely coordinate multiple heterogeneous workers on one local host?
- Can mixed-runtime routing work without silent trust failures?
- Can operator intervention and reconciliation prevent split-brain and stale-state damage?
- Can the system demonstrate safer parallel work than ad hoc multi-agent setups?

Validation mechanisms should include:
- real repo dogfooding in MACS itself
- external early-adopter workflows in real repositories
- mandatory automated failure-mode regression gates
- contributor extension of adapters against a stable minimum contract
- observable operator workflows that can be inspected, replayed, and audited

### Risk Mitigation

The main innovation risks are:
- overclaiming novelty where the market already has adjacent solutions
- building too much architecture before proving the core local-host orchestration loop
- introducing policy and routing complexity faster than users can trust it
- making the adapter model too clever to be extended safely
- failing to prove that "trustworthy orchestration" is materially better than ad hoc multi-agent practice

The mitigations are:
- keep MVP local-host-first and controller-owned
- validate through repeatable orchestrated workflows, not abstract claims
- make failure containment and operator visibility part of the release gate
- keep adapter contracts minimal, explicit, and skeptical
- phase autonomy after authority, evidence, and recovery are proven

## Developer Tool Specific Requirements

### Project-Type Overview

MACS is a developer orchestration tool with a CLI/tmux-first operating model. It is not primarily an SDK, hosted platform, or editor plugin. Its first production-grade release must behave like a trustworthy control plane for repository-local, mixed-runtime agent execution.

The product type imposes three immediate requirements:
- it must be installable and operable by technically capable users without bespoke glue
- it must expose a legible operator control surface for real orchestration work
- it must provide stable extension points for contributors adding runtimes and orchestration logic

### Technical Architecture Considerations

The product architecture must preserve the current brownfield foundations while extending them into a controller-owned orchestration model.

Key project-type architectural requirements:
- preserve the local-host, tmux-based operational model as the Phase 1 foundation
- keep root launchers thin and place orchestration logic in explicit operational modules
- treat the orchestration controller as the product center, with workers and adapters as governed execution backends
- preserve repo-local state and targeting conventions already used by MACS
- ensure the operator-facing surface remains CLI/tmux-native for MVP, with no dependency on a separate hosted control plane

### Language and Runtime Support

The first production-grade release must support a mixed-runtime worker model while keeping product defaults opinionated.

Required support:
- default controller/worker runtime in this repo: `Codex CLI`
- first-class worker runtimes:
  - `Codex CLI`
  - `Claude Code`
  - `Gemini CLI`
  - one local/runtime-neutral adapter
- policy/configuration support for workflow-class-aware runtime defaults:
  - documentation/context
  - planning docs
  - solutioning
  - implementation
  - review
  - privacy-sensitive/offline execution

The product must make runtime capability differences explicit rather than pretending all workers are interchangeable.

### BMAD Execution Policy and Operating Profiles

BMAD execution policy is explicit. Operator-facing BMAD phases map to canonical `workflow_class` values and runtime routing rules:

| BMAD phase | Canonical `workflow_class` | `primary_plus_fallback` | `full_hybrid` | Notes |
| --- | --- | --- | --- | --- |
| Context capture / repo familiarization | `documentation_context` | `codex -> claude` | `codex -> claude` | exclude degraded, unavailable, and quarantined workers |
| Planning artifacts / PRD / story shaping | `planning_docs` | `claude -> codex` | `claude -> codex -> gemini` | optimize for synthesis and critique |
| Solution design / architecture | `solutioning` | `claude -> codex` | `claude -> codex -> gemini` | hybrid profile allows broader alternative exploration |
| Implementation / development | `implementation` | `codex -> claude` | `codex -> claude -> local` | interruptibility required |
| Review / QA / release review | `review` | `codex -> claude` | `codex -> claude -> gemini` | keep review evidence and approval flow explicit |
| Privacy-sensitive / offline work | `privacy_sensitive_offline` | `local only` | `local only` | networked tools forbidden unless policy is explicitly relaxed |

`primary_plus_fallback` is the shipping-default scope-control profile. `full_hybrid` is an explicit opt-in profile that expands the candidate runtime pool without relaxing the safety baseline, operator approvals, or audit requirements.

### Installation and Configuration Model

The tool must be installable and configurable in a way that fits open-source developer workflows.

Installation/configuration requirements:
- runnable from a cloned repo with minimal setup
- repo-local runtime state under explicit project-owned paths
- documented setup flow for local-host orchestration
- documented adapter registration/configuration flow
- documented policy/default configuration for workflow-to-runtime mapping
- no requirement for hosted backend infrastructure in MVP

The configuration model must separate:
- controller defaults
- worker/runtime adapter configuration
- orchestration policy settings
- safety/governance settings
- repo-local state and target metadata
- operating-profile selection layered across controller defaults, routing policy, and governance policy

### Control Surface and Product Interface

The intended MVP interaction model is a local-host operator surface built around CLI/tmux-native orchestration.

Normal Phase 1 operations should be available through MACS-native controller commands or an equivalent controller-owned command surface, with tmux remaining the substrate rather than the primary semantic interface. Raw pane inspection may still be available for diagnosis, but it is not the canonical control path.

The product must expose operator-visible controls for:
- worker discovery/registration
- task creation/assignment
- current ownership and lock inspection
- pause/resume
- reroute
- reconciliation/recovery
- close/archive completed work
- baseline diff/review checkpoint visibility for closeout and safety-relaxing actions
- guarded high-consequence actions such as `abort`, `lock override`, and `lock release`
- event/audit inspection
- token/session-limit visibility where available

This surface must be sufficient for normal orchestration workflows without requiring direct raw tmux manipulation as the primary control path. In Phase 1, `abort`, `lock override`, and `lock release` are intentionally CLI-visible but guarded rather than silently executing under default policy.

### Extension Surface and Adapter Model

Because this is a developer tool, contributor extensibility is part of the product, not just an implementation detail.

The adapter extension model must define:
- minimum adapter contract
- required vs optional runtime signals
- graceful degradation behavior when signals are unavailable
- how adapter capabilities are declared
- how workflow-class defaults and policy rules can reference adapter capabilities
- how adapters are validated before being treated as first-class workers

For Phase 1, "first-class" means contract-complete support, controller-mediated assignment, minimum intervention support appropriate to the runtime, sufficient routing evidence for safe eligibility decisions, and passing required validation coverage for supported behaviors.

The extension surface must favor explicit contracts over hidden conventions.

### Examples and Migration Guidance

The product must help current MACS users move from single-worker supervision to multi-worker orchestration without guessing how the new model maps to the old one.

Required examples/guidance:
- reference orchestration setup in the MACS repo
- example mixed-runtime local-host workflow
- example operator intervention and recovery workflow
- example adapter registration/configuration flow
- migration guidance from current single-controller/single-worker usage to multi-worker orchestration
- contributor guidance for building or extending a runtime adapter

Compatibility and migration guidance must also clarify:
- which current single-worker flows remain supported unchanged in Phase 1
- which flows are superseded by controller-owned orchestration semantics
- whether repo-local state or config migration is required
- that single-worker mode remains a supported operating mode in Phase 1, but is treated as a constrained specialization of the controller-owned orchestration model rather than a separate architecture path

### Implementation Considerations

As a developer tool, MACS will be judged heavily on predictability, inspectability, and ease of adoption.

Implementation priorities should therefore be:
- clear operator semantics before automation depth
- stable adapter contract before broad ecosystem expansion
- explicit state and release-gated failure testing before optimization
- documentation and examples as part of the deliverable, not afterthoughts

This project-type framing keeps the PRD anchored in what users of serious developer tooling actually need: reliable control, understandable behavior, and a practical path to adoption.

## Functional Requirements

### Orchestration Control & Task Lifecycle

- FR1: Operators can start and manage a local-host orchestration session that supervises multiple worker windows under one controller.
- FR2: Operators can create, assign, reassign, pause, resume, abort, reconcile, close, and archive tasks through the MACS orchestration surface.
- FR3: The controller can maintain exactly one current owner for each active task at any given time.
- FR4: The controller can create, renew, expire, revoke, and transfer leases associated with task ownership.
- FR5: Operators can inspect the current lifecycle state of any task, including owner, lease, intervention state, and recent events.
- FR6: The system can prevent conflicting task progression when a task enters intervention hold, reconciliation, or failure review.
- FR6a: The system can represent lease states that distinguish active, paused or suspended, revoked, expired, completed, and historical records.
- FR6b: The system can enforce that a task has zero or one active leases, allowing zero active leases during reconciliation or interrupted reassignment but never more than one.

### Worker Registry & Runtime Management

- FR7: Operators can discover, register, enable, disable, and inspect workers available on the local host.
- FR8: The system can represent workers from Codex CLI, Claude Code, Gemini CLI, and one local/runtime-neutral adapter as first-class workers.
- FR9: Operators can view worker identity, runtime type, availability, interruptibility, freshness, and capability metadata.
- FR10: The system can distinguish required adapter signals from optional runtime-specific enrichment signals.
- FR11: The system can mark workers as healthy, degraded, unavailable, quarantined, or otherwise not eligible for new work based on controller-evaluated evidence.
- FR12: Contributors can add or update runtime adapters against a defined minimum adapter contract without changing controller authority semantics.
- FR12a: The system can classify an adapter as first-class only after required contract support, degraded-mode behavior, intervention support, routing-evidence support, and validation coverage are demonstrated.

### Routing, Policy, and Capability Matching

- FR13: The controller can evaluate eligible workers for a task using policy, capability fit, freshness, health evidence, and current lock state.
- FR14: Operators can define or apply workflow-class-aware runtime defaults for documentation/context, planning docs, solutioning, implementation, review, and privacy-sensitive/offline work.
- FR15: The system can record the routing rationale and evidence associated with each assignment decision.
- FR16: The system can degrade routing behavior safely when some worker signals are unavailable, stale, or untrusted.
- FR17: The system can prevent task assignment to workers that do not satisfy required capabilities, trust boundaries, or governance policy.

### Ownership, Locking, and Safe Parallelisation

- FR18: The controller can create, inspect, update, and release protected-surface locks associated with active work.
- FR19: Operators can view which protected surfaces are currently reserved, blocked, conflicted, or released.
- FR20: The system can prevent unsafe concurrent work when two tasks or workers target the same protected surface.
- FR21: The system can detect duplicate task claims, competing ownership assertions, and split-brain conditions.
- FR22: The system can force reconciliation before conflicting ownership or lock state is allowed to continue.
- FR23: The system can preserve ownership and lock history for audit and post-failure analysis.
- FR23a: The system can support the MVP minimum lock model of file, directory, and policy-defined logical work-surface targets with coarse default granularity.
- FR23b: The system can treat concurrent write-impacting work on the same protected surface as conflicting by default unless explicit policy permits otherwise.

### Monitoring, Intervention, and Recovery

- FR24: The system can monitor worker liveness, session freshness, adapter health, and token or session-limit signals where available.
- FR25: The system can raise visible warnings when worker evidence indicates degraded or unsafe execution conditions.
- FR26: Operators can inspect degraded workers and the evidence supporting the degraded classification.
- FR27: Operators can pause risky work without requiring direct tmux manipulation as the normal control path.
- FR28: Operators can reroute or recover a task from controller-owned state after degradation, failure, or interruption.
- FR29: The system can preserve event history and intervention rationale across recovery and reassignment flows.
- FR30: The system can classify failure conditions such as worker disconnect, stale lease divergence, lock collision, misleading health evidence, and interrupted recovery.

### Auditability, Governance, and Operator Trust

- FR31: The system can maintain an auditable event trail for assignments, lease changes, lock changes, interventions, recoveries, and task closure.
- FR32: Operators can inspect task, worker, lease, lock, and event state without reconstructing orchestration state from raw terminal panes.
- FR33: The system can enforce governance defaults such as skeptical adapter boundaries, bounded-permission execution, and no-auto-push / no-remote-ops style safeguards where relevant.
- FR34: The system can allowlist or pin governed integration surfaces such as MCP-backed tool access where relevant to runtime operation.
- FR35: The system can keep privacy-sensitive or offline-capable workflows routable to appropriate local/runtime-neutral worker options when configured.
- FR35a: The system can apply a decision-rights model that distinguishes automatic controller actions, policy-automatic but operator-visible actions, operator-confirmed actions, and actions forbidden in MVP.
- FR35b: The system can persist audit metadata separately from optional rich content capture and apply policy-based redaction or omission for sensitive content.

### Installation, Configuration, and Adoption

- FR36: Technically capable adopters can install and configure MACS for mixed-runtime local-host orchestration in a real repository without bespoke per-repo glue code beyond documented extension points.
- FR37: Operators can configure controller defaults, worker/runtime adapter settings, orchestration policy settings, safety/governance settings, and repo-local state separately.
- FR38: The product can provide documented setup, onboarding, and migration guidance from current single-controller/single-worker usage to multi-worker orchestration.
- FR39: The product can provide reference examples for mixed-runtime orchestration, intervention and recovery, and adapter registration/configuration.
- FR39a: The product can preserve or clearly document compatibility boundaries for current single-worker usage, including whether state migration or command-surface changes are required.

### Contributor Extension and Validation

- FR40: Contributors can validate adapters and orchestration behavior against a regression suite before runtime support is treated as first-class.
- FR41: The system can expose the minimum adapter contract, declared capabilities, degradation behavior, and validation expectations needed for contributor work.
- FR42: Maintainers can run release-gated orchestration tests covering required happy-path and failure/recovery behaviors.

## Non-Functional Requirements

### Performance

- NFR1: Worker discovery, task inspection, ownership inspection, and lock inspection actions must return operator-visible results within 2 seconds in the reference local-host environment under a 4-worker session.
- NFR2: Normal task assignment, including worker selection, lease creation, lock reservation, and event persistence, must complete within 5 seconds in the reference local-host environment when required worker evidence is available.
- NFR3: Degraded-worker warnings must become visible to the operator within 10 seconds of the controller receiving sufficient evidence to classify the worker as degraded or unsafe.

The timing targets in NFR1-NFR3 assume a reference environment roughly equivalent to:
- one local developer workstation or laptop-class host running a current Unix-like OS
- local tmux-managed workers on the same host
- 4 concurrent workers
- the MACS reference repo or a similarly sized medium engineering repository
- normal local orchestration workloads rather than large-scale batch execution or remote-network-heavy tasks

### Reliability & Recovery

- NFR4: The system must preserve controller-authoritative state for `worker`, `task`, `lease`, `lock`, and `event` across normal orchestration flows, controller restarts, and recoverable worker failures.
- NFR5: The release-gate suite must pass the full mandatory failure-mode matrix for worker disconnect, stale lease/session divergence, duplicate task claim, split-brain ownership, lock collision, misleading health evidence, surfaced budget/session exhaustion, and interrupted recovery before Phase 1 release.
- NFR6: Recovery workflows must preserve audit history and ownership clarity such that no active task can appear to have more than one current owner after reconciliation completes.
- NFR6a: Restart recovery must restore persisted controller state before new assignments, then reconcile live worker/session evidence before risky work is resumed.

### Security & Governance

- NFR7: The controller must treat adapter outputs as bounded evidence rather than trusted truth and must not permit adapters to become the source of truth for ownership, routing, or recovery state.
- NFR8: Product defaults must not initiate autonomous remote operations, automatic pushes, or unapproved external actions as part of normal orchestration behavior.
- NFR9: Governed integration surfaces, including MCP-backed tool access where used, must support allowlisting or equivalent explicit trust controls before being enabled in a production-oriented configuration.
- NFR10: Where runtimes expose approval, sandbox, or permission controls, MACS must preserve and surface those controls rather than bypassing them.

The shipping governance baseline is a repo-local policy surface grounded in `governance-policy.json`, with explicit allowlists, adapter pins, workflow overrides, and audit-content policy. Production-oriented profiles extend that baseline with runtime or model version pins and scoped secret references, but those controls must remain controller-owned and inspectable rather than hidden in adapter code.

For the MVP decision-rights model:
- always automatic: evidence collection, health classification, eligibility filtering, lease expiry evaluation, and warning generation
- policy-automatic but operator-visible: normal task assignment, coarse lock acquisition, worker disable or quarantine drain behavior, and non-destructive throttling actions
- operator-confirmed and implemented: `task pause`, `task resume`, `task reroute`, `recovery retry`, and `recovery reconcile`
- operator-confirmed but guarded in Phase 1: `task abort`, `lock override`, and `lock release`
- forbidden in MVP: automatic pushes, autonomous remote operations outside approved policy, and silent conflict override that bypasses controller auditability

### Observability & Auditability

- NFR11: Every assignment, lease mutation, lock mutation, intervention, recovery action, and task closure must create an audit event with enough context to reconstruct the operator-visible orchestration history.
- NFR12: Event, lease, and lock history must remain inspectable after task completion or failure so maintainers can perform post-run analysis without depending on raw tmux pane history.
- NFR13: Routing decisions must retain enough evidence context that maintainers can understand why a worker was selected, rejected, degraded, or quarantined.
- NFR13a: MVP audit storage must default to local-host retention, capture event metadata by default, and bound or redact rich content capture according to documented local policy.

The minimum event schema for Phase 1 is explicit: `event_id`, `event_type`, `aggregate_type`, `aggregate_id`, `timestamp`, `actor_type`, `actor_id`, `correlation_id`, `causation_id`, `payload`, and `redaction_level`. `payload` must support `affected_refs`, decision metadata, routing or governance references, and governed `audit_content` markers so passing runs are auditable without depending on raw tmux history.

### Usability & Adoption

- NFR14: The intended MVP control surface must support normal orchestration workflows without requiring direct raw tmux manipulation as the primary operating path.
- NFR15: A technically capable adopter must be able to complete documented mixed-runtime local-host setup in a real repository using the supplied configuration and migration guidance, without undocumented repository-specific glue.
- NFR16: The CLI/tmux-native operator experience must preserve clear, consistent terminology for `worker`, `task`, `lease`, `lock`, and `event` across commands, views, and documentation.

### Compatibility & Integration

- NFR17: The MVP must remain local-host-first and must not require hosted backend infrastructure to deliver the Phase 1 orchestration experience.
- NFR18: The product must preserve repo-local state and targeting conventions already used by MACS, including compatibility with existing repository-local orchestration metadata patterns.
- NFR19: Runtime-specific capability differences must degrade gracefully so the absence of optional signals does not break orchestration flows or silently weaken safety semantics.

### Maintainability & Testability

- NFR20: Orchestration logic must remain organized around explicit control-plane entities and state transitions so routing, locking, intervention, and recovery behavior can be tested directly.
- NFR21: Documentation, reference examples, and regression coverage for new orchestration behavior are part of the deliverable and must ship with Phase 1 changes rather than being deferred.
- NFR22: Adapter extension points must remain explicit enough that contributors can implement or update runtime support without reverse-engineering hidden controller assumptions.
