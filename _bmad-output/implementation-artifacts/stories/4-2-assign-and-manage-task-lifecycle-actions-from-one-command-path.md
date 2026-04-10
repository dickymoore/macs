# Story 4.2: Assign and manage task lifecycle actions from one command path

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want to create, assign, reassign, close, and archive tasks through MACS-native commands,
so that normal orchestration never depends on manual tmux surgery.

## Acceptance Criteria

1. The `macs task` family becomes the single controller-first lifecycle surface for normal task actions. `create`, `assign`, `close`, and `archive` work through canonical `macs task <verb>` commands, and the frozen-but-deferred verbs `pause`, `resume`, `reroute`, and `abort` resolve through the same family with explicit contract-stable unsupported or precondition responses rather than missing-command failures or raw tmux fallbacks.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-42-assign-and-manage-task-lifecycle-actions-from-one-command-path] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-6-controller-first-operator-surface-on-the-frozen-cli-contract]
2. Each supported lifecycle action validates authoritative `task`, `lease`, `lock`, and recovery-block metadata before mutating state. `task close` maps to canonical `task.state = completed`, `task archive` maps to `task.state = archived`, and no command may create dual current owners, terminal tasks with live leases, or lingering held locks after closure.  
   [Source: _bmad-output/planning-artifacts/architecture.md#task-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#canonical-state-vocabularies] [Source: tools/orchestration/invariants.py]
3. Assignment becomes a real controller-mediated action rather than a SQLite-only reservation: worker selection, adapter dispatch, delivery acknowledgment or explicit side-effect failure handling, lease and lock transitions, routing rationale, and audit events all occur through one inspected MACS path, and resulting owner, lease, lock, and event changes are immediately visible through the already-landed Story 4.1 inspection surfaces.  
   [Source: _bmad-output/planning-artifacts/architecture.md#write-model] [Source: _bmad-output/planning-artifacts/architecture.md#runtime-adapter-architecture] [Source: _bmad-output/planning-artifacts/epics.md#story-42-assign-and-manage-task-lifecycle-actions-from-one-command-path] [Source: _bmad-output/implementation-artifacts/stories/4-1-provide-compact-list-and-inspect-commands-for-control-plane-objects.md]
4. Human-readable and `--json` responses for `macs task` actions follow the frozen Phase 1 contract: canonical nouns, dense result summaries, event IDs, controller-state-changed reporting, recommended next actions when relevant, stable error codes and exit codes, and JSON envelopes with `ok`, `command`, `timestamp`, `warnings`, `errors`, and action payloads under `data.result` and `data.event`.  
   [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#structured-error-codes] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#exit-codes]
5. Regression coverage and operator documentation ship with the change, proving happy-path create, assign, close, and archive flows, fail-closed behavior on invalid state or side-effect failure, explicit unsupported or precondition handling for deferred verbs, and no regression to task, lease, lock, and event inspection.  
   [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/planning-artifacts/prd.md#non-functional-requirements]

## Tasks / Subtasks

- [x] Canonicalize the `macs task` CLI surface and contract handling. (AC: 1, 4)
  - [x] Extend `tools/orchestration/cli/main.py` so the task family exposes `create`, `assign`, `inspect`, `list`, `close`, and `archive` as real handlers, and add explicit guarded handlers for `pause`, `resume`, `reroute`, and `abort` so the family shape matches the frozen contract even where later stories still own the semantics.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#dependency-notes]
  - [x] Bring `task create` in line with the contract's `--summary` minimum. Keep `--workflow-class`, `--require-capability`, and `--surface` available as optional metadata, and use one documented brownfield-safe default when `--workflow-class` is omitted. Recommended default in this repo: `implementation`, because the shipped policy and repo defaults already prioritize that path.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#minimum-required-flags] [Source: _bmad-output/planning-artifacts/architecture.md#repository-default-decisions] [Source: tools/orchestration/policy.py]
  - [x] Make the canonical `task assign` surface accept exactly one selector of `--worker` or `--workflow-class`. If a no-selector fallback is retained for current brownfield compatibility with stored task metadata, keep it explicitly documented as compatibility-only rather than the primary docs surface.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#minimum-required-flags] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#open-but-frozen-by-assumption] [Source: tools/orchestration/tasks.py]
  - [x] Add a task-family action response helper so human-readable output, JSON envelopes, structured error codes, and exit-code mapping stop drifting from the contract. Keep any shared extraction narrow; do not refactor unrelated command families just for symmetry.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: tools/orchestration/cli/main.py]

- [x] Extend controller-owned task lifecycle helpers for close and archive, and fence deferred verbs safely. (AC: 1, 2, 4)
  - [x] Expand `tools/orchestration/tasks.py` and `tools/orchestration/invariants.py` with controller-owned helpers for close and archive so lifecycle writes reuse canonical state transitions instead of open-coding SQL inside CLI handlers.  
        [Source: _bmad-output/planning-artifacts/architecture.md#controller-core] [Source: _bmad-output/planning-artifacts/architecture.md#task-state-machine] [Source: tools/orchestration/invariants.py]
  - [x] Map the human verb `close` to canonical task state `completed`; do not introduce a new `closed` state. Ending a task must also terminate or complete the current lease, clear current ownership pointers, and release associated locks while preserving history.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#canonical-state-vocabularies] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: tools/orchestration/state_machine.py]
  - [x] Allow `archive` only from terminal task states already frozen by the state machine (`completed`, `failed`, or `aborted`) and preserve lease, lock, and event history for post-run inspection.  
        [Source: _bmad-output/planning-artifacts/architecture.md#task-state-machine] [Source: _bmad-output/planning-artifacts/prd.md#auditability-governance-and-operator-trust] [Source: tools/orchestration/history.py]
  - [x] For `pause`, `resume`, `reroute`, and `abort`, return explicit `unsupported` or `degraded_precondition` responses until the underlying intervention and recovery stories land. Do not fake state mutation or imply that raw tmux remains the normal fallback path.  
        [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-5-recovery-engine-before-controller-surface-expansion] [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-6-controller-first-operator-surface-on-the-frozen-cli-contract] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#structured-error-codes]

- [x] Turn assignment into a real controller-mediated side-effect path. (AC: 2, 3, 4)
  - [x] After routing and lock validation, resolve the selected worker's adapter and dispatch the assignment payload through the adapter contract, then record delivery acknowledgment or explicit failure evidence. Story 4.2 should no longer stop at inserting a pending lease into SQLite.  
        [Source: _bmad-output/planning-artifacts/architecture.md#write-model] [Source: _bmad-output/planning-artifacts/architecture.md#adapter-contract] [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/adapters/base.py]
  - [x] On successful dispatch and acknowledgment, advance the authoritative records from `reserved + pending_accept` into the active runtime path: promote the lease to `active`, the task to `active`, and reserved locks to `active` or an equivalent controller-recognized active lock state.  
        [Source: _bmad-output/planning-artifacts/architecture.md#task-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#locking-and-protected-surface-model]
  - [x] On dispatch or acknowledgment failure, persist explicit safe-state follow-up events and evidence, end or revoke the pending lease, release reserved locks, and return the task to a state the operator can safely inspect and retry (`pending_assignment` when work never became active, `reconciliation` when ambiguity exists). Never leave misleading current ownership behind.  
        [Source: _bmad-output/planning-artifacts/architecture.md#write-model] [Source: _bmad-output/planning-artifacts/architecture.md#restart-recovery-and-reconciliation] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#structured-error-codes]
  - [x] Preserve the existing safety prerequisites from Stories 3.2, 3.3, 3.4, 5.1, and 6.1: routing rationale persistence, lock conflict checks, degraded-worker exclusion, startup recovery blocking, and durable audit history must all remain in force for the new action path.  
        [Source: _bmad-output/implementation-artifacts/stories/3-2-record-explainable-assignment-decisions.md] [Source: _bmad-output/implementation-artifacts/stories/3-3-reserve-protected-surfaces-with-coarse-default-locks.md] [Source: _bmad-output/implementation-artifacts/stories/3-4-block-conflicts-and-duplicate-ownership-claims.md] [Source: _bmad-output/implementation-artifacts/stories/5-1-classify-worker-health-and-surface-warnings-promptly.md] [Source: _bmad-output/implementation-artifacts/stories/6-1-persist-a-durable-event-trail-and-history-inspectors.md]

- [x] Preserve immediate inspectability and keep the change brownfield-safe. (AC: 3, 4, 5)
  - [x] Reuse the Story 4.1 read-side surfaces in `tools/orchestration/history.py`, `tools/orchestration/overview.py`, and existing task inspection rather than building a second inspection layer for action results.  
        [Source: _bmad-output/implementation-artifacts/stories/4-1-provide-compact-list-and-inspect-commands-for-control-plane-objects.md] [Source: tools/orchestration/history.py] [Source: tools/orchestration/overview.py]
  - [x] Ensure action outputs point the operator back to stable inspectors: resulting task IDs, lease IDs, lock IDs, and event IDs must all be directly inspectable through the already-landed commands.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content]
  - [x] Keep the implementation under `tools/orchestration/` and tmux-backed adapters. If formatting code becomes too repetitive, add a small helper such as `tools/orchestration/cli/formatters.py`; otherwise prefer incremental change to `cli/main.py` over a broad CLI reorganization.  
        [Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape] [Source: _bmad-output/project-context.md#development-workflow-rules]
  - [x] Update `README.md` and `docs/getting-started.md` with contract-canonical task action examples, output expectations, and any compatibility fallback notes that remain temporarily supported.  
        [Source: _bmad-output/project-context.md#code-quality--style-rules] [Source: _bmad-output/planning-artifacts/prd.md#maintainability--testability]

- [x] Add regression coverage for lifecycle actions, contract outputs, and fail-closed behavior. (AC: 5)
  - [x] Prefer a focused new test module such as `tools/orchestration/tests/test_task_lifecycle_cli.py` for this story. If shared fixtures from `test_setup_init.py` are needed, extract them first rather than growing the existing file indefinitely.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: _bmad-output/project-context.md#testing-rules]
  - [x] Cover happy paths: create with contract-minimum inputs, assign by explicit worker and workflow-class routing, successful dispatch-to-active transition, close releasing current ownership and locks, and archive preserving durable history.  
        [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#critical-success-moments]
  - [x] Cover failure paths: assignment blocked by startup recovery, stale or degraded worker rejection, lock collision, dispatch or acknowledgment failure, close from an illegal state, archive from a non-terminal state, and deferred verbs returning explicit structured errors instead of traceback or missing-command output.  
        [Source: _bmad-output/planning-artifacts/architecture.md#failure-containment-model] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#structured-error-codes] [Source: tools/orchestration/recovery.py] [Source: tools/orchestration/health.py]
  - [x] Assert contract output shape for `--json` and human-readable task actions, including timestamps, warnings, errors, `data.result`, `data.event`, and the post-action inspectability of task, lease, lock, and event records.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output]

## Dev Notes

### Story Intent

Story 4.2 is the write-side complement to Story 4.1. It should let the operator stay in the controller surface for task lifecycle work, but it must do so by extending the current authoritative store, routing, locks, history, and adapter seams rather than inventing a second orchestration path.  
[Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-6-controller-first-operator-surface-on-the-frozen-cli-contract] [Source: _bmad-output/implementation-artifacts/stories/4-1-provide-compact-list-and-inspect-commands-for-control-plane-objects.md]

### Previous Story Intelligence

- Story 4.1 already landed controller-first list and inspect commands for tasks, locks, leases, events, and overview summaries in `tools/orchestration/cli/main.py`.
- Story 4.1 also added authoritative read helpers in `tools/orchestration/history.py` and `tools/orchestration/overview.py` so common orchestration questions resolve from SQLite state rather than raw pane output.
- Existing regression coverage already walks from assignment into lease and event inspection. Story 4.2 should extend that read-side path after new write actions rather than introducing a separate inspection model.

[Source: _bmad-output/implementation-artifacts/stories/4-1-provide-compact-list-and-inspect-commands-for-control-plane-objects.md#completion-notes-list]

### Brownfield Baseline

- Current `tools/orchestration/cli/main.py` exposes only `task list`, `task create`, `task assign`, and `task inspect`. The contract-frozen write verbs `close`, `archive`, `pause`, `resume`, `reroute`, and `abort` are not yet present.  
  [Source: tools/orchestration/cli/main.py]
- `task create` currently requires `--workflow-class`, which drifts from the frozen contract's `--summary` minimum. `task assign` currently accepts only `--worker`, while existing brownfield behavior also relies on stored task workflow class when no selector is passed.  
  [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#minimum-required-flags]
- `assign_task()` currently persists routing rationale, a `task.assigned` event, a `pending_accept` lease, and reserved locks, but it never dispatches to the selected adapter or promotes the task into `active`. That gap must be closed here or task lifecycle remains controller-written but runtime-inert.  
  [Source: tools/orchestration/tasks.py]
- Current invariant helpers already encode canonical task and lease states, and current lock helpers already detect conflicts and reserve locks. Story 4.2 should extend those seams instead of bypassing them with raw SQL from the CLI layer.  
  [Source: tools/orchestration/invariants.py] [Source: tools/orchestration/state_machine.py] [Source: tools/orchestration/locks.py]
- Worker health classification, routing policy evaluation, recovery blocking, and routing-decision persistence already exist and should remain the authoritative prerequisites for assignment.  
  [Source: tools/orchestration/health.py] [Source: tools/orchestration/routing.py] [Source: tools/orchestration/recovery.py] [Source: tools/orchestration/policy.py]
- The generic JSON error path in `emit_result()` is still setup-specific and does not emit the frozen task-action envelope. Story 4.2 should fix task-family action responses without turning into a whole-CLI rewrite.  
  [Source: tools/orchestration/cli/main.py]

### Technical Requirements

- Use the singular task family name `macs task`; do not introduce plural aliases as the documented primary path.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#contract-decisions]
- Keep `task create` contract-canonical with `--summary` as the minimum required input. If `--workflow-class` is omitted, use one documented brownfield-safe default. Recommended default in this repo: `implementation`, because the shipped policy and repo defaults already privilege that path.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#minimum-required-flags] [Source: _bmad-output/planning-artifacts/architecture.md#repository-default-decisions] [Source: tools/orchestration/policy.py]
- Keep `task assign` contract-canonical with exactly one selector of `--worker` or `--workflow-class`. If a no-selector fallback is retained for compatibility with existing stored task metadata or tests, treat it as a temporary compatibility alias, not the canonical docs surface.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#minimum-required-flags] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#open-but-frozen-by-assumption]
- Map human verbs onto canonical state vocabularies exactly:
  - `task close` -> `task.state = completed`
  - `task archive` -> `task.state = archived`
  - Do not create a new `closed` task state.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#canonical-state-vocabularies] [Source: _bmad-output/planning-artifacts/architecture.md#task-state-machine]
- Keep JSON keys snake_case and use canonical nouns `worker`, `task`, `lease`, `lock`, `event`, and `adapter` in both JSON and human-readable output.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output]
- Keep the implementation in Python 3.8+ stdlib plus SQLite. Do not add third-party Python dependencies, ORMs, or alternative stores for this increment.  
  [Source: _bmad-output/project-context.md#technology-stack--versions]

### Architecture Compliance

- Controller authority first: only controller code mutates task, lease, and lock state. Adapters dispatch, probe, capture, and acknowledge; they do not become the source of truth.  
  [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules]
- Follow the architecture write model exactly: read current state, validate policy and invariants, write intent plus events transactionally, trigger the adapter side effect, persist follow-up evidence and outcomes, and if the side effect fails move the task into an explicit safe state instead of pretending success.  
  [Source: _bmad-output/planning-artifacts/architecture.md#write-model]
- Preserve zero-or-one live lease semantics. Assignment, closure, and archival must not manufacture dual current owners, and successor or reroute semantics must remain blocked until they can satisfy the existing invariant rules.  
  [Source: _bmad-output/planning-artifacts/architecture.md#authoritative-domain-model] [Source: tools/orchestration/invariants.py]
- Preserve coarse lock semantics from Story 3.3 and Story 3.4. Assignment may reserve then activate locks, and closure or archival must release them while keeping the durable history inspectable.  
  [Source: _bmad-output/planning-artifacts/architecture.md#locking-and-protected-surface-model] [Source: _bmad-output/implementation-artifacts/stories/3-3-reserve-protected-surfaces-with-coarse-default-locks.md] [Source: _bmad-output/implementation-artifacts/stories/3-4-block-conflicts-and-duplicate-ownership-claims.md]
- Reuse existing health and recovery safety rails. Task actions must still respect `assignments_blocked` recovery metadata and degraded-worker routing exclusions.  
  [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/recovery.py] [Source: tools/orchestration/health.py]
- Keep event history durable in SQLite plus NDJSON export. Action flows should enrich the audit trail and remain inspectable through Story 4.1 and Story 6.1 surfaces.  
  [Source: _bmad-output/planning-artifacts/architecture.md#persistence-and-audit-architecture] [Source: _bmad-output/implementation-artifacts/stories/6-1-persist-a-durable-event-trail-and-history-inspectors.md]

### File Structure Requirements

- Extend `tools/orchestration/cli/main.py` for task-family verbs, canonical flag parsing, action result output, structured errors, and exit-code mapping.
- Extend `tools/orchestration/tasks.py` for create, assign, close, and archive orchestration logic, compatibility selector handling, and adapter side-effect sequencing.
- Extend `tools/orchestration/locks.py` for lock activation and release helpers tied to lifecycle progression and closure.
- Extend `tools/orchestration/invariants.py` and reuse `tools/orchestration/state_machine.py` for authoritative lifecycle transitions rather than writing direct lifecycle SQL in CLI handlers.
- Extend `tools/orchestration/history.py` only if task action responses need a shared helper for recent events or lock summaries.
- Touch `tools/orchestration/adapters/base.py` and concrete adapters only if assignment payload or delivery acknowledgment needs a shared contract refinement.
- Prefer a focused new test module under `tools/orchestration/tests/` for task lifecycle actions.
- Update `README.md` and `docs/getting-started.md` for operator-facing task command changes.
- Do not move authoritative lifecycle logic into `tools/tmux_bridge/`.

[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]  
[Source: _bmad-output/project-context.md#critical-implementation-rules]

### Testing Requirements

- Use `python3 -m unittest discover -s tools/orchestration/tests` as the primary validation surface.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Add black-box CLI tests for `task create`, `task assign`, `task close`, and `task archive`, including `--json` envelopes, structured errors, and exit-code mapping.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#exit-codes]
- Use isolated tmux sockets or sessions only for dispatch and acknowledgment integration cases; keep close, archive, and invalid state cases SQLite-only where possible.  
  [Source: _bmad-output/planning-artifacts/architecture.md#integration-tests] [Source: _bmad-output/project-context.md#testing-rules]
- Assert immediate inspectability after actions: `task inspect`, `lease inspect` or `lease history`, `lock list`, `event list` or `event inspect`, and `overview show` should all reflect the resulting authoritative state.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/implementation-artifacts/stories/4-1-provide-compact-list-and-inspect-commands-for-control-plane-objects.md]
- Cover failure paths: assignment blocked by startup recovery, stale or degraded worker rejection, lock collision, adapter dispatch or acknowledgment failure, close on illegal state, archive from a non-terminal state, and deferred verbs returning explicit structured errors instead of tracebacks or missing-command output.  
  [Source: _bmad-output/planning-artifacts/architecture.md#failure-containment-model] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#structured-error-codes]
- Preserve existing Story 4.1, Story 5.1, and Story 6.1 inspection behavior while adding the new action path.  
  [Source: _bmad-output/implementation-artifacts/stories/4-1-provide-compact-list-and-inspect-commands-for-control-plane-objects.md] [Source: _bmad-output/implementation-artifacts/stories/5-1-classify-worker-health-and-surface-warnings-promptly.md] [Source: _bmad-output/implementation-artifacts/stories/6-1-persist-a-durable-event-trail-and-history-inspectors.md]

### Git Intelligence Summary

Recent committed work is already concentrated in the exact seams Story 4.2 should extend:

- `c3ccc6a` expanded `tools/orchestration/tasks.py`, `routing.py`, `health.py`, `recovery.py`, and `tools/orchestration/tests/test_setup_init.py`.
- `e474089` established bootstrap and controller-lock behavior that Story 4.2 should treat as fixed infrastructure rather than redesign.
- Recent history is compatibility-heavy, not framework-heavy. Keep this increment as a targeted extension of the existing orchestration modules and tmux-backed adapters.

[Source: git log --oneline -5]  
[Source: git show --stat -1 c3ccc6a]

### Implementation Guardrails

- Do not create new authoritative state names such as `closed`; the human verb `close` maps to `completed`.
- Do not let `macs task assign` remain a database-only reservation that never dispatches to a worker.
- Do not bypass `invariants.py`, `state_machine.py`, or current lock conflict helpers with ad hoc SQL in the CLI layer.
- Do not silently succeed on dispatch failure. If side effects fail, the controller must move to an explicit safe state and say so.
- Do not broaden this into a whole-repo CLI envelope refactor. Focus on the `task` family and the minimum shared helper extraction needed to keep it coherent.
- Do not implement full degraded-session pause, reroute, or recovery semantics here. Story 4.2 may expose contract-stable guarded responses, but the real degraded-path behavior belongs to Stories 4.4, 5.2, 5.3, and 6.2.
- Do not add third-party Python dependencies, ORMs, or non-SQLite storage layers.

### Project Structure Notes

- This repo is still brownfield and shell-first. The authoritative control-plane path lives under `tools/orchestration/`, while `tools/tmux_bridge/` remains the transport substrate.
- Story 4.2 should read as a natural extension of Stories 3.2, 3.3, 3.4, 4.1, 5.1, and 6.1: routing rationale, lock safety, worker health classification, list and inspect views, and durable history already exist and should be composed, not replaced.
- If task action formatting becomes too large for `cli/main.py`, extract a narrowly scoped helper such as `tools/orchestration/cli/formatters.py`; otherwise prefer incremental changes over a broad CLI reorganization.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/planning-artifacts/sprint-plan-2026-04-09.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/4-1-provide-compact-list-and-inspect-commands-for-control-plane-objects.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/invariants.py`
- `tools/orchestration/state_machine.py`
- `tools/orchestration/locks.py`
- `tools/orchestration/routing.py`
- `tools/orchestration/history.py`
- `tools/orchestration/overview.py`
- `tools/orchestration/health.py`
- `tools/orchestration/policy.py`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/recovery.py`
- `tools/orchestration/tests/test_setup_init.py`
- `README.md`
- `docs/getting-started.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Bring `macs task` up to the frozen family shape first, with contract-aligned parser changes and task-family response helpers.
- Drive the implementation red-first from black-box CLI tests, then extend controller lifecycle helpers for close, archive, and guarded deferred verbs.
- Turn assignment into a real adapter-mediated side-effect flow with safe-state fallback, then update docs and finish full regression validation.

### Debug Log References

- Skill used: `bmad-create-story`
- Inputs loaded from the requested planning artifacts, UX spec, sprint tracking file, Story 4.1 artifact, recent git history, and the current `tools/orchestration/` command and state modules
- `2026-04-10T08:19:47+01:00` Story implementation started under `bmad-dev-story`; status changed to `in-progress` and live BMAD execution tracking enabled.
- `2026-04-10T08:19:47+01:00` Red phase started for task-family contract drift; added black-box CLI tests for verb surface, `task create` defaulting/envelope, and `task assign --workflow-class`.
- `2026-04-10T08:26:49+01:00` Created `tools/orchestration/tests/test_task_lifecycle_cli.py` to pin the initial Story 4.2 black-box CLI contract slice before implementation changes.
- `2026-04-10T08:32:27+01:00` Greened the initial contract slice by wiring the task-family action envelope and exposing guarded lifecycle verbs in `tools/orchestration/cli/main.py`; targeted CLI contract tests now pass.
- `2026-04-10T08:25:37+01:00` First red-green slice completed: added `tools/orchestration/tests/test_task_lifecycle_cli.py`, captured the failing `task create --summary` contract test, and made `--workflow-class` optional with default `implementation`.
- `2026-04-10T08:30:47+01:00` Broadened the focused lifecycle CLI contract slice to the live workspace tests, then landed task help verb exposure plus a task-family action envelope for `task create` and `task assign`; `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli` is green.
- `2026-04-10T08:33:28+01:00` Added deferred-verb regression coverage and aligned guarded task verbs to return the contract `unsupported` error with Phase 1 exit code `5`.
- `2026-04-10T08:41:03+01:00` Landed controller-owned happy paths for assignment activation, close, and archive: assignment now dispatches to the selected tmux-backed adapter, records delivery acknowledgment, promotes lease/task/lock state to active, and `task close`/`task archive` now execute real lifecycle transitions.
- `2026-04-10T08:48:37+01:00` Added Story 4.2 failure-path and inspectability regressions for recovery-blocked assignment, stale/degraded worker rejection, lock conflict, side-effect rollback, illegal close/archive attempts, and post-action task/lease/lock/event/overview inspection; the focused lifecycle CLI module is green.
- `2026-04-10T08:51:06+01:00` Full orchestration regression suite passed via `python3 -m unittest discover -s tools/orchestration/tests`; README and getting-started docs were updated to match the landed task lifecycle semantics and error contract.
- `2026-04-10T08:53:17+01:00` Added the remaining explicit-worker and human-readable output regressions, reran the full orchestration unittest suite and tmux smoke check successfully, and completed Story 4.2 with all story checkboxes marked done.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Brownfield-specific guardrails capture the current contract drift in the task family: required-flag mismatches, setup-specific JSON error envelopes, and assignment that still stops at durable reservation instead of adapter dispatch.
- Story tasks explicitly reuse Story 4.1 inspect surfaces and the existing routing, lock, health, invariant, and audit seams while fencing degraded-path semantics for later stories.
- `task create` now accepts the contract-minimum `--summary` input and defaults omitted workflow class metadata to `implementation`.
- The focused lifecycle CLI contract module now verifies the full frozen task help surface plus Story 4.2 JSON action envelopes for `task create` and `task assign`, and the current implementation satisfies those assertions.
- Deferred task verbs now fail closed through the task-family envelope with explicit `unsupported` errors and contract exit code `5`.
- The focused lifecycle contract path now covers dispatch-to-active assignment, close-to-completed with lease and lock release, and archive-to-archived from a terminal state.
- The focused lifecycle CLI module now covers the required failure paths plus post-action inspectability through `task inspect`, `lease inspect/history`, `lock list`, `event inspect/list`, and `overview show`.
- Full orchestration regression coverage is green after updating the brownfield test suite to the Story 4.2 action envelope and active-assignment semantics.
- Operator docs now call out the active assignment path, close/archive lifecycle rules, and stable task-action exit-code meanings.
- Explicit-worker assignment and human-readable task-action outputs are now covered by Story 4.2 regressions alongside the JSON contract assertions.

### File List

- `_bmad-output/implementation-artifacts/stories/4-2-assign-and-manage-task-lifecycle-actions-from-one-command-path.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/invariants.py`
- `tools/orchestration/locks.py`
- `README.md`
- `docs/getting-started.md`

## Change Log

- `2026-04-10T08:19:47+01:00` Started implementation with strict BMAD dev-story workflow; story and sprint status moved to `in-progress`.
- `2026-04-10T08:19:47+01:00` Added first failing black-box CLI tests for the Story 4.2 contract slice.
- `2026-04-10T08:26:49+01:00` Added the first dedicated task lifecycle CLI contract test module covering task-family verbs, `task create` defaulting, and `task assign --workflow-class`.
- `2026-04-10T08:32:27+01:00` Implemented the first green slice for Story 4.2: task-family contract envelopes for create/assign and explicit guarded task verbs now satisfy the initial black-box CLI tests.
- `2026-04-10T08:25:37+01:00` Completed the first red-green slice by landing contract-minimum `task create` support with default workflow class `implementation`.
- `2026-04-10T08:30:47+01:00` Extended the focused lifecycle CLI contract slice to cover task help verb exposure plus Story 4.2 JSON action envelopes for `task create` and `task assign`, and made that module green.
- `2026-04-10T08:33:28+01:00` Added deferred-verb contract tests and corrected guarded task verbs to return Phase 1 exit code `5` for structured `unsupported` responses.
- `2026-04-10T08:41:03+01:00` Implemented assignment promotion to active with adapter dispatch and lock activation, plus real `task close` and `task archive` lifecycle handlers, and made the focused lifecycle CLI contract module green again.
- `2026-04-10T08:48:37+01:00` Added the remaining Story 4.2 failure-path and inspectability regressions to the focused lifecycle CLI module and made that module green again.
- `2026-04-10T08:51:06+01:00` Updated the brownfield orchestration regression suite to the Story 4.2 contract, passed `python3 -m unittest discover -s tools/orchestration/tests`, refreshed operator docs, and moved the story to `review`.
- `2026-04-10T08:53:17+01:00` Added explicit-worker and human-readable output regressions, reran full orchestration validation plus tmux smoke, and marked Story 4.2 done.
