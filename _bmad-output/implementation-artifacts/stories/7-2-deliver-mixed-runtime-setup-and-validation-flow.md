# Story 7.2: Deliver mixed-runtime setup and validation flow

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a technical adopter,
I want a documented setup path that registers and validates mixed runtimes on one local host,
So that I can reach a safe ready state in a real repository without reverse-engineering MACS internals.

## Acceptance Criteria

1. `macs setup validate` exists and validates repo-local adoption state end to end. The command checks repo-local orchestration bootstrap, config-domain visibility, local dependency readiness, enabled-adapter availability, current worker registration and readiness, and routing-default visibility, then reports a stable `PASS | FAIL | PARTIAL | BLOCKED` style outcome in human-readable and `--json` output without requiring operators to inspect raw files or internal tables.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-72-deliver-mixed-runtime-setup-and-validation-flow] [Source: _bmad-output/planning-artifacts/prd.md#installation-configuration-and-adoption] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#soft-nfr-matrix] [Source: _bmad-output/planning-artifacts/evidence-templates/setup-validation-template.md]
2. `macs setup dry-run` provides a conservative, read-only onboarding path. The command shows the exact repo-local steps, checks, and example commands an adopter should run next for controller bootstrap, worker discovery or registration, routing-default inspection, readiness validation, intervention, and recovery, with no controller-state mutation beyond bootstrap reads.  
   [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#adopter-setup-and-onboarding] [Source: _bmad-output/project-context.md#critical-implementation-rules]
3. The setup flow makes supported runtime status and safe-ready-state legible. Validation output distinguishes enabled adapters, runtime binary availability, registered workers, ready workers, degraded-capable but incomplete states, and blocking gaps, while preserving the controller-authority boundary and avoiding any assumption that runtime presence alone proves safety.  
   [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/planning-artifacts/architecture.md#architectural-principles] [Source: _bmad-output/project-context.md#critical-dont-miss-rules]
4. Docs and reference examples cover the real setup flow. `README.md` and `docs/getting-started.md` document a runnable mixed-runtime local-host path using the current repo-local config domains plus explicit example commands for registration, intervention, and recovery, and the examples align with the actual CLI behavior instead of aspirational contract text.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-72-deliver-mixed-runtime-setup-and-validation-flow] [Source: _bmad-output/planning-artifacts/prd.md#installation-configuration-and-adoption] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#adopter-setup-and-onboarding]
5. Setup validation output is evidence-friendly for release readiness without claiming to be the final release package. The command surfaces the core fields needed to populate the existing setup-validation template and the release-readiness NFR15 or RG6 evidence path, but Story 7.2 stops short of generating final release artifacts or broad qualification reports automatically.  
   [Source: _bmad-output/planning-artifacts/evidence-templates/setup-validation-template.md] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#soft-nfr-matrix] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#release-gate-expectation-matrix]
6. Regression coverage proves the setup and validation flow without regressing Story 7.1 config separation, Story 6.x governance and decision-rights behavior, or the frozen setup command family and JSON envelopes.  
   [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md] [Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md]

## Tasks / Subtasks

- [x] Add a shared setup-validation read model for adoption readiness. (AC: 1, 3, 5)
  - [x] Add a narrow helper in `tools/orchestration/` that inspects repo-local config domains, local dependency availability, enabled adapter settings, current workers, readiness state, and routing-default visibility without introducing non-stdlib dependencies.  
        [Source: tools/orchestration/config.py] [Source: tools/orchestration/session.py] [Source: tools/orchestration/workers.py]
  - [x] Map validation status to clear outcomes such as `PASS`, `PARTIAL`, `FAIL`, or `BLOCKED`, and include explicit gaps or next actions rather than vague success text.  
        [Source: _bmad-output/planning-artifacts/evidence-templates/setup-validation-template.md] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#soft-nfr-matrix]
  - [x] Reuse existing adapter descriptors and repo-local adapter settings; do not create a second adapter qualification subsystem in Story 7.2.  
        [Source: tools/orchestration/adapters/registry.py] [Source: _bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md]

- [x] Implement `macs setup validate` and `macs setup dry-run` on the current setup command family. (AC: 1, 2, 5)
  - [x] Add contract-listed `setup validate` and `setup dry-run` verbs in `tools/orchestration/cli/main.py`, keeping human-readable and `--json` output compact and envelope-stable.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: tools/orchestration/cli/main.py]
  - [x] Make `setup validate` surface controller facts, adapter/runtime availability, worker readiness summaries, routing-default visibility, and explicit example commands or evidence refs relevant to safe-ready-state validation.  
        [Source: _bmad-output/planning-artifacts/evidence-templates/setup-validation-template.md] [Source: tools/orchestration/cli/main.py]
  - [x] Make `setup dry-run` read-only and procedural: it should show the exact conservative order for bootstrap, discovery, registration, readiness validation, routing inspection, intervention example, and recovery example without mutating controller ownership or worker records.  
        [Source: _bmad-output/planning-artifacts/ux-design-specification.md#adopter-setup-and-onboarding] [Source: _bmad-output/project-context.md#code-quality--style-rules]

- [x] Keep setup validation controller-owned and bounded. (AC: 2, 3, 5)
  - [x] Do not auto-install runtimes, create hosted dependencies, or silently register workers on the operator’s behalf.  
        [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/project-context.md#framework-specific-rules]
  - [x] Do not treat `command -v` or pane existence as sufficient proof of runtime safety; combine dependency visibility with existing worker and controller facts.  
        [Source: _bmad-output/project-context.md#critical-dont-miss-rules] [Source: tools/orchestration/health.py]
  - [x] Do not broaden Story 7.2 into single-worker migration compatibility notes or contributor adapter qualification guidance; those belong to Stories 7.3 and 7.4.  
        [Source: _bmad-output/planning-artifacts/epics.md#story-73-preserve-and-document-single-worker-compatibility-boundaries] [Source: _bmad-output/planning-artifacts/epics.md#story-74-publish-contributor-facing-adapter-guidance]

- [x] Document the real mixed-runtime setup path and examples. (AC: 4, 5)
  - [x] Update `README.md` and `docs/getting-started.md` to describe the setup flow in the same conservative order that `setup dry-run` reports.  
        [Source: README.md] [Source: docs/getting-started.md]
  - [x] Include explicit example commands for worker registration, readiness validation, routing-default inspection, intervention, and recovery.  
        [Source: _bmad-output/planning-artifacts/epics.md#story-72-deliver-mixed-runtime-setup-and-validation-flow] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#adopter-setup-and-onboarding]
  - [x] Keep the docs aligned with the existing setup-validation template so release-evidence work later can reuse the same structure without ad hoc interpretation.  
        [Source: _bmad-output/planning-artifacts/evidence-templates/setup-validation-template.md]

- [x] Add regression coverage for validation outcomes, dry-run guidance, and evidence-friendly setup output. (AC: 6)
  - [x] Extend `tools/orchestration/tests/test_setup_init.py` with cases for `setup validate` and `setup dry-run`, including incomplete bootstrap, partial readiness, and safe-ready-state success surfaces.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: _bmad-output/planning-artifacts/architecture.md#test-layers]
  - [x] Extend existing CLI tests only where needed to prove the docs and setup examples align with current command behavior rather than creating a parallel test harness.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: tools/orchestration/tests/test_inspect_context_cli.py]
  - [x] Preserve setup-family JSON envelope stability and Story 7.1 config-domain behavior while adding validation or dry-run output.  
        [Source: _bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md]

## Dev Notes

### Previous Story Intelligence

- Story 7.1 already bootstrapped repo-local config domains and added `macs setup check`. Story 7.2 should build on those config files and surfaces rather than reopening configuration separation work.  
  [Source: _bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md]
- Story 7.1 also made adapter enablement fail closed. Setup validation must surface disabled-adapter state clearly instead of trying to bypass repo-local settings during onboarding.  
  [Source: _bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md]
- The UX and release-readiness artifacts already expect a safe dry-run path plus evidence-friendly setup validation. Story 7.2 should make those expectations concrete on the existing setup command family.  
  [Source: _bmad-output/planning-artifacts/ux-design-specification.md#adopter-setup-and-onboarding] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#soft-nfr-matrix]

### Brownfield Reuse Guidance

- `tools/orchestration/cli/main.py` already owns `setup init` and `setup check`; extend the same command family for validate and dry-run before inventing a second onboarding surface.  
  [Source: tools/orchestration/cli/main.py]
- `tools/orchestration/config.py` and `tools/orchestration/session.py` already expose config-domain and path information needed for setup validation. Reuse those outputs instead of re-reading the filesystem ad hoc in multiple places.  
  [Source: tools/orchestration/config.py] [Source: tools/orchestration/session.py]
- `tools/orchestration/adapters/registry.py` and adapter descriptors already carry qualification and unsupported-feature metadata. Reuse those fields for setup visibility rather than creating a separate runtime capability manifest in this story.  
  [Source: tools/orchestration/adapters/registry.py] [Source: tools/orchestration/adapters/base.py]
- `tools/orchestration/tests/test_setup_init.py` is already the high-signal regression surface for bootstrap and onboarding behavior. Prefer extending it over adding a new test module.  
  [Source: tools/orchestration/tests/test_setup_init.py]

### Technical Requirements

- Keep the setup flow local-host-first and repo-local. No hosted services, background daemons, or remote validation calls.
- Use stdlib-only detection for runtime availability, such as `shutil.which`, and keep the signals explicitly labeled as controller facts vs. runtime availability hints.
- Preserve the setup-family command contract and stable `--json` envelopes.
- `setup dry-run` must be read-only.
- `setup validate` may refresh controller-owned readiness signals if needed, but it must not perform destructive or side-effectful orchestration actions.

### Architecture Compliance Notes

- Validation must remain controller-owned. Adapters and runtime binaries can provide evidence of availability, but they do not define setup truth by themselves.
- Keep setup guidance conservative: show gaps and next actions rather than assuming a machine is ready because one runtime is installed.
- Preserve canonical nouns and the current CLI family structure.

### File Structure Requirements

- Prefer extending these files before introducing new modules:
  - `tools/orchestration/cli/main.py`
  - `tools/orchestration/config.py`
  - `tools/orchestration/session.py`
  - `tools/orchestration/adapters/registry.py`
  - `tools/orchestration/tests/test_setup_init.py`
  - `README.md`
  - `docs/getting-started.md`
- Add a small `tools/orchestration/setup.py` helper only if the validation and dry-run read model becomes materially clearer there.

### Testing Requirements

- Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused required validation surface.
- Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.
- Add coverage for blocked validation before bootstrap, partial readiness due to missing runtimes or workers, success output for safe-ready-state, and dry-run example stability.
- Preserve Story 7.1 setup check and config-domain regressions while adding new setup verbs.

### Git Intelligence Summary

- `c3ccc6a` resolved recent review findings while continuing to extend controller-owned seams rather than introducing new subsystems.
- `51d2554` and `e474089` still point to repo-local bootstrap and setup-family behavior as the preferred place for onboarding improvements.
- The safest 7.2 path is to keep the work in `cli/main.py`, current config/bootstrap helpers, docs, and existing setup tests.

### Implementation Guardrails

- Do not implement real runtime installers, credential setup, or automatic worker registration.
- Do not turn setup validation into adapter qualification; qualification and contributor guidance belong later.
- Do not broaden into Story 7.3 compatibility migration docs beyond preserving the current compatibility paths and referencing them accurately.
- Do not add third-party Python dependencies or external service calls.

### Project Structure Notes

- This remains a brownfield, shell-first orchestration controller.
- Story 7.2 should feel like the operator-facing adoption layer on top of Story 7.1’s config separation: validate, guide, and document the real setup path.
- The highest-value increment is an evidence-friendly validation summary plus a dry-run command and docs that match it.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/planning-artifacts/evidence-templates/setup-validation-template.md`
- `_bmad-output/planning-artifacts/release-readiness-evidence-matrix.md`
- `_bmad-output/planning-artifacts/sprint-plan-2026-04-09.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/config.py`
- `tools/orchestration/session.py`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/adapters/codex.py`
- `tools/orchestration/adapters/registry.py`
- `tools/orchestration/tests/test_setup_init.py`
- `README.md`
- `docs/getting-started.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add a small setup-validation read model first, then wire `setup validate` and `setup dry-run` through the current setup-family CLI.
- Prove the blocked and partial cases before the success path, then align docs and examples with the real command behavior.
- Finish with the required test surfaces and an explicit BMAD QA acceptance pass before marking the story done.

### Story Creation Notes

- Skill used: `bmad-create-story`
- Target story auto-discovered from `sprint-status.yaml` after Story 7.1 was completed.
- Inputs reviewed for this story: Epic 7.2 story definition, PRD installation and adoption requirements, UX adopter-onboarding flow, release-readiness NFR15 and RG6 setup-evidence expectations, the setup-validation evidence template, Story 7.1 completion notes, current git history, the live setup-family CLI seams, adapter descriptors, and current setup tests and docs.
- Validation pass applied against `.agents/skills/bmad-create-story/checklist.md`: the story now includes the missing contract-listed `setup validate` and `setup dry-run` surfaces, evidence-template alignment, anti-scope boundaries against Stories 7.3 and 7.4, and concrete regression expectations for blocked, partial, and success setup-validation states.

### Debug Log References

- Story creation validation performed against `.agents/skills/bmad-create-story/checklist.md`
- Focused validation: `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init`
- Full regression validation: `python3 -m unittest discover -s tools/orchestration/tests`
- Explicit BMAD QA acceptance pass completed against Story 7.2 acceptance criteria, docs alignment, and blocked/PARTIAL/PASS setup status reporting.

### Completion Notes List

- Added `tools/orchestration/setup.py` as the shared read-only setup helper for config snapshots, bootstrap checks, dry-run guidance, and evidence-friendly validation summaries.
- Added `macs setup validate` and `macs setup dry-run` to the existing setup command family with human-readable and `--json` output, including explicit `PASS`, `PARTIAL`, `FAIL`, and `BLOCKED` setup status reporting.
- Updated `README.md` and `docs/getting-started.md` to document the conservative mixed-runtime onboarding path, explicit worker-registration examples, and intervention or recovery follow-up commands.
- Added setup regressions for blocked validation, dry-run guidance, PARTIAL readiness, PASS safe-ready-state, and human-readable output surfaces.
- BMAD QA acceptance found one final contract gap in blocked `setup validate` status visibility; that gap was fixed and regression-covered before marking the story done.

### File List

- `_bmad-output/implementation-artifacts/stories/7-2-deliver-mixed-runtime-setup-and-validation-flow.md`
- `README.md`
- `docs/getting-started.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/setup.py`
- `tools/orchestration/tests/test_setup_init.py`

### Change Log

- 2026-04-10: Created Story 7.2 with setup-validation, dry-run, evidence-alignment, docs, and regression scope under Epic 7 adoption flow.
- 2026-04-10: Implemented Story 7.2, passed required validation, completed an explicit BMAD QA acceptance pass, and fixed the final blocked-status reporting gap before marking done.
