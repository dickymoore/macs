# Story 5.2: Freeze risky work through intervention hold and lease suspension

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want degraded tasks to enter an explicit hold state before unsafe work continues,
so that the controller prevents conflicting progression during investigation.

## Acceptance Criteria

1. MACS gains a controller-owned risk-freeze path for already-active work. When an active task's current worker crosses into degraded or otherwise unsafe evidence under controller policy, the controller transitions `task.state` from `active` to `intervention_hold`, transitions the same live lease from `active` or `expiring` to `suspended`, preserves current owner and live-lease identity, and records durable intervention history without creating a successor lease.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-52-freeze-risky-work-through-intervention-hold-and-lease-suspension] [Source: _bmad-output/planning-artifacts/prd.md#monitoring-intervention-and-recovery] [Source: _bmad-output/planning-artifacts/prd.md#orchestration-control--task-lifecycle] [Source: _bmad-output/planning-artifacts/architecture.md#task-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#failure-containment-model]
2. Policy-driven suspension remains distinct from operator-held pause. Story 4.4's `paused` lease semantics remain intact for explicit operator pause or resume, while this story introduces controller-held `suspended` semantics for unresolved risk. Human-readable and `--json` surfaces expose which hold type is active, the intervention basis, and the recommended next action without allowing adapter evidence to overwrite controller truth.  
   [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#surface-model]
3. While a task is in risk hold with a live `paused` or `suspended` lease, conflicting progression is blocked. MACS preserves the current owner, live lease, and protected-surface locks, blocks conflicting reassignment or successor-lease creation until the hold is explicitly resolved, and fails closed instead of silently continuing work.  
   [Source: _bmad-output/planning-artifacts/prd.md#orchestration-control--task-lifecycle] [Source: _bmad-output/planning-artifacts/prd.md#ownership-locking-and-safe-parallelisation] [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: _bmad-output/planning-artifacts/architecture.md#lock] [Source: _bmad-output/planning-artifacts/architecture.md#reconciliation-rules]
4. Controller read-side surfaces reflect the freeze immediately. `macs overview show`, `macs worker inspect`, `macs task inspect`, and `macs lease inspect` surface intervention hold, suspended lease state, intervention basis, current blocking condition, and next actions in both human-readable and machine-readable forms, while preserving the frozen Phase 1 command family and output envelope.  
   [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/planning-artifacts/architecture.md#ux-backing-requirements] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#maintainer-intervenes-in-a-degraded-session]
5. Regression coverage proves policy-driven freeze, live-lease suspension, blocked reassignment while held, preserved lock ownership, clear paused-versus-suspended rendering, and no regression to Story 5.1 worker classification or Story 4.4 operator pause or resume behavior.  
   [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: _bmad-output/planning-artifacts/architecture.md#failure-drill-tests] [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/implementation-artifacts/stories/5-1-classify-worker-health-and-surface-warnings-promptly.md] [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md]

## Tasks / Subtasks

- [x] Add a controller-owned risk-freeze helper for active work. (AC: 1, 2, 3)
  - [x] Extend `tools/orchestration/tasks.py` with a focused helper such as `freeze_task_for_risk(...)` or an equivalently narrow controller-owned path that validates current authoritative state before mutating anything.  
        [Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape] [Source: tools/orchestration/tasks.py]
  - [x] Transition the live lease from `active` or `expiring` to `suspended`, and transition the task from `active` to `intervention_hold`, preserving `current_worker_id`, `current_lease_id`, and existing active locks. Do not create a successor lease and do not release protection during the freeze.  
        [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: tools/orchestration/invariants.py]
  - [x] Record durable event history for the freeze, including intervention basis and evidence summary or reference. Follow the existing `task.*` and `lease.*` event naming pattern already used for assignment, pause, and resume; keep the chosen names explicit enough that inspect and history surfaces can distinguish operator pause from controller suspension.  
        [Source: _bmad-output/planning-artifacts/prd.md#auditability-governance-and-operator-trust] [Source: tools/orchestration/store.py] [Source: tools/orchestration/tasks.py]

- [x] Wire policy-driven freeze into the existing worker-health and recovery seams without broadening into reroute. (AC: 1, 3, 4)
  - [x] Reuse Story 5.1 worker classification results so that when a current owner becomes `degraded`, `unavailable`, or `quarantined`, the controller can freeze the attached active task rather than only warning about the worker.  
        [Source: _bmad-output/implementation-artifacts/stories/5-1-classify-worker-health-and-surface-warnings-promptly.md#completion-notes-list] [Source: tools/orchestration/health.py] [Source: tools/orchestration/cli/main.py]
  - [x] Keep degraded-single-owner risk hold separate from ambiguous-ownership reconciliation. Story 5.2 should place risky but still singly owned work into `intervention_hold` plus `suspended`; Story 5.3 will own lease revocation, successor-lease creation, and reroute semantics.  
        [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#reconciliation-rules] [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-5-recovery-engine-before-controller-surface-expansion]
  - [x] Reuse current recovery metadata such as `assignments_blocked` where it already represents unresolved controller uncertainty, but do not rewrite startup reconciliation into a second model. The brownfield-safe target is shared freeze semantics, not a restart-flow redesign.  
        [Source: tools/orchestration/recovery.py] [Source: tools/orchestration/tasks.py]

- [x] Expose suspended-hold semantics in overview and inspect paths. (AC: 2, 4)
  - [x] Extend `tools/orchestration/tasks.py`, `tools/orchestration/overview.py`, and `tools/orchestration/cli/main.py` so task, worker, lease, and overview surfaces report intervention hold basis, live lease state, and the blocking or recommended next action from controller truth first.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/planning-artifacts/architecture.md#ux-backing-requirements] [Source: tools/orchestration/overview.py] [Source: tools/orchestration/cli/main.py]
  - [x] Update human-readable warnings and JSON payloads so `paused` versus `suspended` is explicit and color-independent, with stable canonical nouns and no change to the frozen top-level envelopes.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#canonical-state-vocabularies]
  - [x] Reuse or narrowly extend `tools/orchestration/interventions.py` for shared intervention-basis or runtime-support rendering if that reduces duplication across task, lease, and worker surfaces.  
        [Source: tools/orchestration/interventions.py] [Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]

- [x] Preserve assignment, lock, and live-lease invariants while held. (AC: 1, 3, 5)
  - [x] Ensure `assign_task(...)` and any adjacent controller-owned assignment path continue to fail closed while a task retains a live `paused` or `suspended` lease or an unresolved intervention hold.  
        [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/invariants.py] [Source: _bmad-output/planning-artifacts/prd.md#orchestration-control--task-lifecycle]
  - [x] Keep lock history and active lock ownership intact during the freeze so protected surfaces remain guarded until later revoke, reconciliation, or reroute flows explicitly supersede the lease.  
        [Source: _bmad-output/planning-artifacts/prd.md#ownership-locking-and-safe-parallelisation] [Source: _bmad-output/planning-artifacts/architecture.md#lock] [Source: tools/orchestration/locks.py]
  - [x] Do not broaden `macs task resume` to reactivate controller-suspended leases unless the resulting flow is explicitly supported by the controller's current recovery rules. Story 5.2's safe minimum is freeze-and-block; Story 5.3 owns the next-step reroute or explicit recovery path.  
        [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#recovery-principles]

- [x] Add regression coverage for risk-freeze behavior and regressions against existing pause semantics. (AC: 5)
  - [x] Extend `tools/orchestration/tests/test_task_lifecycle_cli.py` with black-box cases that freeze an active task because its owner is reclassified or otherwise marked unsafe, verify `task.state == intervention_hold`, verify `lease.state == suspended`, and confirm no successor lease was created.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: _bmad-output/planning-artifacts/architecture.md#test-layers]
  - [x] Extend `tools/orchestration/tests/test_setup_init.py` or an adjacent focused recovery module to cover restart or stale-ownership scenarios that should remain `reconciliation` plus `suspended`, proving Story 5.2 did not collapse restart ambiguity into the wrong state machine branch.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/recovery.py]
  - [x] Extend `tools/orchestration/tests/test_inspect_context_cli.py` or adjacent inspect regressions so overview, task inspect, worker inspect, and lease inspect all surface `suspended` versus `paused` accurately in both human-readable and `--json` output.  
        [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: tools/orchestration/cli/main.py]

## Dev Notes

### Story Intent

Story 5.2 is the first controller-owned recovery-engine slice after Story 5.1's health classification and Story 4.4's operator-held pause or resume path. Story 5.1 can already identify risky workers, and Story 4.4 can already let an operator intentionally pause the current lease. Story 5.2 closes the remaining gap by freezing risky execution automatically from controller policy, using `intervention_hold` plus `suspended` without yet stepping into lease revocation, successor-lease activation, or full reroute semantics.  
[Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-5-recovery-engine-before-controller-surface-expansion] [Source: _bmad-output/implementation-artifacts/stories/5-1-classify-worker-health-and-surface-warnings-promptly.md] [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md]

### Previous Story Intelligence

- Story 5.1 already reclassifies stale workers in `tools/orchestration/health.py`, and `worker list`, `worker inspect`, and `overview show` already call that classification before rendering results. Story 5.2 should reuse that authoritative classification instead of inferring degraded risk from ad hoc probe text.  
  [Source: _bmad-output/implementation-artifacts/stories/5-1-classify-worker-health-and-surface-warnings-promptly.md#completion-notes-list] [Source: tools/orchestration/health.py] [Source: tools/orchestration/cli/main.py]
- Story 4.4 already implemented controller-owned `task pause` and `task resume`, human-readable next actions, and shared reduced-color or narrow rendering. Story 5.2 should extend those same surfaces to distinguish controller-held `suspended` risk freezes from operator-held `paused` holds instead of inventing parallel output paths.  
  [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md] [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/interventions.py]
- Startup recovery already suspends certain live leases and records `assignments_blocked`, but it moves uncertain ownership into `reconciliation` because restart ambiguity is different from degraded-but-single-owner risk. Preserve that distinction.  
  [Source: tools/orchestration/recovery.py] [Source: _bmad-output/planning-artifacts/architecture.md#reconciliation-rules]

### Brownfield Baseline

- `tools/orchestration/state_machine.py` already has the canonical vocabulary needed for this story: task states include `intervention_hold` and `reconciliation`; lease states include both `paused` and `suspended`; both are live-lease states.  
  [Source: tools/orchestration/state_machine.py]
- `tools/orchestration/tasks.py` already owns controller-side `pause_task(...)`, `resume_task(...)`, assignment guards, and paused-task inspect next-action logic. This is the correct first seam for risk-freeze helpers and for blocked-progression enforcement.  
  [Source: tools/orchestration/tasks.py]
- `tools/orchestration/recovery.py` already performs controller-owned suspension during restart recovery, writes `recovery_runs`, and stores metadata like `assignments_blocked`. Story 5.2 should reuse the same authoritative store patterns instead of inventing a second recovery state channel.  
  [Source: tools/orchestration/recovery.py]
- `tools/orchestration/overview.py` already treats `intervention_hold` and `reconciliation` as active surfaced task states, making it the right place to expose newly suspended tasks after policy freeze.  
  [Source: tools/orchestration/overview.py]
- `tools/orchestration/interventions.py` already centralizes runtime pause or resume support warnings. If Story 5.2 needs shared hold-basis or controller-only warning text, extend that helper instead of adding more duplicated formatter logic in `cli/main.py`.  
  [Source: tools/orchestration/interventions.py]
- `assign_task(...)` already rejects most conflicting progression because it only assigns from `pending_assignment` or `reconciliation` and fails if a current lease remains attached. Story 5.2 should harden and prove that behavior for `intervention_hold` plus `suspended`, not rewrite assignment from scratch.  
  [Source: tools/orchestration/tasks.py]

### Technical Requirements

- Preserve canonical state semantics exactly:
  - operator-held pause keeps `task.state == intervention_hold` and `lease.state == paused`
  - controller-held risk freeze keeps `task.state == intervention_hold` and `lease.state == suspended`
  - ambiguous ownership or restart uncertainty still uses `reconciliation` rather than overloading `intervention_hold`  
  [Source: _bmad-output/planning-artifacts/architecture.md#task-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#reconciliation-rules]
- Keep the same live lease in place during freeze. Do not revoke, replace, or clear `current_lease_id` and `current_worker_id` as part of Story 5.2.  
  [Source: _bmad-output/planning-artifacts/prd.md#orchestration-control--task-lifecycle] [Source: tools/orchestration/invariants.py]
- Preserve operator-visible lock protection during the hold. This story freezes risky continuation; it does not release ownership or open the protected surfaces for concurrent work.  
  [Source: _bmad-output/planning-artifacts/prd.md#ownership-locking-and-safe-parallelisation] [Source: tools/orchestration/locks.py]
- Human-readable and JSON output must make the hold basis legible and keep controller truth first. Adapter evidence can support the freeze decision, but it must not become the authoritative state field.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules]
- Stay within Python 3.8+ stdlib, SQLite, and the existing shell-first repo structure; do not add background daemons or third-party scheduling or TUI libraries for this increment.  
  [Source: _bmad-output/project-context.md#technology-stack--versions] [Source: _bmad-output/project-context.md#critical-dont-miss-rules]

### Architecture Compliance

- Controller authority first: the freeze decision and the resulting state transitions happen in controller-owned Python code and authoritative SQLite writes, not in tmux shell state or adapter claims.  
  [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: _bmad-output/project-context.md#framework-specific-rules]
- Follow the write-model pattern already used for lifecycle actions: validate current state, perform transactional store mutations, write durable events, then surface runtime uncertainty or controller-only warnings separately.  
  [Source: _bmad-output/planning-artifacts/architecture.md#write-model] [Source: tools/orchestration/tasks.py]
- Preserve the zero-or-one live-lease invariant. `suspended` is still live, so no successor lease may appear until a later story explicitly revokes or replaces the current one.  
  [Source: _bmad-output/planning-artifacts/architecture.md#lease] [Source: tools/orchestration/invariants.py]
- Maintain the recovery boundary: Story 5.2 freezes and blocks. Story 5.3 handles revocation, reroute, and successor-lease activation; Story 5.4 handles resumable recovery-run persistence beyond the startup baseline already present.  
  [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-5-recovery-engine-before-controller-surface-expansion] [Source: _bmad-output/planning-artifacts/prd.md#monitoring-intervention-and-recovery]
- Preserve audit visibility. Hold entry, basis, and resulting task or lease states must remain inspectable through event and object inspectors rather than only through raw pane history.  
  [Source: _bmad-output/planning-artifacts/prd.md#auditability-governance-and-operator-trust] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#recovery-principles]

### File Structure Requirements

- Extend `tools/orchestration/tasks.py` for controller-owned risk-freeze helpers, blocked progression checks, and intervention-hold inspect context.
- Extend `tools/orchestration/health.py` or a narrowly scoped adjacent helper so worker reclassification can trigger the freeze policy for attached active tasks.
- Extend `tools/orchestration/overview.py` and `tools/orchestration/cli/main.py` so overview, worker, task, and lease surfaces report the new suspended-hold semantics cleanly.
- Reuse and, if needed, narrowly extend `tools/orchestration/interventions.py` for shared intervention-basis or warning formatting.
- Reuse `tools/orchestration/recovery.py` and `tools/orchestration/store.py` patterns for metadata, eventful writes, and recovery-run compatibility rather than creating a parallel persistence model.
- Extend existing regression modules before adding new ones: `tools/orchestration/tests/test_task_lifecycle_cli.py`, `tools/orchestration/tests/test_inspect_context_cli.py`, and `tools/orchestration/tests/test_setup_init.py` are the preferred first targets.

[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]  
[Source: _bmad-output/project-context.md#development-workflow-rules]

### Testing Requirements

- Use `python3 -m unittest discover -s tools/orchestration/tests` as the primary validation surface.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Add black-box CLI coverage showing that a controller command path which reclassifies a current owner to `degraded`, `unavailable`, or `quarantined` also freezes the attached active task into `intervention_hold` with a `suspended` live lease.  
  [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: tools/orchestration/cli/main.py]
- Assert that task, lease, and overview inspection surfaces clearly distinguish `paused` versus `suspended`, surface intervention basis, and keep `warnings` or next actions stable in `--json`.  
  [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output]
- Preserve Story 4.4 regressions for operator pause or resume, including blocked resume behavior, so the new controller-held freeze path does not change operator-held pause semantics.  
  [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md] [Source: tools/orchestration/tests/test_task_lifecycle_cli.py]
- Preserve startup-recovery regressions proving uncertain restart state still becomes `reconciliation` with suspended leases and `assignments_blocked`, not the new degraded-risk hold path.  
  [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/recovery.py]
- Add explicit assertions that no second live lease is created and that active locks remain attached to the predecessor lease while the task is held.  
  [Source: _bmad-output/planning-artifacts/architecture.md#lease] [Source: tools/orchestration/invariants.py] [Source: tools/orchestration/locks.py]

### Git Intelligence Summary

Recent committed work already concentrates in the exact seams Story 5.2 should extend:

- `c3ccc6a` focused on post-review lifecycle and recovery correctness around `tools/orchestration/tasks.py`, tests, and story bookkeeping.
- `51d2554` captured the first recovery or orchestration rework slice.
- `e474089` established orchestration bootstrap and controller-lock foundations that Story 5.2 still depends on for authoritative restart-safe state.
- Current brownfield momentum is in `tasks.py`, `health.py`, `recovery.py`, `cli/main.py`, and the existing orchestration CLI test modules. Keep the implementation centered there rather than creating a parallel recovery subsystem.

[Source: git log --oneline -5]  
[Source: git show --stat --oneline --no-patch c3ccc6a]  
[Source: git show --stat --oneline --no-patch 51d2554]  
[Source: git show --stat --oneline --no-patch e474089]

### Implementation Guardrails

- Do not conflate `paused` and `suspended`; operator intent and controller risk-freeze are different semantics even if both keep the lease live.
- Do not release locks, clear `current_worker_id`, or clear `current_lease_id` when freezing risky work.
- Do not auto-reroute, revoke, replace, or activate a successor lease in this story; that belongs to Story 5.3.
- Do not collapse restart ambiguity or duplicate-claim reconciliation into `intervention_hold` just because the lease is suspended. Keep `reconciliation` reserved for uncertain ownership or restart-safe recovery flows.
- Do not make raw tmux state the authoritative freeze signal. If runtime interruption depth is partial, controller state still freezes progression.
- Do not add new third-party Python dependencies, a background monitoring daemon, or a full-screen TUI to implement this increment.

### Project Structure Notes

- This repo remains a brownfield, shell-first orchestration control plane. `tools/orchestration/` owns controller truth; tmux remains the execution substrate and compatibility layer.
- Story 5.2 should feel like a direct extension of Story 5.1's worker-health classification and Story 4.4's intervention surfaces, not a standalone recovery engine rewrite.
- The safest implementation path is incremental: reuse existing lifecycle, recovery, and inspect seams first, then add narrowly targeted helpers only where repeated logic would otherwise sprawl.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/planning-artifacts/sprint-plan-2026-04-09.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/5-1-classify-worker-health-and-surface-warnings-promptly.md`
- `_bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/health.py`
- `tools/orchestration/recovery.py`
- `tools/orchestration/interventions.py`
- `tools/orchestration/overview.py`
- `tools/orchestration/invariants.py`
- `tools/orchestration/state_machine.py`
- `tools/orchestration/store.py`
- `tools/orchestration/locks.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_setup_init.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add controller-owned risk-freeze helpers in `tools/orchestration/tasks.py` first, then wire them through existing worker-health and operator command paths instead of creating a second recovery subsystem.
- Centralize hold-state next-action and blocking-condition logic in `tools/orchestration/interventions.py` so task, worker, lease, and overview surfaces render `paused` versus `suspended` consistently.
- Prove the behavior with narrow red-green slices across task lifecycle, inspect surfaces, and restart recovery regressions before running the full orchestration suite and a final BMAD QA acceptance pass.

### Story Creation Notes

- Skill used: `bmad-create-story`
- Target story auto-discovered from `sprint-status.yaml` after Story 4.4 was accepted and marked `done`.
- Inputs reviewed for this story: Epic 5 story definition, PRD recovery and lifecycle requirements, architecture state-machine and failure-containment rules, UX intervention flow, project context, Story 5.1 completion notes, Story 4.4 authoritative implementation story, recent git history, and the current brownfield orchestration seams in `tasks.py`, `health.py`, `recovery.py`, `overview.py`, `interventions.py`, and the CLI tests.

### Debug Log References

- `2026-04-10T11:52:00+01:00` Story 5.2 created as the next ready-for-dev BMAD story after QA acceptance closed Story 4.4.
- `2026-04-10T12:05:00+01:00` Story 5.2 moved to `in-progress`; implementation started in narrow red-green slices aligned to freeze semantics, inspect surfaces, invariant enforcement, and explicit QA acceptance.
- `2026-04-10T12:12:00+01:00` First red-green slice landed: failing regressions proved stale-owner freeze semantics and suspended-hold task or lease inspection, then controller-owned `freeze_task_for_risk(...)` plus health-classification wiring made those cases pass.
- `2026-04-10T12:20:00+01:00` Second red-green slice landed: manual worker disable or quarantine now freezes owned active tasks, and worker or overview surfaces report intervention basis, blocking condition, and next actions for suspended holds.
- `2026-04-10T12:27:00+01:00` Final read-side slice landed: `task inspect` and `lease inspect` now trigger the same safety freeze as other read surfaces and serialize blocking condition plus next action without collapsing restart reconciliation semantics.
- `2026-04-10T12:31:56+01:00` Validation completed with `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` and `python3 -m unittest discover -s tools/orchestration/tests` (79 tests, passing). No repo-configured Python lint or static-analysis config was present.
- `2026-04-10T12:31:56+01:00` Explicit BMAD QA acceptance pass completed against Story 5.2. One final acceptance gap was found and fixed during review: `task inspect` and `lease inspect` now classify or freeze unsafe current owners immediately instead of depending on a prior worker-health read path.

### Completion Notes List

- Added controller-owned `freeze_task_for_risk(...)` and `freeze_owned_active_tasks_for_worker(...)` helpers in `tools/orchestration/tasks.py`, transitioning active or expiring live leases to `suspended` and tasks to `intervention_hold` without minting successor leases or releasing locks.
- Wired risk freezes into worker-health classification and manual unsafe worker-state commands so degraded, unavailable, and quarantined owners freeze attached active tasks under controller authority.
- Extended `task inspect`, `worker inspect`, `lease inspect`, and `overview show` to distinguish `paused` versus `suspended`, surface intervention basis plus blocking condition, and report consistent next actions from shared intervention helpers.
- Preserved restart recovery boundaries: startup recovery tasks remain in `reconciliation` with suspended leases, and Story 5.2 does not broaden resume into reactivating controller-suspended leases.
- Added regression coverage for stale-owner freeze, manual disable freeze, suspended-hold inspect surfaces, overview summaries, and restart-recovery stability; then passed the full orchestration unittest discovery suite.
- Explicit BMAD QA acceptance found and closed the final read-surface gap before completion, leaving no outstanding findings against the authoritative story text.

### File List

- `_bmad-output/implementation-artifacts/stories/5-2-freeze-risky-work-through-intervention-hold-and-lease-suspension.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/health.py`
- `tools/orchestration/interventions.py`
- `tools/orchestration/overview.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/workers.py`

### Change Log

- `2026-04-10`: Implemented controller-driven risk holds and live-lease suspension, expanded operator surfaces for suspended-hold visibility, added regression coverage, and completed BMAD QA acceptance with no remaining findings.
