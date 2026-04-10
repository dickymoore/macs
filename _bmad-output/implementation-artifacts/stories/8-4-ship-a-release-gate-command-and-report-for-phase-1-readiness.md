# Story 8.4: Ship a release-gate command and report for Phase 1 readiness

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,
I want one command that summarizes contract, integration, failure-drill, and dogfood readiness,
So that the MVP can be evaluated against explicit release criteria before shipping.

## Acceptance Criteria

1. MACS ships one release-gate invocation on the existing Phase 1 validation surface that reports pass or fail status for first-class adapters, mandatory failure classes, restart recovery invariants, and the four-worker reference scenario in both human-readable and `--json` output. The implementation must stay within the frozen Phase 1 operator CLI contract unless the contract artifact itself is intentionally revised; prefer extending `macs setup validate` over inventing a new top-level family.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-84-ship-a-release-gate-command-and-report-for-phase-1-readiness] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md] [Source: _bmad-output/planning-artifacts/architecture.md#release-gate-matrix] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg5]
2. The release-gate run produces or refreshes the human-readable and machine-readable evidence needed for the Phase 1 release package rather than depending on stale or missing files. At minimum, it must leave current evidence for adapter qualification, the mandatory failure-mode matrix, restart recovery verification, the four-worker dogfood scenario, setup validation, and the release-gate command result itself under `_bmad-output/release-evidence/`.  
   [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg1] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg2] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg3] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg4] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg5] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg6]
3. The gate reuses the existing 8.1, 8.2, and 8.3 validation seams and current controller-owned helpers instead of re-implementing release criteria as disconnected ad hoc checks. Adapter qualification must flow from the shared adapter contract and qualification gate, mandatory failure classes must stay traceable to the dedicated failure-drill layer, restart recovery proof must exercise current persisted-state recovery seams, and dogfood evidence must reuse the four-worker runner or its committed artifact shape.  
   [Source: _bmad-output/implementation-artifacts/stories/8-1-build-unit-and-contract-test-coverage-for-controller-and-adapter-invariants.md] [Source: _bmad-output/implementation-artifacts/stories/8-2-build-integration-and-failure-drill-coverage-for-mandatory-failure-classes.md] [Source: _bmad-output/implementation-artifacts/stories/8-3-validate-the-four-worker-reference-dogfood-scenario.md] [Source: _bmad-output/planning-artifacts/architecture.md#test-harness-design]
4. Story 8.4 stays bounded to release-readiness aggregation, evidence generation, and operator visibility. It does not add new controller lifecycle semantics, does not replace the existing deterministic, failure-drill, or dogfood suites, and does not introduce a second release workflow outside the controller-owned CLI and repo-local evidence package.  
   [Source: _bmad-output/planning-artifacts/architecture.md#release-gate-matrix] [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md] [Source: _bmad-output/project-context.md#code-quality--style-rules]
5. The required validation surface includes a dedicated release-gate regression seam, the existing focused controller CLI regressions, full unittest discovery, and the tmux bridge smoke test if the release-gate command reuses or expands tmux-backed orchestration helpers. An explicit BMAD QA acceptance pass compares the story contract, the release-gate command outputs, the generated evidence package, and the delivered controller behavior before closure.  
   [Source: _bmad-output/project-context.md#testing-rules] [Source: tools/tmux_bridge/tests/smoke.sh]

## Tasks / Subtasks

- [x] Add the bounded release-gate command surface and regression seam. (AC: 1, 4, 5)
  - [x] Extend the existing setup validation path with one discoverable release-gate invocation, keeping the frozen CLI family boundary intact unless the operator CLI contract is deliberately revised. Prefer `macs setup validate --release-gate` over a new top-level family or sibling workflow.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md] [Source: tools/orchestration/cli/main.py]
  - [x] Add a dedicated regression module under `tools/orchestration/tests/` for release-gate behavior and evidence writing. Reuse the current CLI harness patterns and temp-repo setup before adding any new helper abstraction.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/tests/test_failure_drills_cli.py] [Source: tools/orchestration/tests/test_reference_dogfood_cli.py]
  - [x] Keep any shared helper small, stdlib-only, and justified by repeated release-evidence writing or validation orchestration logic.  
        [Source: _bmad-output/project-context.md#testing-rules]

- [x] Generate and summarize RG1 adapter qualification evidence. (AC: 1, 2, 3)
  - [x] Reuse the shared adapter descriptors, contract validation, and qualification gate to produce one current qualification report per first-class adapter under `_bmad-output/release-evidence/adapter-qualification/`.  
        [Source: tools/orchestration/adapters/base.py] [Source: tools/orchestration/adapters/registry.py] [Source: _bmad-output/planning-artifacts/evidence-templates/adapter-qualification-template.md]
  - [x] Surface the adapter gate summary in both human-readable and `--json` release-gate output, including unsupported features and any non-passing qualification result.  
        [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg1] [Source: tools/orchestration/cli/main.py]

- [x] Generate and summarize RG2 mandatory failure-mode evidence and RG3 restart-recovery proof. (AC: 1, 2, 3)
  - [x] Make the release gate produce a current failure-mode matrix report that stays traceable to the mandatory failure classes and the dedicated release-oriented failure-drill layer from Story 8.2.  
        [Source: tools/orchestration/tests/test_failure_drills_cli.py] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg2] [Source: _bmad-output/planning-artifacts/evidence-templates/failure-drill-report-template.md]
  - [x] Add restart-recovery verification that proves the current boot and persisted-state recovery invariants, then write `_bmad-output/release-evidence/restart-recovery-verification-report.md` from that result instead of leaving RG3 implicit in a broad unrelated suite.  
        [Source: tools/orchestration/recovery.py] [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/tests/test_controller_invariants.py] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg3]

- [x] Refresh RG4 dogfood evidence and package the final gate result. (AC: 1, 2, 3, 4)
  - [x] Reuse the four-worker dogfood runner or its existing evidence shape to refresh the RG4 report and machine-readable artifacts during the release-gate run rather than inventing a second dogfood path.  
        [Source: tools/orchestration/dogfood.py] [Source: tools/orchestration/tests/test_reference_dogfood_cli.py] [Source: _bmad-output/release-evidence/four-worker-dogfood-report.md]
  - [x] Write the current setup validation report and the release-gate verification report so the release package contains both the gate inputs and the final gate decision. The release-gate report must link or reference the generated evidence files and preserve exact commands, outcomes, and any blocking gaps.  
        [Source: tools/orchestration/setup.py] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg5] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg6] [Source: _bmad-output/planning-artifacts/evidence-templates/setup-validation-template.md]
  - [x] Update user-facing docs only as needed so the one-command release gate is discoverable from existing setup or release-readiness guidance. Prefer README or existing docs over introducing a parallel documentation surface.  
        [Source: README.md] [Source: docs/getting-started.md] [Source: _bmad-output/project-context.md#code-quality--style-rules]

- [x] Keep Story 8.4 bounded to release readiness. (AC: 4)
  - [x] Do not replace the 8.1 deterministic contract layer, the 8.2 failure-drill layer, or the 8.3 dogfood runner; reuse them and summarize their outputs.  
        [Source: _bmad-output/implementation-artifacts/stories/8-1-build-unit-and-contract-test-coverage-for-controller-and-adapter-invariants.md] [Source: _bmad-output/implementation-artifacts/stories/8-2-build-integration-and-failure-drill-coverage-for-mandatory-failure-classes.md] [Source: _bmad-output/implementation-artifacts/stories/8-3-validate-the-four-worker-reference-dogfood-scenario.md]
  - [x] Do not add a new controller lifecycle or routing model in the name of release reporting. Any production changes must stay narrowly in support of evidence generation, summary output, or safe reuse of existing validation seams.  
        [Source: _bmad-output/planning-artifacts/architecture.md#release-gate-matrix]

- [x] Run and preserve the required validation surfaces. (AC: 1, 2, 3, 5)
  - [x] Run the dedicated release-gate regression suite first so Story 8.4 stays in narrow red-green slices.  
        [Source: _bmad-output/project-context.md#testing-rules]
  - [x] Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused required validation surface.  
        [Source: tools/orchestration/tests]
  - [x] Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.  
        [Source: tools/orchestration/tests]
  - [x] Run `bash tools/tmux_bridge/tests/smoke.sh` if the release gate changes or reuses tmux-backed orchestration helpers.  
        [Source: tools/tmux_bridge/tests/smoke.sh]
  - [x] Use an explicit BMAD QA acceptance pass to compare the story contract, the release-gate command outputs, the evidence package, and the delivered behavior before closing the story.  
        [Source: _bmad-output/project-context.md#testing-rules]

## Dev Notes

### Previous Story Intelligence

- Story 8.3 already created the four-worker runner and RG4 artifact shape. Story 8.4 should call or summarize that path rather than duplicating the scenario with a second harness.  
  [Source: _bmad-output/implementation-artifacts/stories/8-3-validate-the-four-worker-reference-dogfood-scenario.md]
- Story 8.2 established the dedicated failure-drill layer for the mandatory failure classes but intentionally stopped short of release-evidence packaging. Story 8.4 should preserve that release-oriented suite as the source of truth for RG2.  
  [Source: _bmad-output/implementation-artifacts/stories/8-2-build-integration-and-failure-drill-coverage-for-mandatory-failure-classes.md]
- Story 8.1 added the deterministic controller-invariant and adapter-contract seams plus the shared `qualification_gate(...)` helper. Story 8.4 should build RG1 and any deterministic restart checks from those seams instead of broadening the failure-drill layer to cover everything.  
  [Source: _bmad-output/implementation-artifacts/stories/8-1-build-unit-and-contract-test-coverage-for-controller-and-adapter-invariants.md]

### Brownfield Reuse Guidance

- `tools/orchestration/setup.py` already owns read-only validation construction and evidence-friendly data shapes for setup. Extend that surface before inventing a second release-reporting subsystem.  
  [Source: tools/orchestration/setup.py]
- `tools/orchestration/cli/main.py` already routes setup validation and human-readable validation output. Keep any new operator surface compact and consistent with the current validation emit path.  
  [Source: tools/orchestration/cli/main.py]
- `tools/orchestration/adapters/base.py` and `tools/orchestration/adapters/registry.py` already expose the shared contract, validation commands, release-gate criteria, unsupported features, and qualification gate. Use those facts directly for RG1 reporting.  
  [Source: tools/orchestration/adapters/base.py] [Source: tools/orchestration/adapters/registry.py]
- `tools/orchestration/tests/test_failure_drills_cli.py` already names the mandatory failure classes in a release-oriented dedicated suite. Prefer a narrow evidence runner or subprocess wrapper around that suite instead of re-encoding failure classes in a new bespoke checker.  
  [Source: tools/orchestration/tests/test_failure_drills_cli.py]
- `tools/orchestration/tests/test_setup_init.py`, `tools/orchestration/tests/test_controller_invariants.py`, and `tools/orchestration/recovery.py` already hold the current restart-recovery state shapes and invariants. Reuse those seams for RG3 proof and reporting.  
  [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/tests/test_controller_invariants.py] [Source: tools/orchestration/recovery.py]
- `tools/orchestration/dogfood.py` already knows how to write the RG4 report plus machine-readable supporting artifacts. Reuse that helper instead of shelling out to an ad hoc markdown writer.  
  [Source: tools/orchestration/dogfood.py]

### Technical Requirements

- Keep the release gate repo-local, stdlib-only, and controller-owned.
- Prefer one release-gate invocation on the existing setup validation path.
- Produce both human-readable and `--json` summaries with the same gate conclusions.
- Refresh missing or stale release-evidence artifacts instead of silently trusting prior committed files.
- Keep exact commands, report paths, outcomes, and blocking gaps visible in the gate output.

### Architecture Compliance Notes

- The release gate must prove all four Architecture release conditions together: full pass on mandatory failure classes, adapter contract pass for all four first-class adapters, successful four-worker reference scenario, and restart recovery invariant verification.  
  [Source: _bmad-output/planning-artifacts/architecture.md#release-gate-matrix]
- The test harness design still applies: use isolated tmux sockets where tmux-backed runners are involved, store event traces for assertions, and support `--json` output for black-box validation.  
  [Source: _bmad-output/planning-artifacts/architecture.md#test-harness-design]
- The evidence package must stay traceable to the release-readiness matrix rather than to ad hoc operator judgment.  
  [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md]

### File Structure Requirements

- Prefer extending or adding these files before introducing anything broader:
  - `tools/orchestration/setup.py`
  - `tools/orchestration/cli/main.py`
  - `tools/orchestration/adapters/base.py`
  - `tools/orchestration/adapters/registry.py`
  - `tools/orchestration/dogfood.py`
  - `tools/orchestration/tests/test_setup_init.py`
  - `tools/orchestration/tests/test_failure_drills_cli.py`
  - `tools/orchestration/tests/test_reference_dogfood_cli.py`
  - `tools/orchestration/tests/test_release_gate_cli.py`
  - `_bmad-output/release-evidence/adapter-qualification/`
  - `_bmad-output/release-evidence/failure-mode-matrix-report.md`
  - `_bmad-output/release-evidence/restart-recovery-verification-report.md`
  - `_bmad-output/release-evidence/setup-validation-report.md`
  - `_bmad-output/release-evidence/release-gate-command-verification.md`
- Add a small shared helper module only if release-evidence writing or orchestration of the existing suites would otherwise be duplicated heavily.

### Testing Requirements

- Run `python3 -m unittest tools.orchestration.tests.test_release_gate_cli` if a dedicated release-gate module is added.
- Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused required validation surface.
- Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.
- Run `bash tools/tmux_bridge/tests/smoke.sh` before marking the story done if Story 8.4 touches tmux-backed harness behavior.

### Git Intelligence Summary

- Recent Epic 8 work landed in narrow slices and kept each story bounded to one release-gated layer. Story 8.4 should follow that pattern and aggregate the existing seams instead of reopening earlier story scope.
- The repo currently has committed RG4 evidence but no committed RG1 through RG3 package. The release gate therefore needs to materialize or refresh those artifacts instead of only linking to files that do not exist yet.
- The safest 8.4 path is one validation-style command that reuses current helpers, runners, and tests, writes the release package under `_bmad-output/release-evidence/`, and exposes the final pass or fail decision without creating a second control plane.

### Implementation Guardrails

- Do not add a new top-level `release` family unless the operator CLI contract itself is intentionally revised as part of accepted scope.
- Do not let the release gate report success solely because an old markdown file exists; refresh or verify the underlying evidence first.
- Do not duplicate the dogfood flow, failure-drill assertions, or adapter contract declarations in a second disconnected implementation.
- Do not broaden Story 8.4 into new lifecycle semantics, hosted infrastructure, or third-party reporting dependencies.
- Do not let tmux-backed validation contaminate the user’s live tmux environment.

### Project Structure Notes

- This remains a brownfield local-host orchestration repo with controller truth in repo-local SQLite state and transport via tmux.
- Story 8.4 is the packaging and release-decision layer above the already-delivered controller, adapter, failure-drill, and dogfood seams.
- The highest-value increment is a single operator-visible release gate that generates an auditable evidence package and a crisp final readiness summary.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/release-readiness-evidence-matrix.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/planning-artifacts/sprint-plan-2026-04-09.md`
- `_bmad-output/planning-artifacts/evidence-templates/index.md`
- `_bmad-output/planning-artifacts/evidence-templates/adapter-qualification-template.md`
- `_bmad-output/planning-artifacts/evidence-templates/failure-drill-report-template.md`
- `_bmad-output/planning-artifacts/evidence-templates/setup-validation-template.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/stories/8-1-build-unit-and-contract-test-coverage-for-controller-and-adapter-invariants.md`
- `_bmad-output/implementation-artifacts/stories/8-2-build-integration-and-failure-drill-coverage-for-mandatory-failure-classes.md`
- `_bmad-output/implementation-artifacts/stories/8-3-validate-the-four-worker-reference-dogfood-scenario.md`
- `tools/orchestration/setup.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/adapters/registry.py`
- `tools/orchestration/recovery.py`
- `tools/orchestration/dogfood.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_controller_invariants.py`
- `tools/orchestration/tests/test_failure_drills_cli.py`
- `tools/orchestration/tests/test_reference_dogfood_cli.py`
- `tools/tmux_bridge/tests/smoke.sh`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add the release-gate regression seam first and drive the missing command and evidence surfaces red before touching production code.
- Reuse the existing setup validation, adapter qualification, failure-drill, restart-recovery, and dogfood helpers to build one auditable release package.
- Finish with the required validation surfaces, any needed smoke coverage, and an explicit BMAD QA acceptance pass before marking the story done.

### Story Creation Notes

- Skill used: `bmad-create-story`
- Target story auto-discovered from `sprint-status.yaml` after Story 8.3 was completed; Epic 8 retrospective is not due because Epic 8 remains in progress.
- Inputs reviewed for this story: Epic 8.4 story definition, architecture release-gate matrix and test-harness design, operator CLI contract, sprint-plan release criteria, release-readiness evidence matrix, setup validation template, adapter qualification template, Stories 8.1 through 8.3 learnings, current setup validation seams, current adapter contract and qualification helpers, current failure-drill suite, current restart-recovery tests, current dogfood runner, and current release-evidence directory state.
- Validation pass applied against `.agents/skills/bmad-create-story/checklist.md`: the story now includes the frozen-CLI guardrail, the missing requirement to generate current RG1 through RG6 evidence, brownfield reuse guidance for existing release seams, explicit anti-scope boundaries against reopening earlier Epic 8 work, and the required validation surface for the dedicated release-gate regression seam.

### Debug Log References

- Story creation validation performed against `.agents/skills/bmad-create-story/checklist.md`
- `python3 -m unittest tools.orchestration.tests.test_release_gate_cli`
- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init`
- `python3 -m unittest discover -s tools/orchestration/tests`
- `bash tools/tmux_bridge/tests/smoke.sh`
- `python3 -m tools.orchestration.cli.main --repo /home/codexuser/macs_dev setup validate --release-gate --json`
- `python3 -m tools.orchestration.cli.main --repo /home/codexuser/macs_dev setup validate --release-gate`
- BMAD QA acceptance pass executed against Story 8.4 contract, the new release-gate regression suite, the generated release-evidence package, and the delivered operator outputs.

### Completion Notes List

- Added `tools.orchestration.release_gate` as the bounded Phase 1 release-gate aggregator behind `macs setup validate --release-gate`, reusing setup validation, adapter qualification, failure-drill coverage, restart-recovery verification, and the four-worker dogfood runner.
- Generated the release-evidence package under `_bmad-output/release-evidence/`, including setup validation, adapter qualification reports, the failure-mode matrix report, the restart-recovery verification report, the refreshed RG4 dogfood pack, and the final release-gate verification plus summary JSON.
- Hardened the dogfood runner so release-gate execution does not inherit outer tmux session variables and so revision metadata degrades safely when `git` is unavailable on `PATH`.
- Updated README and getting-started guidance so the release gate is discoverable from the existing setup and testing documentation paths.
- Explicit BMAD QA acceptance pass found one final read-side gap: the release-gate command was only showing the failure matrix as a single aggregate status. I fixed that by surfacing per-adapter and per-failure-class statuses in the release-gate output and reran the full required validation surface.
- The committed release-gate run on this repo completed with overall outcome `PARTIAL` because the current local repo has no registered ready workers and does not expose all enabled runtime binaries on `PATH`; adapter qualification, failure-mode matrix, restart recovery, and reference dogfood all passed.

### File List

- `_bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md`
- `_bmad-output/release-evidence/adapter-qualification/claude-qualification-report.md`
- `_bmad-output/release-evidence/adapter-qualification/codex-qualification-report.md`
- `_bmad-output/release-evidence/adapter-qualification/gemini-qualification-report.md`
- `_bmad-output/release-evidence/adapter-qualification/local-qualification-report.md`
- `_bmad-output/release-evidence/failure-mode-matrix-report.md`
- `_bmad-output/release-evidence/four-worker-dogfood-artifacts/four-worker-dogfood-command-log.json`
- `_bmad-output/release-evidence/four-worker-dogfood-artifacts/four-worker-dogfood-pane-captures.json`
- `_bmad-output/release-evidence/four-worker-dogfood-artifacts/four-worker-dogfood-summary.json`
- `_bmad-output/release-evidence/four-worker-dogfood-report.md`
- `_bmad-output/release-evidence/release-gate-command-verification.md`
- `_bmad-output/release-evidence/release-gate-summary.json`
- `_bmad-output/release-evidence/restart-recovery-verification-report.md`
- `_bmad-output/release-evidence/setup-validation-report.md`
- `README.md`
- `docs/getting-started.md`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/dogfood.py`
- `tools/orchestration/release_gate.py`
- `tools/orchestration/tests/test_release_gate_cli.py`

### Change Log

- 2026-04-10: Created Story 8.4 with release-gate scope, existing-CLI guardrails, missing evidence-package requirements, brownfield reuse guidance, and the required validation surface.
- 2026-04-10: Implemented the release-gate command and evidence package, generated the committed release-evidence artifacts, updated the setup/readiness docs, ran the required validations, and completed the explicit BMAD QA acceptance pass.
- 2026-04-10: Fixed the BMAD QA acceptance finding by exposing per-adapter and per-failure-class release-gate statuses, then reran the required validation surface.
