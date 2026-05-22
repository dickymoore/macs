# Story 8.3: Validate the four-worker reference dogfood scenario

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,
I want a repeatable four-worker orchestration scenario in the MACS repo,
So that the Phase 1 release proves real mixed-runtime value under its reference conditions.

## Acceptance Criteria

1. MACS adds a dedicated four-worker reference dogfood validation layer that runs inside the MACS repository against repo-local state and isolated tmux infrastructure. The scenario must use the supported reference runtime mix of Codex, Claude, Gemini, and local workers and must drive the existing controller CLI and persistence seams rather than synthetic helper-only assertions.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-83-validate-the-four-worker-reference-dogfood-scenario] [Source: _bmad-output/planning-artifacts/architecture.md#test-harness-design] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg4]
2. The dogfood scenario completes a defined mixed-runtime orchestration flow with operator-visible ownership, current lease or lock state, routing rationale, and intervention support. The flow must exercise all four reference workers and leave controller-authoritative evidence that no task ever shows more than one live lease.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-83-validate-the-four-worker-reference-dogfood-scenario] [Source: _bmad-output/planning-artifacts/prd.md#non-functional-requirements] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg4]
3. The scenario records the reference timing envelope and proves it against the defined local-host assumptions: worker discovery or inspection within 2 seconds, assignment path within 5 seconds, and degraded-warning visibility within 10 seconds. Where one timing check is driven by controlled evidence injection rather than spontaneous runtime telemetry, the artifact must state that explicitly.  
   [Source: _bmad-output/planning-artifacts/prd.md#performance] [Source: _bmad-output/planning-artifacts/evidence-templates/dogfood-evidence-template.md]
4. Story 8.3 ships the dogfood evidence artifact required by RG4. The implementation writes a committed human-readable report at `_bmad-output/release-evidence/four-worker-dogfood-report.md` and preserves enough machine-readable supporting output to make the run repeatable and auditable.  
   [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg4] [Source: _bmad-output/planning-artifacts/evidence-templates/dogfood-evidence-template.md] [Source: _bmad-output/planning-artifacts/evidence-templates/index.md]
5. Story 8.3 stays bounded to the dogfood scenario and its evidence path. It does not implement the aggregated release-gate command from Story 8.4, does not expand the frozen operator CLI contract with a new top-level family unless the existing contract is intentionally revised, and does not replace the deterministic or failure-drill suites added in Stories 8.1 and 8.2.  
   [Source: _bmad-output/planning-artifacts/operator-cli-contract.md] [Source: _bmad-output/planning-artifacts/epics.md#story-84-ship-a-release-gate-command-and-report-for-phase-1-readiness] [Source: _bmad-output/planning-artifacts/architecture.md#release-gate-matrix]
6. The required validation surface includes the dedicated dogfood suite, the existing focused controller CLI regressions, full unittest discovery, and the tmux bridge smoke test when Story 8.3 adds or adjusts tmux-backed orchestration harness behavior. An explicit BMAD QA acceptance pass compares the story contract, the dogfood suite, the evidence artifact, and the delivered controller behavior before closure.  
   [Source: _bmad-output/project-context.md#testing-rules] [Source: tools/tmux_bridge/tests/smoke.sh]

## Tasks / Subtasks

- [x] Add a dedicated four-worker dogfood scenario runner and regression seam. (AC: 1, 6)
  - [x] Add a discoverable tmux-backed dogfood scenario module or runner under `tools/orchestration/` that uses isolated tmux sockets, repo-local controller state, and the current CLI entrypoint instead of introducing a second orchestration surface.  
        [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/tests/test_failure_drills_cli.py]
  - [x] Add a dedicated regression module under `tools/orchestration/tests/` for the four-worker reference scenario. Reuse the current temporary-repo, isolated-tmux, and CLI harness patterns before introducing any new helper abstraction.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: tools/orchestration/tests/test_failure_drills_cli.py]
  - [x] Keep any new shared helper small, stdlib-only, and justified by repeated tmux session bootstrap, timing capture, or evidence-writing logic.  
        [Source: _bmad-output/project-context.md#testing-rules]

- [x] Exercise a real mixed-runtime flow that reaches all four reference workers. (AC: 1, 2, 5)
  - [x] Start one isolated reference tmux environment that exposes Codex, Claude, Gemini, and local worker panes in a way the current discovery logic can classify without hidden test-only routing shortcuts.  
        [Source: tools/orchestration/workers.py] [Source: tools/orchestration/adapters/registry.py]
  - [x] Create and assign a narrow set of tasks whose workflow classes, required capabilities, and protected surfaces make the routing decisions meaningful and auditable across all four workers. Prefer current routing policy and capability vocabulary over test-only special cases.  
        [Source: tools/orchestration/policy.py] [Source: tools/orchestration/routing.py] [Source: tools/orchestration/tasks.py]
  - [x] Prove visible ownership, lease truth, and lock visibility through existing read surfaces such as `task inspect`, `lease inspect`, `lock list|inspect`, `worker inspect`, `overview show`, or `event list`, and preserve evidence that zero-or-one live lease semantics held throughout the scenario.  
        [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/history.py] [Source: tools/orchestration/overview.py]
  - [x] Exercise at least one supported intervention path inside the dogfood flow, using an existing controller-owned action such as pause or resume, and preserve the resulting decision and event trail in the evidence pack.  
        [Source: tools/orchestration/tasks.py] [Source: _bmad-output/planning-artifacts/evidence-templates/dogfood-evidence-template.md]

- [x] Record the reference timing envelope and degraded-warning visibility explicitly. (AC: 2, 3)
  - [x] Measure discovery or inspection timing and assignment timing inside the dogfood runner using the same commands the operator would use, then surface both machine-readable timings and a human-readable pass or fail summary.  
        [Source: _bmad-output/planning-artifacts/prd.md#performance]
  - [x] Add one controlled degraded-evidence point that proves warning visibility within 10 seconds without widening Story 8.3 into the full failure-drill matrix already covered by Story 8.2. If the warning is triggered by injected stale evidence or another controlled controller-side signal, document that fact in the resulting artifact.  
        [Source: _bmad-output/planning-artifacts/prd.md#performance] [Source: _bmad-output/implementation-artifacts/stories/8-2-build-integration-and-failure-drill-coverage-for-mandatory-failure-classes.md]

- [x] Produce the RG4 evidence artifact and supporting outputs. (AC: 3, 4, 5)
  - [x] Create `_bmad-output/release-evidence/` if it does not already exist and write `_bmad-output/release-evidence/four-worker-dogfood-report.md` using the dogfood evidence template structure as the minimum contract.  
        [Source: _bmad-output/planning-artifacts/evidence-templates/dogfood-evidence-template.md] [Source: _bmad-output/planning-artifacts/evidence-templates/index.md]
  - [x] Preserve machine-readable supporting output for the run, such as structured scenario JSON, event references, or pane-capture snapshots, in a stable repo-local location that the later Story 8.4 release-gate summary can consume or reference.  
        [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#minimum-evidence-package-for-phase-1-release-review]
  - [x] Update user-facing validation documentation only as needed to keep the dogfood run discoverable and repeatable. Prefer README or existing docs over adding a parallel documentation surface unless the run steps become too large to fit cleanly.  
        [Source: _bmad-output/project-context.md#code-quality--style-rules] [Source: README.md] [Source: docs/getting-started.md]

- [x] Keep Story 8.3 bounded to dogfooding and release evidence. (AC: 5)
  - [x] Do not add the final one-command release-gate summary here. At most, expose narrow reusable runner or artifact seams that Story 8.4 can call or summarize.  
        [Source: _bmad-output/planning-artifacts/epics.md#story-84-ship-a-release-gate-command-and-report-for-phase-1-readiness]
  - [x] Do not expand the frozen Phase 1 operator CLI contract with a new top-level `dogfood` family unless the contract artifact itself is intentionally revised as part of the accepted scope. Favor internal helpers, tests, or documentation-driven execution paths.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md]
  - [x] Keep the deterministic 8.1 suites and the 8.2 failure-drill suite intact; Story 8.3 adds the reference scenario and evidence output on top of those layers.  
        [Source: _bmad-output/implementation-artifacts/stories/8-1-build-unit-and-contract-test-coverage-for-controller-and-adapter-invariants.md] [Source: _bmad-output/implementation-artifacts/stories/8-2-build-integration-and-failure-drill-coverage-for-mandatory-failure-classes.md]

- [x] Run and preserve the required validation surfaces. (AC: 1, 2, 3, 4, 6)
  - [x] Run the dedicated dogfood suite before the broader required surface so the scenario stays a narrow red-green entrypoint during development.  
        [Source: _bmad-output/project-context.md#testing-rules]
  - [x] Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused controller validation surface.  
        [Source: tools/orchestration/tests]
  - [x] Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.  
        [Source: tools/orchestration/tests]
  - [x] Run `bash tools/tmux_bridge/tests/smoke.sh` because Story 8.3 adds tmux-backed scenario-harness behavior.  
        [Source: tools/tmux_bridge/tests/smoke.sh]
  - [x] Use an explicit BMAD QA acceptance pass to compare the story contract, the dogfood regression suite, the evidence artifact, and the delivered behavior before closing the story.  
        [Source: _bmad-output/project-context.md#testing-rules]

## Dev Notes

### Previous Story Intelligence

- Story 8.2 established the tmux-backed outer validation layer and explicitly deferred the four-worker dogfood scenario and RG4 evidence artifact to Story 8.3. Reuse its isolated tmux, repo bootstrap, and controller-state assertion patterns instead of building a second integration harness.  
  [Source: _bmad-output/implementation-artifacts/stories/8-2-build-integration-and-failure-drill-coverage-for-mandatory-failure-classes.md]
- Story 8.1 established the deterministic contract and invariant suites that now serve as the fast inner layer beneath dogfooding. Story 8.3 should add the reference scenario and evidence generation on top of those suites, not replace them.  
  [Source: _bmad-output/implementation-artifacts/stories/8-1-build-unit-and-contract-test-coverage-for-controller-and-adapter-invariants.md]

### Brownfield Reuse Guidance

- `tools/orchestration/tests/test_failure_drills_cli.py` already provides the closest current model for isolated tmux sockets, temporary repo roots, seed helpers, and controller-state assertions through the real CLI. Prefer extending or mirroring that style first.  
  [Source: tools/orchestration/tests/test_failure_drills_cli.py]
- `tools/orchestration/tests/test_task_lifecycle_cli.py` already covers real assignment dispatch into tmux panes, narrow worker bootstrap helpers, and human-readable action surfaces. Reuse those patterns for the dogfood happy path and intervention steps.  
  [Source: tools/orchestration/tests/test_task_lifecycle_cli.py]
- `tools/orchestration/tests/test_inspect_context_cli.py` already proves the current inspect and overview read surfaces. Story 8.3 should use those surfaces as evidence targets for ownership, lock, routing, and intervention visibility rather than inventing a new read API.  
  [Source: tools/orchestration/tests/test_inspect_context_cli.py]
- `tools/orchestration/workers.py`, `tools/orchestration/routing.py`, `tools/orchestration/tasks.py`, `tools/orchestration/health.py`, and `tools/orchestration/overview.py` already encode worker discovery, routing rationale, intervention behavior, degraded classification, and controller summaries. Prefer narrow extensions there only if the dogfood runner exposes a real gap in repeatability or evidence export.  
  [Source: tools/orchestration/workers.py] [Source: tools/orchestration/routing.py] [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/health.py] [Source: tools/orchestration/overview.py]

### Technical Requirements

- Keep the dogfood scenario local-host-first, stdlib-only, and tmux-backed.
- Exercise all four reference workers in one repeatable run.
- Preserve controller-authoritative evidence for ownership, routing, locks, interventions, and recent events.
- Capture timing measurements explicitly and compare them to the NFR targets.
- Be honest about any controlled evidence injection used to trigger degraded-warning visibility.

### Architecture Compliance Notes

- The test harness must use isolated tmux sockets, fixture work surfaces, stored event traces, and black-box validation where practical.  
  [Source: _bmad-output/planning-artifacts/architecture.md#test-harness-design]
- Phase 1 release readiness requires a successful 4-worker reference scenario in addition to contract, failure-drill, and restart-recovery proof.  
  [Source: _bmad-output/planning-artifacts/architecture.md#release-gate-matrix]
- Story 8.3 is the dogfood and evidence story, not the final aggregated release gate.  
  [Source: _bmad-output/planning-artifacts/epics.md#story-84-ship-a-release-gate-command-and-report-for-phase-1-readiness]

### File Structure Requirements

- Prefer extending or adding these files before introducing anything broader:
  - `tools/orchestration/tests/test_failure_drills_cli.py`
  - `tools/orchestration/tests/test_task_lifecycle_cli.py`
  - `tools/orchestration/tests/test_inspect_context_cli.py`
  - `tools/orchestration/tests/test_setup_init.py`
  - `tools/orchestration/tests/test_reference_dogfood_cli.py`
  - `tools/orchestration/dogfood.py`
  - `_bmad-output/release-evidence/four-worker-dogfood-report.md`
  - `README.md`
  - `docs/getting-started.md`
- Add a small shared helper only if scenario bootstrap, timing capture, or evidence writing would otherwise be duplicated heavily across the runner and the new regression module.

### Testing Requirements

- Run `python3 -m unittest tools.orchestration.tests.test_reference_dogfood_cli` if a dedicated dogfood module is added.
- Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused controller validation surface.
- Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.
- Run `bash tools/tmux_bridge/tests/smoke.sh` before marking the story done.

### Git Intelligence Summary

- `c3ccc6a` shows the repo is still landing BMAD work incrementally, with review findings resolved in narrow slices rather than broad rewrites.
- `51d2554` and `e474089` remain the signal to reuse existing bootstrap, controller authority, and repo-local state seams rather than bypassing them for convenience.
- The safest 8.3 path is to add one reference dogfood runner plus one dedicated suite and evidence artifact, leaving the final release-gate aggregation for 8.4.

### Implementation Guardrails

- Do not add the final release-gate command in Story 8.3.
- Do not invent a new top-level CLI family that conflicts with the frozen Phase 1 operator contract unless the contract itself is intentionally revised.
- Do not rely on raw pane text alone as the source of truth; always preserve controller-state and event evidence too.
- Do not fake runtime support depth that the adapters do not declare.
- Do not let the dogfood harness contaminate the user’s live tmux environment.
- Do not introduce third-party Python test or reporting dependencies.

### Project Structure Notes

- This remains a brownfield local-host orchestration repo with controller authority in repo-local SQLite state and transport through tmux.
- Story 8.3 should prove mixed-runtime value under those existing constraints, not work around them with hosted services or hidden simulation layers.
- The highest-value increment is a repeatable four-worker scenario with durable evidence output that Story 8.4 can summarize later.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/release-readiness-evidence-matrix.md`
- `_bmad-output/planning-artifacts/evidence-templates/dogfood-evidence-template.md`
- `_bmad-output/planning-artifacts/evidence-templates/index.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/stories/8-1-build-unit-and-contract-test-coverage-for-controller-and-adapter-invariants.md`
- `_bmad-output/implementation-artifacts/stories/8-2-build-integration-and-failure-drill-coverage-for-mandatory-failure-classes.md`
- `tools/orchestration/workers.py`
- `tools/orchestration/routing.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/health.py`
- `tools/orchestration/overview.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_failure_drills_cli.py`
- `tools/tmux_bridge/tests/smoke.sh`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Create the dedicated dogfood scenario runner and regression suite first, driving the missing RG4 evidence seam red before touching production code.
- Add only the narrowest supporting production and documentation seams needed to make the run repeatable, auditable, and bounded to the frozen CLI contract.
- Finish by writing the committed dogfood evidence artifact, then run the required validation surfaces and an explicit BMAD QA acceptance pass before marking the story done.

### Story Creation Notes

- Skill used: `bmad-create-story`
- Target story auto-discovered from `sprint-status.yaml` after Story 8.2 was completed; Epic 8 retrospective is not due because Epic 8 remains in progress.
- Inputs reviewed for this story: Epic 8.3 story definition, PRD timing requirements, architecture test-harness and release-gate matrix, dogfood evidence template, release-readiness RG4 expectations, Story 8.1 and 8.2 learnings, current tmux-backed CLI harnesses, current worker discovery and routing seams, frozen operator CLI contract, project context rules, and recent git history.
- Validation pass applied against `.agents/skills/bmad-create-story/checklist.md`: the story now includes the missing RG4 evidence artifact path, explicit timing-envelope proof obligations, frozen-CLI anti-scope guardrails, brownfield harness reuse notes, and the required validation surface for the dedicated dogfood suite.

### Debug Log References

- Story creation validation performed against `.agents/skills/bmad-create-story/checklist.md`
- `python3 -m unittest tools.orchestration.tests.test_reference_dogfood_cli`
- `python3 -m tools.orchestration.dogfood --operator-id qa.dogfood@example.test --scenario-label release-evidence`
- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init`
- `python3 -m unittest discover -s tools/orchestration/tests`
- `bash tools/tmux_bridge/tests/smoke.sh`
- BMAD QA acceptance pass executed against Story 8.3 contract, the committed RG4 report, the machine-readable summary artifact, the docs updates, and the frozen CLI-family boundary.

### Completion Notes List

- Added `tools.orchestration.dogfood` as a bounded internal scenario runner that drives the existing CLI through an isolated four-window tmux session and records timing, ownership, routing, locks, intervention, and warning visibility.
- Added `test_reference_dogfood_cli.py` to lock the four-worker reference scenario and its evidence outputs into regression coverage.
- Generated and committed the RG4 evidence pack under `_bmad-output/release-evidence/`, including the report, summary JSON, pane captures, and command log.
- Kept Story 8.3 bounded: no new top-level `dogfood` operator CLI family was introduced, and the release-gate aggregation remains deferred to Story 8.4.
- Explicit BMAD QA acceptance pass found no remaining findings after the committed artifact, docs, validation surface, and CLI boundary were reviewed together.

### File List

- `_bmad-output/implementation-artifacts/stories/8-3-validate-the-four-worker-reference-dogfood-scenario.md`
- `_bmad-output/release-evidence/four-worker-dogfood-report.md`
- `_bmad-output/release-evidence/four-worker-dogfood-artifacts/four-worker-dogfood-summary.json`
- `_bmad-output/release-evidence/four-worker-dogfood-artifacts/four-worker-dogfood-pane-captures.json`
- `_bmad-output/release-evidence/four-worker-dogfood-artifacts/four-worker-dogfood-command-log.json`
- `README.md`
- `docs/getting-started.md`
- `tools/orchestration/dogfood.py`
- `tools/orchestration/tests/test_reference_dogfood_cli.py`

### Change Log

- 2026-04-10: Created Story 8.3 with RG4 dogfood scope, reference timing requirements, evidence-artifact obligations, brownfield harness guidance, and anti-scope guardrails for Story 8.4.
- 2026-04-10: Implemented the four-worker reference dogfood runner and regression suite, generated the committed RG4 evidence pack, ran the required validations, and completed the explicit BMAD QA acceptance pass with no findings remaining.
