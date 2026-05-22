# Story 4.3: Inspect degraded evidence and open the right worker pane from context

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want to move from a task or worker record to the relevant evidence and pane,
so that I can investigate live behavior without losing the controller's state context.

## Acceptance Criteria

1. `macs worker inspect` and `macs task inspect` become the primary degraded-session investigation surfaces. When a worker is `degraded`, `unavailable`, or `quarantined`, or when a task is in `intervention_hold` or `reconciliation` or is currently attached to such a worker, the inspect surface shows controller truth first: canonical state, routability or risk, current owner and lease, lock summary, recent event references, and pane target.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-43-inspect-degraded-evidence-and-open-the-right-worker-pane-from-context] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/planning-artifacts/architecture.md#ux-backing-requirements] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#maintainer-intervenes-in-a-degraded-session]
2. The same inspect flow exposes evidence as distinct layers. Controller-authored facts stay separate from adapter-derived evidence, and adapter evidence preserves the common envelope plus explicit `kind` separation so `fact`, `signal`, and `claim` remain distinguishable and untrusted claims never appear as controller truth. Human-readable output renders degraded or missing evidence inline, and `--json` responses for these two inspect surfaces move to the frozen envelope with explicit `timestamp`, `warnings`, `errors`, and evidence-bearing object payloads.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-43-inspect-degraded-evidence-and-open-the-right-worker-pane-from-context] [Source: _bmad-output/planning-artifacts/architecture.md#evidence-envelope] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#evidence-json]
3. From that same task or worker context, the operator can invoke a controller-owned pane navigation path without manual tmux target hunting. Recommended brownfield fit for this repo: add an optional `--open-pane` path to `worker inspect` and `task inspect`, reuse the existing `.codex/target-pane.txt` compatibility mechanism, and perform a best-effort tmux jump only when MACS is running inside a compatible tmux client. If a direct jump cannot be completed, MACS still pins the pane target and returns an explicit warning plus the exact target instead of silently failing.  
   [Inference from: _bmad-output/planning-artifacts/epics.md#story-43-inspect-degraded-evidence-and-open-the-right-worker-pane-from-context, _bmad-output/planning-artifacts/operator-cli-contract.md#command-families, _bmad-output/planning-artifacts/ux-design-specification.md#button-hierarchy, _bmad-output/planning-artifacts/ux-design-specification.md#additional-patterns, and _bmad-output/planning-artifacts/ux-design-specification.md#tmux-workspace-model]
4. The degraded-evidence and pane-open flow preserves the Phase 1 control-plane contract: selectors remain canonical `--worker` and `--task`; normal inspect without `--open-pane` stays read-only; warnings state what is uncertain and what the operator can do next; raw tmux remains the execution substrate rather than the semantic control path.  
   [Source: _bmad-output/planning-artifacts/prd.md#control-surface-and-product-interface] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#human-readable-status-conventions] [Source: _bmad-output/planning-artifacts/architecture.md#surface-model]
5. Regression coverage and operator docs ship with the change, proving degraded worker inspection, task-linked degraded evidence, explicit claim rendering, pane-target pinning and open fallback behavior, and no regression to existing task, lease, lock, event, adapter-probe, or tmux bridge flows.  
   [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-6-controller-first-operator-surface-on-the-frozen-cli-contract] [Source: README.md] [Source: docs/getting-started.md]

## Tasks / Subtasks

- [x] Build reusable worker and task inspection context helpers that expose degraded-session truth without forcing the operator to mentally join multiple commands. (AC: 1, 2, 4)
  - [x] Extend `tools/orchestration/workers.py` to return richer worker inspection context: routability, freshness, interruptibility, current lease count or linked active task summary, pane target metadata, and recent controller evidence references instead of only the raw worker row.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#recommended-default-views]
  - [x] Extend `tools/orchestration/tasks.py` and `tools/orchestration/history.py` so task inspection can show current owner, current lease detail, lock summary, recent events, routing rationale summary, and linked worker risk context from one controller read path.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/planning-artifacts/architecture.md#ux-backing-requirements] [Source: _bmad-output/implementation-artifacts/stories/4-1-provide-compact-list-and-inspect-commands-for-control-plane-objects.md]
  - [x] If `tools/orchestration/cli/main.py` starts accumulating too much evidence-formatting logic, extract a narrow helper such as `tools/orchestration/inspectors.py` or `tools/orchestration/cli/inspectors.py` rather than open-coding more controller reads in the CLI entrypoint.  
        [Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape] [Source: _bmad-output/project-context.md#critical-implementation-rules]

- [x] Reuse adapter probe evidence and render layered degraded evidence without inventing a second evidence schema. (AC: 2, 4)
  - [x] Reuse `get_adapter(...).probe(worker)` and the existing evidence envelope from `tools/orchestration/adapters/base.py` and adapter-specific probe overrides. Group controller facts separately from adapter evidence, and preserve adapter `kind` values so `fact`, `signal`, and `claim` remain inspectable as different trust levels.  
        [Source: _bmad-output/planning-artifacts/architecture.md#evidence-envelope] [Source: tools/orchestration/adapters/base.py] [Source: tools/orchestration/adapters/codex.py]
  - [x] Keep Codex-style runtime self-report surfaces such as `permission_surface` visible as claims or low-confidence evidence, never as controller truth or routing authority.  
        [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: tools/orchestration/adapters/codex.py] [Source: tools/orchestration/tests/test_setup_init.py]
  - [x] Add a narrow last-known-evidence fallback using `evidence_records` only if live probe or capture is unavailable during degraded inspection. Do not turn Story 4.3 into a broad evidence-ingestion rewrite; the goal is reliable inspectability, not a second audit system.  
        [Source: _bmad-output/planning-artifacts/architecture.md#persistence-strategy] [Source: tools/orchestration/store.py]

- [x] Add controller-owned pane navigation from inspect context while preserving brownfield tmux bridge compatibility. (AC: 3, 4)
  - [x] Add optional `--open-pane` handling to `macs worker inspect` and `macs task inspect`, resolving the target worker directly from the worker record or indirectly from the task's current owner.  
        [Inference from: _bmad-output/planning-artifacts/operator-cli-contract.md#minimum-required-flags and _bmad-output/planning-artifacts/ux-design-specification.md#effortless-interactions]
  - [x] Reuse the existing pane-target compatibility path by driving `tools/tmux_bridge/set_target.sh` or an equivalently thin wrapper around the same `.codex/target-pane.txt` semantics. Do not create a parallel target-state file or bypass the current fallback behavior.  
        [Source: _bmad-output/planning-artifacts/architecture.md#compatibility-plan] [Source: tools/tmux_bridge/set_target.sh] [Source: tools/tmux_bridge/common.sh] [Source: docs/getting-started.md]
  - [x] Implement best-effort tmux jumping only when the current invocation can safely address the same tmux server. If a live jump is impossible, return a warning with `tmux_session`, `tmux_pane`, and pinned-target confirmation rather than pretending the pane was opened.  
        [Source: _bmad-output/planning-artifacts/ux-design-specification.md#tmux-workspace-model] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#human-readable-status-conventions]

- [x] Bring `worker inspect` and `task inspect` output into line with the frozen Phase 1 inspect contract for this story's surfaces. (AC: 1, 2, 4)
  - [x] Update human-readable `worker inspect` output to show controller truth first, then degraded warnings, then evidence basis and pane target.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content]
  - [x] Update human-readable `task inspect` output to show summary, state, current owner, current lease, lock summary, recent events, routing rationale summary, linked evidence summary, and pane target or open result.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#maintainer-intervenes-in-a-degraded-session]
  - [x] Move the JSON responses for these two inspect commands to the frozen top-level envelope with `ok`, `command`, `timestamp`, `warnings`, `errors`, and a command-specific object payload. Keep keys snake_case and canonical nouns.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#json-rules]

- [x] Add regression coverage and documentation for degraded evidence inspection and pane opening. (AC: 5)
  - [x] Prefer a focused new CLI regression module such as `tools/orchestration/tests/test_inspect_context_cli.py` instead of continuing to grow `tools/orchestration/tests/test_setup_init.py` indefinitely. Reuse existing tmux fixture patterns and adapter-probe assertions where possible.  
        [Source: _bmad-output/project-context.md#testing-rules] [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/tests/test_task_lifecycle_cli.py]
  - [x] Cover degraded-worker inspection, task inspection linked to a degraded current worker, explicit claim rendering, stale or unavailable probe fallback, and `--open-pane` behavior against isolated tmux sockets.  
        [Source: _bmad-output/planning-artifacts/architecture.md#integration-tests] [Source: _bmad-output/planning-artifacts/architecture.md#failure-drill-tests]
  - [x] Avoid brittle headless assertions that require a human tmux client focus change. It is sufficient to verify target pinning plus reported `opened` versus `pinned_only` status unless the test explicitly attaches a tmux client under isolation.  
        [Inference from: _bmad-output/project-context.md#testing-rules and tools/tmux_bridge/tests/smoke.sh]
  - [x] Update `README.md` and `docs/getting-started.md` with the degraded-inspection flow, `--open-pane` behavior, and the relationship between controller-owned pane opening and the existing `tmux-bridge.sh set_target` helper.  
        [Source: README.md] [Source: docs/getting-started.md]

## Dev Notes

### Story Intent

Story 4.3 is the missing investigation loop between Story 5.1 and the Sprint 6 controller surface. Story 5.1 already classifies degraded workers, Story 4.1 already established controller-side inspection seams, and Story 4.2 already made lifecycle actions real. Story 4.3 should let the operator move from a degraded worker or task to the evidence and live pane without abandoning controller context or manually hunting for tmux targets.  
[Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-5-recovery-engine-before-controller-surface-expansion] [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-6-controller-first-operator-surface-on-the-frozen-cli-contract] [Source: _bmad-output/implementation-artifacts/stories/5-1-classify-worker-health-and-surface-warnings-promptly.md] [Source: _bmad-output/implementation-artifacts/stories/4-1-provide-compact-list-and-inspect-commands-for-control-plane-objects.md] [Source: _bmad-output/implementation-artifacts/stories/4-2-assign-and-manage-task-lifecycle-actions-from-one-command-path.md]

### Previous Story Intelligence

- Story 4.1 added compact read-side surfaces for tasks, locks, leases, events, and overview summaries. Story 4.3 should extend those seams rather than inventing another inspection subsystem.
- Story 4.2 already concentrated recent CLI work in `tools/orchestration/cli/main.py`, `tools/orchestration/tasks.py`, and `tools/orchestration/tests/test_task_lifecycle_cli.py`; Story 4.3 should remain an incremental extension of that shape.
- Story 5.1 already classifies stale or degraded workers under controller authority and automatically excludes them from new routing. Story 4.3 should reuse that classification directly instead of re-deriving degradation from raw pane output.

[Source: _bmad-output/implementation-artifacts/stories/4-1-provide-compact-list-and-inspect-commands-for-control-plane-objects.md#completion-notes-list]  
[Source: _bmad-output/implementation-artifacts/stories/4-2-assign-and-manage-task-lifecycle-actions-from-one-command-path.md#previous-story-intelligence]  
[Source: _bmad-output/implementation-artifacts/stories/5-1-classify-worker-health-and-surface-warnings-promptly.md#completion-notes-list]

### Brownfield Baseline

- `tools/orchestration/cli/main.py` currently keeps `worker inspect` and `task inspect` minimal. They print core IDs and states, but they do not yet surface evidence layers, lock summary, recent events, routability, or warnings inline.  
  [Source: tools/orchestration/cli/main.py]
- `tools/orchestration/tasks.py::inspect_task()` currently returns the task row plus the latest routing decision, but not current lease detail, lock summary, recent events, or linked worker evidence.  
  [Source: tools/orchestration/tasks.py]
- `tools/orchestration/workers.py::inspect_worker()` currently returns only the worker row, not current task linkage, current lease count, adapter support depth, or evidence basis.  
  [Source: tools/orchestration/workers.py]
- `adapter probe --worker` already emits normalized evidence envelopes, including Codex-specific `permission_surface` claims, but those evidence results are isolated from worker and task inspectors today.  
  [Source: tools/orchestration/adapters/base.py] [Source: tools/orchestration/adapters/codex.py] [Source: tools/orchestration/tests/test_setup_init.py]
- The repo already has a pane-target compatibility mechanism in `tools/tmux_bridge/set_target.sh` and `.codex/target-pane.txt`, and the docs still teach it as a manual workflow. There is no controller-owned inspect-to-pane flow yet.  
  [Source: tools/tmux_bridge/set_target.sh] [Source: tools/tmux_bridge/common.sh] [Source: README.md] [Source: docs/getting-started.md]
- `evidence_records` already exists in the SQLite schema but is not yet populated by the current inspection paths. If Story 4.3 needs a last-known evidence fallback, keep the change tightly scoped to inspection.  
  [Source: tools/orchestration/store.py]

### Technical Requirements

- Keep the frozen command families intact. For this repo, the safest contract fit is to extend `worker inspect` and `task inspect` with an optional `--open-pane` path rather than inventing a new primary verb outside the frozen Phase 1 family table.  
  [Inference from: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families and _bmad-output/planning-artifacts/operator-cli-contract.md#minimum-required-flags]
- Keep controller truth authoritative. Degraded status, current owner, lease state, lock state, and routing rationale come from controller records first; adapter evidence augments that truth but must not replace it.  
  [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: _bmad-output/planning-artifacts/prd.md#security--governance]
- Build pane target data from existing worker fields: `tmux_socket`, `tmux_session`, and `tmux_pane`. Preserve compatibility with repo-local `.codex/target-pane.txt` state.  
  [Source: tools/orchestration/workers.py] [Source: tools/tmux_bridge/common.sh]
- Preserve the adapter evidence envelope exactly enough that `kind`, `name`, `value`, `freshness_seconds`, `confidence`, and `source_ref` remain visible in `--json` output and easy to summarize in human-readable output.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#evidence-json] [Source: tools/orchestration/adapters/base.py]
- Keep JSON keys snake_case, use canonical nouns, and include `warnings` whenever evidence is stale, missing, degraded, or only pinned rather than actively opened.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#json-rules] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#human-readable-status-conventions]
- Stay in Python 3.8+ stdlib plus SQLite. If you invoke shell helpers, use subprocess argument lists rather than shell strings.  
  [Source: _bmad-output/project-context.md#technology-stack--versions] [Source: _bmad-output/project-context.md#language-specific-rules]

### Architecture Compliance

- CLI commands and inspector views remain the canonical authority surface; tmux panes are live execution contexts reachable from those views, not the source of truth.  
  [Source: _bmad-output/planning-artifacts/architecture.md#surface-model]
- Reuse `tools/tmux_bridge/` for low-level pane operations and compatibility behavior. Do not move orchestration authority into the shell helpers.  
  [Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape] [Source: _bmad-output/project-context.md#critical-implementation-rules]
- If live probe or pane-open operations fail, fail visibly and preserve safe controller semantics. Surface explicit warnings or structured errors; do not silently claim the pane opened or evidence was refreshed when it was not.  
  [Source: _bmad-output/planning-artifacts/architecture.md#write-model] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#structured-error-codes]
- Keep the evidence stack explainable: controller facts first, then adapter evidence with explicit uncertainty markers, then claims that remain visibly untrusted.  
  [Source: _bmad-output/planning-artifacts/architecture.md#evidence-envelope] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#experience-principles]
- Preserve audit and history inspection surfaces already established in Story 4.1 and Story 6.1; Story 4.3 should compose them, not bypass them with raw pane capture as the only answer.  
  [Source: _bmad-output/planning-artifacts/prd.md#observability--auditability] [Source: _bmad-output/implementation-artifacts/stories/4-1-provide-compact-list-and-inspect-commands-for-control-plane-objects.md] [Source: _bmad-output/implementation-artifacts/stories/6-1-persist-a-durable-event-trail-and-history-inspectors.md]

### File Structure Requirements

- Extend `tools/orchestration/cli/main.py` for richer inspect output, optional `--open-pane`, frozen inspect JSON envelopes, and warning rendering for degraded evidence or pin-only fallbacks.
- Extend `tools/orchestration/workers.py` for worker inspect context, routability, related task or lease metadata, and pane target resolution.
- Extend `tools/orchestration/tasks.py` and `tools/orchestration/history.py` for task inspect context, recent event summaries, linked lease detail, and lock summaries.
- Reuse `tools/orchestration/adapters/base.py` and concrete adapter `probe()` behavior rather than creating a second evidence schema.
- Touch `tools/orchestration/store.py` only if a narrow `evidence_records` fallback is required for last-known degraded evidence.
- Reuse `tools/tmux_bridge/set_target.sh` and current target-pane conventions rather than creating new shell state or duplicate pane-target logic.
- Prefer a focused new CLI regression module under `tools/orchestration/tests/`.
- Update `README.md` and `docs/getting-started.md` for the new inspect-to-pane behavior.

[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]  
[Source: _bmad-output/project-context.md#development-workflow-rules]

### Testing Requirements

- Use `python3 -m unittest discover -s tools/orchestration/tests` as the primary validation surface.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Add black-box CLI coverage for `worker inspect` and `task inspect` in both human-readable and `--json` modes, including degraded warnings, evidence layering, and pane target rendering.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output]
- Use isolated tmux sockets for live probe and pane-target cases. Keep controller-facts-only or stale-fallback cases SQLite-only where possible.  
  [Source: _bmad-output/planning-artifacts/architecture.md#integration-tests] [Source: _bmad-output/project-context.md#testing-rules]
- Assert that Codex `permission_surface` and similar runtime self-reports remain claims or low-confidence evidence in inspect output.  
  [Source: tools/orchestration/adapters/codex.py] [Source: tools/orchestration/tests/test_setup_init.py]
- Assert that `--open-pane` pins the expected target and reports whether the pane was actually opened or only pinned. Avoid brittle headless focus assertions unless the test explicitly attaches a tmux client.  
  [Inference from: tools/tmux_bridge/tests/smoke.sh and _bmad-output/project-context.md#testing-rules]
- Preserve existing Story 4.1 inspection behavior, Story 5.1 degradation behavior, Story 4.2 task lifecycle flows, and adapter-probe regressions while adding the new context inspection path.  
  [Source: _bmad-output/implementation-artifacts/stories/4-1-provide-compact-list-and-inspect-commands-for-control-plane-objects.md] [Source: _bmad-output/implementation-artifacts/stories/4-2-assign-and-manage-task-lifecycle-actions-from-one-command-path.md] [Source: _bmad-output/implementation-artifacts/stories/5-1-classify-worker-health-and-surface-warnings-promptly.md]

### Git Intelligence Summary

Recent committed and in-workspace changes already concentrate in the exact seams Story 4.3 should extend:

- `c3ccc6a` focused on `tools/orchestration/tasks.py`, `health.py`, `recovery.py`, `routing.py`, and `tools/orchestration/tests/test_setup_init.py`.
- The current workspace also carries uncommitted Story 4.2 CLI and task-family changes in `tools/orchestration/cli/main.py`, `tools/orchestration/tasks.py`, and `tools/orchestration/tests/test_task_lifecycle_cli.py`.
- Story 4.3 should therefore stay focused on read-side inspection context, evidence presentation, and pane navigation rather than reopening bootstrap, adapter registration, or broad routing work.

[Source: git log --oneline -5]  
[Source: git show --stat -1 c3ccc6a]  
[Source: git diff -- tools/orchestration/cli/main.py tools/orchestration/tasks.py tools/orchestration/health.py]

### Implementation Guardrails

- Do not create a second non-canonical pane target file or bypass `.codex/target-pane.txt` compatibility.
- Do not flatten controller facts, adapter signals, and untrusted claims into one undifferentiated status blob.
- Do not require raw `tmux capture-pane` output to answer canonical worker or task questions.
- Do not let `worker inspect` or `task inspect` mutate task, lease, lock, or routing authority when `--open-pane` is not requested.
- Do not broaden this story into pause, reroute, reconcile, or recovery semantics; those belong to Stories 4.4 and 5.2 through 5.4.
- Do not add third-party Python dependencies, ORMs, or hosted UI surfaces.

### Project Structure Notes

- This repo remains a brownfield, shell-first control plane layered on tmux. `tools/orchestration/` owns controller truth; `tools/tmux_bridge/` remains the transport and compatibility layer.
- Existing docs still teach manual pane pinning with `tmux-bridge.sh set_target`; Story 4.3 should layer controller-first pane opening above that flow instead of removing the manual escape hatch.
- The current operator experience should keep one controller pane as the source of operational truth for a multi-pane session, with direct but governed access to the linked worker pane when live context is needed.

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
- `_bmad-output/implementation-artifacts/stories/4-2-assign-and-manage-task-lifecycle-actions-from-one-command-path.md`
- `_bmad-output/implementation-artifacts/stories/5-1-classify-worker-health-and-surface-warnings-promptly.md`
- `_bmad-output/implementation-artifacts/stories/6-1-persist-a-durable-event-trail-and-history-inspectors.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/workers.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/history.py`
- `tools/orchestration/overview.py`
- `tools/orchestration/health.py`
- `tools/orchestration/routing.py`
- `tools/orchestration/store.py`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/adapters/codex.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/tmux_bridge/common.sh`
- `tools/tmux_bridge/set_target.sh`
- `tools/tmux_bridge/tests/smoke.sh`
- `README.md`
- `docs/getting-started.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Build reusable inspection-context helpers first so worker and task views share one controller-truth assembly path.
- Add layered adapter evidence and optional pane-opening support on top of that shared inspect context while preserving the frozen command families.
- Land focused CLI regressions and docs updates, then run the full orchestration unittest suite.

### Debug Log References

- Skill used: `bmad-create-story`
- Inputs loaded from the requested planning artifacts, project context, current Story 4.2 artifact, current workspace code, recent git history, and existing tmux bridge docs/helpers.
- `2026-04-10T09:01:04+01:00` Story 4.3 context finalized against the current brownfield workspace baseline and prepared for implementation.
- `2026-04-10T09:10:26+01:00` `bmad-dev-story` execution started. Story status moved to `in-progress`; first red slice targets `macs worker inspect` degraded-context coverage before broader task and pane-navigation work.
- `2026-04-10T09:17:56+01:00` First red-green slice completed for `macs worker inspect --worker <id> --json`: added a focused black-box regression in `tools/orchestration/tests/test_inspect_context_cli.py`, implemented the frozen JSON envelope plus degraded controller-truth pane-target context, and reran `python3 -m unittest tools.orchestration.tests.test_inspect_context_cli` with `OK`.
- `2026-04-10T09:24:46+01:00` Second red-green slice completed for `macs task inspect --task <id> --json`: added a black-box degraded-owner regression, implemented the frozen task inspect envelope plus controller-truth owner, lease, recent event, and pane-target context, and reran `python3 -m unittest tools.orchestration.tests.test_inspect_context_cli` with `OK`.
- `2026-04-10T09:28:34+01:00` Third red-green slice completed for `macs task inspect --task <id> --json`: extended task controller truth with `routing_rationale_summary` and `lock_summary`, kept the change inside the existing inspect helper seams, and reran `python3 -m unittest tools.orchestration.tests.test_inspect_context_cli` with `OK`.
- `2026-04-10T09:32:11+01:00` Fourth red-green slice completed for human-readable `macs worker inspect` and `macs task inspect`: added black-box regressions for controller-truth-first rendering plus separate adapter evidence sections, implemented the minimal CLI inspect rendering, and reran `python3 -m unittest tools.orchestration.tests.test_inspect_context_cli` with `OK`.
- `2026-04-10T09:28:16+01:00` Third and fourth red-green slices completed in the same focused module: `task inspect --json` now surfaces controller-side routing rationale and lock summary, and keeps adapter-derived task evidence separate from controller truth. `python3 -m unittest tools.orchestration.tests.test_inspect_context_cli` reran with `OK` after each minimal implementation step.
- `2026-04-10T09:59:41+01:00` Final red-green slice completed for inspect-driven pane opening: added focused `--open-pane` regressions for worker and task inspect, reused `tools/tmux_bridge/set_target.sh` with repo-local `.codex/target-pane.txt` pinning, implemented `opened` versus `pinned_only` reporting plus explicit pin-only warnings, and reran `python3 -m unittest tools.orchestration.tests.test_inspect_context_cli` with `OK`.
- `2026-04-10T10:03:52+01:00` Story verification completed: updated older inspect callers to the frozen Story 4.3 inspect envelope, reran `python3 -m unittest discover -s tools/orchestration/tests` with `OK`, reran `./tools/tmux_bridge/tests/smoke.sh` with `OK`, and marked Story 4.3 `done`.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story 4.3 is scoped against the repo's current reality: degraded worker classification exists, adapter probe evidence exists separately, and pane target pinning still lives only in the tmux bridge helper path.
- The recommended `--open-pane` shape is an implementation inference chosen to preserve the frozen Phase 1 command families while still providing a controller-owned pane jump from inspect context.
- Landed the first implementation slice only: `worker inspect --json` now emits the frozen top-level envelope and surfaces degraded controller-truth context with pane target metadata for a degraded worker.
- Landed the second implementation slice only: `task inspect --json` now emits the frozen top-level envelope and surfaces degraded-owner controller-truth context with current lease, recent task event refs, and pane target metadata.
- Landed the third implementation slice only: `task inspect --json` now adds controller-truth `routing_rationale_summary` and `lock_summary`, and the focused inspect-context unittest module remains green without widening beyond Story 4.3 inspect seams.
- Landed the fourth implementation slice only: human-readable `worker inspect` and `task inspect` now render degraded warnings plus controller truth before a separate adapter evidence section, covering owner, lease, locks, routing rationale, recent events, and pane target in the focused black-box CLI tests.
- Additional focused slices landed without widening scope: `task inspect --json` now includes routing rationale summary, active lock summary, and a separate adapter evidence layer tied to the current degraded owner.
- Landed the final implementation slice: `worker inspect --open-pane` and `task inspect --open-pane` now pin the repo-local target through `set_target.sh`, report `opened` when the current tmux context can select the pane, and fall back to `pinned_only` with an explicit warning when only pinning is possible.
- Full validation passed after aligning older inspect-callsite tests with the frozen Story 4.3 envelope: `python3 -m unittest discover -s tools/orchestration/tests` and `./tools/tmux_bridge/tests/smoke.sh` both returned `OK`.

### File List

- `_bmad-output/implementation-artifacts/stories/4-3-inspect-degraded-evidence-and-open-the-right-worker-pane-from-context.md`
- `README.md`
- `docs/getting-started.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/workers.py`
