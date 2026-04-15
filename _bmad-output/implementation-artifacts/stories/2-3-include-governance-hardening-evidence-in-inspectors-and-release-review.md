# Story 2.3: Include governance hardening evidence in inspectors and release review

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,  
I want version-pin decisions, secret-scope enforcement, and diff/review checkpoints to appear in audit and release evidence,  
so that governance hardening can be validated without manual reconstruction.

## Acceptance Criteria

1. Given version-pin enforcement has accepted or rejected a governed worker or routing decision, when I inspect the relevant worker, task, or event context, then MACS exposes machine-readable and human-readable version-pin evidence with selector context, expected-versus-observed identities, outcome or reason, and traceability to the active governance policy or snapshot plus the related routing or decision event.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-23-include-governance-hardening-evidence-in-inspectors-and-release-review] [Source: _bmad-output/planning-artifacts/architecture.md#event-record-schema] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/planning-artifacts/prd.md#observability--auditability]
2. Given secret-scope enforcement has allowed or blocked a governed action, when I inspect task or event history or review release evidence, then MACS exposes audit-safe secret-scope evidence with `surface_id`, `secret_ref`, selector context, outcome or reason, and decision linkage, and it never leaks raw secret material.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-23-include-governance-hardening-evidence-in-inspectors-and-release-review] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements] [Source: _bmad-output/planning-artifacts/architecture.md#audit-content-policy] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output]
3. Given checkpoint capture or enforced close/archive gate outcomes exist for a task, when I inspect task or event history or review release evidence, then MACS exposes checkpoint and approval evidence with `checkpoint_id`, `target_action`, actor, baseline repo summary, related policy or task context, and canonical decision-event refs instead of requiring raw filesystem browsing or tmux reconstruction.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-23-include-governance-hardening-evidence-in-inspectors-and-release-review] [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/planning-artifacts/prd.md#compliance--regulatory]
4. Given I run `macs setup validate --release-gate`, when the governance-hardening delta is included in release review, then the existing release-gate summary and evidence package add one governance-hardening criterion plus evidence paths covering version-pin, secret-scope, and checkpoint controls in both human-readable and `--json` output without creating a parallel release workflow.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-23-include-governance-hardening-evidence-in-inspectors-and-release-review] [Source: _bmad-output/planning-artifacts/architecture.md#release-gate-matrix] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg5] [Source: _bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md#acceptance-criteria]
5. Given the governance-hardening validation and release-review coverage runs, when passing and failing scenarios are exercised, then the suites cover version-pin drift, out-of-scope or unresolved secret use, missing checkpoints, and stale or mismatched checkpoints, and a passing run produces attributable evidence without leaking secret material.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-23-include-governance-hardening-evidence-in-inspectors-and-release-review] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg5] [Source: _bmad-output/project-context.md#testing-rules]
6. Story 2.3 stays bounded to cross-surface evidence exposure and release-review aggregation: it reuses existing controller-owned events, routing decisions, review checkpoints, governance snapshot helpers, and release-evidence packaging rather than redesigning version-pin enforcement, secret-resolution, or checkpoint capture, and it does not modify any non-governance-hardening tracker.  
   [Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md#next-epic-preparation] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#additional-requirements] [Inference from: user request to keep scope limited to this lane]

## Tasks / Subtasks

- [x] Add one controller-owned governance-evidence aggregation layer that reuses existing state and event seams instead of inventing another evidence store. (AC: 1, 2, 3, 4, 6)
  - [x] Extend `tools/orchestration/history.py` with one narrow helper or summary path that can resolve governance-hardening evidence from `routing_decisions`, event payloads, `review_checkpoints`, and related decision-event refs, returning one audit-safe structure for inspect and release-review use. Do not add a new SQLite table or a second hidden artifact directory.  
        [Source: tools/orchestration/history.py] [Source: tools/orchestration/store.py] [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records] [Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]
  - [x] Reuse controller-owned evidence fields that already exist today, including `governance_policy_version`, `governance_policy_path`, `blocked_surfaces`, `secret_resolution`, `checkpoint_id`, `decision_event_id`, `routing_decision_id`, `target_action`, `surface_id`, and `secret_ref`, instead of re-deriving or duplicating those facts in a new schema.  
        [Source: tools/orchestration/routing.py] [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/history.py] [Inference from: current write-side payloads already persist the core governance refs needed for read-side aggregation]
  - [x] Keep the aggregated evidence bounded and audit-safe: secret refs and baseline summaries are allowed, but raw secret values, full diff bodies, prompt content, tool output, or tmux transcripts must not become the cross-surface evidence payload.  
        [Source: _bmad-output/planning-artifacts/architecture.md#audit-content-policy] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements] [Source: _bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md#implementation-guardrails]

- [x] Extend existing inspect surfaces so maintainers can see correlated governance-hardening evidence from the current CLI instead of reconstructing it manually. (AC: 1, 2, 3, 6)
  - [x] Update `task inspect` in `tools/orchestration/tasks.py` plus `tools/orchestration/cli/main.py` to surface one compact governance-evidence block built from the current-owner version-pin summary, routing or assignment secret-resolution evidence, recent or enforced checkpoint refs, and related policy or event linkage. Keep this inside the existing task inspect payload and renderer rather than creating a new browser.  
        [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content] [Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md#action-items]
  - [x] Extend `event inspect` so events tied to routing, assignment, checkpoint capture, gated closeout, or policy-blocked outcomes can surface the related governance evidence together, including version-pin summaries where the current event points back to a routing decision and checkpoint or decision refs where the event points to enforced closeout.  
        [Source: tools/orchestration/history.py] [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/architecture.md#event-record-schema] [Inference from: current event inspect already resolves checkpoint and secret-resolution detail, but not the related version-pin evidence from routing decisions]
  - [x] Keep `worker inspect`, `adapter inspect`, and `setup check` additive only where needed to preserve policy-snapshot traceability or selector context; do not expand those surfaces into a second release-review dashboard.  
        [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/setup.py] [Source: _bmad-output/implementation-artifacts/stories/1-2-reject-pin-drift-during-eligibility-and-governed-surface-use.md#surface-version-enforcement-outcomes-through-existing-audit-and-inspect-seams] [Source: _bmad-output/implementation-artifacts/stories/1-4-enforce-scoped-secret-resolution-at-action-time.md#surface-secret-scope-enforcement-outcomes-through-the-existing-audit-and-inspect-seams]

- [x] Extend the existing release-gate surface and evidence package with one governance-hardening criterion and report. (AC: 2, 3, 4, 5, 6)
  - [x] Add a `governance_hardening` criterion to `tools/orchestration/release_gate.py` and thread it through `macs setup validate --release-gate` output in `tools/orchestration/cli/main.py`, reusing Story 8.4’s release-gate structure and evidence-package conventions instead of adding a new top-level family or separate review command.  
        [Source: tools/orchestration/release_gate.py] [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md#brownfield-reuse-guidance] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg5]
  - [x] Write one governance-hardening evidence report under `_bmad-output/release-evidence/` that summarizes pass or fail evidence for version-pin enforcement, secret-scope enforcement, and checkpoint gating, with policy refs, related event IDs, and report paths or artifact refs that remain audit-safe and attributable.  
        [Source: tools/orchestration/release_gate.py] [Source: _bmad-output/planning-artifacts/architecture.md#release-gate-matrix] [Source: _bmad-output/planning-artifacts/prd.md#observability--auditability]
  - [x] If additional generated artifacts are useful, keep them under the current `_bmad-output/release-evidence/` package and thread them through `release-gate-summary.json` or the new criterion payload rather than introducing a second storage root or a second release review format.  
        [Source: _bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md#file-structure-requirements] [Source: tools/orchestration/release_gate.py]

- [x] Extend the existing regression seams so pass/fail governance-hardening evidence is proven in both inspect and release-review flows. (AC: 1, 2, 3, 4, 5)
  - [x] Extend `tools/orchestration/tests/test_inspect_context_cli.py` with focused black-box coverage that proves task and event inspect can surface version-pin acceptance or rejection details, secret-resolution acceptance or rejection details, checkpoint or decision linkage, and policy traceability together while preserving human-readable or JSON parity and keeping raw secret values absent.  
        [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md#action-items]
  - [x] Extend `tools/orchestration/tests/test_task_lifecycle_cli.py` only where needed to seed and verify the write-side evidence that inspect and release review will summarize: version-pin drift, secret-scope block or success, missing checkpoint, stale checkpoint, and successful gated closeout with attributable refs.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: _bmad-output/implementation-artifacts/stories/1-2-reject-pin-drift-during-eligibility-and-governed-surface-use.md#testing-requirements] [Source: _bmad-output/implementation-artifacts/stories/1-4-enforce-scoped-secret-resolution-at-action-time.md#testing-requirements] [Source: _bmad-output/implementation-artifacts/stories/2-2-enforce-the-diff-review-gate-before-closeout-or-safety-relaxation.md#testing-requirements]
  - [x] Extend `tools/orchestration/tests/test_release_gate_cli.py` and, if the setup-validate envelope changes, `tools/orchestration/tests/test_setup_init.py` so the governance-hardening criterion and report path are required in both `--json` and human-readable release-gate output.  
        [Source: tools/orchestration/tests/test_release_gate_cli.py] [Source: tools/orchestration/tests/test_setup_init.py] [Source: _bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md#testing-requirements]
  - [x] Before marking the story done, run the focused governance and release-gate suites plus full orchestration unittest discovery.  
        [Source: _bmad-output/project-context.md#testing-rules]

- [x] Update operator-facing docs only if the visible release-gate or inspect surfaces become inaccurate after the evidence aggregation changes. (AC: 4, 6)
  - [x] Limit any required docs work to the current operator-visible surfaces such as `README.md`, `docs/user-guide.md`, or `docs/how-tos.md`, and defer broader documentation restructuring or release-process expansion.  
        [Source: docs/contributor-guide.md#when-to-touch-which-docs] [Source: _bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md#implementation-guardrails]

- [x] Keep Story 2.3 bounded to evidence exposure and release review. (AC: 6)
  - [x] Do not redesign `surface_version_pins`, `secret_scopes`, `review_checkpoints`, checkpoint freshness rules, task close/archive gating, or adapter probe semantics unless a minimal read-side hook is unavoidable to expose already-authoritative evidence.  
        [Source: _bmad-output/implementation-artifacts/stories/1-2-reject-pin-drift-during-eligibility-and-governed-surface-use.md#implementation-guardrails] [Source: _bmad-output/implementation-artifacts/stories/1-4-enforce-scoped-secret-resolution-at-action-time.md#implementation-guardrails] [Source: _bmad-output/implementation-artifacts/stories/2-2-enforce-the-diff-review-gate-before-closeout-or-safety-relaxation.md#implementation-guardrails]
  - [x] Do not add a hosted review service, external audit exporter, second evidence database, or non-local release workflow.  
        [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries] [Source: _bmad-output/planning-artifacts/architecture.md#release-gate-matrix]
  - [x] Do not edit the historical orchestration tracker or the guided-onboarding tracker as part of implementation.  
        [Source: _bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#overview]

- [x] Review Follow-ups (AI)
  - [x] [AI-Review] Keep task or event inspect and release-review evidence reads from rewriting `governance-policy.json` on disk; keep any governance-policy sanitization in-memory on those read-side paths and prove the policy file stays unchanged after an evidence-read flow. (AC: 1, 2, 4, 5, 6)
  - [x] [AI-Review] Include per-control `governance_hardening` evidence refs in human-readable `macs setup validate --release-gate` output so the release-gate CLI remains aligned with JSON evidence. (AC: 4, 5, 6)

## Dev Notes

### Story Intent

Story 2.3 is the evidence-aggregation layer for the governance-hardening lane. Stories 1.2 and 1.4 already enforce version pins and secret scopes, and Stories 2.1 and 2.2 already capture and enforce review checkpoints, but maintainers still have to mentally stitch those controls together across worker inspect, task inspect, event inspect, and the release-gate package. Story 2.3 should make that control history visible and attributable from the existing inspect and release-review surfaces without reopening the underlying enforcement models.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-23-include-governance-hardening-evidence-in-inspectors-and-release-review]  
[Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md#action-items]

### Governance-Hardening Lane Boundaries

- Use only `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml` for lane tracking.
- Do not edit the historical orchestration tracker at `_bmad-output/implementation-artifacts/sprint-status.yaml`.
- Do not edit the guided-onboarding tracker at `_bmad-output/implementation-artifacts/sprint-status-macs-guided-onboarding.yaml`.
- Treat this as follow-on governance hardening implied by the 2026-04-14 correction pass, not a reopening of the completed orchestration sprint and not part of guided onboarding.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#overview]  
[Source: _bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml]

### Epic Continuity

- Story 1.2 already made version-pin drift fail closed during registration and routing and preserved selector-rich rejection evidence in routing or worker seams.
- Story 1.4 already made secret-scope enforcement fail closed at action time and preserved audit-safe `secret_resolution` summaries in routing, task, and event payloads.
- Story 2.1 already created controller-owned checkpoint artifacts and inspectable checkpoint refs.
- Story 2.2 already linked successful gated close/archive actions to attributable approval events and checkpoint refs.
- Story 8.4 already established the current release-gate report, summary JSON, and evidence-package shape that Story 2.3 should extend instead of replacing.
- The governance-hardening retrospective explicitly calls out human-readable parity with JSON evidence as a required acceptance concern for every remaining story in this lane.

Implementation consequence: Story 2.3 should aggregate existing controller-owned evidence across these seams, not rebuild the control models or invent a new review subsystem.

[Source: _bmad-output/implementation-artifacts/stories/1-2-reject-pin-drift-during-eligibility-and-governed-surface-use.md#completion-notes-list]  
[Source: _bmad-output/implementation-artifacts/stories/1-4-enforce-scoped-secret-resolution-at-action-time.md#completion-notes-list]  
[Source: _bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md#completion-notes-list]  
[Source: _bmad-output/implementation-artifacts/stories/2-2-enforce-the-diff-review-gate-before-closeout-or-safety-relaxation.md#completion-notes-list]  
[Source: _bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md#completion-notes-list]  
[Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md#action-items]

### Brownfield Baseline

- `governance_summary_for_worker(...)` in `tools/orchestration/cli/main.py` already produces live version-pin summaries plus the active governance policy path for worker and task inspect.
- `inspect_task_context(...)` in `tools/orchestration/tasks.py` already exposes `routing_decision`, `secret_resolution`, `recent_checkpoint_refs`, and `recent_event_refs`, but it does not synthesize one combined governance-evidence block.
- `event inspect` in `tools/orchestration/cli/main.py` already resolves checkpoint refs, decision-event refs, and `secret_resolution` payloads, but it does not currently surface related version-pin evidence from the routing decision that led to the event.
- `build_setup_configuration_snapshot(...)` in `tools/orchestration/setup.py` already exposes the active governance snapshot plus normalized secret scopes and surface version pins for configuration-level inspection.
- `tools/orchestration/release_gate.py` currently packages only `setup_validation`, `adapter_qualification`, `failure_mode_matrix`, `restart_recovery`, and `reference_dogfood`; there is no governance-hardening criterion or report yet.
- `tools/orchestration/tests/test_inspect_context_cli.py` and `tools/orchestration/tests/test_release_gate_cli.py` are already the right black-box seams for the new inspect and release-review behavior.

[Source: tools/orchestration/cli/main.py]  
[Source: tools/orchestration/tasks.py]  
[Source: tools/orchestration/history.py]  
[Source: tools/orchestration/setup.py]  
[Source: tools/orchestration/release_gate.py]  
[Source: tools/orchestration/tests/test_inspect_context_cli.py]  
[Source: tools/orchestration/tests/test_release_gate_cli.py]

### Governance Evidence Gap

- Version-pin evidence is currently strongest on `worker inspect` and in routing-decision payloads, not in one task- or event-centered governance summary.
- Secret-scope evidence is currently present on task and event payloads, but it is not packaged into the release-review evidence set.
- Checkpoint and approval evidence is currently present on task and event inspect, but it is not included in the release-gate summary or report package.
- No single current surface ties version-pin, secret-scope, checkpoint, policy snapshot, and canonical decision-event references together for a maintainer doing release review.

Implementation consequence: add additive aggregation on the existing inspect and release-gate read paths rather than widening write-side behavior.

[Inference from: tools/orchestration/cli/main.py, tools/orchestration/tasks.py, tools/orchestration/history.py, tools/orchestration/release_gate.py, and current inspect/release-gate tests]

### Technical Requirements

- Reuse controller-owned evidence already persisted in routing decisions, event payloads, review checkpoints, and active governance snapshots; do not infer governance pass/fail from documentation or static policy alone when controller events already exist.  
  [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records] [Source: _bmad-output/planning-artifacts/architecture.md#event-record-schema]
- Preserve traceability fields wherever practical: `policy_version`, `policy_path`, snapshot traceability status or snapshot ID, `task_id`, `worker_id`, `surface_id`, `secret_ref`, `checkpoint_id`, `target_action`, `routing_decision_id`, `decision_event_id`, and related event IDs.  
  [Source: _bmad-output/planning-artifacts/prd.md#observability--auditability] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content]
- Keep the exposed evidence audit-safe. Secret refs are allowed; raw secret values are forbidden. Checkpoint baseline summaries are allowed; full diff bodies or transcript capture are not a substitute for controller-owned evidence.  
  [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements] [Source: _bmad-output/planning-artifacts/architecture.md#audit-content-policy]
- Preserve current CLI and JSON envelopes for inspect and release-gate surfaces. Add evidence inside existing payloads and reports rather than inventing a second contract shape.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output] [Source: _bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md#acceptance-criteria]
- Keep implementation Python-stdlib-only and compatible with current repo-local state and release-evidence paths.  
  [Source: _bmad-output/project-context.md#technology-stack--versions]

### Architecture Compliance

- Keep controller authority first: this story is primarily read-side aggregation over controller-owned truth, not a new place where adapters or release scripts decide policy outcomes.  
  [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]
- Reuse the existing write model and supporting-evidence model. Routing decisions, event payloads, and review checkpoints remain authoritative; release-review artifacts summarize them.  
  [Source: _bmad-output/planning-artifacts/architecture.md#write-model] [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records]
- Keep the release-review path inside the current repo-local `macs setup validate --release-gate` flow and `_bmad-output/release-evidence/` package.  
  [Source: _bmad-output/planning-artifacts/architecture.md#release-gate-matrix] [Source: _bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md#architecture-compliance-notes]
- Treat human-readable parity with JSON as part of the story contract, not optional polish.  
  [Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md#action-items]

### Suggested Implementation Shape

- Prefer extending `tools/orchestration/history.py` with one or two governance-evidence helper functions rather than introducing a new governance-review subsystem.
- Build one task- and event-oriented `governance_evidence` summary from:
  - worker governance summaries already produced through `governance_summary_for_worker(...)`
  - routing-decision rationale, including rejected-worker or selected-worker version-pin evidence
  - `secret_resolution` payloads already attached to routing and assignment flows
  - `review_checkpoints` plus linked decision events
  - active governance snapshot or policy-path references where they clarify traceability
- Extend `task inspect` and `event inspect` renderers to surface that summary compactly in both human-readable and JSON modes.
- Extend `tools/orchestration/release_gate.py` with one governance-hardening criterion builder that produces a repo-local markdown report plus machine-readable summary fields under the existing release-gate JSON.
- If helper extraction is necessary beyond `history.py`, keep it tiny and adjacent to current read-side or release-gate code rather than adding a new persistence or service layer.

[Inference from: tools/orchestration/cli/main.py, tools/orchestration/history.py, tools/orchestration/tasks.py, tools/orchestration/setup.py, and tools/orchestration/release_gate.py]  
[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]

### File Structure Requirements

- Primary implementation files for this story:
  - `tools/orchestration/history.py`
  - `tools/orchestration/cli/main.py`
  - `tools/orchestration/tasks.py`
  - `tools/orchestration/workers.py`
  - `tools/orchestration/release_gate.py`
  - `tools/orchestration/tests/test_inspect_context_cli.py`
  - `tools/orchestration/tests/test_task_lifecycle_cli.py`
  - `tools/orchestration/tests/test_release_gate_cli.py`
- Optional touch points only if needed:
  - `tools/orchestration/setup.py`
  - `tools/orchestration/policy.py`
  - `tools/orchestration/routing.py`
  - `tools/orchestration/tests/test_setup_init.py`
  - `README.md`
  - `docs/user-guide.md`
  - `docs/how-tos.md`
- Avoid new hidden directories, new state tables, or a second evidence package outside `_bmad-output/release-evidence/`.

[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]  
[Source: _bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md#file-structure-requirements]

### Testing Requirements

- Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_release_gate_cli tools.orchestration.tests.test_setup_init` as the focused required validation surface for this story.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Add black-box inspect coverage proving:
  - version-pin evidence is visible with selector context and expected-versus-observed detail
  - secret-resolution evidence is visible without raw secret leakage
  - checkpoint and approval linkage remain attributable and compact
  - human-readable and JSON outputs stay aligned  
  [Source: tools/orchestration/tests/test_inspect_context_cli.py]
- Add release-gate coverage proving the new governance-hardening criterion, report path, and evidence summary are present in both human-readable and `--json` outputs and that they reflect pass/fail scenarios honestly.  
  [Source: tools/orchestration/tests/test_release_gate_cli.py] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg5]
- Reuse existing task-lifecycle fixtures and seeded repo-state scenarios to exercise version-pin drift, secret-scope block or success, and checkpoint missing or stale conditions instead of inventing a second governance harness.  
  [Source: tools/orchestration/tests/test_task_lifecycle_cli.py]

### Git Intelligence Summary

- Recent committed history still concentrates the highest-value brownfield seams in controller-owned CLI, history, policy, task lifecycle, and release-gate modules, which is exactly where Story 2.3 needs to land.
- The current working tree already contains in-flight edits across `cli/main.py`, `history.py`, `policy.py`, `release_gate.py`, `tasks.py`, `setup.py`, and the related regression suites.
- Story 2.3 is therefore likely to intersect shared files already under active edit. Implementation must work with those changes instead of reverting or relocating them.

[Source: git log --oneline -5]  
[Inference from current git status]

### Implementation Guardrails

- Do not add a new SQLite table, second evidence database, or standalone governance-review service.
- Do not persist raw secret values, full diff bodies, prompt content, tool output, or transcript captures in the new cross-surface evidence summary or release-review report.
- Do not broaden into redesigning version-pin evaluation, secret resolution, checkpoint capture, checkpoint freshness rules, or task close/archive semantics unless a minimal read-side hook is strictly required.
- Do not add a new top-level `release` or `review` command family.
- Do not modify the historical orchestration tracker or the guided-onboarding tracker as part of implementation.
- Do not revert unrelated working-tree changes in shared CLI, policy, history, release-gate, docs, or test files.

[Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]  
[Source: _bmad-output/project-context.md#development-workflow-rules]  
[Source: _bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md#implementation-guardrails]

### Project Structure Notes

- This remains a brownfield, shell-first, Python-stdlib-only orchestration controller with repo-local authority under `.codex/orchestration/`.
- Current inspect and release-review seams already exist; the highest-value increment is to unify and expose governance-hardening evidence across them, not to create a new subsystem.
- Release evidence already has an established home under `_bmad-output/release-evidence/`, and Story 2.3 should extend that package rather than split it.

[Source: _bmad-output/project-context.md#development-workflow-rules]  
[Source: _bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md#project-structure-notes]

### References

- `_bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/planning-artifacts/release-readiness-evidence-matrix.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-14-macs-core-orchestration.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`
- `_bmad-output/implementation-artifacts/epic-1-retro-2026-04-14-governance-hardening.md`
- `_bmad-output/implementation-artifacts/stories/1-2-reject-pin-drift-during-eligibility-and-governed-surface-use.md`
- `_bmad-output/implementation-artifacts/stories/1-4-enforce-scoped-secret-resolution-at-action-time.md`
- `_bmad-output/implementation-artifacts/stories/2-1-capture-attributable-diff-review-checkpoints.md`
- `_bmad-output/implementation-artifacts/stories/2-2-enforce-the-diff-review-gate-before-closeout-or-safety-relaxation.md`
- `_bmad-output/implementation-artifacts/stories/8-4-ship-a-release-gate-command-and-report-for-phase-1-readiness.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/history.py`
- `tools/orchestration/policy.py`
- `tools/orchestration/release_gate.py`
- `tools/orchestration/routing.py`
- `tools/orchestration/setup.py`
- `tools/orchestration/store.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/workers.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_release_gate_cli.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add one read-side governance-evidence summary that reuses routing decisions, secret-resolution payloads, checkpoint refs, and policy snapshot traceability instead of inventing a new evidence store.
- Surface that summary through the existing task and event inspect flows with human-readable or JSON parity.
- Extend `macs setup validate --release-gate` with one governance-hardening criterion and evidence report under the current release-evidence package.
- Lock the behavior down with inspect, lifecycle, release-gate, and setup-validate regressions before implementation closeout.

### Debug Log References

- Story authored with `bmad-create-story`.
- Used the lane-specific tracker `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml` as the sprint source of truth for this slice.
- Loaded the governance-hardening delta epic file, the lane tracker, project context, Epic 1 retrospective, Stories 1.2, 1.4, 2.1, 2.2, and 8.4, plus the live brownfield seams in `cli/main.py`, `history.py`, `tasks.py`, `workers.py`, `setup.py`, `release_gate.py`, `routing.py`, and the inspect or release-gate regression suites.
- 2026-04-15T00:52:50+01:00: Moved the story and the lane-local tracker to `in-progress`; narrowed implementation to read-side aggregation in `history.py`, existing inspect renderers, and the current release-gate package.
- 2026-04-15T01:16:10+01:00: Added the shared governance-evidence summary in `history.py`, threaded it through task or event inspect, and extended release-gate packaging with one governance-hardening criterion plus sanitized sample artifacts under `_bmad-output/release-evidence/`.
- 2026-04-15T01:16:10+01:00: Reused existing task-lifecycle regression coverage for version-pin, secret-scope, and checkpoint failure classes; no additional `test_task_lifecycle_cli.py` or `test_setup_init.py` delta was required for this story.
- 2026-04-15T01:40:40+01:00: Added red regressions for read-only governance evidence reads and human-readable release-gate evidence refs; both failed against the pre-fix behavior as expected.
- 2026-04-15T01:40:40+01:00: Removed bootstrap-time governance-policy rewrites from read-side inspect and release-review flows by keeping governance-policy sanitization in memory for bootstrap snapshots, governance evidence aggregation, and task-inspect worker-governance summaries while leaving durable sanitization on setup or write-side loaders.
- 2026-04-15T01:40:40+01:00: Left the raw-secret dispatch-path comment and the prior checkpoint subsystem scope comment non-actionable for Story 2.3 because the required fix stayed within read-side evidence aggregation and release-gate rendering seams.

### Test Record

- Not run; story creation only.
- 2026-04-15T00:52:50+01:00: Pending red tests for task inspect, event inspect, task lifecycle evidence seeding, and release-gate coverage.
- 2026-04-15T01:16:10+01:00: `python3 -m unittest tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_task_inspect_json_surfaces_compact_governance_evidence_without_secret_leakage tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_event_inspect_surfaces_governance_evidence_and_decision_linkage_without_secret_leakage tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_task_inspect_surfaces_version_pin_rejection_governance_evidence` — PASS.
- 2026-04-15T01:16:10+01:00: `python3 -m unittest tools.orchestration.tests.test_release_gate_cli.ReleaseGateCliTests.test_release_gate_writes_phase1_evidence_package tools.orchestration.tests.test_release_gate_cli.ReleaseGateCliTests.test_release_gate_human_readable_lists_gate_summary_and_evidence tools.orchestration.tests.test_release_gate_cli.ReleaseGateCliTests.test_release_gate_governance_hardening_report_summarizes_control_coverage` — PASS.
- 2026-04-15T01:16:10+01:00: `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_release_gate_cli tools.orchestration.tests.test_setup_init` — PASS (196 tests).
- 2026-04-15T01:16:10+01:00: `python3 -m unittest discover -s tools/orchestration/tests` — PASS (216 tests).
- 2026-04-15T01:40:40+01:00: `python3 -m unittest tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_task_inspect_governance_evidence_read_leaves_governance_policy_unchanged` — PASS.
- 2026-04-15T01:40:40+01:00: `python3 -m unittest tools.orchestration.tests.test_release_gate_cli.ReleaseGateCliTests.test_release_gate_human_readable_lists_gate_summary_and_evidence` — PASS.
- 2026-04-15T01:40:40+01:00: `python3 -m unittest tools.orchestration.tests.test_inspect_context_cli` — PASS (55 tests).
- 2026-04-15T01:40:40+01:00: `python3 -m unittest tools.orchestration.tests.test_release_gate_cli` — PASS (4 tests).
- 2026-04-15T01:40:40+01:00: `python3 -m unittest tools.orchestration.tests.test_setup_init` — PASS (70 tests).
- 2026-04-15T01:40:40+01:00: `python3 -m unittest discover -s tools/orchestration/tests` — PASS (217 tests).

### Completion Notes List

- Created the Story 2.3 implementation brief for the governance-hardening lane.
- Marked Story 2.3 as `ready-for-dev` in the governance-hardening tracker.
- Added one audit-safe governance-evidence summary that reuses routing decisions, secret-resolution summaries, checkpoints, decision events, and governance snapshot traceability without introducing new persistence.
- Surfaced compact `governance_evidence` blocks in task and event inspect JSON plus human-readable output, including version-pin, secret-scope, checkpoint, and decision linkage details.
- Extended `macs setup validate --release-gate` with a `governance_hardening` criterion, a governance-hardening report, and machine-readable sample evidence artifacts under the existing release-evidence package.
- Added black-box inspect and release-gate regressions for governance-hardening evidence and verified the broader orchestration unittest suite stayed green.
- No operator doc delta was required because the inspect and release-gate command families remained accurate after the additive evidence exposure changes.
- Resolved the review follow-up that read-side inspect and release-review evidence reads must not rewrite `governance-policy.json`; task inspect now leaves the policy file unchanged while still keeping raw-secret fields out of inspect output.
- Resolved the review follow-up that human-readable `macs setup validate --release-gate` must expose per-control `governance_hardening` evidence refs alongside outcomes so the CLI matches JSON evidence.
- Kept the raw-secret dispatch-path comment and the checkpoint subsystem scope comment non-actionable for Story 2.3 because no touched file broadened scope beyond read-side governance evidence and release-gate rendering.

### File List

- `_bmad-output/implementation-artifacts/stories/2-3-include-governance-hardening-evidence-in-inspectors-and-release-review.md`
- `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`
- `tools/orchestration/history.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/policy.py`
- `tools/orchestration/release_gate.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_release_gate_cli.py`

### Change Log

- 2026-04-15: Created Story 2.3 and moved the governance-hardening tracker entry from `backlog` to `ready-for-dev`.
- 2026-04-15: Started implementation and moved Story 2.3 from `ready-for-dev` to `in-progress`.
- 2026-04-15: Implemented governance evidence aggregation for inspect and release-gate surfaces, validated the focused governance suites, and moved Story 2.3 to `review`.
- 2026-04-15: Addressed the Story 2.3 review follow-ups for read-only governance evidence reads and human-readable governance control evidence refs, reran the inspect, release-gate, and setup validation surface plus full orchestration discovery, and kept the story in `review`.
