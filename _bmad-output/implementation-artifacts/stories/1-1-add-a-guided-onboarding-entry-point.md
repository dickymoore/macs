# Story 1.1: Add a guided onboarding entry point

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a technical adopter,
I want a guided onboarding command under `macs setup`,
so that I can start from the canonical MACS setup surface instead of piecing together several commands manually.

## Acceptance Criteria

1. Given the current MACS CLI is installed in the repo, when I run `macs setup guide`, then the command resolves through the existing setup-family parser and returns a read-only onboarding briefing instead of failing with an unknown verb.  
   [Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-11-add-a-guided-onboarding-entry-point] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#cli-command-surface]
2. Given I run `macs setup guide --json`, when the command completes, then it returns through the existing setup-family JSON/result conventions and exposes guide data without mutating repo-local controller state.  
   [Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-11-add-a-guided-onboarding-entry-point] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#cli-command-surface] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#safety--governance-boundaries]
3. The guide output makes explicit which recommended commands are read-only versus state-changing follow-ups, using canonical MACS command vocabulary and keeping operator execution explicit.  
   [Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-11-add-a-guided-onboarding-entry-point] [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#guided-onboarding-entry--orientation] [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#governance--safety-boundaries] [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#terminal-specific-tokens]
4. Story 1.1 stays within the guided-onboarding entry-point slice: it establishes the `guide` command and the minimal read-only briefing scaffold without duplicating setup logic or pre-implementing later story scope for full state interpretation, full controller-model explanation, canonical doc-link parity, narrow/no-color polish, or the final stable JSON guidance contract.  
   [Inference from: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#epic-1-start-guided-onboarding-from-the-existing-setup-surface and _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#epic-3-keep-guided-onboarding-canonical-across-docs-terminals-and-automation and _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#epic-4-preserve-authoritative-onboarding-behavior-over-time and _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#read-model-composition]

## Tasks / Subtasks

- [x] Wire the new `guide` verb into the existing setup-family parser and dispatch path. (AC: 1, 2)
  - [x] Add `guide` to the `setup` subparser family in `tools/orchestration/cli/main.py`, matching the current `macs <family> <verb>` grammar and the hidden after-subcommand `--json` pattern used by the other setup verbs.  
        [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#cli-command-surface] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#contract-decisions]
  - [x] Implement `handle_setup_guide` through the existing setup-family command/result flow instead of creating a parallel onboarding entrypoint.  
        [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#structure-patterns] [Source: docs/contributor-guide.md#contribution-workflow]

- [x] Build a minimal read-only guide view model in the current setup read-model module. (AC: 1, 2, 3, 4)
  - [x] Add `build_setup_guide(repo_root, paths)` in `tools/orchestration/setup.py` and compose it from current read-only helpers such as `build_setup_dry_run`, `build_setup_validation`, `build_setup_configuration_snapshot`, and `missing_setup_paths` rather than re-implementing setup semantics.  
        [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#read-model-composition] [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#maintainability--testability]
  - [x] Ensure the guide works on a fresh repo before bootstrap as a read-only briefing and can recommend `macs setup init` as the explicit next operator action without creating `.codex/orchestration/` on its own.  
        [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#journey-1-fresh-repo-not-yet-bootstrapped] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#safety--governance-boundaries]
  - [x] Keep the initial guide payload intentionally narrow: enough for the entry-point briefing and read-only/action labeling now, but shaped so later stories can extend the same model in place.  
        [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#guidance-view-model] [Inference from: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-12-summarize-controller-owned-onboarding-state and _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-13-present-the-controller-model-and-conservative-order and _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-33-provide-stable-json-guidance-output]

- [x] Render guide output through current MACS CLI conventions for both human-readable and JSON modes. (AC: 2, 3, 4)
  - [x] Add human-readable rendering that behaves like a compact operational briefing, not a wizard, and keeps command recommendations copy-pasteable.  
        [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#chosen-direction] [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#typography--layout]
  - [x] Mark follow-up commands explicitly as read-only versus state-changing using direct textual labels such as `[READ-ONLY]` and `[ACTION]`, or an equally explicit equivalent consistent with current CLI output.  
        [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#terminal-specific-tokens] [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#guided-onboarding-entry--orientation]
  - [x] Preserve the current top-level JSON envelope from `emit_setup_result`; add guide-specific data inside `data` rather than inventing a second JSON contract.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required---json-output] [Source: tools/orchestration/cli/main.py]

- [x] Add regression coverage through the existing setup-family test seam. (AC: 1, 2, 3, 4)
  - [x] Extend `tools/orchestration/tests/test_setup_init.py` with guide tests instead of creating a dedicated onboarding-only harness.  
        [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#testing--validation-strategy] [Source: docs/contributor-guide.md#contribution-workflow]
  - [x] Add a test that `macs setup guide` succeeds before bootstrap and remains read-only by leaving `.codex/orchestration/` absent.  
        [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#journey-1-fresh-repo-not-yet-bootstrapped] [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#governance--safety-boundaries]
  - [x] Add JSON coverage for `macs setup guide --json` and human-readable coverage for explicit read-only versus mutating follow-up labels.  
        [Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-11-add-a-guided-onboarding-entry-point] [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#output-modes--accessibility]

- [x] Keep the shipped live surface truthful without pulling forward later documentation work. (AC: 1, 4)
  - [x] Update CLI help text and only the minimal immediate docs/examples required if the new verb becomes operator-visible in the current release surface.  
        [Source: docs/contributor-guide.md#documentation-maintenance-rules] [Source: docs/contributor-guide.md#when-to-touch-which-docs]
  - [x] Defer full guide-to-doc reference mapping and broader docs parity work to Story 3.1.  
        [Inference from: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-31-link-guided-output-to-canonical-docs-and-examples]

### Review Follow-ups (AI)

- [x] [AI-Review][medium] Derive `build_setup_guide` next-action recommendations from the validation result so registered-but-not-ready workers receive the controller-owned remediation instead of a validate loop.
- [x] [AI-Review][low] Update `docs/user-guide.md` and `docs/contributor-guide.md` so the shipped docs surface includes the `macs setup guide` verb.
- [x] [AI-Review][low] Extend `tools/orchestration/tests/test_setup_init.py` with post-bootstrap guide regressions for partial and ready states.

## Dev Notes

### Story Intent

This story is the command-entry slice for the guided-onboarding initiative. Its job is to make `macs setup guide` a real, read-only MACS surface that operators can invoke from the canonical setup family on both fresh and already-bootstrapped repos. It should establish the command seam and minimal briefing scaffold now, while leaving the richer state summary and explanation layers for the next Epic 1 stories.

[Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#epic-1-start-guided-onboarding-from-the-existing-setup-surface]  
[Source: _bmad-output/planning-artifacts/product-brief-macs-guided-onboarding.md]  
[Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#journey-1-fresh-repo-not-yet-bootstrapped]

### Epic Continuity

- Story 1.2 adds the controller-owned onboarding state summary and readiness facts.
- Story 1.3 adds the concise controller-model explanation and conservative setup order explanation.
- Story 3.1 later handles canonical doc/example linkage and docs parity.
- Story 3.2 later hardens narrow-terminal and `NO_COLOR` readability.
- Story 3.3 later freezes the full stable JSON guidance surface.
- Story 4.1 and Story 4.2 later harden read-only boundaries and blocked/partial/pass regression coverage.

Implementation consequence: build the `guide` seam once, in the files that already own setup behavior, so later stories can extend it in place instead of relocating logic.

[Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-12-summarize-controller-owned-onboarding-state]  
[Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-13-present-the-controller-model-and-conservative-order]  
[Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-31-link-guided-output-to-canonical-docs-and-examples]  
[Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-32-render-guided-onboarding-for-narrow-and-no-color-terminals]  
[Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-33-provide-stable-json-guidance-output]  
[Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-41-preserve-read-only-boundaries-in-guided-onboarding]  
[Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-42-regression-cover-blocked-partial-and-pass-guide-states]

### Brownfield Baseline

- `macs` is a thin bash wrapper that dispatches into `python3 -m tools.orchestration.cli.main --repo "$ROOT_DIR"`.
- `tools/orchestration/cli/main.py` already owns the setup-family parser and command dispatch for `init`, `check`, `validate`, and `dry-run`.
- `tools/orchestration/setup.py` already owns the read-only onboarding inputs this feature must reuse: configuration snapshot, conservative dry-run path, readiness validation, and missing-path detection.
- `emit_setup_result` already enforces the current setup-family human-readable and `--json` output envelope.
- `tools/orchestration/cli/rendering.py` already provides width-aware helpers if the new guide needs small reusable rendering support.
- `tools/orchestration/tests/test_setup_init.py` is already the established regression seam for setup-family CLI behavior.

[Source: macs]  
[Source: tools/orchestration/cli/main.py]  
[Source: tools/orchestration/setup.py]  
[Source: tools/orchestration/cli/rendering.py]  
[Source: tools/orchestration/tests/test_setup_init.py]  
[Source: docs/contributor-guide.md#repository-map]

### Technical Requirements

- Stay repo-local, local-host-first, and read-only in all guide modes. Running `guide` must not create controller state or mutate repo-local config.  
  [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#governance--safety-boundaries] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#safety--governance-boundaries]
- Reuse existing setup/readiness read models wherever possible; do not create a second onboarding engine or duplicate readiness logic.  
  [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#maintainability--testability] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#read-model-composition]
- Keep the implementation in Python 3.8+ stdlib and current shell/Python seams; do not introduce third-party dependencies for this CLI slice.  
  [Source: _bmad-output/project-context.md#technology-stack--versions]
- Preserve canonical MACS command vocabulary and the existing `macs <family> <verb>` structure.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#contract-decisions] [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#consistency--traceability]
- Treat runtime binaries on `PATH` as hints and controller facts as authority whenever the guide references current setup state.  
  [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#user-journeys] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#communication-patterns]

### Architecture Compliance

- `tools/orchestration/setup.py` should own `build_setup_guide` and any derived onboarding guidance logic.  
  [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#architectural-boundaries]
- `tools/orchestration/cli/main.py` should own parser registration, handler dispatch, and final rendering for `guide`.  
  [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#architectural-boundaries]
- If a small helper is needed for layout or markers, keep it adjacent to the current CLI rendering helpers; do not create a new onboarding package or shadow subsystem.  
  [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#structure-patterns]
- Use the command-led operational briefing pattern, not a step-by-step wizard or hidden automation flow.  
  [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#chosen-direction]
- Do not add new persistence files, onboarding config files, or a separate docs tree for this feature.  
  [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#file-structure-patterns]
- Keep one primary next action first and label whether follow-up commands are read-only or state-changing.  
  [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#recommendation-rules] [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#next-action-card]

### File Structure Requirements

- Primary code files for this story:
  - `tools/orchestration/cli/main.py`
  - `tools/orchestration/setup.py`
  - `tools/orchestration/tests/test_setup_init.py`
- Optional helper-only touch point if needed:
  - `tools/orchestration/cli/rendering.py`
- Minimal docs/help touch points only if required to keep the shipped command surface truthful:
  - `README.md`
  - `docs/getting-started.md`
  - `docs/how-tos.md`
- Avoid broad guide-doc reference wiring in this story; that belongs to Story 3.1.

[Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#requirements-to-structure-mapping]  
[Source: docs/contributor-guide.md#when-to-touch-which-docs]

### Testing Requirements

- Extend the current setup-family test seam in `tools/orchestration/tests/test_setup_init.py`; do not add an onboarding-only harness.  
  [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#testing--validation-strategy] [Source: docs/contributor-guide.md#contribution-workflow]
- Add coverage that `macs setup guide` succeeds on a fresh repo and remains read-only by not creating `.codex/orchestration/`.  
  [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#journey-1-fresh-repo-not-yet-bootstrapped]
- Add coverage that `macs setup guide --json` uses the existing top-level setup-family JSON envelope and returns guide data under `data`.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required---json-output] [Source: tools/orchestration/cli/main.py]
- Add human-readable coverage that the briefing explicitly labels read-only versus state-changing recommended commands.  
  [Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-11-add-a-guided-onboarding-entry-point] [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#feedback-patterns]
- Keep Story 1.1 test scope focused on command wiring, read-only safety, and explicit labeling. Full blocked/partial/pass matrices, `NO_COLOR`, and 80-column rendering are later-story coverage targets unless an initial implementation choice makes them unavoidable.  
  [Inference from: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-32-render-guided-onboarding-for-narrow-and-no-color-terminals and _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-42-regression-cover-blocked-partial-and-pass-guide-states]

### Implementation Guardrails

- Do not auto-install runtimes, auto-register workers, auto-edit adapter settings, or mutate controller state implicitly.  
  [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#safety--governance-boundaries]
- Do not create onboarding-only status vocabularies, config files, or persistence files.  
  [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#file-structure-patterns] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#outcome-formatting]
- Do not let guide copy outrun controller truth; if guidance and setup logic disagree, the setup logic wins.  
  [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#process-patterns]
- Do not solve Story 1.2, Story 1.3, Story 3.x, or Story 4.x prematurely in this implementation. Build an extendable seam instead.  
  [Inference from: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md]

### Project Structure Notes

- This is a brownfield repo with an already-shipping setup family and a shell wrapper at repo root.
- The safest implementation path is to extend the current setup seam rather than creating a separate onboarding subsystem.
- The guide should feel like a MACS command family member from the first commit, even if later stories deepen the content.

[Source: _bmad-output/project-context.md#development-workflow-rules]  
[Source: docs/contributor-guide.md#before-you-change-anything]  
[Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#selected-foundation-existing-macs-setup-surface]

### References

- `_bmad-output/planning-artifacts/product-brief-macs-guided-onboarding.md`
- `_bmad-output/planning-artifacts/prd-macs-guided-onboarding.md`
- `_bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md`
- `_bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md`
- `_bmad-output/planning-artifacts/epics-macs-guided-onboarding.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/project-context.md`
- `macs`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/setup.py`
- `tools/orchestration/cli/rendering.py`
- `tools/orchestration/tests/test_setup_init.py`
- `README.md`
- `docs/getting-started.md`
- `docs/how-tos.md`
- `docs/contributor-guide.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add guide-focused regression tests to the existing setup-family test seam first and confirm they fail before implementation.
- Wire `macs setup guide` through the current setup-family parser and handler flow in `tools/orchestration/cli/main.py`.
- Build a narrow read-only guide view model in `tools/orchestration/setup.py` by composing the existing dry-run, validation, configuration, and missing-path helpers.
- Keep the initial human-readable output to a compact operational briefing with explicit `[READ-ONLY]` and `[ACTION]` command labels.
- Run targeted setup-family tests, then broader regression coverage, and only then mark story tasks complete.

### Debug Log References

- Story authored with `bmad-create-story`.
- Guided-onboarding initiative artifacts used as the authoritative source set.
- 2026-04-14: Began Story 1.1 implementation under `bmad-dev-story`; the configured default `sprint-status.yaml` does not track this guided-onboarding slice, so the story file remains the authoritative execution record while the initiative-specific sprint ledger is updated separately.
- 2026-04-14: Red phase confirmed with `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_help_lists_guide_verb tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_guide_is_read_only_and_succeeds_before_bootstrap tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_guide_human_readable_labels_commands`; current CLI lacks the `guide` verb and rejects `macs setup guide`.
- 2026-04-14: Implemented `build_setup_guide`, `handle_setup_guide`, human-readable guide rendering, and minimal onboarding doc updates without introducing a parallel onboarding subsystem.
- 2026-04-14: Manual verification completed with `./macs setup guide`, `./macs setup guide --json`, and `./macs setup --help`.
- 2026-04-14: Review follow-up red phase confirmed with `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_guide_is_read_only_and_succeeds_before_bootstrap tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_guide_uses_discover_as_next_action_for_registered_but_not_ready_workers tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_guide_reports_ready_phase_after_bootstrap`; the registered-but-not-ready guide state still looped to `macs setup validate --json`.
- 2026-04-14: Updated `build_setup_guide` to prioritize validation-derived worker remediation, added post-bootstrap guide regressions for partial and ready states, and refreshed `docs/user-guide.md` plus `docs/contributor-guide.md` so the visible docs surface matches the shipped verb.
- 2026-04-14: Finalized Story 1.1 from `review` to `done` after closeout confirmed no actionable review findings remained; this was a records-only BMAD update with no additional code changes.

### Test Record

- 2026-04-14: RED - `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_help_lists_guide_verb tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_guide_is_read_only_and_succeeds_before_bootstrap tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_guide_human_readable_labels_commands` failed because `setup --help` does not list `guide` and the setup parser still rejects `guide` as an unknown verb.
- 2026-04-14: GREEN - the same targeted guide tests passed after wiring the new setup verb and guide output seam.
- 2026-04-14: RED - `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_guide_is_read_only_and_succeeds_before_bootstrap tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_guide_uses_discover_as_next_action_for_registered_but_not_ready_workers tools.orchestration.tests.test_setup_init.SetupInitTests.test_setup_guide_reports_ready_phase_after_bootstrap` failed because the partial post-bootstrap guide state still recommended `macs setup validate --json` instead of the controller-owned discovery remediation.
- 2026-04-14: GREEN - the same targeted post-bootstrap guide tests passed after deriving recommendations from validation-backed worker readiness facts.
- 2026-04-14: PASS - `python3 -m unittest tools.orchestration.tests.test_setup_init`
- 2026-04-14: PASS - `python3 -m unittest discover -s tools/orchestration/tests`

### Completion Notes List

- Added `macs setup guide` to the existing setup-family parser and dispatch flow, including hidden post-verb `--json` support and setup-family help visibility.
- Added a narrow `build_setup_guide(repo_root, paths)` read model that reuses the current dry-run and validation helpers to produce a read-only onboarding briefing without mutating `.codex/orchestration/`.
- Added compact human-readable guide rendering with explicit `[READ-ONLY]` and `[ACTION]` labels and kept the existing setup JSON envelope by returning guide data under `data.guide`.
- Added setup-family regression coverage for help-surface visibility, pre-bootstrap read-only guide behavior, JSON output, and labeled human-readable recommendations.
- Updated only the minimal onboarding docs needed to keep the newly visible `guide` verb truthful in the current shipped surface, while deferring broader guide-to-doc mapping to Story 3.1.
- ✅ Resolved review finding [medium]: `build_setup_guide` now derives the registered-but-not-ready primary recommendation from validation-backed worker readiness facts and promotes `macs worker discover --json` before rerunning validation.
- ✅ Resolved review finding [low]: `docs/user-guide.md` and `docs/contributor-guide.md` now include the `macs setup guide` surface where operators and contributors look up setup verbs.
- ✅ Resolved review finding [low]: `tools/orchestration/tests/test_setup_init.py` now covers post-bootstrap partial and ready guide states so the remediation recommendation stays locked down.
- Final closeout completed as a records-only update after review confirmed no actionable findings remained; no further code changes were required.
- Minor non-blocking residual risks remain intentionally deferred to later guided-onboarding stories: full blocked/partial/pass guide-state hardening, narrow-terminal and `NO_COLOR` rendering polish, and the final stable guide JSON contract.

### File List

- `README.md`
- `docs/contributor-guide.md`
- `docs/getting-started.md`
- `docs/how-tos.md`
- `docs/user-guide.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/setup.py`
- `tools/orchestration/tests/test_setup_init.py`
- `_bmad-output/implementation-artifacts/stories/1-1-add-a-guided-onboarding-entry-point.md`
- `_bmad-output/implementation-artifacts/sprint-status-macs-guided-onboarding.yaml`

### Change Log

- 2026-04-14: Moved Story 1.1 to `in-progress` and started BMAD implementation tracking for the guided onboarding entry point.
- 2026-04-14: Implemented the `macs setup guide` entry point, added regression coverage, updated minimal onboarding docs, and moved Story 1.1 to `review`.
- 2026-04-14: Addressed code review findings for Story 1.1 by switching the partial guide recommendation to controller-owned worker discovery, adding post-bootstrap guide regressions, updating the user and contributor docs surface, and returning the story to `review`.
- 2026-04-14: Closed Story 1.1 from `review` to `done`, recorded the remaining minor deferred risks, and left the implementation unchanged because review found no further actionable work.
