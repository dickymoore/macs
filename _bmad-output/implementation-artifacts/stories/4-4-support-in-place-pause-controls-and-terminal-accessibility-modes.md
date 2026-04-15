# Story 4.4: Support in-place pause controls and terminal accessibility modes

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want pause controls, narrow layouts, and reduced-color modes in the same controller surface,
so that intervention stays accessible in varied terminal conditions.

## Acceptance Criteria

1. `macs task pause` becomes a real controller-owned intervention path instead of a deferred placeholder. For a valid live task, it validates authoritative state, transitions `task.state` from `active` to `intervention_hold`, transitions the live lease from `active` to `paused`, records durable intervention history, and keeps task, lease, lock, and event inspection immediately consistent without requiring raw tmux manipulation as the normal path.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-44-support-in-place-pause-controls-and-terminal-accessibility-modes] [Source: _bmad-output/planning-artifacts/prd.md#control-surface-and-product-interface] [Source: _bmad-output/planning-artifacts/prd.md#monitoring-intervention-and-recovery] [Source: _bmad-output/planning-artifacts/architecture.md#task-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules]
2. `macs task resume` becomes the paired controller-owned release path for operator-held pauses. When a task is in `intervention_hold` with a `paused` live lease, resume returns the task to `active`, returns the same lease to `active`, records durable audit history, and fails closed with structured output when recovery or evidence state means continuation is unsafe.  
   [Source: _bmad-output/planning-artifacts/prd.md#orchestration-control--task-lifecycle] [Source: _bmad-output/planning-artifacts/architecture.md#task-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output]
3. Pause and inspection flows keep the frozen Phase 1 controller-first contract. Human-readable output uses canonical nouns, shows controller truth before adapter evidence, labels uncertainty explicitly, and reports resulting state, event ID, controller-state change, and next actions when relevant. `--json` output keeps the frozen top-level envelope plus action payload and event metadata.  
   [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/planning-artifacts/architecture.md#surface-model] [Source: _bmad-output/planning-artifacts/architecture.md#ux-backing-requirements]
4. The same pause and inspection semantics remain usable in narrow and wide terminals and in standard-color and reduced-color/high-contrast modes. Human-readable layouts stack or compress without changing terminology, state never depends on color alone, and alerts remain understandable in plain-text logs or pasted output. JSON output remains script-stable regardless of terminal presentation mode.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-44-support-in-place-pause-controls-and-terminal-accessibility-modes] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#customization-strategy] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#color-system] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#spacing--layout-foundation] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#accessibility-considerations]
5. Regression coverage and operator documentation ship with the change, proving pause and resume happy paths, fail-closed intervention behavior, accessibility rendering fallbacks, and no regression to the existing Story 4.1, 4.2, and 4.3 task inspection or pane-navigation flows.  
   [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-6-controller-first-operator-surface-on-the-frozen-cli-contract] [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/implementation-artifacts/stories/4-2-assign-and-manage-task-lifecycle-actions-from-one-command-path.md] [Source: _bmad-output/implementation-artifacts/stories/4-3-inspect-degraded-evidence-and-open-the-right-worker-pane-from-context.md]

## Tasks / Subtasks

- [x] Turn `task pause` and `task resume` into real controller-owned lifecycle actions. (AC: 1, 2, 3)
  - [x] Extend `tools/orchestration/tasks.py` with focused helpers for pause and resume so controller-owned state transitions do not stay open-coded in CLI handlers.  
        [Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape] [Source: tools/orchestration/tasks.py]
  - [x] Pause must move `task.state` from `active` to `intervention_hold`, move the current live lease from `active` to `paused`, preserve current owner and protected-surface lock ownership, and emit a durable intervention event.  
        [Source: _bmad-output/planning-artifacts/architecture.md#task-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/prd.md#orchestration-control--task-lifecycle]
  - [x] Resume must only succeed from the controller-recognized paused shape: task in `intervention_hold`, same current lease in `paused`, and no unresolved recovery block or incompatible risk condition. On success it returns task and lease to `active`; on failure it returns structured errors without partial mutation.  
        [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#restart-recovery-and-reconciliation] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules]
  - [x] Keep `reroute` and `abort` on their current story boundaries. Story 4.4 owns real pause/resume semantics, not a broader recovery rewrite.  
        [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-6-controller-first-operator-surface-on-the-frozen-cli-contract] [Source: _bmad-output/implementation-artifacts/stories/4-2-assign-and-manage-task-lifecycle-actions-from-one-command-path.md]

- [x] Wire pause/resume through the existing `macs task` contract and in-context inspection flow. (AC: 1, 2, 3)
  - [x] Replace the current deferred placeholder path in `tools/orchestration/cli/main.py` for `task pause` and `task resume` with real handlers that reuse the existing action-envelope helper shape introduced for Story 4.2.  
        [Source: _bmad-output/implementation-artifacts/stories/4-2-assign-and-manage-task-lifecycle-actions-from-one-command-path.md] [Source: tools/orchestration/cli/main.py]
  - [x] Ensure pause and resume results report the command result, primary object IDs, resulting state, event ID, controller-state-changed flag, and next recommended action in human-readable mode and the frozen action envelope in `--json`.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output]
  - [x] Extend `task inspect` so the operator can see pause-relevant state from the same controller context: current intervention status, live lease state, recent intervention event reference, and the next valid action without leaving the inspect path.  
        [Source: _bmad-output/planning-artifacts/ux-design-specification.md#maintainer-intervenes-in-a-degraded-session] [Source: _bmad-output/planning-artifacts/architecture.md#ux-backing-requirements] [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/tasks.py]
  - [x] Keep tmux pane access secondary to controller semantics. If runtime-level intervention support is partial or unavailable, surface an explicit warning instead of silently treating raw pane control as the primary path.  
        [Source: _bmad-output/planning-artifacts/prd.md#control-surface-and-product-interface] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules] [Inference from: _bmad-output/planning-artifacts/architecture.md#runtime-adapter-architecture and _bmad-output/planning-artifacts/ux-design-specification.md#experience-mechanics]

- [x] Add a shared terminal-rendering seam for narrow layouts and reduced-color accessibility. (AC: 3, 4)
  - [x] Extract or introduce a narrow rendering helper for human-readable CLI output so `task inspect`, `worker inspect`, `task pause`, and `task resume` do not each hand-roll layout branching. A brownfield-safe fit is a small helper under `tools/orchestration/cli/` rather than a CLI rewrite.  
        [Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape] [Source: tools/orchestration/cli/main.py] [Inference from: _bmad-output/planning-artifacts/ux-design-specification.md#implementation-approach and _bmad-output/planning-artifacts/ux-design-specification.md#spacing--layout-foundation]
  - [x] Keep semantics identical across wide and narrow layouts: same canonical nouns, same warning meaning, and the same state transitions, with vertical stacking or compact sections when terminal width is constrained.  
        [Source: _bmad-output/planning-artifacts/ux-design-specification.md#spacing--layout-foundation] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#accessibility-considerations]
  - [x] Support reduced-color or high-contrast rendering without introducing a second vocabulary. Human-readable output must include textual state markers such as `PAUSED`, `HOLD`, `DEGRADED`, and `WARNING` so color remains additive, not required.  
        [Source: _bmad-output/planning-artifacts/ux-design-specification.md#customization-strategy] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#color-system] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#accessibility-considerations]
  - [x] Recommended brownfield implementation: honor environment-driven reduced-color conditions already common in terminal tooling, such as `NO_COLOR`, non-TTY output, or explicit no-color test fixtures, while leaving `--json` payloads unchanged.  
        [Inference from: _bmad-output/planning-artifacts/ux-design-specification.md#customization-strategy, _bmad-output/planning-artifacts/ux-design-specification.md#accessibility-considerations, and tools/orchestration/cli/main.py]

- [x] Preserve history, recovery, and lock invariants while paused. (AC: 1, 2, 3, 5)
  - [x] Reuse invariant and state-machine helpers so pause/resume keeps the zero-or-one live-lease rule and does not manufacture a successor lease or dual ownership.  
        [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: tools/orchestration/invariants.py] [Source: tools/orchestration/state_machine.py]
  - [x] Preserve active lock protection and durable event history during operator-held pause. Pausing should freeze risky continuation, not silently release protection or erase audit context.  
        [Source: _bmad-output/planning-artifacts/prd.md#orchestration-control--task-lifecycle] [Source: _bmad-output/planning-artifacts/prd.md#auditability-governance-and-operator-trust] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#maintainer-intervenes-in-a-degraded-session]
  - [x] If recovery metadata or worker evidence makes continuation unsafe, resume must fail closed and direct the operator toward inspect, reroute, or recovery flows instead of forcing progress.  
        [Source: _bmad-output/planning-artifacts/prd.md#monitoring-intervention-and-recovery] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#maintainer-intervenes-in-a-degraded-session] [Source: tools/orchestration/recovery.py]

- [x] Add documentation and regression coverage for pause/resume plus accessibility behavior. (AC: 5)
  - [x] Extend `tools/orchestration/tests/test_task_lifecycle_cli.py` with black-box pause/resume cases covering active-to-hold, hold-to-active, invalid-state rejection, blocked resume, and structured JSON envelopes.  
        [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: tools/orchestration/tests/test_task_lifecycle_cli.py]
  - [x] Extend `tools/orchestration/tests/test_inspect_context_cli.py` or a narrowly scoped adjacent module with human-readable rendering regressions for narrow widths, reduced-color output, and stable pause-related inspect context.  
        [Source: _bmad-output/project-context.md#testing-rules] [Source: tools/orchestration/tests/test_inspect_context_cli.py]
  - [x] Keep `--json` output assertions presentation-independent so terminal width and color settings never change machine-readable structure.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output]
  - [x] Update `README.md` and `docs/getting-started.md` so the documented `task pause` and `task resume` examples match real behavior and explain the reduced-color or narrow-layout expectations for operators working in low-fidelity terminals.  
        [Source: README.md] [Source: docs/getting-started.md] [Source: _bmad-output/project-context.md#code-quality--style-rules]

## Dev Notes

### Story Intent

Story 4.4 is the intervention and accessibility completion slice for Sprint 6. Story 4.2 already established the canonical `macs task` family and left pause or resume as deferred placeholders; Story 4.3 already established controller-truth-first inspect surfaces and pane navigation. Story 4.4 should make pause or resume real from that same controller-owned surface while ensuring the operator experience stays readable in narrow and reduced-color terminals.  
[Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-6-controller-first-operator-surface-on-the-frozen-cli-contract] [Source: _bmad-output/implementation-artifacts/stories/4-2-assign-and-manage-task-lifecycle-actions-from-one-command-path.md] [Source: _bmad-output/implementation-artifacts/stories/4-3-inspect-degraded-evidence-and-open-the-right-worker-pane-from-context.md]

### Previous Story Intelligence

- Story 4.2 intentionally exposed `pause`, `resume`, `reroute`, and `abort` in the task-family parser before all of those semantics existed. For Story 4.4, replace only the pause and resume placeholder path. Keep reroute and abort on their later story boundaries unless a minimal shared helper change is unavoidable.  
  [Source: _bmad-output/implementation-artifacts/stories/4-2-assign-and-manage-task-lifecycle-actions-from-one-command-path.md] [Source: tools/orchestration/cli/main.py]
- Story 4.3 already froze the `task inspect` and `worker inspect` JSON envelope shape and introduced controller-truth-first human-readable inspectors plus `--open-pane`. Story 4.4 should extend those same emitters instead of inventing a second inspector or a full-screen TUI.  
  [Source: _bmad-output/implementation-artifacts/stories/4-3-inspect-degraded-evidence-and-open-the-right-worker-pane-from-context.md] [Source: tools/orchestration/cli/main.py]
- Story 4.3 also reaffirmed that tmux is the live execution substrate rather than the primary semantic control interface. Pause must stay a controller command first, with any runtime interruption evidence presented as supporting detail rather than source-of-truth state.  
  [Source: _bmad-output/implementation-artifacts/stories/4-3-inspect-degraded-evidence-and-open-the-right-worker-pane-from-context.md] [Source: _bmad-output/planning-artifacts/architecture.md#surface-model]

### Current Repo Context

- `tools/orchestration/cli/main.py` already parses `task pause`, `task resume`, `task reroute`, and `task abort`, and currently routes those verbs through the deferred intervention path introduced by Story 4.2.  
  [Source: tools/orchestration/cli/main.py]
- `tools/orchestration/tasks.py` already owns create, assign, inspect, close, and archive lifecycle helpers, so pause/resume should join that same controller-owned task layer rather than open-coding SQLite changes in CLI handlers.  
  [Source: tools/orchestration/tasks.py]
- `tools/orchestration/state_machine.py` and `tools/orchestration/recovery.py` already recognize `intervention_hold`, `paused`, and paused live-lease handling, which means the repo has the canonical state vocabulary needed for this story without inventing new states.  
  [Source: tools/orchestration/state_machine.py] [Source: tools/orchestration/recovery.py]
- `README.md` and `docs/getting-started.md` already show `macs task pause` and `macs task resume` examples on the operator surface, so documentation currently leads behavior. Story 4.4 should close that gap instead of changing the documented command family.  
  [Source: README.md] [Source: docs/getting-started.md]
- Current human-readable inspect rendering is concentrated in `emit_worker_inspect_human_readable()` and `emit_task_inspect_human_readable()` inside `tools/orchestration/cli/main.py`, making that file the most likely first seam for a shared narrow or reduced-color rendering helper.  
  [Source: tools/orchestration/cli/main.py]

### Technical Requirements

- Use canonical controller state vocabularies exactly:
  - `task pause`: `active` -> `intervention_hold`
  - `lease pause`: `active` -> `paused`
  - `task resume`: `intervention_hold` -> `active`
  - `lease resume`: `paused` -> `active`  
  [Source: _bmad-output/planning-artifacts/architecture.md#task-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#canonical-state-vocabularies]
- Keep `task pause` and `task resume` under the singular canonical family name `macs task`; do not introduce alternate documented verbs or plural family names.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families]
- Keep current ownership and lock protection intact during an operator-held pause. The paused lease remains live and should continue to block conflicting replacement until a later revoke, reroute, or recovery path explicitly supersedes it.  
  [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/prd.md#orchestration-control--task-lifecycle]
- Keep human-readable output compact and copy-paste durable, and keep `--json` payloads stable and presentation-independent.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output]
- Accessibility support applies to the human-readable surface, not the canonical nouns or controller semantics. Reduced-color and narrow layouts must not create a second operator vocabulary.  
  [Source: _bmad-output/planning-artifacts/ux-design-specification.md#customization-strategy] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#accessibility-considerations]
- Stay within Python 3.8+ stdlib, SQLite, tmux-backed orchestration, and repo-local docs conventions.  
  [Source: _bmad-output/project-context.md#technology-stack--versions]

### Architecture Compliance

- Controller authority first: pause and resume mutate authoritative `task`, `lease`, `lock`, and `event` state in controller-owned code only. Adapter or tmux observations may corroborate intervention behavior, but they do not become authority.  
  [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: _bmad-output/project-context.md#framework-specific-rules]
- Preserve the write model discipline already used for controller actions: validate current state, apply canonical mutations transactionally, record events, then surface any runtime-side uncertainty as evidence or warnings rather than hidden state.  
  [Source: _bmad-output/planning-artifacts/architecture.md#write-model] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules]
- Preserve zero-or-one live lease semantics. Pausing should not create a second lease, and resuming should reactivate the same paused lease rather than minting a successor lease.  
  [Source: _bmad-output/planning-artifacts/prd.md#orchestration-control--task-lifecycle] [Source: tools/orchestration/invariants.py]
- Keep event history durable and inspectable. Intervention rationale and follow-up actions must remain visible through task, lease, and event inspection flows.  
  [Source: _bmad-output/planning-artifacts/prd.md#auditability-governance-and-operator-trust] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#maintainer-intervenes-in-a-degraded-session]
- Preserve the hybrid CLI plus tmux surface model. Pause must stay available from the controller surface, with pane access and runtime evidence still reachable but secondary.  
  [Source: _bmad-output/planning-artifacts/architecture.md#surface-model] [Source: _bmad-output/planning-artifacts/prd.md#control-surface-and-product-interface]

### Library / Framework Requirements

- Python implementation remains stdlib-only; do not add third-party terminal UI or color libraries for this story.  
  [Source: _bmad-output/project-context.md#technology-stack--versions]
- Reuse current SQLite-backed orchestration helpers and tmux-bridge compatibility seams instead of introducing a second state or rendering subsystem.  
  [Source: _bmad-output/project-context.md#critical-dont-miss-rules] [Source: _bmad-output/planning-artifacts/architecture.md#compatibility-plan]

### File Structure Requirements

- Extend `tools/orchestration/cli/main.py` for real `task pause` and `task resume` handling, pause-aware inspection output, and shared human-readable rendering hooks.
- Extend `tools/orchestration/tasks.py` for controller-owned pause and resume helpers plus pause-aware inspect context.
- Reuse and, if needed, narrowly extend `tools/orchestration/invariants.py` and `tools/orchestration/state_machine.py` for authoritative pause/resume validation.
- Touch `tools/orchestration/history.py` only if lease or event inspection needs a small helper for pause basis or intervention event summaries.
- If a rendering extraction is needed, prefer a narrow helper under `tools/orchestration/cli/` such as `rendering.py` or `formatters.py` rather than a broad CLI reorganization.  
  [Inference from: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape and tools/orchestration/cli/main.py]
- Extend `tools/orchestration/tests/test_task_lifecycle_cli.py` and `tools/orchestration/tests/test_inspect_context_cli.py` before creating additional large test files.
- Update `README.md` and `docs/getting-started.md` for operator-facing pause/resume and accessibility behavior.

[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]  
[Source: _bmad-output/project-context.md#development-workflow-rules]

### Testing Requirements

- Use `python3 -m unittest discover -s tools/orchestration/tests` as the primary validation surface.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Add black-box CLI tests for:
  - `task pause --task <id> --json`
  - `task resume --task <id> --json`
  - pause or resume human-readable output in narrow-width mode
  - reduced-color or no-color human-readable output with textual severity markers  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#accessibility-considerations]
- Cover invalid or unsafe paths: pausing a non-active task, resuming without a paused live lease, blocked resume because recovery or evidence state is unsafe, and warning-bearing runtime intervention uncertainty.  
  [Source: _bmad-output/planning-artifacts/architecture.md#failure-containment-model] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules]
- Assert that pause keeps current ownership and lock protection visible through `task inspect`, `lease inspect`, `lock inspect` or `lock list`, and recent events.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content]
- Preserve Story 4.3 regressions for `task inspect --open-pane` and `worker inspect --open-pane`; accessibility changes must not break inspect context or JSON envelope shape.  
  [Source: _bmad-output/implementation-artifacts/stories/4-3-inspect-degraded-evidence-and-open-the-right-worker-pane-from-context.md] [Source: tools/orchestration/tests/test_inspect_context_cli.py]
- If pause or resume touches tmux-bridge side effects or target handling, add or adjust adjacent integration-style shell coverage without contaminating the user's live tmux environment.  
  [Source: _bmad-output/project-context.md#testing-rules] [Source: tools/tmux_bridge/tests/smoke.sh]

### Implementation Guardrails

- Do not introduce new authoritative state names such as `held` or `stopped`; use the frozen `intervention_hold` and `paused` vocabularies.
- Do not silently downgrade pause back into a no-op placeholder. If runtime-level interruption is incomplete, say so explicitly and keep controller state authoritative.
- Do not release locks or clear current ownership on pause unless a different recovery or revoke flow explicitly owns that behavior.
- Do not broaden this story into reroute, reconciliation, or abort semantics beyond the minimum guardrail interactions needed for resume safety.
- Do not make color the only state signal, and do not let narrow layouts change meaning or hide critical warnings.
- Do not introduce a full-screen terminal UI or third-party rendering framework for this increment.

### Project Structure Notes

- This repo remains a brownfield, shell-first orchestration codebase. The control-plane path lives under `tools/orchestration/`; tmux remains the execution substrate and compatibility layer.
- Story 4.4 should feel like a direct extension of the already-landed Sprint 6 surfaces: Story 4.2 task-family actions and Story 4.3 inspect/open-pane flows should remain recognizable after the change.
- Accessibility work should centralize layout or color decisions enough to avoid duplication, but it should stay incremental and local to the current CLI surfaces.

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
- `_bmad-output/implementation-artifacts/stories/4-3-inspect-degraded-evidence-and-open-the-right-worker-pane-from-context.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/invariants.py`
- `tools/orchestration/state_machine.py`
- `tools/orchestration/recovery.py`
- `tools/orchestration/history.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/tmux_bridge/tests/smoke.sh`
- `README.md`
- `docs/getting-started.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Replace the Story 4.2 placeholder path for `task pause` and `task resume` with real controller-owned lifecycle helpers first, keeping state-machine and invariant enforcement central.
- Extend existing inspect and task-action renderers next so pause state, next actions, and warnings stay visible in the same controller context across wide, narrow, standard-color, and reduced-color terminals.
- Finish with focused black-box CLI regressions and docs parity, then run the full orchestration unittest suite and any adjacent tmux smoke coverage touched by the change.

### Debug Log References

- Skill used: `bmad-create-story`
- Inputs loaded from the requested planning artifacts, project context, current Sprint 6 story artifacts for 4.2 and 4.3, and the current repo command/docs seams for pause/resume and inspect rendering.
- `2026-04-10T10:05:08+01:00` Story 4.4 context finalized against the current brownfield workspace baseline and prepared for implementation.
- `2026-04-10T11:03:00+01:00` Story 4.4 moved to `in-progress`; implementation proceeded in four red-green slices aligned to lifecycle actions, paused inspect surfaces, terminal rendering, and docs/tests.
- `2026-04-10T11:26:00+01:00` Validation completed with `python3 -m unittest discover -s tools/orchestration/tests` (64 tests, passing). No repo-configured Python lint or static-analysis config was present.
- `2026-04-10T11:44:00+01:00` QA acceptance review found and fixed two contract gaps: resume now fails closed on degraded or recovery-blocked ownership, and pause/resume or paused-inspect human-readable output now reports event IDs, controller-state changes, and next actions. Full validation reran successfully with 68 passing orchestration tests.

### Completion Notes List

- Implemented controller-owned `task pause` and `task resume` helpers that reuse the authoritative task and lease transition seams, keep the same live lease and owner in place, preserve active locks, and emit durable `task.*` plus `lease.*` intervention events.
- Replaced the CLI placeholder path for `task pause` and `task resume` with real action handlers, controller-only runtime pause-depth warnings, pause-aware `task inspect` output, and richer human-readable `lease inspect` output.
- Added small shared helpers under `tools/orchestration/cli/rendering.py` and `tools/orchestration/interventions.py` so narrow-width and reduced-color rendering stays localized to the Story 4.4 surfaces while `--json` remains unchanged.
- Extended black-box regressions for pause/resume JSON contracts, paused inspect context, and `NO_COLOR` plus narrow-width human-readable rendering; then reran the full orchestration unittest discovery suite successfully.
- QA acceptance confirmed Story 4.4 against the authoritative story text after fixing the missing next-action or event metadata in human-readable output and the missing fail-closed resume guard for degraded or recovery-blocked conditions.

### File List

- `_bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `README.md`
- `docs/getting-started.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/cli/rendering.py`
- `tools/orchestration/interventions.py`
- `tools/orchestration/invariants.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`

### Change Log

- `2026-04-10`: Implemented controller-owned pause or resume lifecycle actions, pause-aware inspect output, narrow or no-color human-readable rendering, updated operator docs, fixed QA review gaps in resume safety and action summaries, and passed the full orchestration regression suite.
