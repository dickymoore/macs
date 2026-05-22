# Story 1.4: Enforce scoped-secret resolution at action time

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,  
I want MACS to resolve only in-scope secret references for approved governed actions,  
so that out-of-scope secret use is blocked and attributable.

## Acceptance Criteria

1. Given a task action that targets a governed surface requiring a secret reference, when the controller authorizes execution, then MACS resolves only secret references whose scopes match the effective adapter, workflow-class, surface, and operating-profile context, and successful execution records only non-sensitive reference identifiers and decision links in audit output.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-14-enforce-scoped-secret-resolution-at-action-time] [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries] [Source: _bmad-output/planning-artifacts/architecture.md#event-record-schema]
2. Given a governed action with a missing or out-of-scope secret reference, when the controller evaluates the request, then MACS blocks the action with an audit-safe rejection reason, and no secret material is emitted into events, snapshots, or release evidence.  
   [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-14-enforce-scoped-secret-resolution-at-action-time] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements] [Source: _bmad-output/planning-artifacts/architecture.md#write-model] [Source: _bmad-output/planning-artifacts/architecture.md#audit-content-policy]

## Tasks / Subtasks

- [x] Add one controller-owned action-time secret-resolution evaluator that reuses Story 1.3 selector semantics and keeps raw secret values ephemeral. (AC: 1, 2)
  - [x] Extend `tools/orchestration/policy.py` with a helper that starts from `resolve_secret_scopes(...)`, accepts the effective `adapter_id`, `workflow_class`, `surface_id`, and `operating_profile`, and returns one bounded result for enforcement: applicable scope metadata, required secret refs, audit-safe selector context, and an overall eligible or blocked outcome.  
        [Source: tools/orchestration/policy.py] [Source: _bmad-output/implementation-artifacts/stories/1-3-define-scoped-secret-references-without-persisting-secret-material.md#previous-story-intelligence]
  - [x] Add a narrow controller-owned lookup path for `secret_ref` values that reads from existing local operator-managed environment seams instead of inventing a secret service; if a repo-local source is needed, reuse the current adapter config or worker-env seam (`config_ref`, `.codex/tmux-worker.env`) rather than creating a new policy or state file for secret values.  
        [Source: tools/orchestration/config.py] [Source: README.md#worker-tmux-defaults] [Inference from: the repo currently has `secret_scopes` metadata but no separate secret registry or vault client]
  - [x] Return stable machine-readable failure reasons for the current controller surfaces, such as no matching scope, out-of-scope selector mismatch, or unresolved `secret_ref`, and include only audit-safe fields like `surface_id`, `secret_ref`, and selector context in the returned summary.  
        [Source: tools/orchestration/policy.py] [Source: tools/orchestration/routing.py] [Inference from: existing `surface_version_*` governance rejection patterns]

- [x] Make secret requirement detection explicit at the governed-surface seam instead of inferring it from allowlists or pins. (AC: 1, 2)
  - [x] Add a small controller-readable requirement signal adjacent to the existing adapter-declared governed surfaces so MACS can tell when a surface requires a secret-backed action path; do not assume every governed surface always needs a secret, and do not infer secret requirements from `allowlisted_surfaces`, `pinned_surfaces`, or `surface_version_pins`.  
        [Source: tools/orchestration/adapters/base.py] [Source: tools/orchestration/adapters/registry.py] [Source: _bmad-output/planning-artifacts/architecture.md#adapter-contract] [Inference from: the current adapter descriptor only exposes `governed_surfaces`]
  - [x] Keep the requirement signal bounded to the current Phase 1 controller path so later stories can expand surface coverage without forcing a new secret-governance subsystem now.  
        [Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape] [Source: _bmad-output/planning-artifacts/architecture.md#decision-rights-model]

- [x] Enforce scoped-secret resolution at the selected governed-action seam before any success-shaped assignment state is persisted. (AC: 1, 2)
  - [x] Update `_assign_task_impl(...)` in `tools/orchestration/tasks.py` so once routing selects a worker, MACS evaluates whether the selected governed surface requires secret-backed execution and resolves only the matching secret refs before writing `task.assigned`, reserving the lease, or triggering adapter dispatch. A secret-scope failure must remain a `policy_blocked` outcome with no success-shaped assignment state committed first.  
        [Source: tools/orchestration/tasks.py] [Source: _bmad-output/planning-artifacts/architecture.md#write-model] [Inference from: `_assign_task_impl(...)` currently writes `task.assigned` and lease reservation before `adapter.dispatch(...)`]
  - [x] Keep routing candidate evaluation lightweight and controller-owned: it may use applicable secret-scope metadata for blocker context, but it must not resolve raw secret values for unselected workers during ranking. Resolve secret material only for the selected worker and selected governed surface immediately before dispatch.  
        [Source: tools/orchestration/routing.py] [Source: _bmad-output/planning-artifacts/prd.md#performance] [Source: _bmad-output/planning-artifacts/architecture.md#write-model]
  - [x] Preserve the current decision-rights contract for `task.assign`; secret-scope enforcement is a controller policy check inside an existing policy-automatic action, not a reason to convert assignment into an operator-confirmed secret approval flow.  
        [Source: _bmad-output/planning-artifacts/architecture.md#decision-rights-model] [Source: _bmad-output/planning-artifacts/prd.md#security--governance]

- [x] Deliver the selected secret material to the runtime through a bounded adapter interface without leaking values into controller state. (AC: 1, 2)
  - [x] Extend the adapter contract in `tools/orchestration/adapters/base.py` and only the concrete adapters that need it so controller-mediated dispatch can pass ephemeral secret-bearing context to the runtime while keeping adapters as evidence providers rather than policy authorities.  
        [Source: tools/orchestration/adapters/base.py] [Source: tools/orchestration/adapters/codex.py] [Source: _bmad-output/planning-artifacts/architecture.md#adapter-contract] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]
  - [x] If dispatch needs environment injection or wrapper commands, keep the secret-bearing path transient and local-host only. Do not persist raw secret values into `governance-policy.json`, `adapter-settings.json`, policy snapshots, SQLite state, NDJSON events, release-evidence artifacts, or test fixtures.  
        [Source: tools/orchestration/config.py] [Source: tools/orchestration/store.py] [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]
  - [x] Keep successful audit output bounded to non-sensitive identifiers such as `surface_id`, `secret_ref`, selector context, and decision or event linkage; never echo raw values, serialized environment content, or inline secret payloads through assignment payloads, event payloads, CLI output, or failure messages.  
        [Source: _bmad-output/planning-artifacts/architecture.md#event-record-schema] [Source: _bmad-output/planning-artifacts/architecture.md#audit-content-policy] [Source: tools/orchestration/history.py]

- [x] Surface secret-scope enforcement outcomes through the existing audit and inspect seams. (AC: 1, 2)
  - [x] Extend task action errors, task inspect context, and adjacent CLI formatters so operators can tell whether a governed action was blocked because no scope matched, the selected `secret_ref` could not be resolved, or a bounded secret-backed dispatch succeeded with audit-safe metadata only.  
        [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-inspect-content]
  - [x] Reuse the existing routing-decision, task-event, and event-inspection seams for traceability. If a new event is necessary, keep it small and controller-owned; do not invent a second audit or evidence store for secret-resolution outcomes.  
        [Source: tools/orchestration/routing.py] [Source: tools/orchestration/history.py] [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records]
  - [x] Keep `event inspect`, `task inspect`, and `--json` output honest about redaction level and secret-related payload summaries. Audit-safe evidence must stay inspectable without implying that MACS retained the underlying secret material.  
        [Source: tools/orchestration/history.py] [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required---json-output]

- [x] Add focused regression coverage for secret-resolution success and fail-closed secret-scope blockers without regressing Stories 1.2 and 1.3. (AC: 1, 2)
  - [x] Extend `tools/orchestration/tests/test_task_lifecycle_cli.py` with assignment success and failure cases that prove secret resolution runs only for the selected worker and surface, blocks before `task.assigned` or lease reservation when required refs are absent or unresolved, and returns stable `policy_blocked` envelopes plus next-action guidance.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: tools/orchestration/tasks.py] [Source: _bmad-output/implementation-artifacts/stories/1-2-reject-pin-drift-during-eligibility-and-governed-surface-use.md#testing-requirements]
  - [x] Extend `tools/orchestration/tests/test_inspect_context_cli.py` and, only if needed, `tools/orchestration/tests/test_setup_init.py` so event or task inspection shows audit-safe secret-ref metadata and proves that raw secret values never appear in JSON or human-readable output.  
        [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: tools/orchestration/tests/test_setup_init.py] [Source: _bmad-output/implementation-artifacts/stories/1-3-define-scoped-secret-references-without-persisting-secret-material.md#testing-requirements]
  - [x] Add a narrow no-regression case proving that when no `secret_scopes` apply, or when the selected surface does not require secret-backed execution, current governed-surface and version-pin behavior remains unchanged.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: tools/orchestration/policy.py] [Source: _bmad-output/implementation-artifacts/stories/1-2-reject-pin-drift-during-eligibility-and-governed-surface-use.md#implementation-guardrails]
  - [x] If the adapter dispatch contract changes, extend `tools/orchestration/tests/test_adapter_contracts.py` so the qualification suite remains aligned with the shared adapter contract.  
        [Source: tools/orchestration/tests/test_adapter_contracts.py] [Source: _bmad-output/planning-artifacts/architecture.md#adapter-contract]

- [x] Keep Story 1.4 bounded to action-time enforcement of scoped secret references. (AC: 1, 2)
  - [x] Do not add a hosted vault, enterprise IAM flow, repo-wide secret manager, diff/review checkpoint logic, or release-review evidence expansion in this story.  
        [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#epic-2-prove-and-enforce-baseline-review-before-risky-completion] [Source: _bmad-output/planning-artifacts/prd.md#security--governance]
  - [x] Do not reinterpret `allowlisted_surfaces`, `pinned_surfaces`, or `surface_version_pins` as secret sources, secret requirements, or implicit secret-scope matches.  
        [Source: _bmad-output/implementation-artifacts/stories/1-3-define-scoped-secret-references-without-persisting-secret-material.md#implementation-guardrails]
  - [x] Do not broaden into automatic remote-operation approval, secret rotation workflows, or permanent secret-bearing worker bootstrap files authored by the controller.  
        [Source: _bmad-output/planning-artifacts/architecture.md#product-safety-policies] [Inference from: current repo-local config domains and `tmux-worker.env` patterns]

## Dev Notes

### Story Intent

This story is the enforcement follow-on to Story 1.3. Story 1.3 made `secret_scopes` controller-owned, normalized, and inspectable; Story 1.4 must turn that read model into a fail-closed action-time control so governed actions resolve only in-scope secret refs and block safely before unsafe execution begins.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#story-14-enforce-scoped-secret-resolution-at-action-time]  
[Source: _bmad-output/implementation-artifacts/stories/1-3-define-scoped-secret-references-without-persisting-secret-material.md#story-intent]

### Governance-Hardening Lane Boundaries

- Use only `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml` for lane tracking.
- Do not edit the historical orchestration tracker at `_bmad-output/implementation-artifacts/sprint-status.yaml`.
- Do not edit the guided-onboarding tracker at `_bmad-output/implementation-artifacts/sprint-status-macs-guided-onboarding.yaml`.
- Treat this as follow-on governance hardening implied by the 2026-04-14 correction pass, not a reopening of the completed orchestration sprint and not part of guided onboarding.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#overview]  
[Source: _bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml]

### Previous Story Intelligence

- Story 1.3 already delivered `secret_scopes`, `_normalize_secret_scopes(...)`, `resolve_secret_scopes(...)`, governance snapshot summaries, and adapter-inspect surfacing of applicable secret scopes. Reuse those selector semantics instead of re-deriving matching rules in tasks or adapters.
- Story 1.2 already proved the pattern for fail-closed governance enforcement inside controller-owned routing and assignment flows, with stable machine-readable reasons, compact blocker text, and inspectable routing context.
- Story 1.1 and Story 1.3 already established the active governance snapshot traceability pattern. Story 1.4 should keep secret-enforcement decisions traceable without creating a second secret-audit storage path.
- Story 6.4 and Story 7.1 already established the repo-local governance policy and config-domain seams. Secret enforcement should stay inside those local controller-owned surfaces rather than introducing a parallel configuration subsystem.

[Source: _bmad-output/implementation-artifacts/stories/1-3-define-scoped-secret-references-without-persisting-secret-material.md#previous-story-intelligence]  
[Source: _bmad-output/implementation-artifacts/stories/1-2-reject-pin-drift-during-eligibility-and-governed-surface-use.md#previous-story-intelligence]  
[Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md#brownfield-reuse-guidance]  
[Source: _bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md#brownfield-reuse-guidance]

### Brownfield Continuity

- `tools/orchestration/policy.py` already normalizes and resolves applicable secret scopes, but it stops at metadata and inspection; there is no action-time secret-resolution helper or secret-value lookup yet.
- `tools/orchestration/tasks.py` currently persists `task.assigned` and reserves the new lease before `adapter.dispatch(...)`. If secret resolution is bolted onto the adapter call without moving policy validation earlier, MACS will record success-shaped assignment state before the secret-scope policy check completes.
- `tools/orchestration/routing.py` already persists rejected-worker reasons, governance summaries, blocking conditions, and next-action text through `routing.decision_recorded`; that is the safest place to keep secret-scope blocker context inspectable without inventing a second envelope.
- `tools/orchestration/adapters/base.py` currently exposes a minimal dispatch contract that accepts only the assignment payload. Any secret-bearing extension must stay narrow, explicit, and testable.
- `tools/orchestration/config.py` and the current adapter settings already point to `.codex/tmux-worker.env` as the repo-local worker environment seam. There is no separate controller-owned secret registry or vault client in the current brownfield implementation.

[Source: tools/orchestration/policy.py]  
[Source: tools/orchestration/tasks.py]  
[Source: tools/orchestration/routing.py]  
[Source: tools/orchestration/adapters/base.py]  
[Source: tools/orchestration/config.py]  
[Source: README.md#worker-tmux-defaults]

### Action-Time Secret Resolution Baseline

- The current repo has secret-scope metadata but no dedicated secret-value registry. If a lookup source is required, keep it local and operator-managed by reusing process environment or the existing worker-env seam instead of creating a new secret service.  
  [Source: tools/orchestration/config.py] [Source: README.md#worker-tmux-defaults] [Inference from: current repo structure and absence of a secret registry]
- Determine whether a governed surface requires a secret through explicit controller-readable surface metadata adjacent to the adapter descriptor, not by guessing from allowlists, pins, or secret-scope presence alone.  
  [Source: tools/orchestration/adapters/base.py] [Inference from: the current descriptor does not declare secret requirements]
- Resolve raw secret values only for the selected worker and the selected governed surface immediately before dispatch. Do not retrieve secret material while ranking all routing candidates.  
  [Source: tools/orchestration/routing.py] [Source: _bmad-output/planning-artifacts/architecture.md#write-model]
- When required scope or value resolution fails, block before assignment state mutation and keep the failure attributable through audit-safe metadata only.  
  [Source: tools/orchestration/tasks.py] [Source: _bmad-output/planning-artifacts/architecture.md#event-record-schema]

### Technical Requirements

- Keep secret-scope enforcement controller-owned and repo-local; adapters may receive ephemeral resolved material for execution, but they must not decide scope eligibility or define secret-matching semantics.  
  [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]
- Reuse `resolve_secret_scopes(...)` and the shipping operating-profile vocabulary from Stories 1.1 and 1.3; `primary_plus_fallback` remains the default and `full_hybrid` remains opt-in.  
  [Source: tools/orchestration/policy.py] [Source: _bmad-output/planning-artifacts/architecture.md#operating-profiles]
- If a selected governed action requires a secret and no scope matches, or the selected `secret_ref` cannot be resolved from the permitted local source, fail closed with a stable `policy_blocked` result.  
  [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#structured-error-codes]
- Never persist raw secret values in governance policy files, policy snapshots, controller state tables, NDJSON exports, release-evidence artifacts, CLI output, or test fixtures.  
  [Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#nonfunctional-requirements] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]
- Preserve the current task action JSON and human-readable contract shapes, decision-rights classes, and CLI error semantics.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#global-rules] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required---json-output] [Source: _bmad-output/planning-artifacts/architecture.md#decision-rights-model]
- Keep implementation Python-stdlib-only and compatible with the current repo-local config-domain and tmux-backed adapter seams.  
  [Source: _bmad-output/project-context.md#technology-stack--versions] [Source: _bmad-output/project-context.md#framework-specific-rules]

### Architecture Compliance

- Preserve the write model order: read authoritative state, validate policy and secret scope, then persist intent and state transitions, then perform the secret-bearing side effect.  
  [Source: _bmad-output/planning-artifacts/architecture.md#write-model]
- Treat adapter outputs and runtime behavior as bounded evidence. Secret eligibility, scope matching, and audit shape stay controller-owned.  
  [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries] [Source: _bmad-output/planning-artifacts/prd.md#security--governance]
- Keep operator surfaces compact and truthful: show controller truth first, then bounded secret-scope enforcement detail or the next remediation action.  
  [Source: _bmad-output/planning-artifacts/architecture.md#ux-backing-requirements] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output]
- Reuse existing evidence and event seams for traceability instead of adding a secret-only persistence layer.  
  [Source: _bmad-output/planning-artifacts/architecture.md#supporting-evidence-records] [Source: tools/orchestration/history.py]

### Suggested Implementation Shape

- Add a small helper in `tools/orchestration/policy.py` that combines:
  - `resolve_secret_scopes(...)`
  - selected worker or adapter context
  - governed-surface secret requirement metadata
  - one local secret lookup strategy
  - an audit-safe outcome summary
- Use that helper in `tools/orchestration/tasks.py` after routing has selected the worker and before `task.assigned` is written, so secret-scope policy failures remain policy blocks rather than side-effect failures.
- Keep routing candidate selection mostly unchanged, except for carrying enough secret-scope applicability context to explain blockers if the chosen governed action later fails secret resolution.
- Extend the adapter dispatch seam only as much as needed to pass ephemeral secret-bearing context to the runtime. Prefer transient in-memory or process-level injection over file writes, and never store secret values in controller-managed records.
- Reuse current task, routing, and event-inspection surfaces in `tools/orchestration/cli/main.py` and `tools/orchestration/history.py` so secret enforcement is inspectable without a new command family.

[Inference from: tools/orchestration/policy.py, tools/orchestration/tasks.py, tools/orchestration/routing.py, tools/orchestration/adapters/base.py, and tools/orchestration/cli/main.py]  
[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]

### File Structure Requirements

- Primary implementation files for this story:
  - `tools/orchestration/policy.py`
  - `tools/orchestration/tasks.py`
  - `tools/orchestration/cli/main.py`
  - `tools/orchestration/adapters/base.py`
  - `tools/orchestration/adapters/codex.py`
  - `tools/orchestration/adapters/registry.py`
  - `tools/orchestration/tests/test_task_lifecycle_cli.py`
  - `tools/orchestration/tests/test_inspect_context_cli.py`
- Optional touch points only if the final action-time shape needs them:
  - `tools/orchestration/routing.py`
  - `tools/orchestration/history.py`
  - `tools/orchestration/config.py`
  - `tools/orchestration/tests/test_setup_init.py`
  - `tools/orchestration/tests/test_adapter_contracts.py`
- Avoid broadening into release-gate reporting, a new secret-management package, or non-local controller infrastructure unless a tiny helper extraction is materially clearer than extending the current seams.

[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]  
[Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md#file-structure-requirements]

### Testing Requirements

- Extend the existing lifecycle and inspect regression seams instead of creating a governance-hardening-only harness.  
  [Source: _bmad-output/planning-artifacts/architecture.md#testing-principles]
- Add explicit coverage for:
  - successful selected-worker dispatch when an in-scope secret ref resolves
  - policy-blocked assignment when no scope matches a required surface
  - policy-blocked assignment when the selected `secret_ref` cannot be resolved from the permitted local source
  - audit-safe event, task inspect, and error output that includes `secret_ref` metadata but never raw secret material
  - no-regression behavior when no secret scope applies or the selected surface does not require secret-backed execution  
  [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: tools/orchestration/tests/test_inspect_context_cli.py]
- If the adapter dispatch contract changes, keep the shared adapter contract and qualification tests green.  
  [Source: tools/orchestration/tests/test_adapter_contracts.py] [Source: _bmad-output/planning-artifacts/architecture.md#first-class-adapter-qualification]
- Before marking implementation done, run the focused controller CLI regressions plus full orchestration unittest discovery.  
  [Source: _bmad-output/project-context.md#testing-rules]

### Git Intelligence Summary

- Recent committed history still centers MACS work in controller-owned policy, task lifecycle, CLI, and test seams, which is the safest path for Story 1.4.
- The current working tree already contains uncommitted edits in shared governance, docs, CLI, routing, worker, setup, and test files.
- Story 1.4 is likely to touch several of those same shared seams. Work with those edits and do not revert or overwrite unrelated in-flight changes while implementing the governance-hardening slice.

[Source: git log --oneline -5]  
[Inference from current git status]

### Implementation Guardrails

- Do not persist raw secret values in any repo-managed JSON file, SQLite record, NDJSON event, release-evidence artifact, or test fixture.
- Do not add a second governance-policy file, secret database, hosted vault client, or remote secret service.
- Do not resolve raw secret material during ranking of unselected candidates.
- Do not let adapter code become the authority for secret scope matching, approval, or auditability.
- Do not reinterpret governed-surface allowlists or version pins as implicit secret configuration.
- Do not modify the historical orchestration sprint tracker or the guided-onboarding tracker as part of the implementation.
- Do not revert unrelated working-tree changes in shared policy, task, CLI, adapter, config, or test files.

[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#additional-requirements]  
[Source: _bmad-output/project-context.md#development-workflow-rules]

### Project Structure Notes

- This remains a brownfield, shell-first, Python-stdlib-only orchestration controller.
- The governance-hardening lane is intentionally separate from the historical orchestration sprint and the guided-onboarding initiative, even though all story files live in the shared stories directory.
- The safest implementation path is a narrow extension of current policy, task-assignment, adapter-dispatch, and inspect seams so scoped-secret enforcement stays controller-owned and auditable without introducing a new secret-management subsystem.

[Source: _bmad-output/project-context.md#development-workflow-rules]  
[Source: _bmad-output/planning-artifacts/epics-delta-macs-core-orchestration-governance-hardening-2026-04-14.md#overview]

### References

- `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`
- `_bmad-output/implementation-artifacts/stories/1-4-enforce-scoped-secret-resolution-at-action-time.md`
- `tools/orchestration/policy.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/routing.py`
- `tools/orchestration/history.py`
- `tools/orchestration/config.py`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/adapters/codex.py`
- `tools/orchestration/adapters/registry.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_adapter_contracts.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Add a controller-owned secret-resolution helper that reuses Story 1.3 scope matching and one narrow local `secret_ref` lookup path.
- Move secret-scope enforcement into the pre-dispatch portion of `_assign_task_impl(...)` so policy blocks happen before success-shaped assignment state is persisted.
- Extend the adapter dispatch seam only as much as needed for ephemeral secret delivery and add audit-safe task/event inspection coverage.
- Keep the change set limited to the governance-hardening lane and the current controller-owned task, policy, adapter, and inspect seams.

### Debug Log References

- Story authored with `bmad-create-story`.
- Authoritative tracker: `_bmad-output/implementation-artifacts/sprint-status-macs-core-orchestration-governance-hardening.yaml`.
- Planning sources reviewed: the governance-hardening delta epics file, corrected PRD, corrected architecture, operator CLI contract, 2026-04-14 sprint change proposal, and project context.
- Brownfield continuity reviewed: Stories 6.4, 7.1, 1.1, 1.2, and 1.3; current `policy.py`, `tasks.py`, `routing.py`, `config.py`, adapter contract files, relevant orchestration tests, `git log --oneline -5`, and the current `git status --short`.
- External web research was not required because this story is repo-local governance and task-dispatch work, not third-party API integration.
- 2026-04-14T21:46:20+01:00: Development started under the governance-hardening lane tracker; story status moved to `in-progress` before implementation edits.
- 2026-04-14T22:07:41+01:00: Added controller-owned action-time secret resolution, bounded repo-local env lookup, explicit governed-surface secret requirement metadata, pre-assignment enforcement, audit-safe routing or task or event summaries, and focused regression coverage.
- 2026-04-14T22:07:41+01:00: Full orchestration discovery initially failed because the existing pinned-governed-surface success path must remain unchanged when no scoped secret policy applies; adjusted enforcement so secret-backed gating only activates when a matching surface has scoped-secret policy configured, then reran the full suite to green.

### Completion Notes

- Story 1.4 now resolves scoped secret refs only for the selected worker and selected governed surface through the existing repo-local env seam, blocks before `task.assigned` or lease reservation on selector mismatch or unresolved refs, and keeps raw values out of controller state, events, CLI output, and pane payloads.
- The adapter seam now carries only bounded secret-delivery metadata while the controller remains authoritative for scope matching, failure reasons, and audit shape; current governed-surface flows remain unchanged when no secret-backed policy applies to the selected surface.

### Change Log

- 2026-04-14: Implemented controller-owned action-time secret resolution and repo-local env lookup in `policy.py` and `config.py`, plus explicit governed-surface secret requirement metadata in the adapter descriptor seam.
- 2026-04-14: Moved secret enforcement into the pre-dispatch portion of `_assign_task_impl(...)`, persisted audit-safe secret-resolution summaries through routing and task or event inspection, and added CLI renderers for those summaries.
- 2026-04-14: Added lifecycle, inspect, and adapter-contract regressions covering selected-worker-only resolution, fail-closed blockers, raw-secret redaction, and the no-regression path when scoped-secret policy does not apply.

### Test Record

- Focused regressions:
  - `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_task_assign_rejects_out_of_scope_secret_selector_before_assignment_state tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_task_assign_rejects_unresolved_secret_ref_before_assignment_and_lease_reservation tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_task_assign_resolves_secret_only_for_selected_worker_and_keeps_raw_values_out_of_audit tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_task_assign_keeps_non_governed_or_non_secret_backed_paths_unchanged tools.orchestration.tests.test_task_lifecycle_cli.TaskLifecycleCliContractTests.test_task_assign_allows_pinned_governed_surface_for_matching_adapter tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_task_inspect_surfaces_audit_safe_secret_resolution_metadata_without_raw_values tools.orchestration.tests.test_inspect_context_cli.InspectContextCliContractTests.test_event_inspect_surfaces_secret_resolution_metadata_without_raw_values tools.orchestration.tests.test_adapter_contracts.AdapterContractTests.test_dispatch_accepts_bounded_secret_context_without_exposing_raw_values` -> `Ran 8 tests in 2.429s` / `OK`
- Full suite:
  - `python3 -m unittest discover -s tools/orchestration/tests` -> `Ran 195 tests in 65.005s` / `OK`
