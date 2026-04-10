# Story 5.3: Reconcile ambiguous ownership and reroute safely

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want reroute and recovery flows to revoke or replace unsafe ownership explicitly,
so that a task can move forward without ever appearing to have two active owners.

## Acceptance Criteria

1. MACS gains a controller-owned ambiguous-ownership recovery path for held or reconciliation-bound work. When a task is frozen because of disconnect, duplicate claim, lock collision, misleading health evidence, or equivalent controller uncertainty, the controller persists a recovery record that captures the anomaly basis, predecessor lease and worker, current blocking condition, allowed next actions, and any proposed reroute target without trusting adapter claims as authority.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-53-reconcile-ambiguous-ownership-and-reroute-safely] [Source: _bmad-output/planning-artifacts/architecture.md#recovery-outputs] [Source: _bmad-output/planning-artifacts/architecture.md#reconciliation-rules] [Source: _bmad-output/planning-artifacts/prd.md#journey-2-maintainer-intervenes-in-a-degraded-session-and-recovers-safely] [Source: _bmad-output/planning-artifacts/prd.md#security--governance]
2. `macs task reroute` becomes a controller-owned operator-confirmed recovery action for frozen or reconciliation work. When the operator confirms reroute with `--worker` or `--workflow-class`, the controller transitions the predecessor live lease to `revoked` before any successor lease becomes current, records durable lease or task recovery events, and only then reserves, dispatches, and activates the successor lease. The predecessor lease is linked to the successor through explicit replacement history, and the task never has more than one live owner or live lease at any point in the flow.  
   [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#minimum-required-flags] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/architecture.md#lease] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#decision-rights-model]
3. Reconciliation continues to fail closed until ambiguity is resolved. While a recovery run is pending or a task remains in `intervention_hold` or `reconciliation` with an unresolved predecessor, normal assignment, resume, or successor activation without predecessor resolution is rejected with a clear controller-owned explanation. If reroute side effects fail after predecessor revocation, MACS leaves the task in an explicit safe controller state rather than silently reactivating or fabricating ownership.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-53-reconcile-ambiguous-ownership-and-reroute-safely] [Source: _bmad-output/planning-artifacts/architecture.md#failure-containment-model] [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: _bmad-output/planning-artifacts/prd.md#observability--auditability]
4. Controller-first read surfaces make recovery legible. `macs recovery inspect`, `macs task inspect`, `macs lease inspect`, `macs lease history`, and `macs overview show` surface anomaly summary, predecessor and proposed successor ownership, blocking condition, allowed next actions, recovery-run state, and resulting replacement linkage in both human-readable and `--json` forms while preserving the frozen Phase 1 command vocabulary and output envelope.  
   [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#reconciliation-flow] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#post-recovery-ux]
5. Regression coverage proves ambiguous-ownership reroute or reconciliation behavior, predecessor revocation before successor activation, replacement linkage, blocked unsafe progression, recovery inspect output, and no regressions to Story 5.2 risk-freeze behavior, Story 4.4 pause or resume semantics, or startup recovery invariants.  
   [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: _bmad-output/planning-artifacts/architecture.md#failure-drill-tests] [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/implementation-artifacts/stories/5-2-freeze-risky-work-through-intervention-hold-and-lease-suspension.md] [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md]

## Tasks / Subtasks

- [x] Add controller-owned recovery-run helpers for ambiguous ownership. (AC: 1, 3, 4)
  - [x] Extend `tools/orchestration/recovery.py` with a focused helper or helpers that create, update, and inspect task-scoped recovery metadata using the existing `recovery_runs` table instead of inventing a second persistence channel. Capture anomaly basis, predecessor task or lease refs, proposed action, allowed next actions, and current blocking condition.  
        [Source: _bmad-output/planning-artifacts/architecture.md#recovery-outputs] [Source: tools/orchestration/recovery.py] [Source: tools/orchestration/store.py]
  - [x] Reuse Story 5.2 freeze semantics and startup recovery metadata where possible. Held degraded work and startup reconciliation may arrive through different triggers, but 5.3 should converge them onto one controller-authored recovery summary shape without rewriting restart recovery into a new model.  
        [Source: _bmad-output/implementation-artifacts/stories/5-2-freeze-risky-work-through-intervention-hold-and-lease-suspension.md#brownfield-baseline] [Source: tools/orchestration/recovery.py] [Source: tools/orchestration/tasks.py]
  - [x] Keep the recovery record controller-truth-first. Adapter evidence can be referenced or summarized, but worker claims must not become the canonical current-owner field or the source of recovery state.  
        [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: _bmad-output/project-context.md#framework-specific-rules]

- [x] Implement safe predecessor-resolution and successor-activation for `macs task reroute`. (AC: 2, 3)
  - [x] Extend `tools/orchestration/tasks.py` with a narrow controller-owned reroute helper that only accepts frozen or reconciliation tasks, validates current authoritative state, and treats the CLI command itself as the operator-confirmed recovery action.  
        [Source: _bmad-output/planning-artifacts/architecture.md#decision-rights-model] [Source: tools/orchestration/tasks.py]
  - [x] Revoke the predecessor live lease before any successor lease becomes current. Record explicit `lease.revoked` and successor-linkage history, clear or update task ownership only through existing invariant helpers, and prove that zero-or-one live lease semantics hold across every step of the reroute flow.  
        [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: tools/orchestration/invariants.py]
  - [x] Reuse the existing assignment or dispatch path wherever practical so routing, lock reservation, adapter dispatch, and activation semantics stay consistent with Story 4.2. If shared helpers are needed, extract them narrowly instead of duplicating assign logic in the reroute path.  
        [Source: _bmad-output/implementation-artifacts/stories/4-2-assign-and-manage-task-lifecycle-actions-from-one-command-path.md#architecture-compliance] [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/locks.py]
  - [x] Fail closed on side-effect failure after predecessor revocation. The safe minimum is an explicit blocked controller state with durable recovery metadata and no fabricated active owner; do not silently reactivate the old lease or mint a second live one.  
        [Source: _bmad-output/planning-artifacts/architecture.md#failure-containment-model] [Source: _bmad-output/planning-artifacts/prd.md#security--governance]

- [x] Expose recovery inspection and replacement linkage in operator surfaces. (AC: 1, 4)
  - [x] Implement `macs recovery inspect --task <task-id>` in `tools/orchestration/cli/main.py` using the frozen command family and output envelope. Surface anomaly summary, frozen objects, allowed next actions, comparison of current versus proposed state, and recovery-run status in human-readable and `--json` modes.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output]
  - [x] Extend existing read-side helpers so `task inspect`, `lease inspect`, `lease history`, and `overview show` expose predecessor or successor lease linkage, recovery-run status, blocking condition, and next action consistently without forcing the operator to reconstruct state from event payloads by hand.  
        [Source: _bmad-output/planning-artifacts/ux-design-specification.md#reconciliation-flow] [Source: tools/orchestration/overview.py] [Source: tools/orchestration/history.py] [Source: tools/orchestration/interventions.py]
  - [x] Keep the terminology and output envelope stable: canonical nouns only, snake_case JSON, explicit event IDs for actions, and color-independent phrasing for blocked recovery or reroute conditions.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md]

- [x] Preserve lock, audit, and recovery invariants during reroute. (AC: 2, 3, 4, 5)
  - [x] Preserve predecessor lock history and make successor lock changes inspectable. If locks must move from predecessor to successor lease, do so through explicit release or reserve or activate events rather than by mutating history in place.  
        [Source: _bmad-output/planning-artifacts/architecture.md#lock] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#post-recovery-ux] [Source: tools/orchestration/locks.py]
  - [x] Keep blocked progression coherent across `assign_task(...)`, `resume_task(...)`, and the new reroute or recovery helpers. Tasks with unresolved ambiguity must stay blocked until controller-owned recovery state says otherwise.  
        [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/interventions.py] [Source: _bmad-output/planning-artifacts/architecture.md#reconciliation-rules]
  - [x] Preserve audit continuity through durable events and inspectable history. Recovery decisions, predecessor revocation, successor linkage, and resulting lock changes must remain reconstructable through existing event, task, lease, and overview surfaces.  
        [Source: _bmad-output/planning-artifacts/prd.md#observability--auditability] [Source: tools/orchestration/history.py] [Source: tools/orchestration/store.py]

- [x] Add regression coverage for ambiguous-ownership recovery and safe reroute. (AC: 5)
  - [x] Extend `tools/orchestration/tests/test_task_lifecycle_cli.py` with black-box cases for `macs task reroute`, covering reroute from held or reconciliation state, predecessor revocation before successor activation, structured failure when reroute is illegal, and no dual live leases at any step.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: _bmad-output/planning-artifacts/architecture.md#integration-tests]
  - [x] Extend `tools/orchestration/tests/test_inspect_context_cli.py` or an adjacent focused recovery CLI test so `recovery inspect`, `task inspect`, `lease inspect`, `lease history`, and `overview show` surface anomaly summary, replacement linkage, blocking condition, and next action consistently in human-readable and JSON output.  
        [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content]
  - [x] Extend `tools/orchestration/tests/test_setup_init.py` with regression assertions proving startup recovery still blocks assignments and preserves reconciliation semantics without accidentally auto-rerouting or activating successor leases.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/recovery.py]

## Dev Notes

### Story Intent

Story 5.3 is the first slice that is allowed to change ownership during degraded recovery. Story 5.2 deliberately stopped at freeze-and-block, leaving the operator with a suspended or paused lease and explicit next actions. Story 5.3 closes that gap by making reroute and reconciliation controller-owned, operator-confirmed paths that explicitly revoke or replace unsafe ownership before any successor becomes current. It should feel like a narrow extension of the existing lifecycle and recovery seams, not a new subsystem.  
[Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-5-recovery-engine-before-controller-surface-expansion] [Source: _bmad-output/implementation-artifacts/stories/5-2-freeze-risky-work-through-intervention-hold-and-lease-suspension.md]

### Previous Story Intelligence

- Story 5.2 already freezes risky work into `task.state == intervention_hold` plus `lease.state == suspended` and makes the next operator action explicit as reroute or recovery before resume. Story 5.3 should consume that state directly rather than inventing another precursor hold model.  
  [Source: _bmad-output/implementation-artifacts/stories/5-2-freeze-risky-work-through-intervention-hold-and-lease-suspension.md#completion-notes-list] [Source: tools/orchestration/interventions.py]
- Story 4.4 already established controller-owned pause or resume, runtime-support warnings, and stable human-readable or `--json` action output. Extend those same action-response patterns for reroute and recovery instead of creating special-case envelopes.  
  [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md] [Source: tools/orchestration/cli/main.py]
- Story 4.2 already owns the current assignment pipeline, including routing decision persistence, lock reservation, adapter dispatch, acknowledgment, activation, and rollback on dispatch failure. Story 5.3 should refactor or reuse that path rather than duplicating a second dispatch pipeline inside reroute.  
  [Source: _bmad-output/implementation-artifacts/stories/4-2-assign-and-manage-task-lifecycle-actions-from-one-command-path.md] [Source: tools/orchestration/tasks.py]
- Startup recovery already writes `recovery_runs`, `assignments_blocked`, suspended leases, and `reconciliation` task state. Story 5.3 should reuse those storage and inspect patterns for operator-confirmed recovery instead of inventing a parallel recovery journal.  
  [Source: tools/orchestration/recovery.py] [Source: tools/orchestration/tests/test_setup_init.py]

### Brownfield Baseline

- `tools/orchestration/tasks.py` already contains the key lifecycle seams: assign, pause, resume, freeze-for-risk, current inspect context, and guarded error behavior. `task reroute` exists at the CLI contract level but is still an unsupported stub in `cli/main.py`.  
  [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/cli/main.py]
- `tools/orchestration/recovery.py` already persists startup recovery summaries into `recovery_runs`. That table is the correct first persistence seam for 5.3 recovery summaries and operator-visible recovery state.  
  [Source: tools/orchestration/recovery.py] [Source: tools/orchestration/store.py]
- `tools/orchestration/history.py` already exposes lease replacement linkage through `replacement_lease_id`, and the lease state machine already supports `revoked -> replaced`. Story 5.3 should use those existing nouns instead of inventing a second successor-history model.  
  [Source: tools/orchestration/history.py] [Source: tools/orchestration/state_machine.py]
- `tools/orchestration/locks.py` currently records reserve, activate, and release events tied to a lease. Any safe reroute will need to preserve predecessor lock history and make successor lock movement explicit rather than mutating lock rows in place.  
  [Source: tools/orchestration/locks.py]
- `tools/orchestration/tests/test_task_lifecycle_cli.py` currently expects `task reroute` to return a structured unsupported error. Those regressions are the right narrow red entry point for converting the stub into the real controller-owned action.  
  [Source: tools/orchestration/tests/test_task_lifecycle_cli.py]

### Technical Requirements

- Preserve canonical state semantics exactly:
  - frozen degraded work may remain `intervention_hold` plus `suspended`
  - ambiguous ownership and explicit recovery work use `reconciliation`
  - predecessor leases move through `revoked` and optionally `replaced` when a successor supersedes them
  - no task may have more than one live lease at any point  
  [Source: _bmad-output/planning-artifacts/architecture.md#task-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine]
- Treat `macs task reroute` as operator-confirmed. The command is allowed to change ownership because the operator invoked it, but the controller must still fail closed if prerequisites are not satisfied.  
  [Source: _bmad-output/planning-artifacts/architecture.md#decision-rights-model] [Source: _bmad-output/planning-artifacts/prd.md#security--governance]
- Resolve predecessor ownership explicitly before successor activation. Do not create a successor live lease and then clean up the predecessor afterward.  
  [Source: _bmad-output/planning-artifacts/epics.md#story-53-reconcile-ambiguous-ownership-and-reroute-safely] [Source: _bmad-output/planning-artifacts/architecture.md#failure-containment-model]
- Preserve auditability and inspectability. Recovery decisions, replacement linkage, and lock movement must be visible through the existing controller surfaces rather than only in raw event payloads or tmux panes.  
  [Source: _bmad-output/planning-artifacts/prd.md#journey-3-maintainer-investigates-a-conflict-and-reconstructs-the-failure] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#post-recovery-ux]
- Stay within Python 3.8+ stdlib, SQLite, and the current shell-first repo shape. Do not add third-party dependencies, background daemons, or an alternate recovery store.  
  [Source: _bmad-output/project-context.md#technology-stack--versions] [Source: _bmad-output/project-context.md#critical-dont-miss-rules]

### Architecture Compliance

- Controller authority first: only controller Python code mutates tasks, leases, locks, recovery runs, and event history. Adapters can acknowledge side effects but cannot declare ownership resolution.  
  [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules]
- Reuse the existing write-model approach: validate controller truth first, write transactional state changes plus durable events, then perform dispatch or acknowledgment side effects and recover explicitly on failure.  
  [Source: _bmad-output/planning-artifacts/architecture.md#write-model] [Source: tools/orchestration/tasks.py]
- Preserve the zero-or-one live-lease invariant across the full reroute path, including during any intermediate reserved, revoked, or replaced transitions.  
  [Source: _bmad-output/planning-artifacts/architecture.md#lease] [Source: tools/orchestration/invariants.py]
- Preserve recovery boundaries: Story 5.3 owns explicit revocation, successor activation, and operator-visible recovery inspection; Story 5.4 owns resumable continuation of interrupted recovery runs across restart. Do not broaden 5.3 into full restart-resume orchestration.  
  [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-5-recovery-engine-before-controller-surface-expansion] [Source: _bmad-output/planning-artifacts/architecture.md#failure-containment-model]
- Keep lock and event history durable. Replacement should be inspectable as history, not as destructive mutation that erases what the predecessor held.  
  [Source: _bmad-output/planning-artifacts/prd.md#observability--auditability] [Source: tools/orchestration/history.py] [Source: tools/orchestration/locks.py]

### File Structure Requirements

- Extend `tools/orchestration/tasks.py` for controller-owned reroute orchestration, predecessor-resolution guards, and any narrow assignment-helper extraction needed to reuse current dispatch logic.
- Extend `tools/orchestration/recovery.py` for recovery-run creation, update, and inspection helpers that build task-scoped recovery summaries from authoritative state.
- Extend `tools/orchestration/cli/main.py` for the real `task reroute` action and the new `recovery inspect` command family surface.
- Extend `tools/orchestration/history.py`, `tools/orchestration/overview.py`, and `tools/orchestration/interventions.py` only as needed to surface replacement linkage, blocking condition, and next actions consistently.
- Reuse `tools/orchestration/locks.py`, `tools/orchestration/invariants.py`, and `tools/orchestration/state_machine.py` instead of writing ad hoc SQL transitions in the CLI layer.
- Prefer extending existing regression modules first: `tools/orchestration/tests/test_task_lifecycle_cli.py`, `tools/orchestration/tests/test_inspect_context_cli.py`, and `tools/orchestration/tests/test_setup_init.py` are the preferred initial targets. A focused new recovery CLI test module is acceptable only if those files become materially harder to maintain.

[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]  
[Source: _bmad-output/project-context.md#development-workflow-rules]

### Testing Requirements

- Use `python3 -m unittest discover -s tools/orchestration/tests` as the primary validation surface.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Add black-box CLI coverage proving `macs task reroute` only works from the permitted held or reconciliation states, revokes the predecessor before successor activation, and returns structured controller-owned failures for illegal or incomplete recovery conditions.  
  [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#status-conventions]
- Add inspection coverage proving `macs recovery inspect`, `task inspect`, `lease inspect`, `lease history`, and `overview show` expose anomaly summary, predecessor and successor linkage, blocking condition, and next action in both human-readable and `--json` modes.  
  [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content]
- Preserve Story 5.2 and Story 4.4 regressions. Reroute must not silently reactivate suspended or paused leases through the resume path, and startup recovery must remain assignment-blocking until explicit recovery action resolves it.  
  [Source: _bmad-output/implementation-artifacts/stories/5-2-freeze-risky-work-through-intervention-hold-and-lease-suspension.md] [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md] [Source: tools/orchestration/tests/test_setup_init.py]
- Assert replacement linkage and lock continuity explicitly: predecessor lease history should show `replacement_lease_id`, and lock history should show predecessor release or successor activation events instead of disappearing rows.  
  [Source: tools/orchestration/history.py] [Source: tools/orchestration/locks.py]

### Git Intelligence Summary

Recent committed work is concentrated in the exact seams Story 5.3 should extend:

- `c3ccc6a` concentrated recent lifecycle and recovery work in `tools/orchestration/tasks.py`, tests, and BMAD story bookkeeping.
- `51d2554` captured the initial recovery or rework slice and shows the current brownfield direction: extend the controller modules instead of adding a new subsystem.
- `e474089` established the bootstrap, persistent store, and controller-lock foundations that recovery logic still depends on.
- The repo’s active recovery momentum is already in `tasks.py`, `recovery.py`, `cli/main.py`, `overview.py`, and the existing orchestration unittest modules. Keep Story 5.3 centered there.

[Source: git log --oneline -5]

### Implementation Guardrails

- Do not create any path where a successor lease becomes live before the predecessor live lease is revoked or otherwise no longer live.
- Do not silently convert `intervention_hold` back to `active` as part of reroute. Ownership-changing recovery belongs in explicit reroute or reconciliation code paths, not in `task resume`.
- Do not erase predecessor history by updating old lease or lock rows in place to look like the successor owned them all along.
- Do not let adapters or tmux observations override controller truth during ambiguous ownership recovery.
- Do not broaden Story 5.3 into full restart-resume automation for interrupted recovery runs; that belongs to Story 5.4.
- Do not add third-party Python dependencies, background monitors, or a TUI to deliver this increment.

### Project Structure Notes

- This repo remains a brownfield, shell-first orchestration control plane. `tools/orchestration/` owns controller truth; tmux remains the execution substrate and compatibility layer.
- Story 5.3 should read as the direct follow-on to Story 5.2’s freeze semantics and Story 4.2’s assignment pipeline: explicit revocation first, then reuse the proven dispatch and activation path.
- The safest implementation path is incremental: convert the existing `task reroute` stub into a real controller-owned action, add the minimum `recovery inspect` surface needed to make that action legible, and prove the invariants with targeted regression tests before broader recovery workflow expansion.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/planning-artifacts/sprint-plan-2026-04-09.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/4-2-assign-and-manage-task-lifecycle-actions-from-one-command-path.md`
- `_bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md`
- `_bmad-output/implementation-artifacts/stories/5-2-freeze-risky-work-through-intervention-hold-and-lease-suspension.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/recovery.py`
- `tools/orchestration/history.py`
- `tools/orchestration/overview.py`
- `tools/orchestration/interventions.py`
- `tools/orchestration/invariants.py`
- `tools/orchestration/state_machine.py`
- `tools/orchestration/locks.py`
- `tools/orchestration/store.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_setup_init.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Convert the `task reroute` CLI stub into a controller-owned recovery action by extracting or reusing the current assignment pipeline after explicit predecessor lease revocation.
- Add task-scoped recovery-run helpers and a minimal `recovery inspect` surface so blocked work, proposed successor state, and replacement linkage are legible before and after reroute.
- Prove the flow in narrow red-green slices across lifecycle actions, inspect surfaces, and startup-recovery regressions, then run full validation and explicit BMAD QA acceptance before marking the story done.

### Story Creation Notes

- Skill used: `bmad-create-story`
- Target story auto-discovered from `sprint-status.yaml` after Story 5.2 was marked `done`.
- Inputs reviewed for this story: Epic 5 story definition, PRD degraded-session and failure-analysis journeys, architecture lease and recovery rules, CLI contract recovery surfaces, UX reconciliation flow, project context, Story 5.2 and Story 4.2 implementation notes, startup recovery code, and the current brownfield seams in `tasks.py`, `recovery.py`, `history.py`, `overview.py`, and the orchestration CLI tests.
- Validation pass applied against the BMAD create-story checklist before handoff: the story now includes previous-story intelligence, brownfield-safe reuse guidance, explicit anti-scope guardrails, and concrete regression targets for the existing unsupported `task reroute` stub and the missing recovery inspect surface.

### Debug Log References

- `2026-04-10T13:52:30+01:00` Story 5.3 created as the next ready-for-dev BMAD story after Story 5.2 completion.
- `2026-04-10T13:52:30+01:00` Story 5.3 moved to `in-progress`; implementation started in narrow red-green slices for recovery-run helpers, explicit predecessor revocation, safe reroute, and recovery inspect surfaces.
- `2026-04-10T14:02:00+01:00` First red-green slice landed: `task reroute` now revokes the predecessor lease, releases predecessor locks, reuses the assignment pipeline for the successor, records replacement linkage, and supports explicit reroute even while startup `assignments_blocked` remains set.
- `2026-04-10T14:09:00+01:00` Second red-green slice landed: `recovery inspect` now surfaces task-scoped recovery summaries in JSON and human-readable output, and task plus overview read surfaces expose recovery-run status consistently.
- `2026-04-10T14:14:00+01:00` Explicit BMAD QA acceptance pass found one remaining read-side gap: human-readable task and overview output did not surface recovery-run status. The gap was fixed and regression-covered before final validation.
- `2026-04-10T14:17:29+01:00` Final validation completed with `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` and `python3 -m unittest discover -s tools/orchestration/tests` (89 tests, passing). No repo-configured Python lint or static-analysis config was present.

### Completion Notes List

- Added controller-owned recovery-run helpers in `tools/orchestration/recovery.py` and task-level persistence hooks so held or reconciliation work records anomaly basis, allowed next actions, and proposed successor context in the existing `recovery_runs` table.
- Implemented `macs task reroute` as an operator-confirmed recovery action that revokes the predecessor lease before any successor becomes current, preserves lock history through explicit release and reserve or activate events, and records replacement linkage plus `task.rerouted`.
- Added the `recovery` CLI family with `recovery inspect`, exposing anomaly summary, frozen objects, proposed state, blocking condition, and allowed next actions in human-readable and `--json` forms.
- Extended task and overview read surfaces to show recovery-run status alongside the existing held-task and suspended-lease intervention context.
- Tightened the `task reroute` command contract so one of `--worker` or `--workflow-class` is required, and added regression coverage for legal reroute, illegal reroute, blocked-startup explicit reroute, persisted recovery runs, and read-side recovery visibility.
- Explicit BMAD QA acceptance finished with no remaining findings after the final human-readable recovery-run visibility fix. An unrelated full-suite regression in Codex model parsing was also corrected in `tools/orchestration/adapters/codex.py` before final validation.

### File List

- `_bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `tools/orchestration/adapters/codex.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/overview.py`
- `tools/orchestration/recovery.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`

### Change Log

- `2026-04-10`: Implemented safe ambiguous-ownership reroute, task-scoped recovery summaries, `recovery inspect`, recovery-run visibility on task and overview surfaces, startup-recovery reroute coverage, and a full BMAD QA acceptance pass with no remaining findings.
