# Story 8.2: Build integration and failure-drill coverage for mandatory failure classes

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,
I want tmux-backed integration tests and failure drills for required recovery scenarios,
So that release readiness is based on catastrophe-grade orchestration behavior rather than happy paths alone.

## Acceptance Criteria

1. MACS adds a dedicated tmux-backed integration or failure-drill layer for the mandatory failure classes. The automated suite uses isolated tmux sockets, temporary repo-local state, and fixture work surfaces to exercise controller behavior through the real CLI and persistence seams rather than only deterministic helper calls.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-82-build-integration-and-failure-drill-coverage-for-mandatory-failure-classes] [Source: _bmad-output/planning-artifacts/architecture.md#integration-tests] [Source: _bmad-output/planning-artifacts/architecture.md#failure-drill-tests]
2. The failure-drill coverage proves containment for worker disconnect, stale lease or session divergence, duplicate task claim, split-brain ownership, and lock collision. Each scenario asserts controller-authoritative task, lease, lock, or recovery state plus the durable event trail instead of relying on pane text or shell exit codes alone.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-82-build-integration-and-failure-drill-coverage-for-mandatory-failure-classes] [Source: _bmad-output/planning-artifacts/prd.md#ownership-locking-and-safe-parallelisation] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg2]
3. The failure-drill coverage also proves containment for misleading health evidence, surfaced budget or session exhaustion, and interrupted recovery. Where runtime telemetry is partial, the suite must still show the controller following an explicit safe path such as drain, quarantine, suspension, recovery retry, or operator-visible blocking rather than silently continuing unsafe work.  
   [Source: _bmad-output/planning-artifacts/prd.md#monitoring-intervention-and-recovery] [Source: _bmad-output/planning-artifacts/prd.md#reliability--recovery] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg2]
4. Integration failure drills stay bounded to Story 8.2. This story does not implement the four-worker dogfood scenario, release-evidence artifact generation, or the final release-gate command, but it leaves those later stories with named, discoverable regression seams to build on.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-83-validate-the-four-worker-reference-dogfood-scenario] [Source: _bmad-output/planning-artifacts/epics.md#story-84-ship-a-release-gate-command-and-report-for-phase-1-readiness] [Source: _bmad-output/planning-artifacts/architecture.md#test-layers]
5. The required validation surface includes the new failure-drill suite, the current focused controller CLI regressions, full unittest discovery, and the tmux bridge smoke test when Story 8.2 changes tmux-backed integration behavior or harnesses.  
   [Source: _bmad-output/project-context.md#testing-rules] [Source: tools/tmux_bridge/tests/smoke.sh]

## Tasks / Subtasks

- [x] Add a dedicated tmux-backed failure-drill suite. (AC: 1, 5)
  - [x] Add a discoverable integration-style test module under `tools/orchestration/tests/` for the mandatory failure classes, using isolated tmux sockets, temporary sessions, and repo-local controller state.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: tools/tmux_bridge/tests/smoke.sh]
  - [x] Reuse current repo bootstrap and CLI harness patterns first. Prefer `setup init`, real SQLite state, existing CLI entrypoints, and the current tmux cleanup pattern before introducing any new test helper abstraction.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/session.py] [Source: tools/orchestration/store.py]
  - [x] Add a small shared test helper only if the mandatory failure drills would otherwise duplicate tmux setup or repo bootstrap code heavily. Keep it stdlib-only and local to `tools/orchestration/tests/`.  
        [Source: _bmad-output/project-context.md#testing-rules]

- [x] Cover disconnect, divergence, duplicate-claim, split-brain, and collision containment. (AC: 2, 4)
  - [x] Prove a worker disconnect or disappearance from the discovered tmux roster does not leave active work progressing as if ownership were still healthy. Assert resulting worker, task, lease, and event state through controller reads.  
        [Source: _bmad-output/planning-artifacts/architecture.md#mandatory-failure-classes] [Source: tools/orchestration/workers.py] [Source: tools/orchestration/health.py]
  - [x] Prove stale lease or session divergence on an owned task triggers the current containment path without creating a successor live lease.  
        [Source: _bmad-output/planning-artifacts/architecture.md#failure-drill-tests] [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/recovery.py]
  - [x] Prove duplicate claim and split-brain ownership scenarios are blocked or quarantined by controller authority, preserve the zero-or-one live lease invariant after containment, and leave enough recovery state for later operator reconciliation.  
        [Source: _bmad-output/planning-artifacts/prd.md#ownership-locking-and-safe-parallelisation] [Source: tools/orchestration/invariants.py] [Source: tools/orchestration/recovery.py]
  - [x] Prove lock collision containment with authoritative lock history and task failure or reconciliation evidence rather than pane-only assertions.  
        [Source: tools/orchestration/locks.py] [Source: tools/orchestration/tasks.py]

- [x] Cover misleading health, surfaced budget exhaustion, and interrupted recovery. (AC: 3, 4)
  - [x] Add a failure drill for misleading health evidence that forces the controller onto an explicit safe path such as quarantine, drain, or suspension and preserves an auditable rationale.  
        [Source: _bmad-output/planning-artifacts/architecture.md#containment-decisions] [Source: tools/orchestration/health.py] [Source: tools/orchestration/workers.py]
  - [x] Add a failure drill for surfaced budget or session exhaustion using the narrowest current runtime or controller seam available. The drill must show operator-visible containment and must not pretend unsupported telemetry exists where the adapter contract explicitly says it does not.  
        [Source: _bmad-output/planning-artifacts/architecture.md#mandatory-failure-classes] [Source: tools/orchestration/adapters/base.py] [Source: tools/orchestration/adapters/codex.py]
  - [x] Add a tmux-backed interrupted-recovery drill that proves successor routing remains blocked until retry or reconcile completes and that recovery state remains authoritative across the drill.  
        [Source: tools/orchestration/recovery.py] [Source: tools/orchestration/tasks.py]

- [x] Keep Story 8.2 bounded to integration and failure drills. (AC: 4)
  - [x] Do not implement the four-worker dogfood scenario or the release-gate report command here. At most, name the new suite or tests so Stories 8.3 and 8.4 can reference them cleanly.  
        [Source: _bmad-output/planning-artifacts/epics.md#story-83-validate-the-four-worker-reference-dogfood-scenario] [Source: _bmad-output/planning-artifacts/epics.md#story-84-ship-a-release-gate-command-and-report-for-phase-1-readiness]
  - [x] Keep the deterministic 8.1 unit and contract layers intact; Story 8.2 adds tmux-backed containment coverage and does not replace those suites.  
        [Source: _bmad-output/implementation-artifacts/stories/8-1-build-unit-and-contract-test-coverage-for-controller-and-adapter-invariants.md]

- [x] Run and preserve the required validation surfaces. (AC: 1, 2, 3, 5)
  - [x] Run the focused required validation surface plus any new failure-drill suite before full discovery.  
        [Source: _bmad-output/project-context.md#testing-rules]
  - [x] Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.  
        [Source: tools/orchestration/tests]
  - [x] Run `bash tools/tmux_bridge/tests/smoke.sh` because Story 8.2 adds or adjusts tmux-backed integration coverage.  
        [Source: tools/tmux_bridge/tests/smoke.sh]
  - [x] Use an explicit BMAD QA acceptance pass to compare the story contract, the new failure-drill suite, and the delivered containment behavior before closing the story.  
        [Source: _bmad-output/project-context.md#testing-rules]

## Dev Notes

### Previous Story Intelligence

- Story 8.1 established the deterministic inner test layers and explicitly deferred tmux-backed integration and failure-drill coverage to Story 8.2. Reuse its new deterministic suites as the fast inner regression layer, but do not collapse 8.2 back into helper-level assertions.  
  [Source: _bmad-output/implementation-artifacts/stories/8-1-build-unit-and-contract-test-coverage-for-controller-and-adapter-invariants.md]
- Story 8.1 also added the shared adapter qualification seam and contributor validation commands. Story 8.2 should build outward from those seams instead of duplicating contract-only assertions inside the tmux-backed drills.  
  [Source: _bmad-output/implementation-artifacts/stories/8-1-build-unit-and-contract-test-coverage-for-controller-and-adapter-invariants.md]

### Brownfield Reuse Guidance

- `tools/orchestration/tests/test_task_lifecycle_cli.py` already contains repo-local CLI harness patterns, task and lease seed helpers, and isolated tmux worker setup that match Story 8.2 closely. Extend or mirror those patterns before inventing a new runner.  
  [Source: tools/orchestration/tests/test_task_lifecycle_cli.py]
- `tools/orchestration/tests/test_inspect_context_cli.py` already proves compact tmux session creation, command execution inside tmux, and inspect-surface assertions. Reuse that style where failure drills need read-side confirmation.  
  [Source: tools/orchestration/tests/test_inspect_context_cli.py]
- `tools/orchestration/tests/test_setup_init.py` already covers startup-recovery, blocked assignments, and persisted reconciliation state. Story 8.2 should reuse those established state shapes when turning restart anomalies into tmux-backed drills.  
  [Source: tools/orchestration/tests/test_setup_init.py]
- `tools/orchestration/workers.py`, `tools/orchestration/health.py`, `tools/orchestration/tasks.py`, `tools/orchestration/recovery.py`, and `tools/orchestration/locks.py` already encode the controller containment paths that the failure drills should prove. Prefer narrow production seams there if a test exposes a real gap.  
  [Source: tools/orchestration/workers.py] [Source: tools/orchestration/health.py] [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/recovery.py] [Source: tools/orchestration/locks.py]
- `tools/tmux_bridge/tests/smoke.sh` remains the authoritative low-level tmux cleanup and isolation example. Do not let Story 8.2 contaminate the user’s live tmux environment.  
  [Source: tools/tmux_bridge/tests/smoke.sh]

### Technical Requirements

- Keep the failure drills tmux-backed, stdlib-only, and repo-local.
- Assert authoritative controller state and durable events for every failure class; pane output alone is insufficient.
- Use isolated tmux sockets and cleanup traps for every integration drill.
- Preserve zero-or-one live lease semantics even when the failure drill seeds corrupted or ambiguous state.
- Where runtime telemetry is partial, be explicit about what is simulated, what is directly surfaced, and what remains unsupported by contract.

### Architecture Compliance Notes

- Integration tests should cover controller plus SQLite store plus adapter stubs or real tmux discovery and dispatch seams.  
  [Source: _bmad-output/planning-artifacts/architecture.md#integration-tests]
- Failure-drill tests are explicitly release-gated and must cover worker disappearance, stale divergence, duplicate dispatch or ownership conflict, lock collision, misleading health, and interrupted recovery.  
  [Source: _bmad-output/planning-artifacts/architecture.md#failure-drill-tests] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg2]
- Story 8.2 is not the place for the four-worker dogfood scenario or final release-evidence packaging.  
  [Source: _bmad-output/planning-artifacts/architecture.md#end-to-end-dogfood-scenarios] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#minimum-evidence-package-for-phase-1-release-review]

### File Structure Requirements

- Prefer extending or adding these files before introducing anything broader:
  - `tools/orchestration/tests/test_task_lifecycle_cli.py`
  - `tools/orchestration/tests/test_inspect_context_cli.py`
  - `tools/orchestration/tests/test_setup_init.py`
  - `tools/orchestration/tests/test_failure_drills_cli.py`
  - `tools/orchestration/workers.py`
  - `tools/orchestration/health.py`
  - `tools/orchestration/tasks.py`
  - `tools/orchestration/recovery.py`
- Add a small test helper module only if the new drills would otherwise duplicate tmux socket, repo bootstrap, or event-trace helpers heavily.

### Testing Requirements

- Run `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli` if a dedicated failure-drill module is added.
- Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused required validation surface.
- Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.
- Run `bash tools/tmux_bridge/tests/smoke.sh` before marking the story done.

### Git Intelligence Summary

- `c3ccc6a` shows the repo is still resolving BMAD review findings incrementally rather than via large rewrites. Story 8.2 should follow the same narrow-slice pattern.
- `51d2554` and `e474089` remain the signal that bootstrap, state, and controller authority seams should be reused rather than bypassed in test setup or failure seeding.
- The safest 8.2 path is to add tmux-backed containment drills on top of the new 8.1 deterministic layer, not to replace the existing broad CLI regressions.

### Implementation Guardrails

- Do not broaden Story 8.2 into the four-worker dogfood scenario, release-evidence artifacts, or the release-gate command.
- Do not invent a second orchestration persistence or policy fixture system for the drills.
- Do not treat pane text as controller truth; always assert persisted state and events too.
- Do not fake unsupported runtime telemetry. If a failure class needs simulation, make the simulation explicit and bounded.
- Do not introduce third-party test dependencies or external infrastructure assumptions.

### Project Structure Notes

- This remains a brownfield local-host orchestration repo with controller authority in repo-local SQLite state and transport via tmux.
- Story 8.2 should make catastrophe-grade behavior repeatable in automation without changing that local-host-first design.
- The highest-value increment is a dedicated release-oriented failure-drill suite that later dogfood and release-gate work can reference directly.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/release-readiness-evidence-matrix.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/stories/8-1-build-unit-and-contract-test-coverage-for-controller-and-adapter-invariants.md`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/workers.py`
- `tools/orchestration/health.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/recovery.py`
- `tools/orchestration/locks.py`
- `tools/tmux_bridge/tests/smoke.sh`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Create the tmux-backed failure-drill suite first and drive missing containment behavior red before touching production code.
- Add only the narrowest brownfield production seams needed to make the failure drills honest and repeatable.
- Finish with the required validation surfaces, the tmux bridge smoke test, and an explicit BMAD QA acceptance pass before marking the story done.

### Story Creation Notes

- Skill used: `bmad-create-story`
- Target story auto-discovered from `sprint-status.yaml` after Story 8.1 was completed; Epic 8 retrospective is not due because Epic 8 remains in progress.
- Inputs reviewed for this story: Epic 8.2 story definition, architecture test layers and containment model, PRD failure-class and release-gate requirements, release-readiness RG2 expectations, Story 8.1 learnings, current tmux-backed CLI test harnesses, current startup recovery tests, current controller containment seams, operator CLI contract, project context rules, and recent git history.
- Validation pass applied against `.agents/skills/bmad-create-story/checklist.md`: the story now includes the missing tmux-backed failure-drill scope, brownfield harness reuse guidance, explicit anti-scope guardrails against Stories 8.3 and 8.4, and the required validation surface including smoke coverage.

### Debug Log References

- Story creation validation performed against `.agents/skills/bmad-create-story/checklist.md`
- `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli`
- `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init`
- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init`
- `python3 -m unittest discover -s tools/orchestration/tests`
- `bash tools/tmux_bridge/tests/smoke.sh`

### Completion Notes List

- Added a dedicated tmux-backed failure-drill suite covering worker disconnect, stale divergence, duplicate claim, split-brain startup recovery, lock collision, misleading health evidence, surfaced budget exhaustion, and interrupted recovery with authoritative state and event assertions.
- Hardened worker discovery so a dead tmux server degrades into an empty scoped roster instead of a fatal discover error, and so scoped discovery can still mark previously known workers unavailable.
- Preserved safe inspect behavior for unavailable workers by downgrading adapter probe failures to warnings on task and worker inspect surfaces instead of crashing the read path.
- Added narrow health-signal handling for `signal:budget_exhausted` and `signal:misleading_health`, carrying those tags through health and freeze event payloads so failure drills can assert the event trail honestly.
- Relaxed bootstrap index recreation just enough to let startup recovery contain already-corrupted split-brain persisted state before the live-lease uniqueness index is re-established on a later safe bootstrap.
- Explicit BMAD QA acceptance pass found no remaining findings after validation.

### File List

- `_bmad-output/implementation-artifacts/stories/8-2-build-integration-and-failure-drill-coverage-for-mandatory-failure-classes.md`
- `tools/orchestration/tests/test_failure_drills_cli.py`
- `tools/orchestration/workers.py`
- `tools/orchestration/health.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/store.py`

### Change Log

- 2026-04-10: Created Story 8.2 with tmux-backed failure-drill scope, brownfield harness guidance, release-oriented containment requirements, and anti-scope guardrails for later Epic 8 stories.
- 2026-04-10: Implemented the tmux-backed failure-drill suite, hardened disconnect and probe degradation behavior, added narrow signal-driven containment coverage, ran the required validation surfaces, and completed the explicit BMAD QA acceptance pass.
