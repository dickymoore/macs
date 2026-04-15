# Story 2.2: Enforce the diff/review gate before closeout or safety relaxation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,  
I want MACS to block risky closeout paths until a valid checkpoint exists,  
so that `POL-3` is enforced instead of documented only.

## Acceptance Criteria

1. Given a `macs task close` or `macs task archive` request, when no current diff/review checkpoint exists for that task and requested target action, then MACS refuses the action with a clear explanation of the missing checkpoint requirement and directs the operator to the checkpoint flow instead of mutating controller state.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-22-enforce-the-diffreview-gate-before-closeout-or-safety-relaxation] [Source: _bmad-output/planning-artifacts/prd.md#compliance--regulatory] [Source: _bmad-output/planning-artifacts/architecture.md#product-safety-policies]
2. Given an existing diff/review checkpoint, when the stored checkpoint no longer matches the requested action, current repo state, or live task scope, then MACS treats that checkpoint as stale or invalid and keeps the action blocked until a fresh checkpoint and attributable approval event are recorded.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-22-enforce-the-diffreview-gate-before-closeout-or-safety-relaxation] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements] [Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md#next-epic-preparation]
3. Given a valid checkpoint for `task.close` or `task.archive`, when the operator invokes that action, then MACS records one attributable operator approval or decision event linked to the checkpoint and only then performs the lifecycle mutation, preserving controller-owned causation and traceability through the resulting task event.  
   [Source: _bmad-output/planning-artifacts/prd.md#compliance--regulatory] [Source: _bmad-output/planning-artifacts/architecture.md#event-record-schema] [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records] [Source: _bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md#tasks--subtasks]
4. Given a blocked or successful gated closeout action, when the operator inspects CLI output in human-readable or `--json` mode, then the response stays within the current MACS task action contract while surfacing the gate outcome, checkpoint or decision references, and the next remediation action without inventing a new review surface.  
   [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-payload-patterns] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#human-readable-status-conventions] [Source: _bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md#architecture-compliance]
5. Regression coverage proves fail-closed enforcement for missing checkpoints, stale repo-state mismatches, and target-action mismatches, while preserving current lease completion, lock release, archive semantics, checkpoint capture, and inspect traceability behavior when a valid checkpoint exists.  
   [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md#testing-requirements] [Source: _bmad-output/implementation-artifacts/stories/6-3-enforce-explicit-decision-rights-and-guarded-actions.md#testing-requirements]
6. Story 2.2 stays within governance-hardening gate enforcement: it hardens the current close/archive paths and reusable validation or approval seams only, without broadening into Story 2.3 release-evidence aggregation, hosted review systems, or changes to any non-governance-hardening tracker.  
   [Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md#next-epic-preparation] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#additional-requirements] [Inference from: user request to keep scope limited to this lane]

## Tasks / Subtasks

- [x] Add one controller-owned checkpoint validation path that can answer "is this action currently gate-satisfied?" before state mutation. (AC: 1, 2, 3)
  - [x] Extend `tools/orchestration/checkpoints.py` and, if that proves cleaner, `tools/orchestration/history.py` with a narrow helper that selects the latest checkpoint for a given `task_id` plus `target_action`, re-computes the current repo fingerprint from git, and returns a structured validation result instead of relying on raw artifact files alone.  
        [Source: tools/orchestration/checkpoints.py] [Source: tools/orchestration/history.py] [Source: _bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md#suggested-implementation-shape]
  - [x] Treat a checkpoint as invalid when its `target_action` does not match the requested action, its baseline repo fingerprint no longer matches current HEAD or dirty-state evidence, or its captured task scope no longer matches the live task or lease context. Do not let a `task.close` checkpoint satisfy `task.archive`, or vice versa.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-22-enforce-the-diffreview-gate-before-closeout-or-safety-relaxation] [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/checkpoints.py]
  - [x] Return explicit remediation metadata for missing or stale checkpoints, including the canonical follow-up command `macs task checkpoint --task <task-id> --target-action <task.close|task.archive>`, so blocked actions can fail through contract-shaped controller errors instead of ad hoc strings.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#structured-error-codes] [Source: tools/orchestration/cli/main.py]

- [x] Enforce `POL-3` inside the existing close/archive task flows without auto-capturing a checkpoint. (AC: 1, 2, 3, 4)
  - [x] Gate `close_task(...)` and `archive_task(...)` in `tools/orchestration/tasks.py` before any lease, lock, or task-state mutation, and block the action with no controller-state change when no valid checkpoint is present.  
        [Source: tools/orchestration/tasks.py] [Source: _bmad-output/planning-artifacts/prd.md#compliance--regulatory]
  - [x] Reuse or generalize the current operator-decision event seam so gated close/archive success records one attributable approval event linked to the selected checkpoint, updates `review_checkpoints.decision_event_id`, and carries `checkpoint_id` plus `decision_event_id` into the resulting task lifecycle event payload.  
        [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/store.py] [Source: _bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md#technical-requirements] [Source: _bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md#tasks--subtasks]
  - [x] Preserve current close and archive lifecycle ordering after the gate passes, including lease completion, lock release, and terminal-state transitions. The new gate must wrap those flows, not re-define them.  
        [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/tests/test_task_lifecycle_cli.py]

- [x] Surface gate outcomes through the existing task action contract and minimal inspect traceability. (AC: 3, 4)
  - [x] Keep the current task action JSON envelope intact in `tools/orchestration/cli/main.py`; add gate metadata only inside the existing `data.result`, `data.event`, or structured error result payloads.  
        [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-payload-patterns]
  - [x] Make blocked human-readable output explicit about whether the checkpoint is missing, stale, or mismatched and what command the operator should run next, and make successful close/archive output include the applied checkpoint or decision reference without expanding into Story 2.3 evidence packaging.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#human-readable-status-conventions] [Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md#action-items]
  - [x] Extend `tools/orchestration/history.py` and `event inspect` only as needed so operators can trace a successful gated close/archive event back to the checkpoint and approval link, without introducing a second audit browser or release-review summary in this story.  
        [Source: tools/orchestration/history.py] [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records]

- [x] Extend regression coverage in the existing orchestration CLI seams. (AC: 1, 2, 4, 5)
  - [x] Extend `tools/orchestration/tests/test_task_lifecycle_cli.py` with black-box cases for: close blocked without checkpoint, archive blocked without checkpoint, close or archive blocked when the latest checkpoint is stale after repo changes, close or archive blocked when only the other target action has a checkpoint, and success when a valid target-matched checkpoint exists.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: _bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md#testing-requirements]
  - [x] Assert the blocked paths leave task, lease, lock, checkpoint, and event authority unchanged apart from any allowed explicit error metadata, and assert the successful path persists `decision_event_id` linkage plus lifecycle-event payload refs.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: tools/orchestration/store.py]
  - [x] Extend `tools/orchestration/tests/test_inspect_context_cli.py` only where needed to prove `event inspect` or task-adjacent reads can trace a gated close/archive success through the linked checkpoint and approval event.  
        [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-object-state-fields-in-json]

- [x] Update operator-facing docs and help text only where the visible close/archive workflow changes. (AC: 4, 6)
  - [x] Touch `README.md`, `docs/user-guide.md`, and `docs/how-tos.md` only if current examples or workflow descriptions imply `task close` or `task archive` can succeed without a prior checkpoint. Defer cross-surface governance evidence documentation to Story 2.3.  
        [Source: docs/contributor-guide.md#when-to-touch-which-docs] [Source: _bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md#implementation-guardrails]

- [x] Review Follow-ups (AI). (AC: 2, 3, 5, 6)
  - [x] [AI-Review][high] Make latest-checkpoint selection deterministic for same-second `review_checkpoints` rows by reflecting true insertion order instead of UUID text ordering, and prove `task close` plus `task archive` attach approval linkage to the actual latest checkpoint.  
        [Source: user review finding dated 2026-04-15] [Source: tools/orchestration/history.py] [Source: tools/orchestration/tests/test_task_lifecycle_cli.py]

## Dev Notes

### Story Intent

Story 2.2 is the enforcement half of `POL-3`. Story 2.1 created the controller-owned checkpoint artifact, authority row, and inspectable event linkage; this story must make closeout fail closed until that checkpoint is still valid for the exact action being attempted, then record the attributable approval chain that justifies the final lifecycle mutation.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-22-enforce-the-diffreview-gate-before-closeout-or-safety-relaxation]  
[Source: _bmad-output/planning-artifacts/prd.md#compliance--regulatory]  
[Source: _bmad-output/planning-artifacts/architecture.md#product-safety-policies]

### Epic Continuity

- Story 2.1 already captured repo-native diff or review evidence and persisted `review_checkpoints` rows plus `review.checkpoint_recorded` events.
- Story 2.3 later broadens governance-hardening evidence across inspectors and release-review outputs; Story 2.2 should stop at the narrow event and action-path traceability needed to enforce the gate.
- Epic 1's retrospective explicitly identified freshness, stale-context detection, and remediation guidance as the main correctness risks for Epic 2.

Implementation consequence: harden the current close/archive command path and reuse the existing checkpoint model instead of inventing a new review workflow.

[Source: _bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md#completion-notes-list]  
[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-23-include-governance-hardening-evidence-in-inspectors-and-release-review]  
[Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md#friction-and-risks]

### Previous Story Intelligence

- Story 2.1 intentionally left `task close` and `task archive` behavior unchanged and reserved `decision_event_id` on the checkpoint record so this story could attach approval linkage without redefining stored artifacts.
- Story 2.1 already exposes recent checkpoint references through `task inspect` and `event inspect`; Story 2.2 should extend that traceability only as far as the enforced close/archive path needs.
- Story 6.2 already established the controller-owned operator-decision event pattern for attributable actions.
- Story 6.3 already centralized decision-rights metadata in `tools/orchestration/policy.py`, and it marks `task.close` and `task.archive` as `checkpoint_eligible` without requiring a separate new command family or remote approval channel.

[Source: _bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md#implementation-guardrails]  
[Source: _bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md#suggested-implementation-shape]  
[Source: _bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md#architecture-compliance]  
[Source: _bmad-output/implementation-artifacts/stories/6-3-enforce-explicit-decision-rights-and-guarded-actions.md#technical-requirements]

### Brownfield Baseline

- `tools/orchestration/checkpoints.py` already normalizes `task.close` and `task.archive` checkpoint targets and captures the baseline repo fingerprint, but it does not yet answer whether a stored checkpoint is still current.
- `tools/orchestration/tasks.py` currently writes checkpoint authority through `checkpoint_task(...)`, while `close_task(...)` and `archive_task(...)` still mutate authoritative state with no checkpoint lookup, no freshness validation, and no approval linkage.
- `tools/orchestration/history.py` can already list and inspect checkpoint rows, but it does not yet provide a target-action-aware "latest valid checkpoint" read model.
- `tools/orchestration/cli/main.py` already supports `macs task checkpoint`, `macs task close`, and `macs task archive` in the current task-family envelope, so Story 2.2 should extend those seams instead of adding a second review command family.
- The current regression suites already cover close, archive, checkpoint capture, and inspect traceability, providing the correct black-box seam for new fail-closed enforcement coverage.

[Source: tools/orchestration/checkpoints.py]  
[Source: tools/orchestration/tasks.py]  
[Source: tools/orchestration/history.py]  
[Source: tools/orchestration/cli/main.py]  
[Source: tools/orchestration/tests/test_task_lifecycle_cli.py]  
[Source: tools/orchestration/tests/test_inspect_context_cli.py]

### Technical Requirements

- Fail closed before any close or archive state mutation when no valid checkpoint exists for the requested action.  
  [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements] [Source: _bmad-output/planning-artifacts/prd.md#compliance--regulatory]
- Re-compute the current repo fingerprint at action time from git and compare it against the stored baseline; do not trust the captured artifact files alone as proof of freshness.  
  [Source: tools/orchestration/checkpoints.py] [Source: _bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md#technical-requirements]
- Treat target-action mismatch and task-scope drift as invalidation signals alongside repo-state drift. The gate is action-specific and context-specific, not a generic "some checkpoint exists" check.  
  [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-22-enforce-the-diffreview-gate-before-closeout-or-safety-relaxation]
- Record attributable operator approval through controller-owned events and link that approval to the selected checkpoint and resulting lifecycle event. Do not add a second approval database, hosted review service, or out-of-band workflow.  
  [Source: _bmad-output/planning-artifacts/architecture.md#event-record-schema] [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records] [Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md#next-epic-preparation]
- Do not auto-capture a checkpoint during `task close` or `task archive`; the checkpoint must remain operator-visible and explicitly attributable rather than silently synthesized during closeout.  
  [Source: _bmad-output/planning-artifacts/prd.md#compliance--regulatory] [Inference from: POL-3 requires the workflow to surface a diff/review checkpoint before closeout]
- Stay within Python 3.8+ stdlib, repo-local shell semantics, and current subprocess safety boundaries.  
  [Source: _bmad-output/project-context.md#technology-stack--versions] [Source: _bmad-output/project-context.md#language-specific-rules]

### Architecture Compliance

- Keep controller authority first: checkpoint validation, approval linkage, and lifecycle gating happen in controller code before any adapter-side or lifecycle mutation work.  
  [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: _bmad-output/planning-artifacts/prd.md#technical-constraints]
- Reuse the current event schema and existing task/history seams instead of building a parallel approval or audit subsystem.  
  [Source: _bmad-output/planning-artifacts/architecture.md#event-record-schema] [Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]
- Preserve the split between filesystem evidence and authority records: `.codex/orchestration/checkpoints/` remains evidence storage, while SQLite and events remain source of truth for gate enforcement.  
  [Source: _bmad-output/planning-artifacts/architecture.md#suggested-storage-layout] [Source: _bmad-output/planning-artifacts/architecture.md#persistence-strategy]
- Keep the operator surface inside the existing `task` family. No new TUI, background approval daemon, or external review workflow belongs in this story.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: _bmad-output/planning-artifacts/architecture.md#product-safety-policies]

### Suggested Implementation Shape

- Add one narrow validation helper in `tools/orchestration/checkpoints.py` or `tools/orchestration/history.py` that:
  - loads the latest checkpoint for `task_id` plus `target_action`
  - recomputes current git fingerprint
  - compares repo-state and task-scope compatibility
  - returns a structured gate result with a remediation command when blocked
- Reuse or generalize the current operator decision-event helper in `tools/orchestration/tasks.py` so close/archive success can create one attributable approval event without forking a second approval path.
- Gate `close_task(...)` and `archive_task(...)` through that validation helper, update `review_checkpoints.decision_event_id` on the checkpoint being approved, and thread `checkpoint_id` plus `decision_event_id` into the resulting `task.completed` or `task.archived` payloads.
- Keep CLI changes thin: extend current task action success and error rendering to show gate outcome or linked refs, then extend inspect readers only where the approval chain would otherwise be opaque.

[Inference from: tools/orchestration/tasks.py, tools/orchestration/checkpoints.py, tools/orchestration/history.py, tools/orchestration/cli/main.py, and tools/orchestration/store.py]  
[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]

### File Structure Requirements

- Primary implementation files for this story:
  - `tools/orchestration/tasks.py`
  - `tools/orchestration/checkpoints.py`
  - `tools/orchestration/history.py`
  - `tools/orchestration/cli/main.py`
  - `tools/orchestration/tests/test_task_lifecycle_cli.py`
  - `tools/orchestration/tests/test_inspect_context_cli.py`
- Optional touch points only if needed:
  - `tools/orchestration/policy.py`
  - `tools/orchestration/store.py`
  - `README.md`
  - `docs/user-guide.md`
  - `docs/how-tos.md`
- Do not broaden into release-gate packaging, release-review summaries, or cross-surface evidence aggregation in this story.

[Source: _bmad-output/project-context.md#development-workflow-rules]  
[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]

### Testing Requirements

- Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused required validation surface.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Add black-box lifecycle tests covering missing checkpoint, stale checkpoint after additional repo changes, target-action mismatch, blocked close/archive with no state mutation, and successful close/archive with persisted approval linkage.  
  [Source: tools/orchestration/tests/test_task_lifecycle_cli.py]
- Keep existing checkpoint capture and inspect regressions green so Story 2.2 hardens enforcement without regressing Story 2.1 traceability.  
  [Source: _bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md#testing-requirements] [Source: tools/orchestration/tests/test_inspect_context_cli.py]
- Prefer tmux-light seeded task fixtures unless a live lease or lock transition is required to prove close semantics. This story is about the gate, not new worker-runtime behavior.  
  [Inference from: tools/orchestration/tests/test_task_lifecycle_cli.py and _bmad-output/project-context.md#testing-rules]

### Git Intelligence Summary

- Recent committed history still concentrates orchestration work in controller-owned lifecycle, CLI, history, and evidence seams, so Story 2.2 should stay in those same modules rather than introduce a new governance subsystem.
- The current working tree already contains in-flight edits across policy, CLI, history, tasks, store, docs, tests, and release-evidence files. Implementation must work with those changes instead of reverting or relocating them.
- The highest-signal brownfield seams for this story are `tools/orchestration/tasks.py`, `tools/orchestration/checkpoints.py`, `tools/orchestration/history.py`, `tools/orchestration/cli/main.py`, and the existing orchestration CLI regression suites.

[Source: git log --oneline -5]  
[Inference from current git status]

### Implementation Guardrails

- Do not auto-create or refresh a checkpoint inside `task close` or `task archive`.
- Do not treat any checkpoint for the task as sufficient; the checkpoint must match the requested target action and still match current repo and task context.
- Do not add a hosted review service, semantic-review pipeline, or remote approval workflow.
- Do not broaden into Story 2.3 release evidence, release-gate aggregation, or inspector-wide governance summaries.
- Do not modify the historical orchestration sprint tracker, the guided-onboarding tracker, or any planning artifact outside this governance-hardening lane-local story and tracker update.
- Do not revert unrelated working-tree changes in shared CLI, history, policy, task, store, docs, or test files.

### Project Structure Notes

- This remains a brownfield, shell-first, Python-stdlib-only orchestration controller with repo-local authority under `.codex/orchestration/`.
- The cleanest Story 2.2 path is to validate against the checkpoint model Story 2.1 already created, then wrap current close/archive flows with that gate.
- Success should feel like a narrow governance hardening of the existing task family, not a new review subsystem.

[Source: _bmad-output/project-context.md#development-workflow-rules]  
[Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md#action-items]

### References

- `_bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`
- `_bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md`
- `_bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md`
- `_bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md`
- `_bmad-output/implementation-artifacts/stories/6-3-enforce-explicit-decision-rights-and-guarded-actions.md`
- `tools/orchestration/checkpoints.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/history.py`
- `tools/orchestration/policy.py`
- `tools/orchestration/store.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add one target-action-aware checkpoint validation helper first so close and archive can ask for a current gate result without open-coding git or SQL logic in multiple places.
- Thread that helper through `close_task(...)` and `archive_task(...)`, then add the minimal approval-event linkage needed to satisfy `POL-3` without inventing a second approval subsystem.
- Extend lifecycle and inspect regressions for missing, stale, mismatched, and successful gated closeout paths before touching docs.

### Debug Log References

- Story authored with `bmad-create-story`.
- Used the lane-specific tracker `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml` as the sprint source of truth for this slice.
- Loaded the governance-hardening delta epic file, current PRD, architecture, operator CLI contract, project context, Epic 1 retrospective, Story 2.1, Story 6.2, Story 6.3, recent git history, and the live brownfield seams in `tasks.py`, `checkpoints.py`, `history.py`, `policy.py`, `store.py`, `cli/main.py`, and the orchestration CLI tests.
- Validation pass applied against `.agents/skills/bmad-create-story/checklist.md`: the story now includes stale-checkpoint detection, target-action-specific gate rules, explicit approval-linkage work, bounded reuse guidance for controller-owned decision events, anti-scope guardrails against Story 2.3 expansion, and regression expectations for fail-closed close/archive enforcement.
- 2026-04-15T00:02:28+01:00: Development execution started. Loaded the BMAD dev-story workflow, project config, project context, lane tracker, Story 2.1 checkpoint authority shape, and the current working-tree implementations of checkpoint capture, task lifecycle, history, CLI rendering, and orchestration CLI regressions before patching.
- 2026-04-15T00:09:00+01:00: Implemented the target-action-aware checkpoint validation helper, threaded gated close/archive approval linkage through `tasks.py`, and extended CLI plus `event inspect` output so blocked and successful gate outcomes stay inside the existing task action contract.
- 2026-04-15T00:15:00+01:00: Focused validation initially exposed two success tests that were still asserting the checkpoint actor instead of the close/archive invoker. Updated those tests to run the gated action with an explicit `MACS_OPERATOR_ID`.
- 2026-04-15T00:18:00+01:00: Full discovery initially exposed higher-level flows still closing tasks without a checkpoint. Patched the reference dogfood runner to bootstrap a git repo and capture `task.close` checkpoints before closeout, then updated the release-gate harness PATH fixture to include `git` for the new checkpoint prerequisite.
- 2026-04-15T00:39:46+01:00: Resumed Story 2.2 for the follow-up review finding, added failing same-second checkpoint regressions for `task close` and `task archive`, and confirmed the gate was incorrectly using UUID text order when multiple checkpoints shared the same second-level `captured_at`.
- 2026-04-15T00:39:46+01:00: Kept the fix narrow to `tools/orchestration/history.py` plus lifecycle regressions, changed latest-checkpoint reads to use insertion-order tie-breaking (`rowid DESC` after `captured_at DESC`), reran the story-focused suites and full orchestration discovery successfully, and treated broader repo diff/scope-contamination review comments as non-actionable for this story because the touched seams stayed lane-local.

### Test Record

- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_task_close_completes_active_task_and_releases_live_ownership tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_task_archive_marks_terminal_task_archived tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_event_inspect_traces_gated_archive_to_checkpoint_and_decision_event` — passed (`OK`, 3 tests).
- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` — passed (`OK`, 187 tests).
- `python3 -m unittest tools.orchestration.tests.test_reference_dogfood_cli tools.orchestration.tests.test_release_gate_cli` — passed (`OK`, 5 tests).
- `python3 -m unittest discover -s tools/orchestration/tests` — passed (`OK`, 210 tests).
- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_task_close_uses_true_latest_checkpoint_when_same_second_records_exist tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_task_archive_uses_true_latest_checkpoint_when_same_second_records_exist` — failed first with 2 deterministic ordering mismatches selecting `checkpoint-zzzzzzzzzzzz`, then passed (`OK`, 2 tests) after the history-order fix.
- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` — passed (`OK`, 189 tests).
- `python3 -m unittest discover -s tools/orchestration/tests` — passed (`OK`, 212 tests).

### Completion Notes List

- Added target-action-aware checkpoint validation in `tools/orchestration/checkpoints.py` plus read-side helpers in `tools/orchestration/history.py`, including repo fingerprint digests, fail-closed gate outcomes, remediation commands, and task-scope mismatch detection.
- Hardened `close_task(...)` and `archive_task(...)` so they block before any lifecycle mutation when the checkpoint is missing, stale, or mismatched, and so successful gated actions record one attributable operator approval event that updates `review_checkpoints.decision_event_id`.
- Threaded `checkpoint_id` and `decision_event_id` through `lease.completed`, `task.completed`, and `task.archived` payloads, then extended `event inspect` and task action rendering so operators can trace blocked or successful gate outcomes without a new review surface.
- Extended black-box lifecycle and inspect regressions for missing, stale, mismatched, and successful gated close/archive paths, then updated the reference dogfood and release-gate harness to satisfy the new checkpoint prerequisite.
- Updated the README and user guide snippets that previously implied direct `task close` or `task archive` success without a prior checkpoint.
- Tightened checkpoint ordering in `tools/orchestration/history.py` so same-second checkpoint rows are resolved by true insertion order (`rowid`) instead of lexicographic `checkpoint_id`, keeping gated close/archive selection deterministic without weakening fail-closed behavior.
- Added same-second lifecycle regressions proving both `task close` and `task archive` select the actual latest checkpoint and persist `decision_event_id` linkage on that row rather than on an older same-second checkpoint.

### File List

- `_bmad-output/implementation-artifacts/stories/2-2-enforce-the-diff-review-gate-before-closeout-or-safety-relaxation.md`
- `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`
- `README.md`
- `docs/user-guide.md`
- `tools/orchestration/checkpoints.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/dogfood.py`
- `tools/orchestration/history.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_reference_dogfood_cli.py`
- `tools/orchestration/tests/test_release_gate_cli.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`

### Change Log

- 2026-04-15: Development execution started; story status updated to `in-progress`.
- 2026-04-15: Implemented checkpoint freshness validation, gated close/archive approval linkage, contract-preserving CLI traceability, and the required lifecycle plus inspect regressions.
- 2026-04-15: Updated dogfood/release-gate compatibility and operator docs for the checkpoint-gated close/archive workflow, reran focused and full orchestration suites successfully, and marked the story `done`.
- 2026-04-15: Addressed the same-second checkpoint ordering review finding with a narrow history read-order fix plus close/archive regressions, reran the story-focused suites and full orchestration discovery successfully, and kept the story status at `done`.
