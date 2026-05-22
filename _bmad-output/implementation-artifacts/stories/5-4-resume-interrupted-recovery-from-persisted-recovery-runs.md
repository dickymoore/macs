# Story 5.4: Resume interrupted recovery from persisted recovery runs

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,
I want recovery actions and anomalies to persist as resumable recovery runs,
so that controller restart or operator interruption does not erase recovery context.

## Acceptance Criteria

1. Recovery-run persistence becomes controller-authoritative across restart and partial recovery progress. When a reroute, freeze, or startup-reconciliation flow creates or updates a recovery run, MACS stores the detected anomaly, evidence references or summaries, current versus proposed controller state, allowed next actions, and the recovery phase in the existing `recovery_runs` table so the controller can resume from durable state instead of reconstructing context from tmux or adapter claims.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-54-resume-interrupted-recovery-from-persisted-recovery-runs] [Source: _bmad-output/planning-artifacts/architecture.md#recovery-outputs] [Source: _bmad-output/planning-artifacts/architecture.md#interrupted-recovery] [Source: _bmad-output/planning-artifacts/prd.md#monitoring-intervention-and-recovery] [Source: _bmad-output/project-context.md#framework-specific-rules]
2. Startup recovery restores interrupted recovery context instead of replacing it with a generic fresh scan. When `macs setup init` or equivalent controller restart logic finds unresolved recovery runs, it preserves their run IDs, states, anomaly details, evidence references, recommended actions, and affected task or lease refs; it also surfaces them in the startup summary while continuing to classify live ownership uncertainty and `assignments_blocked` according to existing restart-safety rules.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-54-resume-interrupted-recovery-from-persisted-recovery-runs] [Source: _bmad-output/planning-artifacts/architecture.md#reconciliation-rules] [Source: _bmad-output/planning-artifacts/architecture.md#failure-containment-model] [Source: _bmad-output/planning-artifacts/prd.md#reliability--recovery] [Source: _bmad-output/implementation-artifacts/stories/1-4-restore-controller-state-safely-on-restart.md]
3. Controller-owned recovery commands can continue or explicitly clear an interrupted recovery from persisted state. `macs recovery inspect` surfaces restored run metadata even when the affected task no longer has a live predecessor lease, `macs recovery retry` resumes the controller-owned continuation path from the persisted recovery run, and `macs recovery reconcile` can explicitly abandon the interrupted run with durable audit so later routing is an intentional fresh action rather than an accidental continuation.  
   [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#reconciliation-flow] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#post-recovery-ux]
4. Successor routing fails closed while an interrupted recovery run remains unresolved. If a task has a pending interrupted recovery run after restart or operator exit, normal successor assignment or resumed reroute for that task is rejected until the operator either completes the persisted recovery through the supported controller action or explicitly abandons it with audit, and MACS still preserves zero-or-one live lease invariants throughout the resumed flow.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-54-resume-interrupted-recovery-from-persisted-recovery-runs] [Source: _bmad-output/planning-artifacts/architecture.md#interrupted-recovery] [Source: _bmad-output/planning-artifacts/architecture.md#release-gate-matrix] [Source: _bmad-output/planning-artifacts/prd.md#reliability--recovery]
5. Regression coverage proves recovery-run restoration after restart, resumed reroute after predecessor revocation, explicit recovery abandonment, recovery inspect visibility, and no regressions to Story 5.3 safe reroute, Story 5.2 freeze semantics, Story 4.4 pause or resume semantics, or Story 1.4 startup recovery invariants.  
   [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: _bmad-output/planning-artifacts/architecture.md#release-gate-matrix] [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md] [Source: _bmad-output/implementation-artifacts/stories/5-2-freeze-risky-work-through-intervention-hold-and-lease-suspension.md] [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md]

## Tasks / Subtasks

- [x] Extend the recovery-run model so interrupted work is resumable from durable controller state. (AC: 1, 2, 4)
  - [x] Expand `tools/orchestration/recovery.py` so a recovery run records recovery phase, evidence summary or refs, current controller state, proposed continuation state, and allowed next actions without introducing a second persistence channel beyond `recovery_runs`.  
        [Source: tools/orchestration/recovery.py] [Source: tools/orchestration/store.py] [Source: _bmad-output/planning-artifacts/architecture.md#recovery-outputs]
  - [x] Reuse Story 5.3 recovery-run helpers rather than replacing them. The brownfield-safe target is to enrich the existing recovery payload shape so restart and resumed actions can trust it, not to add a parallel restart-only model.  
        [Source: _bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md#completion-notes-list] [Source: tools/orchestration/recovery.py]
  - [x] Preserve controller-truth-first semantics. Adapter evidence may be referenced, but worker claims or tmux observations must not become the authoritative source of current owner, routing state, or recovery phase.  
        [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: _bmad-output/project-context.md#critical-dont-miss-rules]

- [x] Restore unresolved recovery runs during startup and surface them explicitly. (AC: 2, 4)
  - [x] Extend `restore_startup_state(...)` and adjacent restart helpers so unresolved task-scoped or startup-scoped recovery runs are discovered and surfaced in startup output instead of being overwritten by a fresh generic run.  
        [Source: tools/orchestration/recovery.py] [Source: _bmad-output/planning-artifacts/architecture.md#reconciliation-rules] [Source: _bmad-output/implementation-artifacts/stories/1-4-restore-controller-state-safely-on-restart.md]
  - [x] Keep restart safety rules narrow: continue using `assignments_blocked` for unresolved live-ownership uncertainty, but also preserve per-task interrupted-recovery blocking so unaffected tasks are not unnecessarily frozen.  
        [Source: _bmad-output/planning-artifacts/architecture.md#reconciliation-rules] [Source: _bmad-output/planning-artifacts/prd.md#reliability--recovery]
  - [x] Ensure recovery inspect and startup summary can point to the same restored recovery run IDs after restart so operators are not forced to guess whether a run is new or resumed.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: tools/orchestration/cli/main.py]

- [x] Implement controller-owned recovery continuation and explicit abandonment commands. (AC: 3, 4)
  - [x] Implement `macs recovery retry` as the continuation path for an unresolved recovery run, reusing the existing assignment or reroute pipeline where possible so a task can resume after an interruption such as predecessor revocation before successor activation.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/tasks.py]
  - [x] Implement `macs recovery reconcile` as the explicit controller-owned way to clear or abandon an interrupted recovery run with durable audit, leaving later assignment or reroute to happen only as a fresh deliberate action.  
        [Source: _bmad-output/planning-artifacts/ux-design-specification.md#reconciliation-flow] [Source: tools/orchestration/store.py] [Source: tools/orchestration/recovery.py]
  - [x] Record explicit recovery events for retry, resume, completion, or abandonment so a later inspector can tell whether the operator continued an existing run or deliberately cleared it. Keep this limited to recovery-run lifecycle and do not broaden into Story 6.2 rationale capture.  
        [Source: _bmad-output/planning-artifacts/architecture.md#recovery-outputs] [Source: _bmad-output/planning-artifacts/prd.md#auditability-governance-and-operator-trust]

- [x] Fail closed for successor routing while interrupted recovery remains pending. (AC: 3, 4, 5)
  - [x] Add narrow guards in the task assignment or reroute path so a task with an unresolved interrupted recovery run cannot silently mint a successor lease through the normal path. The supported continuation path should direct the operator to `macs recovery inspect`, `macs recovery retry`, or `macs recovery reconcile` as appropriate.  
        [Source: tools/orchestration/tasks.py] [Source: _bmad-output/planning-artifacts/architecture.md#interrupted-recovery]
  - [x] Preserve zero-or-one live lease invariants when a retry resumes after a predecessor was already revoked. Story 5.4 must not reanimate old ownership, duplicate current leases, or fabricate replacement history.  
        [Source: tools/orchestration/invariants.py] [Source: _bmad-output/planning-artifacts/architecture.md#release-gate-matrix]
  - [x] Keep unrelated tasks assignable unless startup recovery already requires a global block. Story 5.4 is about resumable recovery context, not a repo-wide freeze on every pending recovery record.  
        [Source: _bmad-output/planning-artifacts/prd.md#reliability--recovery] [Source: _bmad-output/project-context.md#code-quality--style-rules]

- [x] Extend read surfaces and regression coverage for resumed recovery runs. (AC: 3, 5)
  - [x] Extend `tools/orchestration/tests/test_setup_init.py` with restart cases proving unresolved recovery runs survive restart, preserve run IDs and decision context, and keep affected tasks blocked until retry or reconcile clears the run.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: _bmad-output/planning-artifacts/architecture.md#release-gate-matrix]
  - [x] Extend `tools/orchestration/tests/test_task_lifecycle_cli.py` with black-box cases for interrupted reroute continuation, explicit recovery reconcile or abandonment, and failure-closed assignment or reroute while a recovery run is unresolved.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: tools/orchestration/cli/main.py]
  - [x] Extend `tools/orchestration/tests/test_inspect_context_cli.py` so recovery inspect, task inspect, and overview surfaces show restored recovery-run status, next actions, and continuation versus abandonment state in both human-readable and `--json` output.  
        [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: tools/orchestration/overview.py] [Source: tools/orchestration/cli/main.py]

## Dev Notes

### Story Intent

Story 5.4 closes the remaining recovery-engine gap after Story 5.3. MACS can already freeze risky work, persist a recovery run, and reroute safely while the controller stays online. The missing slice is restart-safe continuation when recovery itself is interrupted, especially once predecessor ownership has already been revoked or the operator exits mid-flow.  
[Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-5-recovery-engine-before-controller-surface-expansion] [Source: _bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md]

### Previous Story Intelligence

- Story 5.3 already established the only recovery persistence channel this story should use: `tools/orchestration/recovery.py` writes task-scoped recovery metadata into `recovery_runs`, and `macs recovery inspect` plus task or overview read surfaces already read from that table. Story 5.4 should enrich and resume those records rather than adding a second restart ledger.  
  [Source: _bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md#completion-notes-list] [Source: tools/orchestration/recovery.py]
- Story 5.3 reroute explicitly revokes the predecessor lease before successor activation. If the controller exits between those steps, the affected task can legitimately be left in `reconciliation` with no current live lease while a pending recovery run still exists. That state must be treated as resumable interrupted recovery, not as ordinary free assignment.  
  [Source: _bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md#implementation-guardrails] [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/invariants.py]
- Story 5.2 and Story 4.4 already centralized blocking-condition and next-action rendering in controller-owned helpers. Reuse those seams when extending read-side messaging for resumed recovery rather than inventing a new display path.  
  [Source: _bmad-output/implementation-artifacts/stories/5-2-freeze-risky-work-through-intervention-hold-and-lease-suspension.md#completion-notes-list] [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md] [Source: tools/orchestration/interventions.py]
- Story 1.4 already made startup recovery authoritative and restart-safe for persisted live state. Story 5.4 should extend that restart path to restore pending recovery runs, not replace the controller bootstrap model.  
  [Source: _bmad-output/implementation-artifacts/stories/1-4-restore-controller-state-safely-on-restart.md] [Source: tools/orchestration/recovery.py]

### Technical Requirements

- Treat unresolved recovery runs as first-class controller state even when the task currently has no live lease. Recovery context cannot disappear just because predecessor revocation already happened before the interruption.  
  [Source: _bmad-output/planning-artifacts/architecture.md#interrupted-recovery] [Source: tools/orchestration/tasks.py]
- Preserve state authority boundaries: restart and resumed recovery must read persisted controller state first, then optionally layer fresh evidence without letting adapters override canonical ownership or recovery phase.  
  [Source: _bmad-output/planning-artifacts/prd.md#reliability--recovery] [Source: _bmad-output/project-context.md#framework-specific-rules]
- Keep successor activation explicit. `recovery retry` may continue a pending reroute or assignment path, but it must still respect predecessor-resolution ordering and zero-or-one live lease invariants.  
  [Source: _bmad-output/planning-artifacts/architecture.md#interrupted-recovery] [Source: tools/orchestration/invariants.py]
- Explicit abandonment must be durable and inspectable, but Story 5.4 does not need freeform rationale capture or rich causal linking beyond the current event model. Story 6.2 owns that broader intervention-rationale enhancement.  
  [Source: _bmad-output/planning-artifacts/prd.md#auditability-governance-and-operator-trust] [Source: _bmad-output/planning-artifacts/epics.md#story-62-preserve-intervention-rationale-across-recovery-and-reassignment]
- Stay within Python 3.8+ stdlib, SQLite, and the existing shell-first repo structure; do not add daemons, external queues, or third-party libraries.  
  [Source: _bmad-output/project-context.md#technology-stack--versions] [Source: _bmad-output/project-context.md#development-workflow-rules]

### Architecture Compliance

- Keep the controller authoritative. Recovery-run restoration, retry, and abandonment must all be represented by durable SQLite writes and controller events, not implicit tmux-side conventions.  
  [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: tools/orchestration/store.py]
- Reuse the existing write-model pattern: validate current persisted state, mutate transactionally, write durable events, then render human-readable or JSON output from the same controller truth.  
  [Source: _bmad-output/planning-artifacts/architecture.md#write-model] [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/cli/main.py]
- Preserve restart boundaries: startup recovery may surface pending runs and set global `assignments_blocked` when live ownership is uncertain, but task-scoped interrupted recovery should otherwise block only the affected task’s successor routing path.  
  [Source: _bmad-output/planning-artifacts/architecture.md#reconciliation-rules] [Source: tools/orchestration/recovery.py]
- Preserve audit visibility. Operators must be able to inspect whether a recovery run was resumed, completed, or abandoned after restart rather than reverse-engineering that from raw pane output.  
  [Source: _bmad-output/planning-artifacts/architecture.md#recovery-outputs] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content]

### File Structure Requirements

- Extend `tools/orchestration/recovery.py` for recovery-run persistence shape, startup restoration of unresolved runs, and controller-owned retry or reconcile helpers.
- Extend `tools/orchestration/tasks.py` with narrow guards or continuation helpers so interrupted recovery cannot be bypassed by the normal assignment path.
- Extend `tools/orchestration/cli/main.py` so `recovery inspect`, `recovery retry`, and `recovery reconcile` use the same frozen envelopes and concise human-readable output style as other controller actions.
- Extend `tools/orchestration/overview.py` and any adjacent inspect helpers only as needed so resumed recovery is legible in existing read surfaces.
- Prefer extending the current orchestration regression modules before creating new ones: `tools/orchestration/tests/test_setup_init.py`, `tools/orchestration/tests/test_task_lifecycle_cli.py`, and `tools/orchestration/tests/test_inspect_context_cli.py`.

[Source: _bmad-output/project-context.md#development-workflow-rules]  
[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]

### Testing Requirements

- Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused required validation surface for this story.  
  [Source: _bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md#debug-log-references]
- Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Add restart-focused tests proving an interrupted recovery run survives controller restart without losing run ID, anomaly summary, or proposed continuation state.  
  [Source: tools/orchestration/tests/test_setup_init.py] [Source: _bmad-output/planning-artifacts/architecture.md#release-gate-matrix]
- Add black-box command tests for `macs recovery retry` and `macs recovery reconcile`, including the case where predecessor revocation already happened before restart and the case where later fresh assignment remains blocked until reconcile or retry resolves the run.  
  [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: tools/orchestration/cli/main.py]
- Preserve regressions for Story 5.3 safe reroute, Story 5.2 freeze, Story 4.4 pause or resume, and Story 1.4 startup recovery so this story does not regress existing containment and restart behavior.  
  [Source: _bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md] [Source: _bmad-output/implementation-artifacts/stories/5-2-freeze-risky-work-through-intervention-hold-and-lease-suspension.md] [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md] [Source: _bmad-output/implementation-artifacts/stories/1-4-restore-controller-state-safely-on-restart.md]

### Git Intelligence Summary

Recent committed work is already concentrated in the exact seams Story 5.4 should extend:

- `c3ccc6a` resolved review findings in the recovery and lifecycle area and confirms that recent sprint momentum is in controller-owned recovery correctness rather than new subsystem creation.
- `51d2554` captured the earlier recovery rework slice that Story 5.4 now needs to finish for restart-safe continuation.
- `e474089` established orchestration bootstrap and controller-lock foundations that startup recovery and resumable recovery runs still depend on.
- Current brownfield momentum remains in `tools/orchestration/recovery.py`, `tools/orchestration/tasks.py`, `tools/orchestration/cli/main.py`, and the existing orchestration test modules. Keep implementation centered there.

[Source: git log --oneline -5]  
[Source: git show --stat --oneline --no-patch c3ccc6a]  
[Source: git show --stat --oneline --no-patch 51d2554]  
[Source: git show --stat --oneline --no-patch e474089]

### Implementation Guardrails

- Do not create a second recovery persistence channel in metadata or a new table when `recovery_runs` already exists.
- Do not silently auto-assign or auto-reroute affected tasks on restart just because a proposed worker was already persisted.
- Do not treat a task in `reconciliation` with no current live lease as ordinary safe assignment if an unresolved recovery run says the prior recovery flow was interrupted.
- Do not broaden this story into rich rationale capture, event-tail UX expansion, or general audit-history work that belongs to Epic 6.
- Do not block unrelated task assignment unless existing startup recovery rules already require the repo-wide `assignments_blocked` safety gate.
- Do not add third-party Python dependencies, background services, or a TUI to implement resumable recovery.

### Project Structure Notes

- This repo remains a brownfield, shell-first orchestration control plane. `tools/orchestration/` owns controller truth; tmux remains the execution substrate and compatibility layer.
- Story 5.4 should feel like the direct completion of Story 5.3’s reroute semantics and Story 1.4’s restart model, not a new recovery subsystem.
- The safest implementation path is incremental: enrich the existing recovery-run shape, restore unresolved runs during startup, wire the missing `recovery retry/reconcile` actions, then prove the behavior with focused restart and lifecycle regressions.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/planning-artifacts/sprint-plan-2026-04-09.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/1-4-restore-controller-state-safely-on-restart.md`
- `_bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md`
- `_bmad-output/implementation-artifacts/stories/5-2-freeze-risky-work-through-intervention-hold-and-lease-suspension.md`
- `_bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md`
- `tools/orchestration/recovery.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/overview.py`
- `tools/orchestration/interventions.py`
- `tools/orchestration/invariants.py`
- `tools/orchestration/store.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Enrich the existing `recovery_runs` payload shape and startup restoration path first so interrupted recovery becomes durable and inspectable before new command behavior is added.
- Implement `recovery retry` and `recovery reconcile` as narrow controller-owned actions that reuse existing reroute or assignment seams where possible instead of duplicating routing logic.
- Prove the behavior in narrow red-green slices around restart restoration, per-task fail-closed routing, and read-side recovery visibility, then finish with full validation and an explicit BMAD QA acceptance pass.

### Story Creation Notes

- Skill used: `bmad-create-story`
- Target story auto-discovered from `sprint-status.yaml` after Story 5.3 was completed.
- Inputs reviewed for this story: Epic 5 story definition, PRD recovery and restart requirements, architecture reconciliation and interrupted-recovery rules, operator CLI contract, UX recovery flow, project context, Story 1.4 startup recovery, Story 5.2 and Story 5.3 implementation notes, current git history, and the live brownfield seams in `recovery.py`, `tasks.py`, `overview.py`, `cli/main.py`, and the orchestration CLI tests.
- Validation pass applied against the BMAD create-story checklist before dev handoff: the story now includes previous-story intelligence, brownfield-safe reuse guidance, explicit anti-scope guardrails, a clear recovery-command target, and regression requirements for interrupted reroute and restart restoration.

### Debug Log References

- `2026-04-10T14:28:33+01:00` Story 5.4 created as the next BMAD story from `sprint-status.yaml`, validated against the create-story checklist, and moved to `ready-for-dev`.
- `2026-04-10T14:28:50+01:00` Story 5.4 moved to `in-progress`; implementation started with red tests for unresolved interrupted recovery blocking and persisted `recovery retry`.
- `2026-04-10T14:31:00+01:00` First red-green slice landed: normal `task assign` now fails closed on unresolved interrupted recovery, `macs recovery retry` resumes persisted continuation, and `macs recovery reconcile` can explicitly abandon the run with audit.
- `2026-04-10T14:35:00+01:00` Second red-green slice landed: startup summary now surfaces unresolved task-scoped recovery runs, and reconciliation tasks without a live lease surface controller-owned blocking and next action through task or recovery inspect.
- `2026-04-10T14:40:00+01:00` Explicit BMAD QA acceptance pass found one final read-side gap: human-readable `overview show` hid reconciliation tasks with interrupted recovery runs. The surface was fixed and regression-covered before completion.
- `2026-04-10T14:42:11+01:00` Validation completed with `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` and `python3 -m unittest discover -s tools/orchestration/tests` (95 tests, passing). No repo-configured Python lint or static-analysis config was present.

### Completion Notes List

- Extended `tools/orchestration/recovery.py` so unresolved recovery runs can be queried, abandoned, restored in startup summaries, and rendered with explicit interruption-aware next actions.
- Added controller-owned `macs recovery retry` and `macs recovery reconcile` flows in `tools/orchestration/tasks.py` and `tools/orchestration/cli/main.py`, reusing the existing assignment or reroute pipeline rather than inventing a parallel recovery dispatcher.
- Added a fail-closed assignment guard so a task in `reconciliation` with an unresolved interrupted recovery run cannot silently mint a fresh successor lease through the normal path.
- Surfaced interrupted recovery guidance in task inspect, recovery inspect, startup init, and overview output, including human-readable reconciliation summaries for recovery runs with no current live lease.
- Added restart, retry, reconcile, and interrupted-recovery inspect regressions across the existing orchestration test modules.
- Explicit BMAD QA acceptance passed with no remaining findings after the final overview visibility fix.

### File List

- `_bmad-output/implementation-artifacts/stories/5-4-resume-interrupted-recovery-from-persisted-recovery-runs.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `tools/orchestration/recovery.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/overview.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_setup_init.py`
