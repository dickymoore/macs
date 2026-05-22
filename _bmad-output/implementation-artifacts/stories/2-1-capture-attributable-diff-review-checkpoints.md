# Story 2.1: Capture attributable diff/review checkpoints

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,  
I want a baseline diff/review checkpoint artifact tied to task and action context,  
so that close/archive and guarded actions have inspectable preconditions.

## Acceptance Criteria

1. Given a task that is ready for close/archive or a request to perform a safety-relaxing action, when I invoke the review-checkpoint flow, then MACS captures repo-native diff/review evidence with actor identity, timestamp, affected refs, and baseline repo state, and the checkpoint is linked to the relevant task or decision context as referenced evidence.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-21-capture-attributable-diffreview-checkpoints] [Source: _bmad-output/planning-artifacts/prd.md#compliance--regulatory] [Source: _bmad-output/planning-artifacts/architecture.md#product-safety-policies] [Source: _bmad-output/planning-artifacts/architecture.md#event-record-schema]
2. Given a recorded diff/review checkpoint, when I inspect audit history later, then I can trace the checkpoint to the related action request and decision event, and the justification does not depend on raw tmux pane history alone.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-21-capture-attributable-diffreview-checkpoints] [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/planning-artifacts/prd.md#observability--auditability]

## Tasks / Subtasks

- [x] Add one controller-owned review-checkpoint capture helper that writes a repo-local evidence bundle plus stable metadata. (AC: 1, 2)
  - [x] Add a small helper module such as `tools/orchestration/checkpoints.py` that accepts `task_id`, canonical target action, and affected refs, then captures repo-native baseline evidence from the current repo worktree into `paths.checkpoints_dir` under a stable `checkpoint_id` bundle. The bundle should include audit-safe metadata plus repo-native evidence refs such as baseline HEAD or explicit unborn-HEAD marker, dirty-state summary, affected paths, and diff/review summary outputs.  
        [Source: tools/orchestration/session.py] [Source: tools/orchestration/config.py] [Source: _bmad-output/planning-artifacts/architecture.md#suggested-storage-layout] [Source: _bmad-output/planning-artifacts/prd.md#compliance--regulatory]
  - [x] Keep raw diff/review artifacts repo-local and referenceable, but do not treat files under `.codex/orchestration/checkpoints/` as authority records by themselves. The authoritative linkage must remain controller-owned metadata and event refs.  
        [Source: _bmad-output/planning-artifacts/architecture.md#suggested-storage-layout] [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records]
  - [x] Fail clearly when repo-native checkpoint evidence cannot be captured or normalized. Do not emit a success-shaped checkpoint with missing baseline repo state, missing actor attribution, or placeholder artifact refs.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements] [Source: _bmad-output/planning-artifacts/prd.md#compliance--regulatory]

- [x] Persist checkpoint authority in controller state and event history instead of relying on filesystem artifacts alone. (AC: 1, 2)
  - [x] Extend `tools/orchestration/store.py` with one dedicated supporting-evidence table for review checkpoints, or a narrowly generalized controller-owned evidence registry if that is materially cleaner, keyed by `checkpoint_id` and storing task or action context, actor identity, capture time, artifact refs, and a structured baseline repo fingerprint. Do not overload `routing_decisions`, `recovery_runs`, or `policy_snapshots` for checkpoint storage.  
        [Source: tools/orchestration/store.py] [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records] [Inference from: the current schema has no checkpoint-specific authority table and the shipped `evidence_records` table is unused by current read paths]
  - [x] Emit one controller-owned checkpoint event such as `review.checkpoint_recorded` in `events` and `events.ndjson`, carrying `checkpoint_id`, target action, `affected_refs`, audit-safe `evidence_refs`, and any already-known related decision-event reference.  
        [Source: tools/orchestration/store.py] [Source: _bmad-output/planning-artifacts/architecture.md#event-record-schema] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content]
  - [x] Preserve a stable field for later approval linkage, such as `target_action` plus optional `decision_event_id`, so Story 2.2 can attach enforced approval events without redefining the checkpoint model or rewriting stored artifacts.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-22-enforce-the-diffreview-gate-before-closeout-or-safety-relaxation] [Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md#next-epic-preparation]

- [x] Expose a task-scoped checkpoint capture flow on the existing operator surface without enforcing it yet. (AC: 1)
  - [x] Add a discoverable `checkpoint` verb under the existing `macs task` family in `tools/orchestration/cli/main.py`, with `--task` plus an explicit target action selector normalized to the current controller decision-rights vocabulary (`task.close`, `task.archive`, and the future safety-relaxing action keys that will reuse this format). Keep the CLI surface in the existing task family rather than introducing a new top-level review command family.  
        [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: _bmad-output/planning-artifacts/architecture.md#product-safety-policies]
  - [x] Return the checkpoint result through the current MACS action envelope in both human-readable and `--json` modes, including `checkpoint_id`, target action, captured-at timestamp, task ID, event ID, artifact refs, and a next action that points back to inspectable controller surfaces.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output]
  - [x] Keep `task close` and `task archive` behavior unchanged in Story 2.1 apart from any narrow inspectability or follow-up hints required to point operators at the new checkpoint flow. Blocking or freshness enforcement belongs to Story 2.2.  
        [Source: tools/orchestration/tasks.py] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-22-enforce-the-diffreview-gate-before-closeout-or-safety-relaxation]

- [x] Surface checkpoint references through the existing inspect and history seams. (AC: 2)
  - [x] Extend `tools/orchestration/history.py` so event and task-adjacent read models can surface latest or relevant checkpoint refs, target action, actor identity, capture time, baseline repo summary, and any related decision-event linkage without forcing operators to browse raw files directly.  
        [Source: tools/orchestration/history.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md#architecture-compliance]
  - [x] Extend `tools/orchestration/cli/main.py` task and event inspect rendering to show checkpoint evidence refs compactly in human-readable and `--json` output, reusing the current event and affected-ref presentation style instead of inventing a second audit browser.  
        [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md#tasks--subtasks]
  - [x] If recovery or lease inspectors need one narrow addition to show a task's latest checkpoint context, keep that read-side change incremental and tied to existing `recent_event_refs` or decision-event lookup patterns.  
        [Source: tools/orchestration/recovery.py] [Source: tools/orchestration/history.py] [Source: tools/orchestration/cli/main.py]

- [x] Add focused regression coverage for capture, attribution, and inspectability. (AC: 1, 2)
  - [x] Extend `tools/orchestration/tests/test_task_lifecycle_cli.py` with black-box cases proving `macs task checkpoint` is discoverable, succeeds for a task-scoped target action, writes the checkpoint bundle under `.codex/orchestration/checkpoints/`, returns stable checkpoint metadata in JSON and human-readable output, and leaves the task family contract envelope intact.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output]
  - [x] Add a fail-closed regression showing checkpoint capture rejects missing or unusable repo-native diff evidence with a structured controller error and no persisted checkpoint row or success event.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements] [Source: tools/orchestration/tests/test_task_lifecycle_cli.py]
  - [x] Extend `tools/orchestration/tests/test_inspect_context_cli.py` so `task inspect` and `event inspect` surface checkpoint refs, actor identity, target action, and artifact linkage without relying on raw tmux or ad hoc file browsing.  
        [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content]
  - [x] If store bootstrap or layout handling changes, extend `tools/orchestration/tests/test_setup_init.py` so new checkpoint metadata tables or bundle directories remain repo-local, bootstrapped, and restart-safe.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/session.py]

- [x] Keep Story 2.1 bounded to checkpoint capture and attribution only. (AC: 1, 2)
  - [x] Do not block `task close`, `task archive`, or any guarded action yet. Story 2.1 captures and links the checkpoint; Story 2.2 enforces freshness and required presence.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-22-enforce-the-diffreview-gate-before-closeout-or-safety-relaxation]
  - [x] Do not expand release-gate, audit-report, or release-evidence packaging in this story; Story 2.3 owns cross-surface evidence exposure for governance hardening.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-23-include-governance-hardening-evidence-in-inspectors-and-release-review] [Source: _bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md#implementation-guardrails]
  - [x] Do not treat raw tmux pane history, prompt capture, terminal capture, tool output, or release-review markdown as a substitute for controller-owned diff/review checkpoint evidence.  
        [Source: _bmad-output/planning-artifacts/prd.md#compliance--regulatory] [Source: _bmad-output/planning-artifacts/architecture.md#audit-content-policy]
  - [x] Do not introduce hosted review services, semantic AI review pipelines, or remote approval workflows in this increment. Keep the checkpoint path repo-local, controller-owned, and compatible with current Python-stdlib-only constraints.  
        [Source: _bmad-output/project-context.md#technology-stack--versions] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]

- [x] Review Follow-ups (AI). (AC: 1, 2)
  - [x] [AI-Review][high] Reject unsupported or unknown `--target-action` values so checkpoint authority only accepts explicit controller-known checkpoint targets instead of arbitrary dotted strings.  
        [Source: user review finding dated 2026-04-14] [Source: _bmad-output/planning-artifacts/architecture.md#product-safety-policies]
  - [x] [AI-Review][medium] Ensure untracked-only worktrees emit reviewable diff/stat/summary evidence for new files instead of empty diff artifacts plus only a filename list.  
        [Source: user review finding dated 2026-04-14] [Source: _bmad-output/planning-artifacts/prd.md#compliance--regulatory]

## Dev Notes

### Story Intent

This story establishes the capture substrate for `POL-3`. MACS already has controller-owned task lifecycle commands, durable events, attributable intervention decisions, and repo-local evidence-writing patterns, but close/archive and adjacent guarded flows do not yet preserve one explicit diff/review checkpoint artifact with controller-owned linkage. Story 2.1 should create that checkpoint model now without yet enforcing checkpoint freshness or presence before action execution.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-21-capture-attributable-diffreview-checkpoints]  
[Source: _bmad-output/planning-artifacts/prd.md#compliance--regulatory]  
[Source: _bmad-output/planning-artifacts/architecture.md#product-safety-policies]

### Epic Continuity

- Epic 2 is intentionally split into three layers: capture the checkpoint, enforce the checkpoint gate, then surface checkpoint and governance hardening through inspectors and release review.
- Story 2.1 should therefore create one reusable checkpoint artifact and metadata model that later stories can validate and summarize, rather than trying to enforce or package everything now.
- The governance-hardening retrospective explicitly calls out stale-context detection, remediation guidance, and controller-owned reuse of task, routing, and event seams as the major risks for this epic.

Implementation consequence: make checkpoint metadata reusable and inspectable now, but keep gate enforcement for Story 2.2 and broad evidence aggregation for Story 2.3.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#epic-2-prove-and-enforce-baseline-review-before-risky-completion]  
[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-22-enforce-the-diffreview-gate-before-closeout-or-safety-relaxation]  
[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-23-include-governance-hardening-evidence-in-inspectors-and-release-review]  
[Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md#next-epic-preparation]

### Brownfield Reuse Guidance

- `tools/orchestration/tasks.py` already owns `close_task(...)` and `archive_task(...)`, and both currently mutate authoritative task state without any repo-native diff/review checkpoint capture or approval linkage.
- Story 6.2 already introduced the controller-owned pattern for attributable operator decisions via durable events and affected refs. Story 2.1 should reuse that event vocabulary and read-side style rather than introducing a second approval or audit store.
- Story 6.3 already centralized decision-rights action keys in `tools/orchestration/policy.py`. The checkpoint flow should normalize target actions to that same vocabulary so later enforcement does not need alias translation glue.
- `tools/orchestration/history.py` and current CLI inspect surfaces already know how to display `affected_refs`, actor identity, causation, and decision-event references. Extend those seams for checkpoint refs instead of inventing a checkpoint-only browser.
- `tools/orchestration/session.py` and the current state-layout config already provision `.codex/orchestration/checkpoints/`, but the architecture explicitly describes that directory as artifact storage rather than controller authority.
- Story 8.4 and `tools/orchestration/release_gate.py` already show the current repo-local pattern for writing machine-readable and human-readable evidence bundles. That evidence-writing style is worth reusing for checkpoint artifacts, but Story 2.1 must not wire checkpoint evidence into release-gate output yet.

[Source: tools/orchestration/tasks.py]  
[Source: tools/orchestration/history.py]  
[Source: tools/orchestration/session.py]  
[Source: tools/orchestration/config.py]  
[Source: tools/orchestration/policy.py]  
[Source: tools/orchestration/release_gate.py]  
[Source: _bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md#completion-notes-list]  
[Source: _bmad-output/implementation-artifacts/stories/6-3-enforce-explicit-decision-rights-and-guarded-actions.md#technical-requirements]  
[Source: _bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md#brownfield-reuse-guidance]

### Technical Requirements

- Capture checkpoint evidence from the repo-native git worktree and make the baseline state explicit: current HEAD or explicit unborn-HEAD marker, worktree status summary, affected paths, and diff/review summary refs. Do not replace git-backed evidence with tmux-only or narrative-only notes.  
  [Source: _bmad-output/planning-artifacts/prd.md#compliance--regulatory] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements]
- Preserve actor identity, capture time, target action, and affected refs in controller-owned metadata so a later inspector can reconstruct who captured the checkpoint and what it was intended to protect.  
  [Source: _bmad-output/planning-artifacts/architecture.md#event-record-schema] [Source: _bmad-output/planning-artifacts/prd.md#observability--auditability]
- Keep checkpoint authority controller-owned and repo-local. Workers and adapters may provide context or remain the subject of the checkpointed action, but they must not author, approve, or redefine the checkpoint model.  
  [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries] [Source: _bmad-output/project-context.md#framework-specific-rules]
- Treat checkpoint artifacts as referenced evidence, not the authority record. SQLite plus event history should tell MACS what checkpoint exists and where its evidence lives.  
  [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records] [Source: _bmad-output/planning-artifacts/architecture.md#write-model]
- If the repo is in a detached-HEAD or unborn-HEAD state, capture that explicitly in the baseline metadata rather than leaving nulls or inventing a fake revision.  
  [Inference from: repo-native checkpoint freshness will later depend on a truthful baseline fingerprint even when a normal branch ref is absent]
- Stay within Python 3.8+ stdlib, repo-local shell semantics, and current subprocess safety rules.  
  [Source: _bmad-output/project-context.md#technology-stack--versions] [Source: _bmad-output/project-context.md#language-specific-rules]

### Architecture Compliance

- Preserve the controller-authority split: the controller captures and records checkpoint metadata and evidence refs; the checkpoint is not delegated to adapters or worker runtimes.  
  [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]
- Reuse the current event schema cleanly. `review.checkpoint_recorded` should fit the canonical event fields and payload fragments already defined for `affected_refs`, `decision_event_id`, and evidence refs.  
  [Source: _bmad-output/planning-artifacts/architecture.md#event-record-schema]
- Keep filesystem checkpoint bundles and authoritative state separate. The `.codex/orchestration/checkpoints/` directory may hold artifact bundles, but controller truth must remain in SQLite and NDJSON so replay and inspection do not depend on ad hoc file naming alone.  
  [Source: _bmad-output/planning-artifacts/architecture.md#suggested-storage-layout] [Source: _bmad-output/planning-artifacts/architecture.md#persistence-strategy]
- Extend current inspect surfaces instead of building a second audit UI. `task inspect`, `event inspect`, and adjacent history readers already satisfy the product’s audit-first posture.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md#architecture-compliance]

### Suggested Implementation Shape

- Add `tools/orchestration/checkpoints.py` as the narrow helper for:
  - capturing git-backed baseline metadata and diff/review outputs
  - writing the checkpoint bundle under `paths.checkpoints_dir`
  - normalizing checkpoint metadata for persistence
  - emitting or preparing one controller-owned checkpoint event payload
- Add a task-family action in `tools/orchestration/cli/main.py` and a small task-scoped orchestration entrypoint in `tools/orchestration/tasks.py` that:
  - validates the task exists
  - normalizes the requested target action key
  - captures the checkpoint bundle
  - persists checkpoint metadata plus `review.checkpoint_recorded`
  - returns the current MACS action envelope with stable refs and next steps
- Keep the helper generic enough that Story 2.2 can reuse it for non-task guarded actions or later approval linkage even if Story 2.1 only exposes a task-scoped operator surface.
- Extend `tools/orchestration/history.py` with one reader for latest or referenced checkpoint metadata so task and event inspectors can show checkpoint refs without open-coding SQL or filesystem scans in the CLI.

[Inference from: tools/orchestration/tasks.py, tools/orchestration/history.py, tools/orchestration/store.py, tools/orchestration/session.py, and tools/orchestration/cli/main.py]  
[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]

### File Structure Requirements

- Primary implementation files for this story:
  - `tools/orchestration/cli/main.py`
  - `tools/orchestration/tasks.py`
  - `tools/orchestration/history.py`
  - `tools/orchestration/store.py`
  - `tools/orchestration/session.py`
  - `tools/orchestration/tests/test_task_lifecycle_cli.py`
  - `tools/orchestration/tests/test_inspect_context_cli.py`
- Preferred new helper file if the capture logic is more than a few functions:
  - `tools/orchestration/checkpoints.py`
- Optional touch points only if needed:
  - `tools/orchestration/config.py`
  - `tools/orchestration/setup.py`
  - `tools/orchestration/tests/test_setup_init.py`
  - `README.md`
  - `docs/user-guide.md`
  - `docs/how-tos.md`
- Do not add release-gate or dogfood wiring in this story unless a tiny helper extraction is strictly necessary to reuse existing evidence-writing utilities.

[Source: _bmad-output/project-context.md#development-workflow-rules]  
[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]

### Testing Requirements

- Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused required validation surface because this story touches task-family actions, inspect readers, and likely store or session bootstrap.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Add black-box task-family tests covering:
  - help visibility or parser exposure for `task checkpoint`
  - successful checkpoint capture with stable JSON and human-readable output
  - structured failure when repo-native diff evidence is unavailable or unusable
  - no unintended behavior change to current `task close` and `task archive` success paths  
  [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output]
- Add inspect-side tests proving `task inspect` and `event inspect` surface checkpoint refs, actor identity, target action, and evidence linkage without requiring raw file browsing.  
  [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content]
- If a new checkpoint metadata table or layout bootstrap behavior is added, keep startup and repo-local bootstrap regressions green in `test_setup_init.py`.  
  [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/session.py]

### Git Intelligence Summary

- Recent committed history still concentrates orchestration work in controller-owned lifecycle, CLI, history, and evidence seams, so Story 2.1 should stay in those same modules rather than start a new governance subsystem.
- The current working tree already contains in-flight edits across shared governance, CLI, history, task, routing, config, docs, and test files. Story 2.1 is likely to touch several of those seams, so implementation must work with those changes instead of reverting them.
- The highest-signal brownfield files for this story are `tools/orchestration/tasks.py`, `tools/orchestration/cli/main.py`, `tools/orchestration/history.py`, `tools/orchestration/store.py`, `tools/orchestration/session.py`, and the existing orchestration CLI regression suites.

[Source: git log --oneline -5]  
[Inference from current git status]

### Implementation Guardrails

- Do not block `task close`, `task archive`, or any safety-relaxing action yet; that is Story 2.2.
- Do not add a second approval system, hosted review workflow, or remote review service.
- Do not treat `.codex/orchestration/checkpoints/` as the sole source of truth; authoritative checkpoint existence and linkage must live in controller state and events.
- Do not persist raw tmux transcripts, prompt content, tool output, or secret material as the checkpoint substitute.
- Do not broaden into Story 2.3 release-review evidence packaging, release-gate aggregation, or inspector-wide governance summary work beyond the narrow checkpoint refs needed for traceability.
- Do not revert unrelated working-tree changes in shared policy, CLI, task, history, config, or test files.
- Do not modify the historical orchestration sprint tracker or the guided-onboarding tracker as part of implementation.

### Project Structure Notes

- This remains a brownfield, shell-first, Python-stdlib-only orchestration controller with repo-local state under `.codex/orchestration/`.
- The existing `checkpoints/` directory is available for artifact bundles, but the architecture explicitly says it is not an authority store; Story 2.1 should honor that split.
- The cleanest implementation path is one small checkpoint helper plus thin extensions to the task-family action path and current inspect readers, so Story 2.2 can later enforce freshness without backfilling a new model.

[Source: _bmad-output/project-context.md#development-workflow-rules]  
[Source: _bmad-output/planning-artifacts/architecture.md#suggested-storage-layout]

### References

- `_bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`
- `_bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md`
- `_bmad-output/implementation-artifacts/stories/1-4-enforce-scoped-secret-resolution-at-action-time.md`
- `_bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md`
- `_bmad-output/implementation-artifacts/stories/6-3-enforce-explicit-decision-rights-and-guarded-actions.md`
- `_bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/history.py`
- `tools/orchestration/store.py`
- `tools/orchestration/session.py`
- `tools/orchestration/config.py`
- `tools/orchestration/policy.py`
- `tools/orchestration/recovery.py`
- `tools/orchestration/release_gate.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_setup_init.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add one controller-owned checkpoint helper first so repo-native evidence capture, artifact writing, and metadata normalization live in one bounded place.
- Wire a task-scoped `checkpoint` action through the existing task family and current inspect surfaces without changing close/archive enforcement in this story.
- Lock the behavior down with black-box task and inspect regressions, then run focused and full orchestration test suites before any `done` transition.

### Debug Log References

- Story authored with `bmad-create-story`.
- Used the lane-specific tracker `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml` as the sprint source of truth for this slice.
- Loaded the governance-hardening delta epic file, current PRD, architecture, operator CLI contract, project context, Epic 1 retrospective, and the live brownfield seams in `tasks.py`, `history.py`, `store.py`, `session.py`, `policy.py`, `cli/main.py`, and `release_gate.py`.
- Validation pass applied against `.agents/skills/bmad-create-story/checklist.md`: the story now includes a controller-owned checkpoint model, explicit artifact-vs-authority boundaries for `.codex/orchestration/checkpoints/`, reuse guidance for decision-event and inspect seams, anti-scope guardrails against premature enforcement and release-evidence packaging, and regression expectations for checkpoint capture plus traceability.
- 2026-04-14T22:31:58+01:00: Dev execution started under `bmad-dev-story`; story status moved to `in-progress` and current controller/task/history/store/CLI seams were loaded before implementation.
- 2026-04-14T22:51:26+01:00: Implemented controller-owned checkpoint capture in `tools/orchestration/checkpoints.py`, persisted authoritative `review_checkpoints` rows plus `review.checkpoint_recorded` events, and added task/event inspect readers plus compact CLI rendering for checkpoint refs.
- 2026-04-14T22:51:26+01:00: Added black-box lifecycle, inspect, and setup regressions for `macs task checkpoint`; the first focused pass exposed git worktree-root normalization, that defect was fixed, and the rerun plus full discovery suite passed.
- 2026-04-14T23:50:01+01:00: Resumed Story 2.1 from review to address two follow-up findings; tightened checkpoint target-action normalization so only explicit controller-known checkpoint targets (`task.close`, `task.archive`) are accepted and added regression coverage for unsupported and unknown values.
- 2026-04-14T23:50:01+01:00: Updated checkpoint artifact capture so untracked-only worktrees write reviewable diff/stat/summary evidence for new files, fixed the focused-suite message-contract mismatch, reran the required focused suites (181 tests) and full orchestration discovery (204 tests), and completed the story.

### Test Record

- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` — passed (`OK`, 181 tests).
- `python3 -m unittest discover -s tools/orchestration/tests` — passed (`OK`, 204 tests).

### Completion Notes List

- Added `tools/orchestration/checkpoints.py` to capture repo-native git status, diff, staged diff, HEAD state, affected paths, and audit-safe metadata into `.codex/orchestration/checkpoints/<checkpoint_id>/`.
- Added controller-owned checkpoint authority via the new `review_checkpoints` table and `review.checkpoint_recorded` events, including stable `target_action`, `decision_event_id`, baseline fingerprint, and artifact refs.
- Added `macs task checkpoint --target-action ...` without changing `task close` or `task archive` enforcement behavior in this story.
- Tightened checkpoint target-action normalization so only explicit controller-known checkpoint targets are accepted for Story 2.1, using controller-owned decision-rights vocabulary instead of arbitrary dotted strings.
- Combined tracked and untracked review artifacts so untracked-only worktrees now preserve reviewable diff/stat/summary evidence for affected new files instead of only a filename list.
- Extended task and event inspect surfaces to expose recent checkpoint refs, actor identity, target action, baseline repo summary, and compact artifact linkage.
- Added black-box lifecycle regressions for unsupported or unknown target actions and untracked-only worktrees, then passed the focused required suites plus the full orchestration discovery suite.

### File List

- `_bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md`
- `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`
- `tools/orchestration/checkpoints.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/history.py`
- `tools/orchestration/policy.py`
- `tools/orchestration/store.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`

### Change Log

- 2026-04-14: Created Story 2.1 and moved the governance-hardening tracker entry from `backlog` to `ready-for-dev`; `epic-2` entered `in-progress`.
- 2026-04-14: Development execution started; story status updated to `in-progress`.
- 2026-04-14: Implemented controller-owned diff/review checkpoint capture, task/event inspect traceability, and regression coverage; story status updated to `review`.
- 2026-04-14: Addressed review findings for explicit checkpoint target-action validation and untracked-only diff evidence, reran focused and full orchestration suites successfully, and updated the story status to `done`.
