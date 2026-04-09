# Advanced Elicitation Note - PRD

**Source PRD:** `/home/codexuser/macs_dev/_bmad-output/planning-artifacts/prd.md`  
**Generated:** 2026-04-09  
**Purpose:** Mandatory post-PRD advanced elicitation gate for exhaustive BMAD BMM. This note sharpens weaknesses, hidden assumptions, contradictions, and higher-order improvements without replacing the current PRD structure.

## Skill Execution Record

### Step 1: Registry Loading

Loaded:
- `/.agents/skills/bmad-advanced-elicitation/methods.csv`
- `/_bmad/_config/agent-manifest.csv`

### Step 2: Selected Methods

The skill normally presents interactive options. Because this invocation requested a concrete artifact rather than an interactive elicitation session, the gate was executed in artifact mode using a balanced set of five methods selected for this PRD:

1. **First Principles Analysis**
2. **Socratic Questioning**
3. **Pre-mortem Analysis**
4. **Architecture Decision Records**
5. **User Persona Focus Group**

### Step 3: Proceed Decision

`x` applied in artifact mode after analysis. No structural rewrite was performed; the output below is a sharpening note for the existing PRD.

## Executive Assessment

The PRD is strong on product thesis, scope discipline, and safety framing. The main gaps are not strategic; they are operational-definition gaps. Several key ideas are asserted clearly but are not yet pinned down tightly enough to become unambiguous architecture, stories, and release gates.

The most important theme from elicitation is this: the PRD defines **authority** well, but still under-defines **mechanics**. The next refinement should make authority testable by clarifying state durability, lock granularity, lease semantics, intervention permissions, adapter qualification, and release-governance boundaries that depend on external adoption.

## Sharpened Findings

### 1. Release Success Depends on External Validation the Team Does Not Fully Control

**Why this matters:** The measurable outcome requiring "at least one early external adopter workflow in a real repository" is valuable as validation, but risky as a hard Phase 1 release condition because external uptake is partly outside the maintainers' control.

**Weakness exposed:** The PRD currently mixes product validation evidence with core release readiness.

**Recommended update note:** Keep external adopter proof as a success signal, but downgrade it from a hard release gate to either:
- a post-release validation milestone, or
- a conditional launch criterion with an internal substitute such as two distinct real-repo dogfood workflows if no external adopter is available by release cutoff.

**Sections affected:** `Measurable Outcomes`, `Validation Approach`

### 2. "Exactly 1 Active Lease Record" Needs Stronger State Semantics

**Why this matters:** The PRD repeatedly states single-owner authority and exactly one active lease, but lease transfer, renewal, pause, reroute, and reconciliation flows imply temporal overlap risks unless state transitions are defined precisely.

**Weakness exposed:** The PRD does not yet specify whether lease transfer is atomic, whether paused leases remain active, or whether replacement leases can coexist during recovery windows.

**Recommended update note:** Add explicit semantics for:
- `active` vs `historical` lease records
- lease transfer rules
- paused vs suspended vs revoked lease states
- controller behavior during interrupted reassignment
- whether a task may have zero active leases during reconciliation

**Sections affected:** `Technical Success`, `Measurable Outcomes`, `FR3-FR6`, `NFR6`

### 3. Protected-Surface Locking Is Central but Still Too Abstract

**Why this matters:** The product differentiator depends heavily on safe parallelisation, but "protected surface" is not defined tightly enough to support implementation or reliable testing.

**Weakness exposed:** It is unclear whether locks apply to files, directories, task domains, branches, docs, issue IDs, architectural components, or policy-defined logical scopes.

**Recommended update note:** Define a minimum lock model in the PRD:
- lock target types supported in MVP
- default granularity
- conflict resolution rules
- operator override semantics
- whether read/read, read/write, and write/write distinctions exist in MVP

**Sections affected:** `MVP`, `Journey Requirements Summary`, `FR18-FR23`, `NFR20`

### 4. Controller Authority Is Clear, but State Durability Is Not

**Why this matters:** A controller-owned control plane only earns trust if its state survives controller restarts and partial failures in a defined way.

**Weakness exposed:** The PRD speaks about auditability and recovery, but does not explicitly state persistence expectations for controller state after process crash, host reboot, or tmux restart.

**Recommended update note:** Add assumptions and requirements for:
- persistence layer or persistence strategy for `worker`, `task`, `lease`, `lock`, and `event`
- restart recovery behavior
- crash consistency expectations
- restoration order and reconciliation on boot

**Sections affected:** `Technical Constraints`, `Reliability & Recovery`, `Technical Architecture Considerations`

### 5. The MVP Operator Surface Is Intentionally CLI/tmux-Native but Functionally Underspecified

**Why this matters:** The PRD correctly avoids prematurely requiring a GUI, but it does not yet define what constitutes the canonical operator surface for normal workflows.

**Weakness exposed:** "without manual direct tmux surgery" is clear as a negative requirement, but the positive requirement is still soft.

**Recommended update note:** Clarify whether MVP normal operations are performed through:
- dedicated CLI commands,
- a controller REPL/TUI,
- structured tmux panes with command bindings,
- or a hybrid approach.

Also define the minimum required operator-visible views for state inspection and intervention.

**Sections affected:** `MVP`, `Control Surface and Product Interface`, `NFR14`

### 6. Adapter Qualification Criteria Need a More Explicit Bar

**Why this matters:** The PRD uses "first-class worker support" and "first-class runtime adapters" as a major promise, but the acceptance threshold for that label is not explicit enough.

**Weakness exposed:** A runtime could be called first-class while exposing materially different signals, intervention behaviors, or reliability guarantees.

**Recommended update note:** Add a PRD-level definition for when an adapter is considered first-class:
- required contract surfaces
- required test coverage
- required degraded-mode behavior
- minimum intervention support
- minimum routing evidence support

**Sections affected:** `Runtime target`, `Integration Requirements`, `Extension Surface and Adapter Model`, `FR8-FR12`, `FR40-FR42`

### 7. Governance Language Is Strong but Permission Boundaries Are Not Explicit Enough

**Why this matters:** The PRD emphasizes operator oversight, bounded permissions, and no-auto-push behavior, but does not yet specify which actions require explicit operator authorization versus policy-driven automatic controller action.

**Weakness exposed:** Recovery and reroute are described as operator-driven, while routing and some classifications are controller-driven. The action boundary is not crisply defined.

**Recommended update note:** Add a small decision-rights model:
- actions always automatic
- actions policy-automatic but operator-visible
- actions requiring explicit operator confirmation
- actions forbidden in MVP

**Sections affected:** `Compliance & Regulatory`, `Governance defaults`, `FR24-FR35`, `NFR8-NFR10`

### 8. Performance Targets Need a Reference Environment Definition

**Why this matters:** The latency targets are useful, but currently non-reproducible because the reference environment is not described.

**Weakness exposed:** Without a benchmark profile, the targets cannot become reliable acceptance criteria.

**Recommended update note:** Define the reference environment for NFR timing:
- host class
- OS baseline
- tmux/session assumptions
- adapter count
- worker concurrency model
- expected repo size or workload profile

**Sections affected:** `NFR1-NFR3`

### 9. Auditability Requirements Need a Privacy/Retention Counterbalance

**Why this matters:** Strong audit trails are useful, but this product also touches repository content, prompts, and possibly sensitive terminal output.

**Weakness exposed:** The PRD requires rich auditability without stating what must not be persisted, how sensitive content is redacted, or how long records are retained.

**Recommended update note:** Add a baseline audit data policy covering:
- metadata vs content capture
- redaction expectations
- retention expectations
- local-only storage assumptions for MVP

**Sections affected:** `Compliance & Regulatory`, `Auditability, Governance, and Operator Trust`, `NFR11-NFR13`

### 10. Migration Guidance Is Present but Missing Compatibility Boundaries

**Why this matters:** Brownfield adoption will fail if current single-worker users cannot tell what remains compatible, what is deprecated, and what changes behaviorally.

**Weakness exposed:** The PRD requests migration guidance but does not state what compatibility promises the Phase 1 release intends to preserve.

**Recommended update note:** Add a compatibility subsection clarifying:
- what existing workflows remain supported unchanged
- what workflows are superseded
- what config/state migrations are required
- whether single-worker mode remains a first-class path

**Sections affected:** `Project Context`, `Examples and Migration Guidance`, `FR38`

## Contradictions and Tensions to Resolve

### A. Minimal MVP vs Broad "First-Class" Runtime Matrix

There is a delivery tension between keeping MVP small and promising four first-class adapters at once. The PRD should explicitly state whether those adapters must all reach the same operational depth in Phase 1, or whether one or two are full-depth and others are contract-compliant but lower-confidence.

### B. Safe Automation vs Fast Operator Flow

The PRD wants both explicit operator oversight and low-friction orchestration. That is achievable, but only if the product distinguishes routine automatic actions from actions that always require confirmation. Right now that split is implied rather than specified.

### C. CLI/tmux-Native UX vs "No Manual tmux Surgery"

This is directionally consistent, not logically inconsistent, but the PRD should sharpen the boundary: tmux may remain the substrate while the canonical control path must be commandable through MACS semantics rather than pane archaeology.

## Missing Assumptions to Make Explicit

- The controller state store is local and durable enough for restart recovery in MVP.
- Workers are not trusted to mutate authoritative orchestration state directly.
- Adapters may emit claims, but the controller decides final classification and assignment.
- A task may temporarily have zero active leases during reconciliation, but never more than one.
- Lock granularity will intentionally start coarse in MVP.
- Operator identity may initially be local-session identity rather than enterprise IAM.
- External network access and remote side effects are policy-controlled and disabled by default where relevant.

## Higher-Order Improvements

### Improvement 1: Add a Small State Model Appendix

Without changing the PRD structure, add a compact appendix or inline subsection defining the lifecycle states for:
- task
- lease
- worker health
- lock
- intervention

This would materially reduce ambiguity before architecture and story decomposition.

### Improvement 2: Add a Release-Gate Matrix Reference

The PRD repeatedly references mandatory failure-mode coverage. Add a named matrix artifact or appendix reference so the release gate is concrete and traceable rather than implied.

### Improvement 3: Separate Product Truths from Repo-Specific Defaults

The PRD does a good job stating that `Codex CLI` is the default runtime in this repo. Strengthen the distinction between:
- product-wide truths,
- MACS-repo reference defaults,
- user-configurable deployment defaults.

That will prevent future confusion when the product is used outside this repository.

### Improvement 4: Add a "Non-Goals That Protect MVP" Block

The out-of-scope language is solid, but it would be stronger if grouped as explicit non-goals that explain what the team is refusing to solve in Phase 1, especially around:
- distributed orchestration
- autonomous replanning
- semantic merge intelligence
- enterprise IAM
- hosted control planes

## Suggested PRD Update Inserts

These can be applied without changing the document's structure:

1. Add a clarifying note under `Measurable Outcomes` that external adopter evidence is a validation milestone, not necessarily a hard ship blocker.
2. Add a short semantic block under `Technical Success` or `Functional Requirements` defining lease states and the zero-or-one-active-lease rule.
3. Add a short protected-surface definition under `Ownership, Locking, and Safe Parallelisation`.
4. Add persistence and restart-recovery language under `Reliability & Recovery`.
5. Add a canonical MVP operator-surface definition under `Control Surface and Product Interface`.
6. Add first-class adapter qualification criteria under `Extension Surface and Adapter Model`.
7. Add audit metadata/redaction bounds under `Observability & Auditability` or `Compliance & Regulatory`.

## Gate Outcome

**Outcome:** PRD passes the advanced elicitation gate with required follow-up sharpening.

**Reason:** The document is strategically coherent and structured well enough to proceed, but the next planning layer should absorb the clarifications above before architecture and story decomposition are treated as settled.

**Recommended status:** `Proceed with refinement notes attached`
