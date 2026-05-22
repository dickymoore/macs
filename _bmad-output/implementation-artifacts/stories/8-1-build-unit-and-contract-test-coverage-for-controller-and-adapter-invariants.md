# Story 8.1: Build unit and contract test coverage for controller and adapter invariants

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,
I want deterministic unit and contract suites around state transitions and adapter behavior,
So that core orchestration semantics can be validated without relying only on live sessions.

## Acceptance Criteria

1. MACS adds a dedicated deterministic unit-test layer for controller invariants. The automated suite includes focused tests for task, lease, lock, routing, and recovery state semantics using repo-local SQLite fixtures and controller helpers rather than tmux-backed panes or broad end-to-end command paths.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-81-build-unit-and-contract-test-coverage-for-controller-and-adapter-invariants] [Source: _bmad-output/planning-artifacts/architecture.md#unit-tests] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#nfr20]
2. MACS adds a shared adapter contract-test layer that validates the published contract directly. The contract suite covers base adapter contract conformance, evidence-envelope normalization, unsupported-feature declarations, degraded-mode declarations, and the shared validation metadata that contributors and maintainers now rely on.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-81-build-unit-and-contract-test-coverage-for-controller-and-adapter-invariants] [Source: _bmad-output/planning-artifacts/architecture.md#contract-tests] [Source: _bmad-output/implementation-artifacts/stories/7-4-publish-contributor-facing-adapter-guidance.md]
3. First-class qualification gating becomes explicit and testable. A runtime adapter cannot be treated as first-class when the shared contract checks fail, and the contract suite proves that a broken reference-style adapter is blocked by the shared qualification gate rather than qualifying by declaration alone.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-81-build-unit-and-contract-test-coverage-for-controller-and-adapter-invariants] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg1] [Source: _bmad-output/planning-artifacts/prd.md#contributor-extension-and-validation]
4. The deterministic test layer stays separate from tmux-backed integration and failure drills. Story 8.1 documents and implements unit and contract coverage only; mandatory disconnect, split-brain, collision, and dogfood scenarios remain intentionally scoped to Stories 8.2 through 8.4.  
   [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: _bmad-output/implementation-artifacts/epic-7-retro-2026-04-10.md]
5. Docs and contributor validation guidance align with the new shared test layers. The published adapter-validation guidance and any shared contract metadata point at the new deterministic contract or unit commands instead of only the broad CLI suite, and the regression surface proves those references stay honest.  
   [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#nfr21] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#nfr22] [Source: docs/adapter-contributor-guide.md]

## Tasks / Subtasks

- [x] Add a deterministic controller-invariant unit suite. (AC: 1, 4)
  - [x] Add a dedicated test module under `tools/orchestration/tests/` for direct task, lease, lock, routing, and recovery invariant checks using temporary repo-local state and SQLite fixtures rather than tmux-backed CLI flows.  
        [Source: tools/orchestration/invariants.py] [Source: tools/orchestration/locks.py] [Source: tools/orchestration/routing.py] [Source: tools/orchestration/recovery.py]
  - [x] Cover at least one high-signal invariant per domain in the deterministic layer: zero-or-one live lease enforcement, invalid task activation without a live lease, protected-surface conflict detection, routing rejection or selection behavior, and interrupted-recovery blocking semantics.  
        [Source: _bmad-output/planning-artifacts/architecture.md#unit-tests]
  - [x] Reuse existing bootstrap helpers such as `bootstrap_state_store(...)`, `ensure_orchestration_store(...)`, and the current JSON policy defaults instead of creating a second persistence or policy fixture system.  
        [Source: tools/orchestration/store.py] [Source: tools/orchestration/session.py] [Source: tools/orchestration/policy.py]

- [x] Add a shared adapter contract suite. (AC: 2, 3)
  - [x] Add a dedicated contract-test module that validates `BaseTmuxAdapter` descriptor and validation behavior, evidence-envelope normalization, unsupported-feature declarations, degraded-mode metadata, and shared validation-command metadata.  
        [Source: tools/orchestration/adapters/base.py]
  - [x] Prove the current registry adapters pass the shared contract suite without depending on live tmux sessions for the core contract checks.  
        [Source: tools/orchestration/adapters/registry.py] [Source: tools/orchestration/adapters/codex.py]
  - [x] Add a narrow broken-adapter fixture or subclass that fails the shared contract checks, then prove the shared qualification gate blocks first-class eligibility for that adapter.  
        [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg1] [Source: _bmad-output/planning-artifacts/architecture.md#first-class-adapter-qualification]

- [x] Make shared qualification gating explicit without broadening scope. (AC: 3, 4)
  - [x] Add or extend a shared helper on the adapter contract seam so contract success or failure can be evaluated as a first-class qualification gate in deterministic tests.  
        [Source: tools/orchestration/adapters/base.py]
  - [x] Keep Story 8.1 bounded to deterministic qualification gating only. Do not build the full release-gate command, tmux-backed failure drills, or first-class promotion automation here.  
        [Source: _bmad-output/planning-artifacts/epics.md#story-82-build-integration-and-failure-drill-coverage-for-mandatory-failure-classes] [Source: _bmad-output/planning-artifacts/epics.md#story-84-ship-a-release-gate-command-and-report-for-phase-1-readiness]
  - [x] Preserve existing adapter inspect or validate surfaces unless a narrow shared-contract clarification is needed to keep the deterministic contract layer honest.  
        [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/implementation-artifacts/stories/7-4-publish-contributor-facing-adapter-guidance.md]

- [x] Align contributor guidance and shared validation references. (AC: 2, 5)
  - [x] Update contributor-facing validation guidance so the shared validation workflow includes the new deterministic contract and unit suites alongside the broader regression commands.  
        [Source: docs/adapter-contributor-guide.md]
  - [x] If shared adapter metadata exposes validation commands, keep those references aligned with the new dedicated suites rather than leaving the contributor contract pointed only at `test_setup_init.py`.  
        [Source: tools/orchestration/adapters/base.py]
  - [x] Do not broaden Story 8.1 into release-evidence artifact generation; at most, make the future control-plane testability trace easier to produce from deterministic test module names and scope.  
        [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#nfr20]

- [x] Run and preserve the required validation surfaces. (AC: 1, 2, 3, 5)
  - [x] Run the focused required validation surface plus full discovery before marking the story done.  
        [Source: _bmad-output/project-context.md#testing-rules]
  - [x] Ensure the new deterministic test modules are discoverable by the repo’s current unittest entrypoints and do not regress the existing broad CLI suites.  
        [Source: tools/orchestration/tests]
  - [x] Use an explicit BMAD QA acceptance pass to compare the story contract, deterministic test modules, contributor guidance, and any qualification-gate surface before closing the story.  
        [Source: _bmad-output/project-context.md#testing-rules]

## Dev Notes

### Previous Story Intelligence

- Epic 7 ended with explicit setup, compatibility, and contributor guidance, but its retrospective identified the main risk entering Epic 8: validation is still concentrated in broad CLI suites instead of explicit unit and contract layers.  
  [Source: _bmad-output/implementation-artifacts/epic-7-retro-2026-04-10.md]
- Story 7.4 centralized shared adapter contract metadata in `BaseTmuxAdapter` and published contributor validation guidance. Story 8.1 should build the shared contract suite around that seam instead of re-specifying the contract in test-only constants.  
  [Source: _bmad-output/implementation-artifacts/stories/7-4-publish-contributor-facing-adapter-guidance.md]
- Stories 7.1 through 7.3 proved that new read or validation seams land cleanly when they reuse current bootstrap and setup helpers first. Story 8.1 should do the same for deterministic test setup.  
  [Source: _bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md] [Source: _bmad-output/implementation-artifacts/stories/7-2-deliver-mixed-runtime-setup-and-validation-flow.md] [Source: _bmad-output/implementation-artifacts/stories/7-3-preserve-and-document-single-worker-compatibility-boundaries.md]

### Brownfield Reuse Guidance

- `tools/orchestration/invariants.py` and `tools/orchestration/state_machine.py` already centralize task and lease transition rules. Prefer direct unit coverage there instead of recreating the same assertions through CLI orchestration flows.  
  [Source: tools/orchestration/invariants.py] [Source: tools/orchestration/state_machine.py]
- `tools/orchestration/locks.py`, `tools/orchestration/routing.py`, and `tools/orchestration/recovery.py` already expose deterministic helpers that can be exercised against temporary SQLite state and repo-local policy files.  
  [Source: tools/orchestration/locks.py] [Source: tools/orchestration/routing.py] [Source: tools/orchestration/recovery.py]
- `tools/orchestration/store.py` and `tools/orchestration/session.py` already provide the cleanest seams for isolated repo-local controller-state fixtures. Reuse them before adding test-only bootstrap code.  
  [Source: tools/orchestration/store.py] [Source: tools/orchestration/session.py]
- Current regression breadth lives mostly in `test_task_lifecycle_cli.py`, `test_setup_init.py`, and `test_inspect_context_cli.py`. Story 8.1 should add dedicated deterministic suites, not move or rewrite the existing broad CLI tests wholesale.  
  [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/tests/test_inspect_context_cli.py]

### Technical Requirements

- Keep the new test layers deterministic and stdlib-only.
- Avoid tmux dependencies in the unit and contract suites unless a single narrow normalization case cannot be proved otherwise.
- Preserve repo-local bootstrap and policy semantics by using the real store schema and routing policy defaults where feasible.
- Make first-class qualification gating explicit enough to be asserted directly in tests.
- Keep the existing broad CLI suites discoverable and green; Story 8.1 adds layers, it does not replace them.

### Architecture Compliance Notes

- Unit tests should prove explicit state-transition rules for task, lease, lock, routing, and recovery behavior.  
  [Source: _bmad-output/planning-artifacts/architecture.md#unit-tests]
- Contract tests should prove base adapter contract conformance, envelope normalization, unsupported-feature declarations, and qualification checks.  
  [Source: _bmad-output/planning-artifacts/architecture.md#contract-tests]
- Integration and failure-drill scenarios stay out of scope for this story.  
  [Source: _bmad-output/planning-artifacts/architecture.md#integration-tests] [Source: _bmad-output/planning-artifacts/architecture.md#failure-drill-tests]

### File Structure Requirements

- Prefer extending or adding these files before introducing anything broader:
  - `tools/orchestration/adapters/base.py`
  - `tools/orchestration/tests/test_task_lifecycle_cli.py`
  - `tools/orchestration/tests/test_setup_init.py`
  - `tools/orchestration/tests/test_controller_invariants.py`
  - `tools/orchestration/tests/test_adapter_contracts.py`
  - `docs/adapter-contributor-guide.md`
- Add a small shared test helper only if the new deterministic suites would otherwise duplicate temp-repo bootstrap or event-fixture logic heavily.

### Testing Requirements

- Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused required validation surface.
- Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.
- Add discoverable deterministic suites for controller invariants and adapter contracts.
- Keep tmux-backed failure drills, smoke tests, and dogfood scenarios out of the required scope unless a narrow seam is directly touched.

### Git Intelligence Summary

- `c3ccc6a` shows the current repo posture: recent work keeps landing on existing controller seams and resolving review findings incrementally.
- `51d2554` and `e474089` remain the signals that bootstrap, state, and controller authority seams should be reused rather than bypassed in test setup.
- The safest 8.1 path is to formalize the deterministic layer under `tools/orchestration/tests/` while leaving the broad CLI suites intact as outer regression coverage.

### Implementation Guardrails

- Do not broaden Story 8.1 into tmux-backed failure drills, release-evidence artifact generation, or the final release-gate command.
- Do not duplicate the adapter contract in multiple test-only locations when `BaseTmuxAdapter` already centralizes it.
- Do not make qualification gating depend on docs or static labels alone; it must be assertable from shared contract results.
- Do not replace current CLI suites with new unit tests; keep both layers.
- Do not introduce third-party test libraries or fixture frameworks.

### Project Structure Notes

- This remains a brownfield control-plane repo with explicit state helpers and broad CLI regressions already in place.
- Story 8.1 should make the deterministic proof layer explicit, faster to reason about, and easier to reuse in later release-gate work.
- The highest-value increment is two dedicated suites plus a shared qualification-gate seam that later failure drills and release reporting can build on.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/release-readiness-evidence-matrix.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/epic-7-retro-2026-04-10.md`
- `_bmad-output/implementation-artifacts/stories/7-4-publish-contributor-facing-adapter-guidance.md`
- `tools/orchestration/invariants.py`
- `tools/orchestration/state_machine.py`
- `tools/orchestration/locks.py`
- `tools/orchestration/routing.py`
- `tools/orchestration/recovery.py`
- `tools/orchestration/store.py`
- `tools/orchestration/session.py`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/adapters/registry.py`
- `tools/orchestration/adapters/codex.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `docs/adapter-contributor-guide.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add the deterministic contract and invariant tests first, proving the new suites fail red on the missing qualification-gate seam before touching production code.
- Add the shared adapter qualification-gate helper next and keep any contract-metadata updates centralized in `BaseTmuxAdapter`.
- Finish by aligning contributor validation guidance, then run the required validation surfaces and an explicit BMAD QA acceptance pass before marking done.

### Story Creation Notes

- Skill used: `bmad-create-story`
- Target story auto-discovered from `sprint-status.yaml` after Epic 7 and its optional retrospective were completed.
- Inputs reviewed for this story: Epic 8.1 story definition, PRD validation requirements, architecture unit and contract test layers, release-readiness NFR20/RG1/NFR22 expectations, Epic 7 retrospective findings, Story 7.4 contract surfacing work, current deterministic helper seams, current test module inventory, and recent git history.
- Validation pass applied against `.agents/skills/bmad-create-story/checklist.md`: the story now includes the missing deterministic test-layer split, shared qualification-gate seam, contributor-guidance alignment, brownfield reuse notes, and anti-scope guardrails against Stories 8.2 through 8.4.

### Debug Log References

- Story creation validation performed against `.agents/skills/bmad-create-story/checklist.md`
- `python3 -m unittest tools.orchestration.tests.test_adapter_contracts tools.orchestration.tests.test_controller_invariants tools.orchestration.tests.test_setup_init`
- `python3 -m unittest tools.orchestration.tests.test_adapter_contracts`
- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init`
- `python3 -m unittest discover -s tools/orchestration/tests`
- `bash tools/tmux_bridge/tests/smoke.sh`

### Completion Notes List

- Added a dedicated deterministic controller-invariant suite that exercises lease, task, lock, routing, and recovery semantics against repo-local SQLite state without tmux-backed orchestration flows.
- Added a shared adapter contract suite plus an explicit `BaseTmuxAdapter.qualification_gate(...)` helper so first-class eligibility depends on shared contract success instead of declaration alone.
- Aligned shared validation metadata and contributor guidance with the new deterministic suites.
- BMAD QA acceptance pass found one remaining gap: degraded-mode and core contract declarations were only covered implicitly in the contract suite. Tightened the deterministic contract assertions, reran validation, and closed the story with no findings remaining.

### File List

- `_bmad-output/implementation-artifacts/stories/8-1-build-unit-and-contract-test-coverage-for-controller-and-adapter-invariants.md`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/tests/test_adapter_contracts.py`
- `tools/orchestration/tests/test_controller_invariants.py`
- `tools/orchestration/tests/test_setup_init.py`
- `docs/adapter-contributor-guide.md`

### Change Log

- 2026-04-10: Created Story 8.1 with deterministic unit-suite, adapter-contract-suite, qualification-gate, contributor-guidance, and regression scope under Epic 8.
- 2026-04-10: Implemented deterministic controller-invariant and adapter-contract suites, added the shared qualification gate, aligned contributor validation commands, ran required validations, and completed the explicit BMAD QA acceptance pass.
