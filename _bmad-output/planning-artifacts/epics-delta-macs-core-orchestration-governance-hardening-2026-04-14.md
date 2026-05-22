---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/product-brief-macs_dev.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/prd.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/architecture.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-14-macs-core-orchestration.md
---

# macs_dev - Governance Hardening Backlog Delta

## Overview

This document is a focused addendum for follow-on governance hardening work implied by the corrected MACS core orchestration planning set. It does not rewrite `_bmad-output/planning-artifacts/epics.md`, it does not reopen the completed original orchestration sprint, and it does not touch the guided-onboarding initiative.

The corrected planning set does not require retroactive changes to the shipped core orchestration epic/story IDs, but it does explicitly reserve three governance controls as follow-on implementation hardening: strict version-pin enforcement, scoped-secret handling, and stronger baseline diff/review capture or enforcement. Those items are only partially represented by the current backlog through broad governance and release-evidence stories, so a separate delta backlog is warranted rather than treating this as documentation-only precision.

Tracker recommendation: keep the completed orchestration sprint tracker unchanged. If maintainers decide to execute this addendum, create a separate sprint tracker for governance hardening follow-on work rather than editing the historical orchestration sprint status.

## Requirements Inventory

### Functional Requirements

DFR1: Operators can define controller-owned `surface_version_pins` for approved governed surfaces, runtime or model identities, workflow classes, and operating profiles without relying on hidden adapter conventions.
DFR2: The controller can enforce configured version pins during worker registration, routing eligibility, and governed-surface invocation, rejecting mismatches or missing version evidence with explicit operator-visible reasons and audit events.
DFR3: Operators can define `secret_scopes` that bind secret references to approved adapter, workflow, surface, and operating-profile contexts without exposing raw secret values through controller state or events.
DFR4: The controller can resolve only in-scope secret references for approved governed actions, block out-of-scope or missing secret use, and preserve audit-safe evidence for secret-mediated decisions.
DFR5: Operators can capture a baseline diff/review checkpoint tied to task, actor, timestamp, affected refs, and repo state before task close/archive or any action that relaxes a safety boundary.
DFR6: The controller can enforce `POL-3` by blocking close/archive and safety-relaxing actions until a valid diff/review checkpoint and attributable approval event exist.
DFR7: Maintainers can inspect version-pin decisions, secret-scope enforcement, and diff/review checkpoints through audit and release-evidence surfaces without reconstructing the control history manually.

### NonFunctional Requirements

DNFR1: Version-pin evaluation must remain controller-owned, deterministic, and inspectable; governed actions must not silently fall back to unpinned runtime or model versions when a pinning rule applies.
DNFR2: Raw secret values must never be persisted in controller events, policy snapshots, diff/review artifacts, or release-evidence outputs; only secret reference metadata and redaction markers may be retained.
DNFR3: Diff/review checkpoints must capture enough structured context to support attribution and replayability, including actor identity, timestamp, baseline repo state, affected refs, and linked decision events.
DNFR4: If version evidence is missing, secret scope is ambiguous, or diff/review evidence is absent or stale, MACS must fail closed for the governed action and provide a clear remediation path.
DNFR5: Automated validation and release evidence must cover passing and failing cases for version-pin drift, out-of-scope secret use, missing diff checkpoints, and stale or mismatched review checkpoints.

### Additional Requirements

- Extend the governance-policy surface with first-class `surface_version_pins` and `secret_scopes` fields while keeping those controls repo-local, controller-owned, and visible in policy snapshots.
- Treat governed-surface version metadata as bounded evidence: missing or stale version signals must block or quarantine governed actions when pinning policy applies.
- Model secret handling around scoped secret references rather than secret values; scope selectors must support at least adapter, workflow class, governed surface, and operating profile.
- Persist diff/review checkpoints as referenced evidence linked to canonical decision events so close/archive and guarded actions do not depend on raw tmux history for justification.
- Keep this addendum limited to post-correction governance hardening. Do not renumber or reopen the completed core orchestration epic set and do not mix in guided-onboarding backlog work.

### UX Design Requirements

Not applicable for this delta pass. No separate UX design document was included in the requested source-of-truth set.

### FR Coverage Map

DFR1: Epic 1 - Govern Approved Surface Versions and Secret Access
DFR2: Epic 1 - Govern Approved Surface Versions and Secret Access
DFR3: Epic 1 - Govern Approved Surface Versions and Secret Access
DFR4: Epic 1 - Govern Approved Surface Versions and Secret Access
DFR5: Epic 2 - Prove and Enforce Baseline Review Before Risky Completion
DFR6: Epic 2 - Prove and Enforce Baseline Review Before Risky Completion
DFR7: Epic 2 - Prove and Enforce Baseline Review Before Risky Completion

## Epic List

### Epic 1: Govern Approved Surface Versions and Secret Access
Maintainers can trust that production-oriented governance profiles only use explicitly pinned runtime or model surfaces and least-privilege secret references, with all decisions remaining controller-owned and inspectable.
**FRs covered:** DFR1, DFR2, DFR3, DFR4

### Epic 2: Prove and Enforce Baseline Review Before Risky Completion
Operators and maintainers can capture and enforce attributable diff/review checkpoints before closing work or relaxing safety boundaries, and can verify that governance hardening is present in audit and release evidence.
**FRs covered:** DFR5, DFR6, DFR7

## Epic 1: Govern Approved Surface Versions and Secret Access

Maintainers can trust that production-oriented governance profiles only use explicitly pinned runtime or model surfaces and least-privilege secret references, with all decisions remaining controller-owned and inspectable.

### Story 1.1: Model controller-owned surface version pins

As a maintainer,
I want inspectable `surface_version_pins` rules in governance policy,
So that approved surfaces and runtime or model identities are pinned by policy instead of adapter convention.

**Requirements:** DFR1; DNFR1

**Acceptance Criteria:**

**Given** a repository with governance policy for governed surfaces
**When** I define or inspect a production-oriented operating profile
**Then** MACS supports `surface_version_pins` keyed by explicit surface, adapter, workflow-class, and operating-profile selectors
**And** policy snapshots preserve the effective pin set with versioned audit references

**Given** an existing configuration that uses allowlists and adapter pins only
**When** no `surface_version_pins` are configured
**Then** existing governance behavior remains compatible without inventing implicit version-pin rules
**And** the operator-facing policy view makes the absence of version pins explicit

### Story 1.2: Reject pin drift during eligibility and governed-surface use

As an operator,
I want MACS to block or quarantine governed actions when required version pins do not match live evidence,
So that production-oriented profiles do not silently drift.

**Requirements:** DFR2; DNFR1, DNFR4

**Acceptance Criteria:**

**Given** a worker registration, routing decision, or governed-surface action under a profile with version-pin requirements
**When** the reported runtime or model version does not match the configured pin
**Then** MACS rejects or quarantines the action with an explicit mismatch reason and affected selector context
**And** the decision is recorded as audit evidence rather than treated as an eligible success

**Given** a worker or surface subject to version-pin policy
**When** version evidence is missing, stale, or not trustworthy enough for evaluation
**Then** MACS fails closed for the governed action
**And** the operator receives a remediation path instead of a silent fallback to unpinned execution

### Story 1.3: Define scoped secret references without persisting secret material

As a maintainer,
I want `secret_scopes` to bind secret references to allowed execution contexts,
So that secret access stays least-privilege and inspectable.

**Requirements:** DFR3; DNFR2

**Acceptance Criteria:**

**Given** a governed surface that may require credentials or tokens
**When** I configure or inspect governance policy
**Then** MACS supports `secret_scopes` that bind secret references to explicit adapter, workflow-class, surface, and operating-profile selectors
**And** controller-visible policy state stores only secret reference metadata and redaction markers rather than raw secret values

**Given** a policy snapshot or governance inspection view
**When** I review configured secret scopes
**Then** I can see which secret references are eligible for which contexts
**And** no inspection path reveals secret values directly

### Story 1.4: Enforce scoped-secret resolution at action time

As an operator,
I want MACS to resolve only in-scope secret references for approved governed actions,
So that out-of-scope secret use is blocked and attributable.

**Requirements:** DFR4; DNFR2, DNFR4

**Acceptance Criteria:**

**Given** a task action that targets a governed surface requiring a secret reference
**When** the controller authorizes execution
**Then** MACS resolves only secret references whose scopes match the effective adapter, workflow-class, surface, and operating-profile context
**And** successful execution records only non-sensitive reference identifiers and decision links in audit output

**Given** a governed action with a missing or out-of-scope secret reference
**When** the controller evaluates the request
**Then** MACS blocks the action with an audit-safe rejection reason
**And** no secret material is emitted into events, snapshots, or release evidence

## Epic 2: Prove and Enforce Baseline Review Before Risky Completion

Operators and maintainers can capture and enforce attributable diff/review checkpoints before closing work or relaxing safety boundaries, and can verify that governance hardening is present in audit and release evidence.

### Story 2.1: Capture attributable diff/review checkpoints

As a maintainer,
I want a baseline diff/review checkpoint artifact tied to task and action context,
So that close/archive and guarded actions have inspectable preconditions.

**Requirements:** DFR5; DNFR3

**Acceptance Criteria:**

**Given** a task that is ready for close/archive or a request to perform a safety-relaxing action
**When** I invoke the review-checkpoint flow
**Then** MACS captures repo-native diff/review evidence with actor identity, timestamp, affected refs, and baseline repo state
**And** the checkpoint is linked to the relevant task or decision context as referenced evidence

**Given** a recorded diff/review checkpoint
**When** I inspect audit history later
**Then** I can trace the checkpoint to the related action request and decision event
**And** the justification does not depend on raw tmux pane history alone

### Story 2.2: Enforce the diff/review gate before closeout or safety relaxation

As an operator,
I want MACS to block risky closeout paths until a valid checkpoint exists,
So that `POL-3` is enforced instead of documented only.

**Requirements:** DFR6; DNFR3, DNFR4

**Acceptance Criteria:**

**Given** a task close/archive request or a guarded action that relaxes a safety boundary
**When** no current diff/review checkpoint exists
**Then** MACS refuses the action with a clear explanation of the missing checkpoint requirement
**And** the operator is directed to the checkpoint flow rather than allowed to bypass policy silently

**Given** an existing diff/review checkpoint
**When** the checkpoint no longer matches the relevant repo state, task scope, or action context
**Then** MACS treats the checkpoint as stale or invalid
**And** the action remains blocked until a fresh checkpoint and attributable approval event are recorded

### Story 2.3: Include governance hardening evidence in inspectors and release review

As a maintainer,
I want version-pin decisions, secret-scope enforcement, and diff/review checkpoints to appear in audit and release evidence,
So that governance hardening can be validated without manual reconstruction.

**Requirements:** DFR7; DNFR5

**Acceptance Criteria:**

**Given** governance hardening is enabled in validation, dogfood, or release-review flows
**When** I inspect history or run the release-gate summary
**Then** MACS exposes machine-readable and human-readable evidence for version-pin acceptance or rejection, secret-scope acceptance or rejection, and diff/review checkpoint enforcement
**And** the evidence links back to the relevant policy snapshot, task or action, and canonical decision events

**Given** automated validation for the governance-hardening delta
**When** the regression and release-gate suites run
**Then** they cover passing and failing cases for version-pin drift, out-of-scope secret use, missing checkpoints, and stale or mismatched checkpoints
**And** a passing run produces attributable evidence without leaking secret material
