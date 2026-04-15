# Story 1.3: Define scoped secret references without persisting secret material

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,  
I want `secret_scopes` to bind secret references to allowed execution contexts,  
so that secret access stays least-privilege and inspectable.

## Acceptance Criteria

1. Given a governed surface that may require credentials or tokens, when I configure or inspect governance policy, then MACS supports `secret_scopes` that bind secret references to explicit adapter, workflow-class, surface, and operating-profile selectors, and controller-visible policy state stores only secret reference metadata and redaction markers rather than raw secret values.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-13-define-scoped-secret-references-without-persisting-secret-material] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#additional-requirements] [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]
2. Given a policy snapshot or governance inspection view, when I review configured secret scopes, then I can see which secret references are eligible for which contexts, and no inspection path reveals secret values directly.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-13-define-scoped-secret-references-without-persisting-secret-material] [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records] [Source: _bmad-output/planning-artifacts/architecture.md#ux-backing-requirements] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]

## Tasks / Subtasks

- [x] Extend the repo-local governance-policy shape with first-class `secret_scopes` records and one deterministic resolver. (AC: 1, 2)
  - [x] Update `tools/orchestration/policy.py` defaults and normalization helpers so `governance-policy.json` can carry controller-owned `secret_scopes` entries with explicit selector fields (`surface_id`, `adapter_id`, `workflow_class`, `operating_profile`) plus a secret reference identifier and audit-safe redaction or display metadata, while ignoring or rejecting inline secret-value fields.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#additional-requirements] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries] [Inference from: tools/orchestration/policy.py and the existing `surface_version_pins` record shape]
  - [x] Add one helper that resolves the effective secret scopes for a given workflow class, operating profile, adapter, and governed surface so Story 1.4 can reuse the same selector semantics for action-time enforcement instead of re-deriving them.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-14-enforce-scoped-secret-resolution-at-action-time] [Source: _bmad-output/planning-artifacts/architecture.md#operating-profiles] [Inference from: `resolve_surface_version_pins(...)` in tools/orchestration/policy.py]
  - [x] Keep absent `secret_scopes` equivalent to an explicit no-secret-scope state; do not infer secret requirements from governed-surface allowlists, adapter pins, or version-pin rules.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-13-define-scoped-secret-references-without-persisting-secret-material] [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-14-macs-core-orchestration.md#follow-on-observations]

- [x] Preserve inspectable policy snapshots and setup read models for secret-scope state. (AC: 1, 2)
  - [x] Reuse the existing `policy_snapshots` table and `active_governance_snapshot(...)` path instead of inventing a second snapshot or secret-registry mechanism; snapshot-preserved governance payloads must surface normalized or effective secret scopes with the active operating profile.  
        [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records] [Source: tools/orchestration/policy.py] [Source: tools/orchestration/store.py]
  - [x] Extend `tools/orchestration/setup.py` so `build_setup_configuration_snapshot()` exposes the active operating profile, active governance snapshot reference, and either the normalized secret-scope set or an explicit `none_configured` state in `macs setup check` JSON output.  
        [Source: tools/orchestration/setup.py] [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md]
  - [x] If the live governance policy diverges from the active snapshot, keep the snapshot-captured secret-scope summary inspectable alongside the stale-vs-live traceability signal rather than hiding it.  
        [Source: tools/orchestration/policy.py] [Source: _bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md#completion-notes-list]

- [x] Surface applicable secret scopes through the existing governance inspection seams without leaking secret material. (AC: 1, 2)
  - [x] Extend `describe_adapter_governance(...)`, `adapter_governance_summary(...)`, and adjacent CLI formatting helpers so `macs adapter inspect` shows per-surface applicable secret scopes for declared governed surfaces and a compact top-level summary of the effective secret scopes in the current inspection context.  
        [Source: tools/orchestration/policy.py] [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/architecture.md#ux-backing-requirements]
  - [x] Keep human-readable and `--json` output controller-owned, compact, and audit-safe: show `secret_ref`, selector context, and redaction or display metadata only; never render tokens, passwords, or inline secret payloads.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-13-define-scoped-secret-references-without-persisting-secret-material] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules]
  - [x] Reuse the existing setup and adapter inspect seams first; touch `worker inspect` or `task inspect` only if the same read-side summary can be reused without implying that action-time secret resolution already exists.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md]

- [x] Add focused regression coverage for bootstrap compatibility and inspection output. (AC: 1, 2)
  - [x] Extend `tools/orchestration/tests/test_setup_init.py` with governance bootstrap and `setup check` assertions for explicit no-secret-scope state, normalized secret-scope rendering, and stale-vs-live snapshot visibility when `secret_scopes` changes after bootstrap.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: _bmad-output/planning-artifacts/architecture.md#testing-principles]
  - [x] Extend `tools/orchestration/tests/test_inspect_context_cli.py` so `macs adapter inspect --json` exposes applicable secret-scope summaries for declared governed surfaces while excluding non-matching scope records from the top-level effective summary.  
        [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: tools/orchestration/cli/main.py]
  - [x] Add a narrow no-regression assertion only if needed to prove that absent `secret_scopes` does not change current governed-surface and version-pin behavior.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: _bmad-output/implementation-artifacts/stories/1-2-reject-pin-drift-during-eligibility-and-governed-surface-use.md#testing-requirements]

- [x] Keep Story 1.3 bounded to secret-scope modeling and inspection only. (AC: 1, 2)
  - [x] Do not resolve secret references at action time, inject secrets into adapters, mutate worker environments, or add secret-manager integrations in this story; those belong to Story 1.4.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-14-enforce-scoped-secret-resolution-at-action-time]
  - [x] Do not persist raw secret values in governance policy files, policy snapshots, event payloads, release evidence, or test fixtures.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]
  - [x] Do not broaden into diff/review checkpoints, release-evidence expansion, or remote policy sources in this story.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#epic-2-prove-and-enforce-baseline-review-before-risky-completion] [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-14-macs-core-orchestration.md#follow-on-observations]

- [x] Review Follow-ups (AI). (AC: 1, 2)
  - [x] [AI-Review][High] Reject unsupported inline secret-material fields during `secret_scopes` normalization and scrub them from repo-local `governance-policy.json` on controller load so Story 1.3 no longer accepts or retains raw secret values.  
        [Source: user review finding dated 2026-04-14] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-13-define-scoped-secret-references-without-persisting-secret-material]

## Dev Notes

### Story Intent

This story is the schema and inspection foundation for secret governance in the lane-local governance-hardening backlog. Story 6.4 already established the repo-local `governance-policy.json` surface, Story 7.1 kept governance as its own configuration domain, and Stories 1.1-1.2 established the pattern of modeling a new controller-owned governance control before enforcing it. Story 1.3 should add controller-owned `secret_scopes` and inspectable summaries while leaving actual secret resolution and action-time blocking for Story 1.4.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-13-define-scoped-secret-references-without-persisting-secret-material]  
[Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-14-macs-core-orchestration.md#follow-on-observations]  
[Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md]  
[Source: _bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md]

### Governance-Hardening Lane Boundaries

- Use only `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml` for lane tracking.
- Do not edit the historical orchestration tracker at `_bmad-output/implementation-artifacts/sprint-status.yaml`.
- Do not edit the guided-onboarding tracker at `_bmad-output/implementation-artifacts/sprint-status-macs-guided-onboarding.yaml`.
- Treat this as follow-on governance hardening implied by the 2026-04-14 correction pass, not a reopening of the completed orchestration sprint and not part of guided onboarding.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#overview]  
[Source: _bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml]

### Previous Story Intelligence

- Story 1.1 already introduced controller-owned `operating_profile`, selector normalization, active governance snapshot traceability, and `resolve_surface_version_pins(...)`. Reuse that normalization and selector pattern for `secret_scopes` instead of creating a second secret-specific matching model.
- Story 1.2 proved that governance-hardening controls can be threaded through existing controller-owned summaries, inspect output, and rejection context without changing the top-level CLI contract. For Story 1.3, reuse the read-side summary pattern but stop before action-time enforcement.
- Stories 1.1 and 1.2 explicitly deferred `secret_scopes` and secret resolution. Story 1.3 should pick up only the policy-modeling and inspection half of that deferred work.

[Source: _bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md#previous-story-intelligence]  
[Source: _bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md#implementation-guardrails]  
[Source: _bmad-output/implementation-artifacts/stories/1-2-reject-pin-drift-during-eligibility-and-governed-surface-use.md#previous-story-intelligence]  
[Source: _bmad-output/implementation-artifacts/stories/1-2-reject-pin-drift-during-eligibility-and-governed-surface-use.md#implementation-guardrails]

### Brownfield Continuity

- `tools/orchestration/policy.py` already bootstraps repo-local governance policy, normalizes `operating_profile`, resolves effective governed-surface policy, resolves effective version pins, and exposes active governance snapshot metadata.
- `tools/orchestration/setup.py` already returns a governance summary from `build_setup_configuration_snapshot()` with `operating_profile`, `active_snapshot`, and `surface_version_pins`; the safest implementation path is to extend that existing read model with `secret_scopes`.
- `describe_adapter_governance(...)` and `adapter_governance_summary(...)` already scope governance readouts by declared governed surfaces and current inspection context, which is the right place to show applicable secret-scope references without inventing a separate governance command family.
- `tools/orchestration/cli/main.py` already has compact summary helpers and stale-snapshot rendering for governance output. Add adjacent secret-scope formatting rather than a new output subsystem.

[Source: tools/orchestration/policy.py]  
[Source: tools/orchestration/setup.py]  
[Source: tools/orchestration/cli/main.py]  
[Source: _bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md]

### Secret-Scope Model Guardrail

- Model `secret_scopes` as scoped references, not secret material. Each record should keep only audit-safe metadata such as the secret reference id plus controller-readable selector context and redaction or display metadata.
- Keep selector semantics aligned with `surface_version_pins`: explicit `surface_id`, `adapter_id`, `workflow_class`, and `operating_profile`, with the same default-any matching behavior where selectors are omitted.
- Preserve the shipping operating-profile vocabulary from Story 1.1: `primary_plus_fallback` remains the default and `full_hybrid` remains opt-in.
- Make the effective-scope helper usable by later action-time enforcement, but do not require any secret resolution side effects or credential retrieval in this story.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#additional-requirements]  
[Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]  
[Source: _bmad-output/planning-artifacts/architecture.md#operating-profiles]  
[Inference from: `resolve_surface_version_pins(...)` and related selector helpers in tools/orchestration/policy.py]

### Technical Requirements

- Keep governance repo-local, controller-owned, and inspectable; do not move secret-scope authority into adapters, runtime configs, or remote policy sources.  
  [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/project-context.md#framework-specific-rules]
- Persist only secret reference metadata and redaction markers. Never persist raw secret values, inline credential blobs, or real secret material in `governance-policy.json`, policy snapshots, events, release evidence, or tests.  
  [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]
- Preserve backward compatibility when `secret_scopes` is absent; current governed-surface allowlists, adapter pins, and version-pin behavior must stay unchanged.  
  [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-14-macs-core-orchestration.md#follow-on-observations] [Source: _bmad-output/implementation-artifacts/stories/1-2-reject-pin-drift-during-eligibility-and-governed-surface-use.md#technical-requirements]
- Keep the policy schema deterministic and JSON-friendly. Prefer a list of explicit scope records over opaque nested maps or adapter-specific conventions.  
  [Inference from: tools/orchestration/policy.py and the existing `surface_version_pins` schema]
- Keep implementation Python-stdlib-only and preserve the current CLI and JSON envelope patterns.  
  [Source: _bmad-output/project-context.md#technology-stack--versions] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required---json-output]

### Architecture Compliance

- Reuse the existing write model: normalize policy, capture snapshots, and expose read-side summaries without introducing hidden state or runtime side effects.  
  [Source: _bmad-output/planning-artifacts/architecture.md#write-model]
- Preserve `policy_snapshots` as the traceability mechanism for secret-scope state instead of adding a parallel secret registry or secret-audit store in this story.  
  [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records]
- Keep controller truth first in CLI output: show the active operating profile, live or snapshot traceability, and bounded secret-scope metadata before any adapter hints.  
  [Source: _bmad-output/planning-artifacts/architecture.md#ux-backing-requirements] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules]
- Do not change routing eligibility, worker registration, or governed-surface action semantics in Story 1.3; action-time secret enforcement belongs to Story 1.4.  
  [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-14-enforce-scoped-secret-resolution-at-action-time]

### Suggested Implementation Shape

- Add `_normalize_secret_scopes(...)` plus `resolve_secret_scopes(...)` in `tools/orchestration/policy.py`, reusing the same selector normalization helpers and default operating-profile behavior already used for `surface_version_pins`.
- Extend `normalize_governance_policy()`, `DEFAULT_GOVERNANCE_POLICY`, `active_governance_snapshot()`, and `describe_adapter_governance(...)` so live and snapshot summaries include `secret_scopes`.
- Extend `build_setup_configuration_snapshot()` in `tools/orchestration/setup.py` so `macs setup check --json` carries the effective secret-scope summary under the current governance-policy summary.
- Add compact CLI helpers in `tools/orchestration/cli/main.py` analogous to the current version-pin summary renderers so `macs setup check` and `macs adapter inspect` can show applicable secret scopes in both human-readable and `--json` modes.
- Keep the scope-to-surface mapping on existing declared governed surfaces where possible so later action-time secret resolution can reuse the same surface context rather than re-deriving it elsewhere.

[Inference from: tools/orchestration/policy.py, tools/orchestration/setup.py, and tools/orchestration/cli/main.py]  
[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]

### File Structure Requirements

- Primary implementation files for this story:
  - `tools/orchestration/policy.py`
  - `tools/orchestration/setup.py`
  - `tools/orchestration/cli/main.py`
  - `tools/orchestration/tests/test_setup_init.py`
  - `tools/orchestration/tests/test_inspect_context_cli.py`
- Optional touch points only if the final read-side shape needs them:
  - `tools/orchestration/tests/test_task_lifecycle_cli.py`
  - `tools/orchestration/store.py`
- Avoid broadening into task-action execution, worker mutation, release-gate reporting, external secret-manager modules, or new controller packages unless a tiny helper extraction is materially clearer than extending the current governance seams.

[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]  
[Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md]

### Testing Requirements

- Extend the existing setup and inspect regression seams instead of creating a secret-governance-only harness.  
  [Source: _bmad-output/planning-artifacts/architecture.md#testing-principles]
- Add explicit coverage for:
  - bootstrap or load behavior when `secret_scopes` is absent
  - normalized and effective secret-scope rendering in `macs setup check`
  - adapter-inspect exposure of applicable secret scopes for declared governed surfaces
  - stale-vs-live governance snapshot handling for secret-scope summaries
  - no-regression behavior for current governed-surface and version-pin flows when `secret_scopes` is absent  
  [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: tools/orchestration/tests/test_task_lifecycle_cli.py]
- Before marking the implementation done, run the focused controller CLI regressions plus full orchestration unittest discovery.  
  [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/planning-artifacts/architecture.md#testing-principles]

### Git Intelligence Summary

- Recent committed history still centers MACS work in controller-owned governance, policy, CLI, and test seams, which is the safest path for Story 1.3.
- The current working tree already contains uncommitted edits in shared governance-hardening and guided-onboarding files, including `tools/orchestration/policy.py`, `tools/orchestration/cli/main.py`, `tools/orchestration/setup.py`, and the main orchestration test suite.
- Story 1.3 is likely to touch some of those same shared seams. Work with those edits and do not revert or overwrite unrelated in-flight changes while implementing the secret-scope slice.

[Source: git log --oneline -5]  
[Inference from current git status]

### Implementation Guardrails

- Do not persist or print raw secret values, credential blobs, or real tokens anywhere in the implementation or tests.  
  [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements]
- Do not add action-time secret resolution, secret injection, environment mutation, or external secret-manager integrations here.  
  [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-14-enforce-scoped-secret-resolution-at-action-time]
- Do not reinterpret governed-surface allowlists, adapter pins, or version pins as implicit secret scopes; `secret_scopes` is a separate controller-owned control.  
  [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-14-macs-core-orchestration.md#issue-summary]
- Do not modify the historical orchestration sprint tracker or the guided-onboarding tracker as part of the implementation.  
  [Source: _bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml]
- Do not revert unrelated working-tree changes in shared policy, CLI, setup, or test files.  
  [Source: _bmad-output/project-context.md#development-workflow-rules] [Inference from current git status]

### Project Structure Notes

- This remains a brownfield, shell-first, Python-stdlib-only orchestration controller.
- The governance-hardening lane is intentionally separate from the historical orchestration sprint and the guided-onboarding initiative, even though all story files live in the shared stories directory.
- The cleanest implementation path is a narrow extension of the current governance-policy and inspection seams so secret-scope modeling stays inspectable and controller-owned without prematurely adding secret-resolution behavior.

[Source: _bmad-output/project-context.md#development-workflow-rules]  
[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#overview]

### References

- `_bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md`
- `_bmad-output/planning-artifacts/product-brief-macs_dev.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-14-macs-core-orchestration.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`
- `_bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md`
- `_bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md`
- `_bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md`
- `_bmad-output/implementation-artifacts/stories/1-2-reject-pin-drift-during-eligibility-and-governed-surface-use.md`
- `tools/orchestration/policy.py`
- `tools/orchestration/setup.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/store.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add controller-owned `secret_scopes` schema defaults, normalization, and effective-scope resolution in `tools/orchestration/policy.py`.
- Surface the active secret-scope summary through `macs setup check` and `macs adapter inspect`, including governance snapshot traceability and explicit no-secret-scope state.
- Extend the existing orchestration CLI tests for bootstrap compatibility, inspect output, and no-regression when `secret_scopes` is absent.
- Resolve the high review finding by rejecting unsupported `secret_scopes` fields during direct normalization and scrubbing those fields from repo-local governance policy files during controller-owned loads.

### Debug Log References

- Story authored with `bmad-create-story`.
- Authoritative tracker: `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`.
- Planning sources reviewed: the governance-hardening delta epics file, corrected PRD, corrected architecture, operator CLI contract, 2026-04-14 sprint change proposal, and project context.
- Brownfield continuity reviewed: Stories 6.4, 7.1, 1.1, and 1.2; current `policy.py`, `setup.py`, `cli/main.py`, relevant governance and inspect tests, `git log --oneline -5`, and the current `git status --short`.
- External web research was not required because this story is repo-local governance-policy modeling and inspection work, not third-party API integration.
- 2026-04-14: Development started; story and governance-hardening lane tracker moved to `in-progress`.
- 2026-04-14: Added red-phase coverage for `secret_scopes` normalization, `setup check` summaries, and `adapter inspect` summaries; targeted tests failed as expected because the resolver and read-side summaries were not implemented yet.
- 2026-04-14: Implemented controller-owned `secret_scopes` defaults, normalization, snapshot-safe persistence, setup summaries, and adapter inspect summaries without adding action-time secret resolution.
- 2026-04-14: Re-ran focused setup and inspect suites plus full orchestration unittest discovery after replacing unsafe inline-test placeholders with audit-safe neutral fixture data.
- 2026-04-14: Resumed from review to address the high inline-secret-material finding; added a rejecting normalization guard plus repo-local governance-policy scrubbing for unsupported `secret_scopes` fields.
- 2026-04-14: Re-ran focused review-fix tests, the story’s setup and inspect regression suites, and full orchestration unittest discovery after confirming inline secret fields were scrubbed from `governance-policy.json`.

### Test Record

- 2026-04-14: Red phase confirmed with targeted regressions failing as expected:
  - `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_secret_scope_resolution_returns_explicit_none_configured_when_field_missing`
  - `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_secret_scope_resolution_ignores_inline_secret_value_fields_and_filters_to_effective_context`
  - `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_reports_governance_operating_profile_snapshot_and_no_pins_in_json`
  - `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_reports_effective_secret_scopes_for_active_profile_in_json`
  - `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_reports_stale_governance_snapshot_after_post_bootstrap_policy_edit`
  - `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_human_readable_reports_governance_profile_snapshot_and_no_pins`
  - `python3 -m unittest tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_adapter_inspect_json_surfaces_applicable_secret_scope_policy`
  - `python3 -m unittest tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_adapter_inspect_json_excludes_non_matching_secret_scopes_from_top_level_summary`
  - Observed failures: missing `resolve_secret_scopes`, missing `secret_scopes` summaries in setup snapshot and adapter inspect output, and missing human-readable `Secret scopes` lines.
- 2026-04-14: Green phase validation passed:
  - `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_secret_scope_resolution_returns_explicit_none_configured_when_field_missing tools.orchestration.tests.test_setup_init.SetupInitTests.test_secret_scope_resolution_ignores_inline_secret_value_fields_and_filters_to_effective_context tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_reports_governance_operating_profile_snapshot_and_no_pins_in_json tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_reports_effective_secret_scopes_for_active_profile_in_json tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_reports_stale_governance_snapshot_after_post_bootstrap_policy_edit tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_human_readable_reports_governance_profile_snapshot_and_no_pins tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_adapter_inspect_json_surfaces_applicable_secret_scope_policy tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_adapter_inspect_json_excludes_non_matching_secret_scopes_from_top_level_summary` -> `Ran 8 tests in 1.249s` / `OK`
  - `python3 -m unittest tools.orchestration.tests.test_setup_init tools.orchestration.tests.test_inspect_context_cli` -> `Ran 115 tests in 23.795s` / `OK`
  - `python3 -m unittest discover -s tools/orchestration/tests` -> `Ran 188 tests in 62.865s` / `OK`
- 2026-04-14: Review-finding red phase confirmed with targeted regressions failing as expected:
  - `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_secret_scope_resolution_rejects_inline_secret_material_fields tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_reports_effective_secret_scopes_for_active_profile_in_json`
  - Observed failures: direct secret-scope normalization still accepted unsupported inline secret-material fields, and `governance-policy.json` still retained `secret_value` after controller inspection.
- 2026-04-14: Review-finding validation passed:
  - `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_secret_scope_resolution_rejects_inline_secret_material_fields tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_reports_effective_secret_scopes_for_active_profile_in_json` -> `Ran 2 tests in 0.235s` / `OK`
  - `python3 -m unittest tools.orchestration.tests.test_setup_init tools.orchestration.tests.test_inspect_context_cli` -> `Ran 115 tests in 21.480s` / `OK`
  - `python3 -m unittest discover -s tools/orchestration/tests` -> `Ran 188 tests in 61.313s` / `OK`

### Completion Notes

- Added controller-owned `secret_scopes` to the governance policy defaults and resolver path, and tightened the schema so direct normalization now rejects unsupported inline secret-material fields instead of silently accepting them.
- Scrubbed unsupported `secret_scopes` fields from repo-local `governance-policy.json` during controller-owned policy bootstrap and load paths so raw secret-like values cannot remain persisted after policy inspection.
- Kept secret-scope state inspectable through the existing `policy_snapshots` and setup summary seams by snapshotting normalized governance payloads and exposing active or stale snapshot secret-scope summaries alongside the active operating profile.
- Extended `macs setup check` and `macs adapter inspect` to surface effective secret scopes and per-surface applicable secret scopes in both human-readable and `--json` output without rendering inline secret payloads.
- Added focused regression coverage for absent secret scopes, active-profile filtering, stale-vs-live snapshot visibility, and adapter-inspect applicability or exclusion cases; the full orchestration unittest discovery passed after the story implementation.
- ✅ Resolved review finding [High]: inline secret material can no longer be accepted silently or remain persisted in `governance-policy.json` through `secret_scopes` normalization.

## File List

- `_bmad-output/implementation-artifacts/stories/1-3-define-scoped-secret-references-without-persisting-secret-material.md`
- `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`
- `tools/orchestration/policy.py`
- `tools/orchestration/setup.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`

## Change Log

- 2026-04-14: Implemented Story 1.3 secret-scope governance modeling, snapshot-safe inspection summaries, adapter inspection exposure, and regression coverage; status moved to `review`.
- 2026-04-14: Addressed the high review finding by rejecting unsupported inline secret-material fields, scrubbing them from repo-local governance policy files on controller load, rerunning Story 1.3 regressions, and moving the story to `done`.
