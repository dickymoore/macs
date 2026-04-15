# Story 6.3: Enforce explicit decision rights and guarded actions

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want automatic, policy-automatic, operator-confirmed, and forbidden actions to be explicit,
so that MACS moves quickly where safe and stops where human authorization is required.

## Acceptance Criteria

1. MACS applies one explicit MVP decision-rights classification for controller actions instead of ad hoc per-command gating. When the controller evaluates normal routing, worker quarantine or drain, pause or resume, reroute, recovery retry or reconcile, abort, or lock-exception actions, it uses one shared policy mapping that distinguishes `automatic`, `policy_automatic`, `operator_confirmed`, and `forbidden_in_mvp` without delegating authority to adapters or hidden CLI-only conditionals.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-63-enforce-explicit-decision-rights-and-guarded-actions] [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/planning-artifacts/architecture.md#decision-rights-model]
2. Supported operator-confirmed actions fail closed until the operator confirms them explicitly. `task pause`, `task resume`, `task reroute`, `recovery retry`, and `recovery reconcile` require an explicit confirmation signal even when the command runs non-interactively, and their success or failure output makes the decision-rights class, whether confirmation was required, and whether controller state changed legible in human-readable and `--json` output.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-63-enforce-explicit-decision-rights-and-guarded-actions] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#intervention-flow] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#recovery-principles]
3. Policy-automatic actions remain low-friction but operator-visible. Normal task assignment, coarse lock reservation during assignment, and worker disable or quarantine drain behavior continue without confirmation, but action results and structured errors make the applied class explicit so operators can distinguish controller-safe automation from operator-confirmed intervention.  
   [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/planning-artifacts/architecture.md#decision-rights-model] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output]
4. Forbidden or not-yet-available high-consequence actions are rejected clearly and safely. `task abort`, `lock override`, and `lock release` do not mutate controller state in Phase 1, but the CLI recognizes them, explains the decision-rights class and why execution is blocked, and returns stable structured errors instead of parser-level ambiguity or silent attempts.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-63-enforce-explicit-decision-rights-and-guarded-actions] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#structured-error-codes] [Source: _bmad-output/planning-artifacts/architecture.md#operator-confirmed] [Source: _bmad-output/planning-artifacts/architecture.md#forbidden-in-mvp]
5. Regression coverage proves explicit decision-rights enforcement without regressing Story 6.2 rationale audit continuity, Story 5.x recovery safety, Story 4.4 pause semantics, or the frozen JSON envelopes.  
   [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md] [Source: _bmad-output/implementation-artifacts/stories/5-4-resume-interrupted-recovery-from-persisted-recovery-runs.md] [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md]

## Tasks / Subtasks

- [x] Add one shared MVP decision-rights evaluator and keep it repo-local. (AC: 1, 3, 4)
  - [x] Extend `tools/orchestration/policy.py` with a narrow controller-owned evaluator or metadata helper that maps known action keys to `automatic`, `policy_automatic`, `operator_confirmed`, or `forbidden_in_mvp`, plus confirmation and allow or block metadata suitable for command handlers.  
        [Source: tools/orchestration/policy.py] [Source: _bmad-output/planning-artifacts/architecture.md#decision-rights-model]
  - [x] Reuse the existing repo-local policy module and avoid introducing a new governance file, remote policy source, or operator-editable decision-rights config in Story 6.3; config separation belongs to Story 7.1 and governance expansion belongs to Story 6.4.  
        [Source: tools/orchestration/policy.py] [Source: _bmad-output/implementation-artifacts/sprint-status.yaml] [Source: _bmad-output/project-context.md#critical-dont-miss-rules]
  - [x] Cover both currently executable actions and CLI-visible guarded actions that remain blocked in Phase 1, so `task abort`, `lock override`, and `lock release` can fail through the same explicit policy path instead of disappearing into parser gaps.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: tools/orchestration/cli/main.py]

- [x] Enforce confirmation for supported operator-confirmed task and recovery actions. (AC: 2)
  - [x] Add explicit confirmation flags for supported high-consequence task and recovery actions in `tools/orchestration/cli/main.py`, and fail closed with structured controller errors when confirmation is missing rather than making parser-required flags that bypass contract-shaped output.  
        [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#json-envelope]
  - [x] Gate `pause`, `resume`, `reroute`, `recovery retry`, and `recovery reconcile` through the shared evaluator before lifecycle mutation, preserving the existing Story 6.2 decision-event audit path once confirmation is supplied.  
        [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/recovery.py] [Source: _bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md]
  - [x] Keep state mutation ordering unchanged after confirmation, especially predecessor-revocation-before-successor-activation, interrupted-recovery continuation, and paused-lease resume safeguards.  
        [Source: tools/orchestration/tasks.py] [Source: _bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md] [Source: _bmad-output/implementation-artifacts/stories/5-4-resume-interrupted-recovery-from-persisted-recovery-runs.md]

- [x] Make policy-automatic and guarded outcomes explicit on the CLI without breaking envelopes. (AC: 2, 3, 4)
  - [x] Extend action success payloads and human-readable summaries for `task assign`, `task pause`, `task resume`, `task reroute`, `recovery retry`, `recovery reconcile`, and worker disable or quarantine drain results so the decision-rights class and confirmation status are legible without changing the top-level response shape.  
        [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output]
  - [x] Add lock-family parser support for at least the frozen `inspect`, `override`, and `release` verbs necessary for explicit structured rejections in Phase 1, even if override and release remain blocked.  
        [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/locks.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families]
  - [x] Ensure structured errors for blocked or forbidden actions include the attempted operation, reason, whether controller state changed, and affected IDs when known.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#human-readable-status-conventions] [Source: tools/orchestration/cli/main.py]

- [x] Keep the story bounded to enforcement, not governance expansion. (AC: 1, 4)
  - [x] Do not add remote operation support, automatic push or deploy behavior, adapter-driven state mutation, policy-file editing UX, or new destructive lock or abort semantics in this increment.  
        [Source: _bmad-output/planning-artifacts/architecture.md#forbidden-in-mvp] [Source: _bmad-output/planning-artifacts/prd.md#security--governance]
  - [x] Do not weaken current auditability or operator attribution; decision-rights enforcement should reuse the existing Story 6.2 rationale-bearing event path instead of forking a second approval system.  
        [Source: _bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md] [Source: _bmad-output/planning-artifacts/prd.md#auditability-governance-and-operator-trust]

- [x] Add regression coverage for confirmation gates, explicit policy classes, and guarded rejections. (AC: 5)
  - [x] Extend `tools/orchestration/tests/test_task_lifecycle_cli.py` with black-box cases proving operator-confirmed actions fail closed without confirmation, succeed with confirmation, and preserve existing rationale and causation behavior after confirmation.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: _bmad-output/planning-artifacts/architecture.md#contract-tests]
  - [x] Extend `tools/orchestration/tests/test_task_lifecycle_cli.py` or adjacent CLI contract tests to cover `task abort`, `lock override`, and `lock release` structured guarded failures, plus policy-automatic `task assign` visibility.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: tools/orchestration/cli/main.py]
  - [x] Extend `tools/orchestration/tests/test_inspect_context_cli.py` only where needed to prove human-readable or JSON action output stays contract-shaped while surfacing decision-rights metadata.  
        [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output]

## Dev Notes

### Story Intent

Story 6.3 hardens the controller’s action boundary after Story 6.2 made operator rationale durable. The repo now needs one explicit place where MACS decides whether an action runs automatically, runs with operator visibility, requires deliberate confirmation, or is blocked in Phase 1. This story should make that boundary concrete in the existing CLI and controller code paths without opening the broader policy-governance work reserved for Stories 6.4 and 7.1.  
[Source: _bmad-output/planning-artifacts/epics.md#story-63-enforce-explicit-decision-rights-and-guarded-actions] [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md]

### Previous Story Intelligence

- Story 6.2 already introduced a shared decision-event audit pattern for pause, reroute, retry, and reconcile. Story 6.3 should enforce confirmation before those same flows execute, then reuse the existing rationale and causation chain after confirmation rather than recording approval in a second subsystem.  
  [Source: _bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md#completion-notes-list] [Source: tools/orchestration/tasks.py]
- Story 5.4 established interrupted recovery as a controller-owned state that blocks fresh assignment until the operator explicitly retries or reconciles. Story 6.3 should add confirmation gates around those recovery actions, not reinterpret recovery state or add alternate continuation paths.  
  [Source: _bmad-output/implementation-artifacts/stories/5-4-resume-interrupted-recovery-from-persisted-recovery-runs.md] [Source: tools/orchestration/recovery.py]
- Story 5.3 made reroute ordering safety-critical. Decision-rights enforcement must not disturb predecessor revocation, replacement lease activation ordering, or zero-or-one live lease invariants.  
  [Source: _bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md] [Source: tools/orchestration/tasks.py]
- Story 4.4 established pause and resume semantics and inspect expectations. If pause or resume becomes confirmation-gated, the controller-state, warning, and accessibility output from that story must still hold once confirmation is provided.  
  [Source: _bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md]

### Technical Requirements

- Centralize the MVP decision-rights mapping in controller code so action handlers stop re-encoding policy in scattered branches.  
  [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/planning-artifacts/architecture.md#decision-rights-model]
- Preserve operator-confirmed behavior for high-consequence actions even in non-interactive CLI usage. Missing confirmation must be reported through contract-shaped structured errors, not `argparse` exits or silent controller-side fallback.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#structured-error-codes]
- Preserve NFR7 and NFR10 boundaries: adapters remain bounded evidence, and any runtime approval or permission controls surfaced by workers must not be bypassed by new controller shortcuts.  
  [Source: _bmad-output/planning-artifacts/prd.md#security--governance]
- Keep current top-level JSON envelopes stable. Add decision-rights metadata inside existing `data.result`, object payloads, or structured error result fields instead of changing the contract envelope.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#json-envelope]

### Architecture Compliance

- Reuse the existing `tools/orchestration/policy.py` seam for controller policy logic; do not create a second policy loader or governance service for Story 6.3.  
  [Source: tools/orchestration/policy.py] [Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]
- Keep controller authority first. Decision-rights classification and confirmation gating happen before any adapter dispatch or task, lease, or lock mutation.  
  [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: _bmad-output/planning-artifacts/prd.md#security--governance]
- Use the CLI as the only operator surface for this increment. No new TUI, background prompt, or out-of-band approval channel should be introduced.  
  [Source: _bmad-output/planning-artifacts/architecture.md#operator-surface] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#purpose]

### File Structure Requirements

- Extend `tools/orchestration/policy.py` for shared decision-rights metadata and evaluation helpers.
- Extend `tools/orchestration/cli/main.py` to add confirmation flags, guarded lock verbs, and decision-rights rendering on success and failure paths.
- Extend `tools/orchestration/tasks.py` and, only where necessary, `tools/orchestration/recovery.py` to enforce confirmation before state mutation while preserving existing Story 6.2 event flow after confirmation.
- Extend `tools/orchestration/locks.py` only if needed for inspect support or explicit blocked-action metadata; do not implement real override semantics in Story 6.3.
- Prefer extending `tools/orchestration/tests/test_task_lifecycle_cli.py` and `tools/orchestration/tests/test_inspect_context_cli.py` before adding new test modules.

[Source: _bmad-output/project-context.md#development-workflow-rules]  
[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]

### Testing Requirements

- Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused required validation surface.  
  [Source: _bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md#debug-log-references]
- Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Add contract tests covering both missing-confirmation failure and confirmed success for supported operator-confirmed actions, plus explicit guarded failures for blocked or forbidden commands.  
  [Source: _bmad-output/planning-artifacts/architecture.md#contract-tests] [Source: tools/orchestration/tests/test_task_lifecycle_cli.py]
- Keep existing event and inspect regressions green so decision-rights metadata does not break Story 6.1 and Story 6.2 action output or history readers.  
  [Source: _bmad-output/implementation-artifacts/stories/6-1-persist-a-durable-event-trail-and-history-inspectors.md] [Source: _bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md]

### Git Intelligence Summary

Recent committed work is still concentrated in controller-owned lifecycle and inspect seams, so the safest 6.3 path is to extend the same files instead of starting a new governance subsystem:

- `c3ccc6a` resolved recent review findings in lifecycle and recovery surfaces.
- `51d2554` and `e474089` reinforced controller-owned persistent state and orchestration bootstrap as the preferred authority boundary.
- The highest-signal brownfield seams remain `tools/orchestration/policy.py`, `tools/orchestration/cli/main.py`, `tools/orchestration/tasks.py`, `tools/orchestration/recovery.py`, and the existing orchestration CLI regression modules.

[Source: git log --oneline -5]

### Implementation Guardrails

- Do not add a configurable governance file, policy editor, or separate approval database in this story.
- Do not implement real `task abort`, `lock override`, or `lock release` mutation semantics; this story should make their guarded rejection explicit and structured.
- Do not weaken or bypass adapter approval or sandbox controls.
- Do not change lifecycle ordering, current-owner invariants, or recovery-run semantics just to make policy enforcement easier.
- Do not broaden into Story 6.4 privacy or audit-content governance or Story 7.1 configuration separation.

### Project Structure Notes

- This remains a brownfield, shell-first controller. Decision-rights enforcement should feel like a narrow hardening of existing command paths, not a new subsystem.
- The cleanest implementation is one shared action-policy helper plus thin CLI and lifecycle call-site enforcement.
- Human-readable and `--json` output must stay compact and explicit so operators can tell whether a command ran automatically, required confirmation, or was blocked.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/planning-artifacts/sprint-plan-2026-04-09.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md`
- `_bmad-output/implementation-artifacts/stories/5-4-resume-interrupted-recovery-from-persisted-recovery-runs.md`
- `_bmad-output/implementation-artifacts/stories/5-3-reconcile-ambiguous-ownership-and-reroute-safely.md`
- `_bmad-output/implementation-artifacts/stories/4-4-support-in-place-pause-controls-and-terminal-accessibility-modes.md`
- `tools/orchestration/policy.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/recovery.py`
- `tools/orchestration/locks.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_setup_init.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add a small shared decision-rights evaluator first, then thread it through the narrowest CLI task and recovery command paths.
- Introduce guarded confirmation behavior in red-green slices so the action envelopes and existing rationale trail stay stable.
- Add explicit blocked lock and abort command coverage, then run required validation and a BMAD QA acceptance pass before completion.

### Story Creation Notes

- Skill used: `bmad-create-story`
- Target story auto-discovered from `sprint-status.yaml` after Story 6.2 was completed.
- Inputs reviewed for this story: Epic 6 story definition, PRD security and governance requirements, architecture decision-rights model and recommended module shape, operator CLI contract, UX intervention and recovery guidance, sprint-plan notes, Story 6.2 completion notes, recent git history, and the live brownfield seams in `policy.py`, `cli/main.py`, `tasks.py`, `recovery.py`, `locks.py`, and the orchestration CLI tests.
- Validation pass applied against the BMAD create-story checklist before dev handoff: the story now includes previous-story intelligence, brownfield reuse guidance, explicit anti-scope guardrails, command-surface gaps around guarded lock verbs, and regression expectations for confirmation-gated operator actions.

### Debug Log References

- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_task_pause_transitions_active_task_to_intervention_hold_without_replacing_live_lease tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_task_resume_restores_operator_paused_task_on_same_lease tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_recovery_retry_resumes_interrupted_recovery_run_without_predecessor_lease tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_lock_override_and_release_are_explicitly_guarded_in_phase1`
- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli`
- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init`
- `python3 -m unittest discover -s tools/orchestration/tests`
- Explicit BMAD QA acceptance pass against Story 6.3 on 2026-04-10 found one remaining gap in human-readable `recovery retry` state-change visibility; it was fixed, regression-covered, and both required validation commands were rerun green.

### Completion Notes List

- Added a shared decision-rights evaluator in `tools/orchestration/policy.py` and reused it across supported task, recovery, worker, and guarded lock command paths without introducing new governance config.
- `task pause`, `task resume`, `task reroute`, `recovery retry`, and `recovery reconcile` now fail closed without `--confirm`, then preserve the existing rationale-bearing controller event path after confirmation.
- `task assign` and worker disable or quarantine results now surface policy-automatic classification, while `task abort`, `lock override`, and `lock release` return explicit structured guarded errors with no controller mutation.
- Added `lock inspect` and explicit guarded parser support for `lock override` and `lock release` so the frozen CLI contract no longer falls back to parser ambiguity for those verbs.
- Extended lifecycle regression coverage for missing confirmation, confirmed success, guarded abort and lock failures, startup recovery reroute with confirmation, and human-readable recovery output.
- Required validations passed after the QA fix: `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` and `python3 -m unittest discover -s tools/orchestration/tests`, both green at 110 tests.

### File List

- `_bmad-output/implementation-artifacts/stories/6-3-enforce-explicit-decision-rights-and-guarded-actions.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `tools/orchestration/policy.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/locks.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_setup_init.py`

### Change Log

- 2026-04-10: Created Story 6.3 with explicit decision-rights scope, shared-policy seam guidance, guarded-command expectations, validation targets, and anti-scope guardrails.
- 2026-04-10: Implemented Story 6.3 decision-rights enforcement, confirmation gates, guarded lock and abort surfaces, regression coverage, and post-fix BMAD QA acceptance.
