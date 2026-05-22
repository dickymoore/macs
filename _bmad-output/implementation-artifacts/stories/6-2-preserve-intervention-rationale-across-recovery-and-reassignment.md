# Story 6.2: Preserve intervention rationale across recovery and reassignment

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,
I want recovery decisions to carry operator rationale and causation links,
so that ownership changes remain explainable after degraded workflows.

## Acceptance Criteria

1. Operator-confirmed intervention decisions become first-class audit records. When the operator confirms a pause, reroute, recovery retry, recovery reconcile, or equivalent recovery-path decision, MACS records actor identity, intervention rationale, correlation context, and affected object refs in the durable event trail using controller-authoritative event storage rather than ad hoc tmux notes or console-only output.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-62-preserve-intervention-rationale-across-recovery-and-reassignment] [Source: _bmad-output/planning-artifacts/prd.md#auditability-governance-and-operator-trust] [Source: _bmad-output/planning-artifacts/architecture.md#audit-content-policy] [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules]
2. Resulting recovery or reassignment transitions remain causally connected to the originating intervention decision. Lease, task, lock, and recovery events emitted as part of an operator-confirmed reroute or reconciliation flow preserve causation links back to the recorded decision so later inspection can reconstruct why the controller changed ownership, released or transferred protection, or abandoned or resumed recovery.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-62-preserve-intervention-rationale-across-recovery-and-reassignment] [Source: _bmad-output/planning-artifacts/architecture.md#event] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#maintainer-intervenes-in-a-degraded-session]
3. Read-side inspection surfaces make intervention rationale legible. `macs event inspect`, `macs event list`, `macs task inspect`, `macs lease inspect`, `macs lease history`, and `macs recovery inspect` surface actor identity, intervention rationale, causation continuity, and affected task or lease refs in both human-readable and `--json` output without changing the frozen top-level envelopes or inventing a second audit store.  
   [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/planning-artifacts/prd.md#monitoring-intervention-and-recovery]
4. Audit capture remains metadata-first and local-host safe. Story 6.2 preserves rationale, actor identity, and evidence references or summaries needed for operator-visible explanation, but does not broaden into rich prompt or terminal transcript capture, enterprise IAM, or policy-rights enforcement that belongs to later stories.  
   [Source: _bmad-output/planning-artifacts/prd.md#auditability-governance-and-operator-trust] [Source: _bmad-output/planning-artifacts/architecture.md#audit-content-policy] [Source: _bmad-output/project-context.md#critical-dont-miss-rules]
5. Regression coverage proves rationale-bearing intervention events, causal linkage across reroute or reconciliation transitions, inspect-surface visibility, and no regressions to Story 6.1 event/history readers, Story 5.4 interrupted recovery behavior, Story 5.3 safe reroute invariants, or Story 4.4 pause semantics.  
   [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/implementation-artifacts/stories/6-1-persist-a-durable-event-trail-and-history-inspectors.md] [Source: _bmad-output/implementation-artifacts/stories/5-4-resume-interrupted-recovery-from-persisted-recovery-runs.md] [Source: _bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md] [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md]

## Tasks / Subtasks

- [x] Add a shared intervention-decision audit helper and reuse the existing event store. (AC: 1, 2, 4)
  - [x] Add a focused helper in `tools/orchestration/tasks.py` or a narrowly shared adjacent module that records an operator-confirmed intervention decision event with actor identity, rationale, correlation context, and affected task, lease, worker, or recovery refs using the existing `events` table and `EventRecord`.  
        [Source: tools/orchestration/store.py] [Source: tools/orchestration/tasks.py] [Source: _bmad-output/planning-artifacts/architecture.md#event]
  - [x] Derive MVP operator identity from local session context rather than enterprise IAM and keep the event metadata local-host safe.  
        [Source: _bmad-output/planning-artifacts/prd.md#auditability-governance-and-operator-trust] [Source: _bmad-output/project-context.md#framework-specific-rules]
  - [x] Reuse the current event schema instead of creating a second rationale table or transcript store. Story 6.2 should enrich the durable event trail, not fork audit storage.  
        [Source: tools/orchestration/store.py] [Source: _bmad-output/planning-artifacts/architecture.md#audit-content-policy]

- [x] Thread rationale and causation through operator-confirmed intervention flows. (AC: 1, 2)
  - [x] Extend controller-owned pause, reroute, recovery retry, and recovery reconcile paths so the initial decision event captures rationale and the resulting lease, task, and recovery events chain causation back to that decision.  
        [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/recovery.py] [Source: _bmad-output/implementation-artifacts/stories/5-4-resume-interrupted-recovery-from-persisted-recovery-runs.md]
  - [x] Keep unsupported abort behavior out of scope, but structure the shared helper so later abort work can use the same rationale and causation pattern without backfilling the event model.  
        [Source: _bmad-output/planning-artifacts/epics.md#story-62-preserve-intervention-rationale-across-recovery-and-reassignment] [Source: tools/orchestration/cli/main.py]
  - [x] Preserve zero-or-one live lease and current-owner invariants while adding rationale capture; do not let audit enrichment change lifecycle ordering or recovery safety rules.  
        [Source: tools/orchestration/invariants.py] [Source: _bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md]

- [x] Make rationale and causation visible in existing inspect surfaces. (AC: 3, 4)
  - [x] Extend `tools/orchestration/history.py` readers so event inspection returns actor identity, causation, rationale payload, and affected refs in a form suitable for JSON and human-readable rendering.  
        [Source: tools/orchestration/history.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content]
  - [x] Extend `tools/orchestration/cli/main.py` event, task, lease, and recovery output so intervention rationale and causation continuity are legible without changing the top-level JSON envelopes.  
        [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output]
  - [x] Reuse current recent-event and history surfaces so inspectors can connect the decision record to resulting task or lease transitions instead of inventing a separate audit browser.  
        [Source: tools/orchestration/history.py] [Source: tools/orchestration/overview.py] [Source: _bmad-output/implementation-artifacts/stories/6-1-persist-a-durable-event-trail-and-history-inspectors.md]

- [x] Keep audit payloads metadata-first and bounded. (AC: 4)
  - [x] Limit Story 6.2 payload additions to rationale text, actor identity, affected refs, evidence summaries or refs, and decision classification metadata needed to explain the intervention.  
        [Source: _bmad-output/planning-artifacts/architecture.md#audit-content-policy] [Source: _bmad-output/planning-artifacts/prd.md#auditability-governance-and-operator-trust]
  - [x] Do not add prompt capture, tool-output capture, terminal snapshots, or governance policy files as part of this increment.  
        [Source: _bmad-output/project-context.md#critical-dont-miss-rules] [Source: _bmad-output/planning-artifacts/prd.md#auditability-governance-and-operator-trust]

- [x] Add regression coverage for rationale-bearing intervention history. (AC: 5)
  - [x] Extend `tools/orchestration/tests/test_task_lifecycle_cli.py` with black-box cases proving pause, reroute, recovery retry, or recovery reconcile record rationale-bearing decision events and preserve causation across resulting transitions.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: _bmad-output/planning-artifacts/architecture.md#test-layers]
  - [x] Extend `tools/orchestration/tests/test_inspect_context_cli.py` with event, task, lease, and recovery inspection assertions that expose actor identity, rationale, and causation continuity in both human-readable and `--json` output.  
        [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: tools/orchestration/cli/main.py]
  - [x] Extend `tools/orchestration/tests/test_setup_init.py` or adjacent history regressions only where needed to prove durable event continuity is preserved across restart and does not regress the existing event or history readers from Story 6.1.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: _bmad-output/implementation-artifacts/stories/6-1-persist-a-durable-event-trail-and-history-inspectors.md]

## Dev Notes

### Story Intent

Story 6.2 adds the explanation layer that Epic 5 recovery work now depends on. The control plane already persists events and can recover safely; this story makes operator-confirmed recovery and reassignment decisions attributable and explainable after the fact without expanding into governance policy enforcement or rich-content capture.  
[Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#dependency-notes] [Source: _bmad-output/implementation-artifacts/stories/5-4-resume-interrupted-recovery-from-persisted-recovery-runs.md]

### Previous Story Intelligence

- Story 6.1 already established the durable `events` table and the first event/lease readers. Story 6.2 should enrich those existing readers and payload shapes instead of creating a second audit subsystem.  
  [Source: _bmad-output/implementation-artifacts/stories/6-1-persist-a-durable-event-trail-and-history-inspectors.md#completion-notes-list] [Source: tools/orchestration/history.py]
- Story 5.4 added controller-owned `recovery retry` and `recovery reconcile` events plus interrupted-recovery inspect surfaces, but those actions still use generic controller actor identity and thin payloads. Story 6.2 should reuse those seams to attach rationale and causation rather than reworking recovery state.  
  [Source: _bmad-output/implementation-artifacts/stories/5-4-resume-interrupted-recovery-from-persisted-recovery-runs.md#completion-notes-list] [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/recovery.py]
- Story 5.3 already made reroute causal ordering safety-critical. Audit enrichment must not disturb predecessor-revocation-before-successor-activation ordering or current-owner invariants.  
  [Source: _bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md#implementation-guardrails] [Source: tools/orchestration/invariants.py]
- Story 4.4 introduced the operator-confirmed pause path. That is the narrowest existing intervention action to use as the first rationale-bearing regression seam.  
  [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md] [Source: tools/orchestration/tasks.py]

### Technical Requirements

- Preserve actor identity in the durable trail for operator-confirmed actions. MVP identity may be local-session identity, but it must not collapse back to a generic `controller-main` actor on the recorded decision itself.  
  [Source: _bmad-output/planning-artifacts/prd.md#auditability-governance-and-operator-trust] [Source: _bmad-output/planning-artifacts/architecture.md#audit-content-policy]
- Preserve causation continuity. Either the recorded decision event becomes the direct causation parent of resulting transitions, or the payload clearly identifies the decision event ID being followed; later inspection must not require inference from timestamps alone.  
  [Source: _bmad-output/planning-artifacts/architecture.md#event] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#maintainer-intervenes-in-a-degraded-session]
- Keep audit capture metadata-first. Do not add transcript, prompt, or terminal capture beyond rationale text and evidence refs or summaries.  
  [Source: _bmad-output/planning-artifacts/architecture.md#audit-content-policy] [Source: _bmad-output/planning-artifacts/prd.md#auditability-governance-and-operator-trust]
- Stay within Python 3.8+ stdlib, SQLite, and the current shell-first repo structure.  
  [Source: _bmad-output/project-context.md#technology-stack--versions]

### Architecture Compliance

- Reuse the current event schema and `EventRecord` path. The architecture already reserves `actor_type`, `actor_id`, `correlation_id`, `causation_id`, `payload`, and `redaction_level`; Story 6.2 should use those fields coherently rather than add a new audit abstraction.  
  [Source: _bmad-output/planning-artifacts/architecture.md#event] [Source: tools/orchestration/store.py]
- Keep controller authority first. The controller records the decision and resulting transitions; adapters and tmux may contribute evidence refs or summaries, but they do not become the source of truth for rationale or ownership.  
  [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: _bmad-output/project-context.md#framework-specific-rules]
- Prefer incremental read-model extension. Event inspect, task inspect, lease inspect, recovery inspect, and lease history already exist; extend them with rationale fields instead of building a new audit command family.  
  [Source: tools/orchestration/history.py] [Source: tools/orchestration/cli/main.py]

### File Structure Requirements

- Extend `tools/orchestration/tasks.py` for shared intervention-decision recording and rationale-bearing operator flows.
- Extend `tools/orchestration/history.py` for event payload and causation readers.
- Extend `tools/orchestration/cli/main.py` so event, task, lease, and recovery outputs surface the new rationale fields in human-readable and JSON forms.
- Reuse `tools/orchestration/recovery.py` only where the recovery decision flows need rationale propagation.
- Prefer extending `tools/orchestration/tests/test_task_lifecycle_cli.py`, `tools/orchestration/tests/test_inspect_context_cli.py`, and `tools/orchestration/tests/test_setup_init.py` before adding new test modules.

[Source: _bmad-output/project-context.md#development-workflow-rules]  
[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]

### Testing Requirements

- Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused required validation surface.  
  [Source: _bmad-output/implementation-artifacts/stories/5-4-resume-interrupted-recovery-from-persisted-recovery-runs.md#debug-log-references]
- Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Add black-box assertions for rationale-bearing pause, reroute, and recovery actions, including direct event inspection of actor identity, rationale, affected refs, and causation.  
  [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: tools/orchestration/history.py]
- Preserve Story 6.1 event/history regressions and Story 5.4 interrupted-recovery behavior while adding the new audit fields.  
  [Source: _bmad-output/implementation-artifacts/stories/6-1-persist-a-durable-event-trail-and-history-inspectors.md] [Source: _bmad-output/implementation-artifacts/stories/5-4-resume-interrupted-recovery-from-persisted-recovery-runs.md]

### Git Intelligence Summary

Recent committed work remains concentrated in the exact seams Story 6.2 should extend:

- `c3ccc6a` resolved review findings in the lifecycle and recovery area, which means current brownfield momentum is still in controller-owned write paths and inspect surfaces.
- `51d2554` and `e474089` reinforce that the durable state and bootstrap layers are already the preferred place for new authority-bearing metadata.
- The highest-signal code seams for this story are `tools/orchestration/tasks.py`, `tools/orchestration/history.py`, `tools/orchestration/cli/main.py`, and the existing CLI regression modules.

[Source: git log --oneline -5]

### Implementation Guardrails

- Do not add a new audit database, rationale table, or transcript store.
- Do not broaden Story 6.2 into decision-rights enforcement, approval workflows, or governed-surface policy; that belongs to Story 6.3 and Story 6.4.
- Do not change lifecycle ordering or safety invariants just to make event causation easier to serialize.
- Do not implement abort semantics in this story if the action is still unsupported; keep the shared rationale plumbing reusable for later work instead.
- Do not regress the existing event JSON envelopes or the event/lease readers from Story 6.1.

### Project Structure Notes

- This repo remains a brownfield, shell-first orchestration control plane. `tools/orchestration/` owns controller truth and audit metadata; tmux remains the execution substrate.
- Story 6.2 should feel like an incremental enrichment of the existing event trail and recovery surfaces, not a new governance subsystem.
- The safest path is to record one explicit intervention decision event, chain resulting transitions back to it, then expose that continuity in the current inspect surfaces.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/planning-artifacts/sprint-plan-2026-04-09.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/6-1-persist-a-durable-event-trail-and-history-inspectors.md`
- `_bmad-output/implementation-artifacts/stories/5-4-resume-interrupted-recovery-from-persisted-recovery-runs.md`
- `_bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md`
- `_bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md`
- `tools/orchestration/store.py`
- `tools/orchestration/history.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/recovery.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/overview.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_setup_init.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add one shared intervention-decision audit helper first and use it on the narrowest existing operator-confirmed actions before broadening to all supported recovery flows.
- Extend current event/history readers and inspect surfaces to show rationale and causation continuity rather than building new audit commands.
- Prove the behavior in red-green slices around pause, reroute, and recovery reconcile/retry, then run full validation and an explicit BMAD QA acceptance pass.

### Story Creation Notes

- Skill used: `bmad-create-story`
- Target story auto-discovered from `sprint-status.yaml` after Story 5.4 was completed.
- Inputs reviewed for this story: Epic 6 story definition, PRD audit and governance requirements, architecture event and audit-content rules, UX degraded-session recovery flow, sprint dependency notes, Story 6.1 completion notes, Story 5.4 implementation notes, current git history, and the live brownfield seams in `store.py`, `history.py`, `tasks.py`, `recovery.py`, `cli/main.py`, and the orchestration CLI tests.
- Validation pass applied against the BMAD create-story checklist before dev handoff: the story now includes previous-story intelligence, brownfield-safe reuse guidance, explicit anti-scope guardrails, and regression targets for rationale-bearing intervention history without broadening into 6.3/6.4.

### Debug Log References

- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_task_pause_records_operator_decision_event_and_causation_with_rationale`
- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_recovery_retry_keeps_reroute_events_attached_to_one_operator_decision`
- `python3 -m unittest tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_event_inspect_json_surfaces_actor_rationale_and_affected_refs tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_event_inspect_human_readable_surfaces_actor_rationale_and_affected_refs tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_task_inspect_json_recent_events_surface_actor_rationale_and_causation`
- `python3 -m unittest tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_lease_inspect_json_surfaces_latest_decision_actor_rationale_and_recent_event tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_lease_history_json_surfaces_latest_event_causation_and_decision_context tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_recovery_inspect_json_surfaces_anomaly_current_and_proposed_state tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_recovery_inspect_human_readable_surfaces_anomaly_current_and_proposed_state`
- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init`
- `python3 -m unittest discover -s tools/orchestration/tests`
- Explicit BMAD QA acceptance pass against Story 6.2 completed on 2026-04-10; one final human-readable `event list` legibility gap around affected refs was found, fixed, and revalidated green.

### Completion Notes List

- Added rationale-bearing operator decision recording for `task pause`, `task reroute`, `recovery retry`, and `recovery reconcile`, using local-session operator identity and the existing durable event trail only.
- Threaded decision IDs and intervention rationale through downstream lease, task, recovery, and lock events so recovery and reroute flows stay attributable without changing lifecycle ordering.
- Extended `event inspect`, `event list`, `task inspect`, `lease inspect`, `lease history`, and `recovery inspect` to surface actor identity, rationale, affected refs, and causation continuity in JSON and human-readable output.
- Added black-box regression coverage for pause, reroute, recovery retry, recovery reconcile, event inspection, task inspection, lease inspection/history, and recovery inspection.
- Required validations passed: `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` and `python3 -m unittest discover -s tools/orchestration/tests`, both green at 107 tests.
- Explicit BMAD QA acceptance pass found one final gap in human-readable `event list` affected-ref visibility; that was fixed before completion and no findings remain.

### File List

- `_bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/history.py`
- `tools/orchestration/locks.py`
- `tools/orchestration/recovery.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/workers.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`

### Change Log

- 2026-04-10: Implemented Story 6.2 rationale-bearing intervention audit flow, inspect-surface enrichment, lock-event causation propagation, regression tests, and post-fix BMAD QA acceptance.
