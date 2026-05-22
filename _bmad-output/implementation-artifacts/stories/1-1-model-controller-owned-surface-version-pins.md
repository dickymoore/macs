# Story 1.1: Model controller-owned surface version pins

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,  
I want inspectable `surface_version_pins` rules in governance policy,  
so that approved surfaces and runtime or model identities are pinned by policy instead of adapter convention.

## Acceptance Criteria

1. Given a repository with governance policy for governed surfaces, when I define or inspect a production-oriented operating profile, then MACS supports `surface_version_pins` keyed by explicit surface, adapter, workflow-class, and operating-profile selectors, and policy snapshots preserve the effective pin set with versioned audit references.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-11-model-controller-owned-surface-version-pins] [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/planning-artifacts/architecture.md#operating-profiles] [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records]
2. Given an existing configuration that uses allowlists and adapter pins only, when no `surface_version_pins` are configured, then existing governance behavior remains compatible without inventing implicit version-pin rules, and the operator-facing policy view makes the absence of version pins explicit.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-11-model-controller-owned-surface-version-pins] [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-14-macs-core-orchestration.md#follow-on-observations] [Source: _bmad-output/planning-artifacts/product-brief-macs_dev.md#technical-approach]

## Tasks / Subtasks

- [x] Extend the repo-local governance-policy shape with first-class version-pin selectors and an explicit operating-profile seam. (AC: 1, 2)
  - [x] Update `tools/orchestration/policy.py` defaults and normalization helpers so `governance-policy.json` can carry controller-owned `surface_version_pins` plus an explicit operating-profile selector, using visible fields for `surface_id`, `adapter_id`, `workflow_class`, `operating_profile`, and expected runtime/model identity rather than hidden adapter-specific conventions.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#additional-requirements] [Source: _bmad-output/planning-artifacts/prd.md#installation-and-configuration-model] [Source: tools/orchestration/policy.py]
  - [x] Keep `allowlisted_surfaces` and `pinned_surfaces` behavior unchanged when `surface_version_pins` is absent; missing pins must mean "no version pins configured", not an implied pin copied from adapter pinning.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-11-model-controller-owned-surface-version-pins] [Source: tools/orchestration/policy.py]
  - [x] Add one deterministic helper that resolves the effective pin set for a given workflow class, operating profile, adapter, and governed surface so Story 1.2 can reuse the same policy semantics for enforcement instead of re-deriving them.  
        [Source: _bmad-output/planning-artifacts/architecture.md#routing-and-policy-engine] [Source: _bmad-output/planning-artifacts/architecture.md#operating-profiles] [Inference from: tools/orchestration/policy.py and tools/orchestration/routing.py]

- [x] Preserve inspectable policy snapshots and audit references for version-pin state. (AC: 1)
  - [x] Reuse the existing `policy_snapshots` table and metadata path instead of creating a second snapshot mechanism; surface the active governance snapshot id alongside the normalized or effective version-pin view so operators can trace the policy readout back to one snapshot.  
        [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records] [Source: tools/orchestration/policy.py] [Source: tools/orchestration/store.py]
  - [x] Ensure the snapshot-preserved governance payload or snapshot-adjacent controller summary keeps the effective pin set legible for the active operating profile, without turning adapter self-reporting into the authority source.  
        [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries] [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records]
  - [x] Keep this story bounded to policy modeling and inspectability only; pin-drift rejection, stale or missing version evidence, and quarantine behavior belong to Story 1.2.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-12-reject-pin-drift-during-eligibility-and-governed-surface-use]

- [x] Surface version-pin presence or explicit absence through existing governance inspection paths. (AC: 1, 2)
  - [x] Extend `tools/orchestration/setup.py` and `macs setup check` so the governance-policy section shows the active operating profile, governance snapshot reference, and either the normalized pin set or an explicit `none_configured` state in both `--json` and human-readable output.  
        [Source: tools/orchestration/setup.py] [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/tests/test_setup_init.py]
  - [x] Extend `macs adapter inspect` to show the applicable version-pin policy beside the existing governed-surface summary, and touch `worker inspect` only if the same controller-owned summary can be reused without duplicating selector logic.  
        [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/tests/test_inspect_context_cli.py]
  - [x] Keep output compact and controller-owned; operators should not need to reverse-engineer raw JSON files or runtime capture conventions just to tell whether version pins exist.  
        [Source: _bmad-output/planning-artifacts/architecture.md#ux-backing-requirements] [Source: _bmad-output/project-context.md#code-quality--style-rules]

- [x] Add focused regression coverage for schema compatibility and inspection output. (AC: 1, 2)
  - [x] Extend `tools/orchestration/tests/test_setup_init.py` with governance bootstrap and `setup check` assertions for explicit no-pins state, active operating-profile visibility, and normalized pin rendering when `surface_version_pins` is configured.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: _bmad-output/planning-artifacts/architecture.md#testing-principles]
  - [x] Extend `tools/orchestration/tests/test_inspect_context_cli.py` or the closest adapter-inspect seam so `macs adapter inspect --json` surfaces the applicable version-pin view without regressing current governed-surface reporting.  
        [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: tools/orchestration/cli/main.py]
  - [x] Add a narrow no-regression assertion only if needed to prove that absent `surface_version_pins` does not change current allowlist or adapter-pin routing outcomes.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md]

- [x] Address Story 1.1 review follow-ups for snapshot traceability and adapter applicability summaries. (AC: 1, 2)
  - [x] Make `setup check` and `adapter inspect` surface when the active governance snapshot is stale relative to post-bootstrap `governance-policy.json` edits, while keeping the snapshot-captured version-pin summary inspectable for the active operating profile.  
        [Source: tools/orchestration/policy.py] [Source: tools/orchestration/setup.py] [Source: tools/orchestration/cli/main.py]
  - [x] Ensure adapter-inspect top-level applicable version-pin summaries exclude pins for undeclared governed surfaces by deriving the top-level summary from declared-surface applicability.  
        [Source: tools/orchestration/policy.py] [Source: tools/orchestration/tests/test_inspect_context_cli.py]

- [x] Keep Story 1.1 bounded to version-pin modeling, snapshots, and inspection only. (AC: 2)
  - [x] Do not implement routing eligibility rejection, governed-surface action blocking, or stale or missing version-evidence handling here; that is Story 1.2.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-12-reject-pin-drift-during-eligibility-and-governed-surface-use]
  - [x] Do not introduce `secret_scopes`, secret resolution plumbing, diff or review checkpoints, or release-evidence expansion here; those belong to Stories 1.3, 1.4, and Epic 2.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-13-define-scoped-secret-references-without-persisting-secret-material] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#epic-2-prove-and-enforce-baseline-review-before-risky-completion]
  - [x] Do not add a second governance file, remote policy source, or adapter-owned pin evaluation path.  
        [Source: _bmad-output/planning-artifacts/product-brief-macs_dev.md#technical-approach] [Source: _bmad-output/project-context.md#critical-dont-miss-rules]

## Dev Notes

### Story Intent

This story is the schema and inspection foundation for the governance-hardening lane. Historical Story 6.4 already gave MACS a repo-local `governance-policy.json`, governed-surface allowlists and adapter pins, and local policy snapshots. Story 1.1 should extend that same controller-owned surface with first-class version-pin rules and an explicit operating-profile seam so later enforcement work has a stable, inspectable source of truth.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-11-model-controller-owned-surface-version-pins]  
[Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-14-macs-core-orchestration.md#follow-on-observations]  
[Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md]

### Governance-Hardening Lane Boundaries

- Use only `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml` for lane tracking.
- Do not edit the historical orchestration tracker at `_bmad-output/implementation-artifacts/sprint-status.yaml`.
- Do not edit the guided-onboarding tracker at `_bmad-output/implementation-artifacts/sprint-status-macs-guided-onboarding.yaml`.
- Treat this as follow-on hardening for corrected governance requirements, not a reopening of the original orchestration sprint and not part of guided onboarding.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#overview]  
[Source: _bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml]

### Brownfield Continuity

- `tools/orchestration/policy.py` currently governs `allowlisted_surfaces`, `pinned_surfaces`, workflow overrides, audit-content policy, and decision-rights metadata. There is no first-class `surface_version_pins` or operating-profile-aware selector helper yet.
- `tools/orchestration/setup.py` already exposes the full governance-policy payload through `build_setup_configuration_snapshot`, so the safest inspection path is to extend that output rather than inventing a new governance command family.
- `macs adapter inspect` already attaches an adapter governance summary, and `setup init` already reports governance-policy `snapshot_id`. Reuse those seams instead of creating parallel reporting paths.
- `policy_snapshots` already persist `snapshot_id`, `policy_origin`, `policy_version`, `captured_at`, and `payload`; Story 1.1 should build on that table, not replace it.

[Source: tools/orchestration/policy.py]  
[Source: tools/orchestration/setup.py]  
[Source: tools/orchestration/cli/main.py]  
[Source: tools/orchestration/store.py]  
[Source: _bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md]

### Version-Evidence Guardrail

Current brownfield code already exposes one relevant evidence seam: `CodexAdapter.probe()` can derive a low-confidence `permission_surface` claim that includes `model`, `sandbox`, and `approval_policy`. Story 1.1 should make the policy schema capable of expressing pins against explicit runtime or model identities, but it should not yet turn those claims into hard enforcement or pretend every adapter already emits trustworthy version evidence.

[Source: tools/orchestration/adapters/codex.py]  
[Source: tools/orchestration/tests/test_setup_init.py]  
[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-12-reject-pin-drift-during-eligibility-and-governed-surface-use]

### Technical Requirements

- Keep governance repo-local, controller-owned, and inspectable; do not move policy authority into adapters or runtime-specific config.
- Preserve backward compatibility when `surface_version_pins` is absent. Existing repos that only use surface allowlists and adapter pins must continue to behave the same way.
- Make absence explicit. New repos may bootstrap an empty `surface_version_pins` field or equivalent explicit no-pins state, and older repos without the field should normalize to the same no-pins result without silent mutation.
- Use the existing operating-profile vocabulary: `primary_plus_fallback` is the shipping default and `full_hybrid` is the opt-in broader profile.
- Keep the policy schema deterministic and JSON-friendly. Prefer a list of explicit pin records over a deeply nested map so inspection order and future selector resolution stay stable.
- Keep implementation Python-stdlib-only and aligned with the current controller/read-model seams.

[Source: _bmad-output/planning-artifacts/prd.md#bmad-execution-policy-and-operating-profiles]  
[Source: _bmad-output/planning-artifacts/prd.md#installation-and-configuration-model]  
[Source: _bmad-output/planning-artifacts/prd.md#security--governance]  
[Source: _bmad-output/planning-artifacts/architecture.md#operating-profiles]  
[Source: _bmad-output/project-context.md#technology-stack--versions]

### Architecture Compliance

- Reuse the existing repo-local write model: normalize policy, capture snapshots, and expose read-side summaries without introducing hidden state or non-local dependencies.
- Keep adapters as evidence providers only. They may eventually supply runtime or model version signals, but they must not define the pinning rule semantics.
- Keep operator surfaces compact: CLI views should show controller truth first, then bounded evidence or derived summaries.
- Do not change routing or assignment rejection semantics in this story; that belongs to the subsequent enforcement story.

[Source: _bmad-output/planning-artifacts/architecture.md#write-model]  
[Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]  
[Source: _bmad-output/planning-artifacts/architecture.md#ux-backing-requirements]  
[Source: _bmad-output/planning-artifacts/architecture.md#routing-outcome-contract]

### Suggested Implementation Shape

- Add a small normalization layer in `tools/orchestration/policy.py` for explicit version-pin records, along with one helper that resolves the effective pin set for a specific workflow class, operating profile, adapter, and governed surface.
- Thread that normalized or effective view into `build_setup_configuration_snapshot()` so `macs setup check` can display policy path, snapshot id, operating profile, and version pins from one existing read model.
- Reuse `adapter_governance_summary()` or an adjacent helper in `tools/orchestration/cli/main.py` to show the applicable version-pin view for `macs adapter inspect`.
- Only touch adapter descriptors if the controller-owned inspection path needs a small, explicit hint about which evidence field names are available later for enforcement; avoid premature evidence-enforcement coupling.

[Inference from: tools/orchestration/policy.py, tools/orchestration/setup.py, and tools/orchestration/cli/main.py]  
[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]

### File Structure Requirements

- Primary implementation files for this story:
  - `tools/orchestration/policy.py`
  - `tools/orchestration/setup.py`
  - `tools/orchestration/cli/main.py`
  - `tools/orchestration/tests/test_setup_init.py`
  - `tools/orchestration/tests/test_inspect_context_cli.py`
- Optional touch points only if required by the final read-side shape:
  - `tools/orchestration/store.py`
  - `tools/orchestration/adapters/base.py`
  - `tools/orchestration/adapters/codex.py`
  - `tools/orchestration/tests/test_task_lifecycle_cli.py`
- Avoid broadening into routing, task mutation, release-gate, or secret-handling modules unless a tiny import-level change is unavoidable.

[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]  
[Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md]

### Testing Requirements

- Extend the existing config and inspection regression seams instead of creating a governance-hardening-only harness.
- Add explicit coverage for:
  - bootstrap or load behavior when `surface_version_pins` is absent
  - normalized version-pin rendering in `setup check`
  - adapter-inspect exposure of the applicable version-pin summary
  - no-regression behavior for current governed-surface allowlist or adapter-pin routing when no version pins are configured
- Before marking the implementation done, run the focused controller CLI regressions plus full orchestration unittest discovery.

[Source: _bmad-output/project-context.md#testing-rules]  
[Source: _bmad-output/planning-artifacts/architecture.md#testing-principles]  
[Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md#testing-requirements]

### Git Intelligence Summary

- Recent committed history still centers MACS changes in controller-owned bootstrap, policy, and CLI seams, which is the safest path for Story 1.1.
- The current working tree already contains uncommitted guided-onboarding and documentation edits in `tools/orchestration/cli/main.py`, `tools/orchestration/setup.py`, `tools/orchestration/tests/test_setup_init.py`, `README.md`, and several docs files.
- Story 1.1 is likely to touch some of those same read-side seams. Work with those edits and do not revert or overwrite unrelated in-flight changes while implementing the governance-hardening slice.

[Source: git log --oneline -5]  
[Inference from current git status]

### Implementation Guardrails

- Do not treat adapter pins as version pins; `pinned_surfaces` and `surface_version_pins` are separate controls with separate semantics.
- Do not reject workers, block governed-surface actions, or quarantine anything on version mismatch in this story.
- Do not introduce `secret_scopes`, secret values, or secret-resolution paths here.
- Do not create a second governance-policy file, remote policy source, or adapter-owned policy evaluator.
- Do not modify the historical orchestration sprint tracker or the guided-onboarding tracker as part of the implementation.
- Do not revert unrelated working-tree changes in shared setup, CLI, or docs files.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#additional-requirements]  
[Source: _bmad-output/project-context.md#development-workflow-rules]

### Project Structure Notes

- This remains a brownfield, shell-first, Python-stdlib-only orchestration controller.
- The governance-hardening lane is intentionally separate from the historical orchestration sprint and the guided-onboarding initiative, even though all story files live in the shared stories directory.
- The cleanest implementation is a narrow extension of the existing governance-policy and inspection seams, leaving enforcement and release-evidence expansion for later stories in this lane.

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
- `_bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md`
- `_bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md`
- `tools/orchestration/policy.py`
- `tools/orchestration/setup.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/store.py`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/adapters/codex.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Extend the governance-policy schema and normalization helpers with explicit version-pin records plus an operating-profile-aware resolved-pin helper.
- Surface the governance snapshot reference, operating profile, and normalized or effective version-pin summary through `setup check` and adapter inspection without changing enforcement semantics.
- Add focused regression coverage for explicit no-pins compatibility and configured version-pin visibility, then run the usual controller CLI and full unittest validation before marking the story done.

### Debug Log References

- Story authored with `bmad-create-story`.
- Authoritative tracker: `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`.
- Planning sources reviewed: the governance-hardening delta epics file, corrected product brief, corrected PRD, corrected architecture, and the 2026-04-14 sprint change proposal.
- Brownfield continuity reviewed: Story 6.4 governance policy work, Story 7.1 config-domain inspection work, current `policy.py`, `setup.py`, `cli/main.py`, relevant governance and inspect tests, `git log --oneline -5`, and the current `git status --short`.
- External web research was not required because this story is repo-local policy and inspection modeling, not third-party API integration work.
- 2026-04-14: Began Story 1.1 implementation under `bmad-dev-story`, marked the governance-hardening tracker `in-progress`, and confirmed the current worktree already contains unrelated guided-onboarding edits in shared setup/CLI/test seams that must be preserved.
- 2026-04-14: Red phase confirmed with `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_init_bootstraps_repo_local_governance_policy_file tools.orchestration.tests.test_setup_init.SetupInitTests.test_surface_version_pin_resolution_returns_explicit_none_configured_when_field_missing tools.orchestration.tests.test_setup_init.SetupInitTests.test_surface_version_pin_resolution_filters_to_effective_context tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_reports_governance_operating_profile_snapshot_and_no_pins_in_json tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_reports_effective_surface_version_pins_for_active_profile_in_json tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_human_readable_reports_governance_profile_snapshot_and_no_pins tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_adapter_inspect_json_surfaces_applicable_surface_version_pin_policy`; the governance policy still lacked `operating_profile`, setup-check governance summaries, and a reusable version-pin resolver.
- 2026-04-14: Implemented controller-owned governance normalization in `tools/orchestration/policy.py`, including default `operating_profile`, explicit `surface_version_pins`, `resolve_surface_version_pins()`, and active governance snapshot lookup without changing current allowlist or adapter-pin enforcement behavior.
- 2026-04-14: Threaded the normalized governance summary into `tools/orchestration/setup.py` and `tools/orchestration/cli/main.py` so `macs setup check` and `macs adapter inspect` expose the active operating profile, governance snapshot id, and either effective version pins or explicit no-pin state in both JSON and human-readable output.
- 2026-04-14: Added focused regression coverage in `tools/orchestration/tests/test_setup_init.py` and `tools/orchestration/tests/test_inspect_context_cli.py`, then confirmed the existing governed-surface routing behavior still passes with `tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_task_assign_allows_pinned_governed_surface_for_matching_adapter`.
- 2026-04-14: Addressed review follow-ups by making stale governance snapshots explicit after post-bootstrap policy edits and by constraining adapter-inspect top-level version-pin summaries to declared governed surfaces only.

### Test Record

- 2026-04-14: RED - `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_init_bootstraps_repo_local_governance_policy_file tools.orchestration.tests.test_setup_init.SetupInitTests.test_surface_version_pin_resolution_returns_explicit_none_configured_when_field_missing tools.orchestration.tests.test_setup_init.SetupInitTests.test_surface_version_pin_resolution_filters_to_effective_context tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_reports_governance_operating_profile_snapshot_and_no_pins_in_json tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_reports_effective_surface_version_pins_for_active_profile_in_json tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_human_readable_reports_governance_profile_snapshot_and_no_pins tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_adapter_inspect_json_surfaces_applicable_surface_version_pin_policy` failed because the bootstrap policy file, setup snapshot, and adapter inspection surface did not yet expose the new controller-owned version-pin model.
- 2026-04-14: GREEN - the same targeted Story 1.1 regressions passed after wiring governance-policy normalization, effective pin resolution, snapshot lookup, and inspection rendering.
- 2026-04-14: GREEN - `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_reports_governance_operating_profile_snapshot_and_no_pins_in_json tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_reports_effective_surface_version_pins_for_active_profile_in_json tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_check_reports_stale_governance_snapshot_after_post_bootstrap_policy_edit tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_adapter_inspect_json_surfaces_applicable_surface_version_pin_policy tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_adapter_inspect_json_excludes_undeclared_surface_pins_from_top_level_summary tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_adapter_inspect_json_reports_stale_governance_snapshot_after_post_bootstrap_policy_edit`
- 2026-04-14: PASS - `python3 -m unittest tools.orchestration.tests.test_setup_init tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_task_assign_allows_pinned_governed_surface_for_matching_adapter`
- 2026-04-14: PASS - `python3 -m unittest discover -s tools/orchestration/tests`

### Completion Notes List

- Added explicit controller-owned `operating_profile` and `surface_version_pins` fields to the default governance policy, while normalizing older repos without pins to the same explicit no-pin state instead of inventing implicit pins from adapter policy.
- Added reusable governance helpers in `tools/orchestration/policy.py` for active governance snapshot lookup and deterministic effective version-pin resolution by workflow class, operating profile, adapter, and surface.
- Extended `macs setup check` JSON and human-readable output to show the active operating profile, active governance snapshot reference, and either effective version pins or an explicit `none_configured` state through the existing governance-policy section.
- Extended `macs adapter inspect` to expose the applicable controller-owned version-pin policy alongside the declared governed-surface summary without introducing worker blocking or pin-drift enforcement.
- Added explicit snapshot traceability metadata and stale-snapshot rendering so post-bootstrap governance-policy edits no longer present live version pins as though they were preserved by the active snapshot.
- Tightened adapter-inspect top-level version-pin summaries so only declared governed surfaces contribute to the applicable policy view, matching the per-surface applicability breakdown.
- Added focused regression coverage for bootstrap defaults, explicit no-pin compatibility, normalized pin rendering, adapter inspection output, and existing governed-surface routing compatibility.
- Kept Story 1.1 bounded to modeling and inspection only; no routing rejection, governed-surface action blocking, secret-scope plumbing, or new governance file sources were added.

### File List

- `tools/orchestration/policy.py`
- `tools/orchestration/setup.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `_bmad-output/implementation-artifacts/stories/1-1-model-controller-owned-surface-version-pins.md`
- `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`

### Change Log

- 2026-04-14: Moved Story 1.1 to `in-progress` and started BMAD implementation tracking for controller-owned surface version pins.
- 2026-04-14: Implemented controller-owned surface version-pin normalization and snapshot-aware inspection summaries in policy, setup, and adapter inspection seams, added focused regression coverage, and moved Story 1.1 to `review`.
- 2026-04-14: Addressed post-review snapshot-traceability and declared-surface applicability defects, reran focused plus full orchestration regressions, and moved Story 1.1 to `done`.
