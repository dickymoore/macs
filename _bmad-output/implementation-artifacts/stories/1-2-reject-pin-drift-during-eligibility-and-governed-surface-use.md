# Story 1.2: Reject pin drift during eligibility and governed-surface use

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,  
I want MACS to block or quarantine governed actions when required version pins do not match live evidence,  
so that production-oriented profiles do not silently drift.

## Acceptance Criteria

1. Given a worker registration, routing decision, or governed-surface action under a profile with version-pin requirements, when the reported runtime or model version does not match the configured pin, then MACS rejects or quarantines the action with an explicit mismatch reason and affected selector context, and the decision is recorded as audit evidence rather than treated as an eligible success.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-12-reject-pin-drift-during-eligibility-and-governed-surface-use] [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/planning-artifacts/architecture.md#routing-outcome-contract] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]
2. Given a worker or surface subject to version-pin policy, when version evidence is missing, stale, or not trustworthy enough for evaluation, then MACS fails closed for the governed action, and the operator receives a remediation path instead of a silent fallback to unpinned execution.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-12-reject-pin-drift-during-eligibility-and-governed-surface-use] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#additional-requirements] [Source: _bmad-output/planning-artifacts/architecture.md#evidence-envelope] [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-14-macs-core-orchestration.md#follow-on-observations]

## Tasks / Subtasks

- [x] Add one controller-owned version-pin evidence evaluator that reuses Story 1.1 selector semantics instead of re-deriving them in each call site. (AC: 1, 2)
  - [x] Extend `tools/orchestration/policy.py` with a helper that combines `resolve_surface_version_pins(...)`, worker freshness, adapter evidence, and current selector context (`surface_id`, `adapter_id`, `workflow_class`, `operating_profile`) into one structured result for enforcement and inspection.  
        [Source: tools/orchestration/policy.py] [Source: _bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md#completion-notes-list]
  - [x] Return stable machine-readable failure reasons that fit the existing routing style, such as `surface_version_pin_mismatch:<surface>`, `surface_version_evidence_missing:<surface>`, `surface_version_evidence_stale:<surface>`, and `surface_version_evidence_untrusted:<surface>`, along with structured expected-vs-observed selector details for audit output.  
        [Source: tools/orchestration/routing.py] [Source: _bmad-output/planning-artifacts/architecture.md#routing-outcome-contract] [Inference from: existing governed-surface reason strings in tools/orchestration/policy.py and tools/orchestration/routing.py]
  - [x] Keep the evidence summary bounded and audit-safe: preserve expected and observed runtime/model identities, confidence, freshness, and `source_ref`, but do not persist raw pane captures or adapter-specific terminal transcripts.  
        [Source: _bmad-output/planning-artifacts/architecture.md#evidence-envelope] [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records] [Source: _bmad-output/planning-artifacts/prd.md#security--governance]

- [x] Enforce version pins in the current controller-owned eligibility paths rather than inventing a new governance subsystem. (AC: 1, 2)
  - [x] Update worker registration handling so profile-wide or workflow-agnostic version pins that are already decidable at registration time can reject or quarantine unsafe workers before they are promoted to normal ready-state use.  
        [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/workers.py] [Source: _bmad-output/planning-artifacts/prd.md#worker-registry--runtime-management] [Inference from: workflow-specific selectors are not fully known during `worker register`]
  - [x] Update task routing and assignment evaluation so workers with applicable governed-surface pins are probed for live runtime/model evidence and become ineligible when the evidence mismatches, is missing, is stale, or lacks sufficient trust for the required pin.  
        [Source: tools/orchestration/routing.py] [Source: tools/orchestration/tasks.py] [Source: _bmad-output/planning-artifacts/architecture.md#routing-and-policy-engine] [Source: _bmad-output/planning-artifacts/architecture.md#routing-outcome-contract]
  - [x] Treat the current worker registration plus routing or assignment flow as the enforcement surface for this story; do not create a separate generic governed-action executor or a parallel policy engine just for version pins.  
        [Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape] [Inference from: tools/orchestration/cli/main.py, tools/orchestration/routing.py, and tools/orchestration/tasks.py]

- [x] Reuse existing probe and health seams so MACS stays controller-owned and fail-closed when evidence quality is weak. (AC: 1, 2)
  - [x] Reuse `adapter.probe(worker)` as the live evidence seam and normalize its facts, signals, or claims instead of scraping runtime state through a new side channel.  
        [Source: tools/orchestration/adapters/base.py] [Source: tools/orchestration/adapters/codex.py] [Source: _bmad-output/planning-artifacts/architecture.md#runtime-adapter-architecture]
  - [x] Only probe when relevant pins can apply, so ordinary unpinned routing stays on the current low-overhead path. Determine applicability from Story 1.1 policy selectors before triggering live evidence collection.  
        [Source: tools/orchestration/policy.py] [Source: _bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md#technical-requirements] [Inference from: `routing.py` currently evaluates workers without live probe calls]
  - [x] If automatic quarantine is used for proven drift, reuse the existing worker quarantine or health-classification paths and freeze active tasks through the current controller-owned drain behavior rather than mutating worker state ad hoc.  
        [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/health.py] [Source: _bmad-output/planning-artifacts/prd.md#security--governance]

- [x] Surface version-pin enforcement outcomes through existing audit and inspect seams. (AC: 1, 2)
  - [x] Extend routing-decision rationale, rejected-worker context, and operator-facing blocker text so maintainers can tell whether a candidate failed because of pin mismatch, missing evidence, stale evidence, or insufficient confidence, without reconstructing the decision from raw tmux history.  
        [Source: tools/orchestration/routing.py] [Source: tools/orchestration/tasks.py] [Source: _bmad-output/planning-artifacts/prd.md#observability--auditability]
  - [x] Reuse the existing governance summary surfaces in `worker inspect`, `task inspect`, `adapter inspect`, or `setup check` only as needed to keep selector context and remediation visible; do not create a separate version-pin dashboard in this story.  
        [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/setup.py] [Source: _bmad-output/planning-artifacts/architecture.md#ux-backing-requirements]
  - [x] Preserve routing and worker audit evidence in the existing `routing_decisions`, event records, and optional snapshot references rather than inventing a second storage silo for version-pin enforcement.  
        [Source: tools/orchestration/store.py] [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records]

- [x] Add focused regression coverage for mismatched, missing, stale, and low-trust version evidence without regressing Story 1.1 inspection behavior or Story 6.4 governed-surface enforcement. (AC: 1, 2)
  - [x] Extend `tools/orchestration/tests/test_task_lifecycle_cli.py` with assignment failures that preserve routing context for version-pin mismatch and fail-closed evidence gaps.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md#testing-requirements]
  - [x] Add or extend worker registration and governance-inspection tests in `tools/orchestration/tests/test_setup_init.py` and `tools/orchestration/tests/test_inspect_context_cli.py` so applicable pins, observed evidence, and remediation paths remain inspectable in JSON and human-readable modes.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: _bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md#testing-requirements]
  - [x] Keep explicit no-regression coverage for the cases where `surface_version_pins` is absent or no pin applies, so current allowlist and adapter-pin behavior continues unchanged.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: _bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md#implementation-guardrails]

- [x] Keep Story 1.2 bounded to enforcement of the existing version-pin model. (AC: 1, 2)
  - [x] Do not redesign `surface_version_pins`, policy snapshots, or operating-profile semantics unless an additive evidence-status field is required for enforcement or inspection clarity.  
        [Source: _bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md#completion-notes-list] [Source: _bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md#implementation-guardrails]
  - [x] Do not introduce `secret_scopes`, secret resolution, diff/review checkpoints, release-evidence expansion, or remote policy sources in this story; those belong to later governance-hardening stories.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-13-define-scoped-secret-references-without-persisting-secret-material] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#epic-2-prove-and-enforce-baseline-review-before-risky-completion]

- [x] Address post-review Story 1.2 findings without broadening the governance-hardening scope. (AC: 1, 2)
  - [x] Require explicit live runtime probe evidence for runtime-only pin evaluation and stop treating cached worker metadata as trusted runtime identity.  
        [Source: tools/orchestration/policy.py] [Source: tools/orchestration/adapters/base.py] [Source: tools/orchestration/tests/test_setup_init.py]
  - [x] Record registration-time blocked promotion through explicit quarantine audit evidence instead of success-shaped registration audit labels.  
        [Source: tools/orchestration/workers.py] [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/tests/test_setup_init.py]

## Dev Notes

### Story Intent

This story is the enforcement follow-on to Story 1.1. Story 1.1 made `surface_version_pins` controller-owned, inspectable, and operating-profile-aware; Story 1.2 turns that same model into fail-closed eligibility behavior for the existing worker-registration and routing seams, without pretending secrets, release evidence, or diff/review gates are already implemented.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-12-reject-pin-drift-during-eligibility-and-governed-surface-use]  
[Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-14-macs-core-orchestration.md#follow-on-observations]  
[Source: _bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md#completion-notes-list]

### Governance-Hardening Lane Boundaries

- Use only `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml` for lane tracking.
- Do not edit the historical orchestration tracker at `_bmad-output/implementation-artifacts/sprint-status.yaml`.
- Do not edit the guided-onboarding tracker at `_bmad-output/implementation-artifacts/sprint-status-macs-guided-onboarding.yaml`.
- Treat this as follow-on governance hardening implied by the 2026-04-14 correction pass, not a reopening of the completed orchestration sprint and not part of guided onboarding.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#overview]  
[Source: _bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml]

### Previous Story Intelligence

- Story 1.1 already added controller-owned `operating_profile`, `surface_version_pins`, `resolve_surface_version_pins(...)`, and active governance-snapshot read models. Reuse those helpers instead of re-deriving selector matching inside routing or CLI handlers.
- Story 1.1 also wired the normalized pin summary into `macs setup check` and `macs adapter inspect`, including stale-vs-live snapshot visibility. Story 1.2 should preserve those read-side semantics and layer enforcement on top of the live governance policy, not the snapshot payload alone.
- Story 1.1 explicitly deferred routing rejection, governed-surface blocking, stale or missing version-evidence handling, secret scopes, and release-evidence expansion. Those deferred items are the core scope for Story 1.2 and later governance-hardening stories.

[Source: _bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md#completion-notes-list]  
[Source: _bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md#implementation-guardrails]

### Brownfield Continuity

- `tools/orchestration/policy.py` already owns governed-surface allowlists, adapter pins, workflow overrides, version-pin selector resolution, and governance snapshot lookups, but current worker governance still ends at allowlist and adapter-pin evaluation.
- `tools/orchestration/routing.py` already persists `rejected_workers`, `reasons`, governance summaries, blocking conditions, and next actions through `routing.decision_recorded`; the safest enforcement path is additive to that existing result model.
- `tools/orchestration/tasks.py` already persists failed or blocked assignment context without inventing a second action envelope, so version-pin failures should flow through the same task assignment error shape.
- `handle_worker_command(... register ...)` currently checks adapter enablement and then promotes the worker into ready-state registration without consulting version pins or live probe evidence.
- Existing inspect paths already have controller-owned seams for governance context: `worker inspect`, `task inspect`, `adapter inspect`, and `setup check`.

[Source: tools/orchestration/policy.py]  
[Source: tools/orchestration/routing.py]  
[Source: tools/orchestration/tasks.py]  
[Source: tools/orchestration/cli/main.py]  
[Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md]

### Version-Evidence Baseline

- `adapter.probe(worker)` is the current live evidence seam. It already returns bounded facts, signals, or claims with `observed_at`, `freshness_seconds`, `confidence`, and `source_ref`.
- `CodexAdapter.probe()` currently emits a `permission_surface` claim containing `approval_policy`, `sandbox`, and `model`, with `medium` confidence only when the CLI flags are visible in pane capture and `low` confidence otherwise.
- Other adapters currently degrade safely and may not emit runtime or model identity at all. When a version pin applies, that absence must become a fail-closed governance result rather than a silent pass.
- Worker freshness already has controller-owned semantics in routing and health classification (`>60s` stale for routing, `>600s` unavailable in health classification). Version-evidence staleness should align with those existing freshness concepts instead of creating a hidden second clock.

[Source: tools/orchestration/adapters/base.py]  
[Source: tools/orchestration/adapters/codex.py]  
[Source: tools/orchestration/routing.py]  
[Source: tools/orchestration/health.py]  
[Source: tools/orchestration/tests/test_setup_init.py]

### Technical Requirements

- Keep version-pin enforcement controller-owned and repo-local; adapters may supply evidence, but they must not become the authority for whether a worker or governed action is policy-compliant.
- If an applicable pin expects a runtime or model identity and the observed value is absent, unknown, stale, or not trustworthy enough, fail closed. Do not silently fall back to allowlists, adapter pins, or successful eligibility.
- Registration-time checks should only enforce pins that are already decidable without task workflow context; workflow-specific pins belong in routing or assignment where `workflow_class` is known.
- Reuse the shipping operating-profile vocabulary from Story 1.1: `primary_plus_fallback` remains the default and `full_hybrid` remains opt-in.
- Keep machine-readable reasons stable and selector-specific so existing routing and inspect surfaces can remain compact while still explaining why a worker was rejected or quarantined.
- Keep implementation Python-stdlib-only and preserve the current CLI and JSON envelope patterns.

[Source: _bmad-output/planning-artifacts/prd.md#bmad-execution-policy-and-operating-profiles]  
[Source: _bmad-output/planning-artifacts/prd.md#security--governance]  
[Source: _bmad-output/planning-artifacts/architecture.md#operating-profiles]  
[Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]  
[Source: _bmad-output/project-context.md#technology-stack--versions]

### Architecture Compliance

- Preserve the existing write model: read authoritative state, validate policy, persist routing or worker evidence summaries and decision records, then perform side effects or state transitions.
- Use the existing routing outcome contract to keep ranked candidates, rejected workers, rejection reasons, and governance-policy references inspectable after failed eligibility.
- Keep evidence bounded as fact, signal, or claim with explicit freshness and confidence rather than turning adapter outputs into raw trusted truth.
- Prefer compact CLI summaries that show controller truth first, then the bounded version-pin evidence summary or remediation path when a worker is blocked.

[Source: _bmad-output/planning-artifacts/architecture.md#write-model]  
[Source: _bmad-output/planning-artifacts/architecture.md#routing-outcome-contract]  
[Source: _bmad-output/planning-artifacts/architecture.md#evidence-envelope]  
[Source: _bmad-output/planning-artifacts/architecture.md#ux-backing-requirements]

### Suggested Implementation Shape

- Add a small evaluator in `tools/orchestration/policy.py` that accepts the live governance policy, effective selector context, worker freshness, and adapter evidence, and returns:
  - applicable pins
  - observed runtime and model evidence
  - structured mismatch or missing-evidence reasons
  - an overall `eligible` or `blocked` outcome
- Extend `evaluate_worker_governance(...)` to consume that helper after current allowlist or adapter-pin checks, so version-pin decisions stay in one controller-owned governance summary instead of being split between multiple modules.
- In `routing.py`, determine whether pins can apply before probing workers. If none can apply, keep the current routing path. If pins do apply, probe only those candidate workers and thread the resulting version-pin outcome into rejected-worker reasons and routing rationale.
- In `cli/main.py` or `workers.py`, add a narrow registration preflight that can reject or quarantine workers for profile-wide or workflow-agnostic pin drift without trying to solve workflow-specific routing at registration time.
- Reuse existing inspection helpers only where needed to expose version-pin outcomes and remediation commands such as reviewing the active governance policy or probing the worker explicitly.

[Inference from: tools/orchestration/policy.py, tools/orchestration/routing.py, tools/orchestration/workers.py, and tools/orchestration/cli/main.py]  
[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]

### File Structure Requirements

- Primary implementation files for this story:
  - `tools/orchestration/policy.py`
  - `tools/orchestration/routing.py`
  - `tools/orchestration/tasks.py`
  - `tools/orchestration/workers.py`
  - `tools/orchestration/cli/main.py`
  - `tools/orchestration/tests/test_task_lifecycle_cli.py`
  - `tools/orchestration/tests/test_setup_init.py`
  - `tools/orchestration/tests/test_inspect_context_cli.py`
- Optional touch points only if required by the final enforcement shape:
  - `tools/orchestration/health.py`
  - `tools/orchestration/store.py`
  - `tools/orchestration/adapters/base.py`
  - `tools/orchestration/adapters/codex.py`
- Avoid broadening into release-gate, secret-handling, or a new controller module unless a tiny helper extraction becomes materially clearer than extending the current governance seams.

[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]  
[Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md]

### Testing Requirements

- Extend the existing governance and lifecycle regression seams instead of creating a governance-hardening-only harness.
- Add explicit coverage for:
  - worker registration rejection or quarantine when a registration-time-applicable pin mismatches
  - task assignment rejection when version evidence mismatches, is missing, is stale, or is insufficiently trustworthy
  - no-regression behavior when no `surface_version_pins` are configured or when a configured pin does not apply to the current selector context
  - inspection or blocker output that preserves selector context and remediation guidance
- Before marking the implementation done, run the focused controller CLI regressions plus full orchestration unittest discovery.

[Source: _bmad-output/project-context.md#testing-rules]  
[Source: _bmad-output/planning-artifacts/architecture.md#testing-principles]  
[Source: _bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md#testing-requirements]

### Git Intelligence Summary

- Recent committed history still centers MACS changes in controller-owned bootstrap, policy, routing, and CLI seams, which is the safest path for Story 1.2.
- The current working tree already contains uncommitted guided-onboarding and documentation edits in `tools/orchestration/cli/main.py`, `tools/orchestration/setup.py`, `tools/orchestration/tests/test_setup_init.py`, `README.md`, and several docs files.
- Story 1.2 is likely to touch some of those same shared seams plus `tools/orchestration/policy.py`. Work with those edits and do not revert or overwrite unrelated in-flight changes while implementing the governance-hardening slice.

[Source: git log --oneline -5]  
[Inference from current git status]

### Implementation Guardrails

- Do not redesign the `surface_version_pins` schema or duplicate Story 1.1 selector logic.
- Do not add a second governance-policy file, remote version registry, or adapter-owned policy evaluator.
- Do not persist raw pane captures, secret material, or broad runtime transcripts as part of version-pin enforcement evidence.
- Do not broaden into `secret_scopes`, secret resolution, diff/review checkpoints, or release-evidence expansion.
- Do not modify the historical orchestration sprint tracker or the guided-onboarding tracker as part of the implementation.
- Do not revert unrelated working-tree changes in shared CLI, setup, policy, or docs files.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#additional-requirements]  
[Source: _bmad-output/project-context.md#development-workflow-rules]

### Project Structure Notes

- This remains a brownfield, shell-first, Python-stdlib-only orchestration controller.
- The governance-hardening lane is intentionally separate from the historical orchestration sprint and the guided-onboarding initiative, even though all story files live in the shared stories directory.
- The safest implementation path is a narrow extension of the current policy, routing, worker, and inspect seams so version-pin enforcement stays inspectable and controller-owned without reopening the planning-correction or onboarding tracks.

[Source: _bmad-output/project-context.md#development-workflow-rules]  
[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#overview]

### References

- `_bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md`
- `_bmad-output/planning-artifacts/product-brief-macs_dev.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-14-macs-core-orchestration.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`
- `_bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md`
- `_bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md`
- `_bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md`
- `tools/orchestration/policy.py`
- `tools/orchestration/routing.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/workers.py`
- `tools/orchestration/health.py`
- `tools/orchestration/store.py`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/adapters/codex.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add one controller-owned version-pin evidence evaluator that reuses Story 1.1 policy selectors and normalizes bounded runtime or model evidence into stable enforcement results.
- Thread that evaluator into worker registration and task routing so pin drift becomes a fail-closed eligibility decision with inspectable reasons and audit evidence.
- Extend existing inspect surfaces only as needed for remediation clarity, then lock the behavior down with targeted governance and lifecycle regression coverage plus full orchestration unittest validation.

### Debug Log References

- Story authored with `bmad-create-story`.
- Authoritative tracker: `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`.
- Planning sources reviewed: the governance-hardening delta epics file, corrected product brief, corrected PRD, corrected architecture, and the 2026-04-14 sprint change proposal.
- Prior governance-hardening context reviewed: Story 1.1 completion notes and guardrails.
- Brownfield seams reviewed: `policy.py`, `routing.py`, `tasks.py`, `workers.py`, `cli/main.py`, `health.py`, `store.py`, base adapter evidence contracts, Codex probe behavior, and the current governance-related tests.
- Git context reviewed: `git log --oneline -5` and the current `git status --short`.
- Review follow-up findings addressed: runtime-only pins now require live runtime probe evidence, and registration-time governance quarantine now writes explicit quarantine audit events.
- External web research was not required because this story is repo-local governance enforcement work, not third-party API integration.

### Test Record

- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli` (pass, 51 tests)
- `python3 -m unittest tools.orchestration.tests.test_setup_init` (pass, 66 tests)
- `python3 -m unittest tools.orchestration.tests.test_inspect_context_cli` (pass, 44 tests)
- `python3 -m unittest discover -s tools/orchestration/tests` (pass, 183 tests)

### Completion Notes List

- Added controller-owned surface-version evidence evaluation in `policy.py`, reusing Story 1.1 selector resolution while producing bounded expected-versus-observed runtime and model summaries plus stable surface-specific failure reasons.
- Tightened runtime pin enforcement so runtime-only selectors rely on explicit live probe evidence, with the tmux adapter base now emitting a bounded runtime-identity envelope instead of policy falling back to cached worker metadata.
- Enforced applicable version pins during routing with on-demand adapter probing, fail-closed eligibility for mismatch, missing, stale, and low-trust evidence, and clearer blocker and remediation text in the existing routing surfaces.
- Enforced workflow-agnostic version pins during `worker register`, quarantining drifted workers before ready-state promotion and recording blocked registration through explicit `worker.quarantined` audit evidence plus governance context.
- Extended worker and task inspect outputs to surface version-pin enforcement details without creating a parallel governance dashboard or persisting raw pane captures.
- Added regression coverage for routing, registration, inspect, and runtime-only pin fail-closed paths, and validated the full orchestration test suite.

### File List

- `_bmad-output/implementation-artifacts/stories/1-2-reject-pin-drift-during-eligibility-and-governed-surface-use.md`
- `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/policy.py`
- `tools/orchestration/routing.py`
- `tools/orchestration/workers.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`

### Change Log

- 2026-04-14: Addressed review follow-ups by removing cached runtime-metadata fallback from runtime-only pin enforcement, emitting live runtime-identity probe evidence, recording registration-time drift as `worker.quarantined`, and rerunning targeted plus full orchestration tests.
- 2026-04-14: Completed Story 1.2, marked the governance-hardening tracker entry `done`, and captured passing focused plus full orchestration test results.
- 2026-04-14: Began Story 1.2 implementation and moved the story status to `in-progress`.
- 2026-04-14: Created Story 1.2 and moved the governance-hardening tracker entry from `backlog` to `ready-for-dev`.
