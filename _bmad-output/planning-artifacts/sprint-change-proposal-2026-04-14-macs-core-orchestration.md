# Sprint Change Proposal - MACS Core Orchestration Correction Pass

Date: 2026-04-14
Scope: core orchestration planning artifacts only
Mode: batch correction pass

## 1. Issue Summary

The MACS core orchestration planning set was directionally correct, but several release-critical concepts were still too soft or too implicit:

- BMAD execution phases were described as workflow classes, but phase-to-runtime routing policy was not explicit enough.
- Safety language existed, but not as first-class product policies.
- Auditability requirements were strong, but the canonical event schema was still underspecified.
- Trust-boundary controls existed, but allowlists, adapter pins, version-pin intent, scoped-secret intent, and governed-surface rules were not framed as one coherent control model.
- Success criteria covered timings and release gates, but not the core operational metrics now needed for trustworthy orchestration.
- Scope control between a conservative shipping profile and a broader hybrid profile was implied rather than defined.

This correction pass uses the existing MACS core artifacts and implemented stories as the authoritative base. It does not restart planning and it does not touch the guided-onboarding track.

## 2. Evidence Base

The change is grounded in the delivered core orchestration work, especially:

- Story 3.1: workflow-aware routing policy
- Story 6.1: durable event trail and inspectors
- Story 6.3: explicit decision rights and guarded actions
- Story 6.4: governed surfaces, privacy routing, and audit-content policy
- Story 7.1: separated config domains
- Story 8.4: release-gate command and auditable evidence package
- `_bmad-output/release-evidence/release-gate-summary.json`
- `_bmad-output/release-evidence/four-worker-dogfood-artifacts/four-worker-dogfood-summary.json`

## 3. Impact Analysis

- Epic impact: no new epics or story IDs are required. The correction clarifies already-delivered scope in Epics 3, 6, 7, and 8.
- Sprint impact: no `sprint-status.yaml` change is required.
- MVP impact: unchanged product boundary, but the shipping-default operating profile is now explicitly `primary_plus_fallback`, and `full_hybrid` is explicitly opt-in.
- Secondary artifacts: the current operator CLI contract and release-evidence package remain compatible with this correction pass and did not require direct edits in this pass.

## 4. Applied Artifact Changes

### Product Brief

Changed:
- generalized mixed-runtime language -> explicit BMAD phase-to-runtime routing intent
- implicit safety posture -> named product-policy stance
- high-level success language -> measurable operational trust outcomes
- open-ended hybrid posture -> explicit default shipping profile plus opt-in hybrid profile

Why:
- the brief needed to state the operating policy, not just the orchestration aspiration

### PRD

Changed:
- added explicit BMAD execution-policy and operating-profile section
- promoted no-auto-push, no autonomous remote ops, diff/review gates, and operator approvals into first-class product policies
- sharpened measurable outcomes with conflict-prevention, stale-lease recovery, reroute success, intervention frequency, false-safe routing, and auditable passing-run targets
- clarified guarded high-consequence actions so Phase 1 docs match the implemented decision-rights model
- made the minimum event schema explicit at the product-requirements level

Why:
- the PRD is the right place to turn implementation-backed governance intent into product contract language

### Architecture

Changed:
- replaced suggestive routing language with explicit BMAD phase-routing and operating-profile rules
- aligned policy examples to the implemented JSON policy shape
- added a concrete event-record schema plus supporting evidence-record schemas
- made decision-rights classes match the implemented controller policy
- expanded trust-boundary controls into a concrete matrix covering adapters, governed surfaces, networked mutation, and scoped secrets
- added operational metrics and evidence sources to the release-validation architecture

Why:
- the architecture needed to move from “auditable and governed” language to inspectable schemas, controls, and measurement paths

## 5. Recommended Path Forward

Selected approach: direct adjustment

Rationale:
- the implementation already supports the core controller-authority, routing, governance, and audit surfaces
- the main issue was planning precision, not implementation invalidation
- rollback is unnecessary and a full replan would create churn without new product value

## 6. Follow-On Observations

- Current implementation already enforces governed-surface allowlists, adapter pins, audit-content redaction or omission, and explicit operator confirmation for reroute, pause or resume, and recovery actions.
- Strict runtime or model version-pin enforcement and scoped-secret plumbing are now explicit planning controls, but they remain follow-on hardening work rather than artifacts this correction pass pretends are already fully implemented.
- Baseline diff/review gating is now an explicit product policy. Current MACS behavior already preserves operator attribution and event history; dedicated diff-capture automation remains follow-on implementation hardening if maintainers want enforcement beyond the current controller and audit workflow.

## 7. Scope Classification and Handoff

Scope classification: Moderate

Handoff:
- PM / Architect / SM only if maintainers want backlog follow-up for version-pin enforcement, scoped-secret handling, or automated diff/review capture
- no immediate epic resequencing or sprint-status rewrite is required

## 8. Completion Statement

The correction pass is complete for the core orchestration track. The planning artifacts now describe explicit BMAD routing policy, first-class product safety policy, a concrete audit schema, clearer trust boundaries, measurable trust metrics, and explicit operating profiles without restarting the MACS plan.
