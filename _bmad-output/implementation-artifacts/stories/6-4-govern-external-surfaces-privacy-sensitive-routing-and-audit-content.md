# Story 6.4: Govern external surfaces, privacy-sensitive routing, and audit content

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,
I want MCP or similar integrations, privacy-sensitive workflows, and rich audit capture to be policy-controlled,
So that governance defaults remain conservative and inspectable.

## Acceptance Criteria

1. MACS introduces one repo-local governance policy surface, separate from the existing routing-policy defaults but still stored under `.codex/orchestration`, that covers governed integration surfaces and audit-content capture. The controller bootstraps and loads this policy authoritatively, records its snapshot locally, and makes the active governance defaults inspectable without requiring code edits or a broad Story 7.1 configuration domain split.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-64-govern-external-surfaces-privacy-sensitive-routing-and-audit-content] [Source: _bmad-output/planning-artifacts/prd.md#installation-configuration-and-adoption] [Source: _bmad-output/planning-artifacts/architecture.md#repository-default-decisions]
2. Governed external surfaces are explicit and conservative by default. Adapter or runtime descriptors can declare governed surfaces such as MCP-backed or tool-invocation trust boundaries, governance policy can allowlist or pin them, and routing or inspection output makes it clear when a worker is eligible, rejected, or constrained because governed surfaces are not permitted under the active policy.  
   [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/planning-artifacts/prd.md#functional-requirements] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries] [Source: _bmad-output/planning-artifacts/epics.md#fr34-the-system-can-allowlist-or-pin-governed-integration-surfaces-such-as-mcp-backed-tool-access-where-relevant-to-runtime-operation]
3. Privacy-sensitive and offline workflow routing remains controller-owned and policy-visible. Privacy-sensitive work still prefers local or runtime-neutral workers by default, explicit policy can further constrain or relax governed-surface use for those classes, and task, routing, or overview inspection surfaces make the blocking condition or next action legible when non-local or non-allowlisted workers are rejected.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-64-govern-external-surfaces-privacy-sensitive-routing-and-audit-content] [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/planning-artifacts/architecture.md#repository-default-decisions] [Source: _bmad-output/planning-artifacts/architecture.md#routing-outcome-contract]
4. Audit metadata and optional rich content are governed separately before persistence. Event and recovery history continue to retain default metadata such as actor identity, state transitions, routing rationale, intervention rationale, and affected refs, while optional prompt content, terminal snapshots, and tool outputs are either omitted or redacted according to policy before they are written to SQLite or NDJSON export. Read surfaces preserve or expose the resulting `redaction_level` without pretending omitted content was retained.  
   [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/planning-artifacts/prd.md#observability--auditability] [Source: _bmad-output/planning-artifacts/architecture.md#audit-content-policy]
5. Regression coverage proves governance defaults without regressing Story 3.1 workflow routing, Story 3.2 routing explainability, Story 6.1 durable event inspection, Story 6.2 rationale continuity, or Story 6.3 decision-rights enforcement and frozen CLI envelopes.  
   [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/implementation-artifacts/stories/3-1-configure-workflow-aware-routing-policy.md] [Source: _bmad-output/implementation-artifacts/stories/3-2-record-explainable-assignment-decisions.md] [Source: _bmad-output/implementation-artifacts/stories/6-1-persist-a-durable-event-trail-and-history-inspectors.md] [Source: _bmad-output/implementation-artifacts/stories/6-3-enforce-explicit-decision-rights-and-guarded-actions.md]

## Tasks / Subtasks

- [x] Add a narrow repo-local governance policy bootstrap and loader without broadening into Story 7.1. (AC: 1)
  - [x] Extend `tools/orchestration/policy.py` with a dedicated governance policy default and loader under `.codex/orchestration`, plus snapshot capture that reuses the existing local policy bootstrap path instead of introducing remote config or a new authority source.  
        [Source: tools/orchestration/policy.py] [Source: tools/orchestration/session.py] [Source: _bmad-output/planning-artifacts/prd.md#installation-configuration-and-adoption]
  - [x] Ensure `setup init` creates or preserves the repo-local governance policy file and exposes enough status for operators and tests to confirm it exists, while keeping full configuration separation out of scope until Story 7.1.  
        [Source: tools/orchestration/session.py] [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/tests/test_setup_init.py]

- [x] Govern adapter-declared external surfaces conservatively and make the result inspectable. (AC: 2, 3)
  - [x] Extend adapter descriptors or registry metadata to declare governed surfaces or trust-boundary facts in a controller-owned way, so adapters can describe MCP-like or tool-backed surfaces without becoming policy authorities themselves.  
        [Source: tools/orchestration/adapters/base.py] [Source: tools/orchestration/adapters/registry.py] [Source: _bmad-output/project-context.md#critical-dont-miss-rules]
  - [x] Extend routing evaluation so governed-surface allowlisting or pinning participates in worker eligibility and rejection reasons alongside existing freshness, state, capability, and privacy-sensitive local-only rules.  
        [Source: tools/orchestration/routing.py] [Source: _bmad-output/planning-artifacts/architecture.md#routing-outcome-contract]
  - [x] Surface the active governed-surface result through existing inspectable seams such as `adapter inspect`, `task inspect`, `worker inspect`, or `overview show` without inventing a broad config editor or a new remote-governance command family.  
        [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/overview.py] [Source: tools/orchestration/history.py]

- [x] Preserve local-first routing for privacy-sensitive work and make governance blockers explicit. (AC: 2, 3)
  - [x] Keep `privacy_sensitive_offline` local-first behavior intact, and, where policy adds governed-surface constraints, reject unsafe candidates with stable machine-readable reasons instead of opaque routing failure.  
        [Source: tools/orchestration/routing.py] [Source: tools/orchestration/tests/test_setup_init.py]
  - [x] Ensure task and overview read surfaces explain whether a privacy-sensitive route was blocked by non-local runtime, non-allowlisted governed surface, or both, and point to the next safe operator action when possible.  
        [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/overview.py] [Source: tools/orchestration/cli/main.py]

- [x] Add policy-aware audit-content retention with redaction or omission before persistence. (AC: 4)
  - [x] Introduce one controller-owned helper for audit-content policy evaluation so event writers can distinguish default metadata from optional rich content such as prompts, terminal snapshots, and tool outputs before they persist anything.  
        [Source: tools/orchestration/store.py] [Source: tools/orchestration/policy.py] [Source: _bmad-output/planning-artifacts/architecture.md#audit-content-policy]
  - [x] Apply that helper to the narrowest existing event paths that carry optional rich content first, preserving current metadata and rationale trails while marking redacted or omitted content explicitly through `payload` and `redaction_level`.  
        [Source: tools/orchestration/tasks.py] [Source: tools/orchestration/recovery.py] [Source: tools/orchestration/history.py]
  - [x] Keep event and inspect readers honest: `event inspect`, `event list`, and downstream task or lease context should reflect the stored redaction state rather than reconstructing removed content at read time.  
        [Source: tools/orchestration/history.py] [Source: tools/orchestration/cli/main.py]

- [x] Keep the story bounded to conservative governance defaults, not broad configuration or new remote features. (AC: 1, 2, 4)
  - [x] Do not add remote controller operation, automatic pushes, autonomous external actions, adapter-driven routing authority, or full policy-editing UX in this story.  
        [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries]
  - [x] Do not build retention jobs, enterprise IAM, multi-host storage, or transcript-search subsystems; the contract here is repo-local defaults, inspectability, and pre-persistence redaction or omission.  
        [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/project-context.md#framework-specific-rules]

- [x] Add regression coverage for governance policy bootstrap, governed-surface routing, and audit redaction behavior. (AC: 5)
  - [x] Extend `tools/orchestration/tests/test_setup_init.py` with bootstrap coverage proving the repo-local governance policy is created and that privacy-sensitive routing plus governed-surface policy rejects or prefers workers as intended.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/session.py]
  - [x] Extend `tools/orchestration/tests/test_task_lifecycle_cli.py` with black-box cases proving governed-surface restrictions affect assignment outcomes and that JSON envelopes remain stable when routes are rejected or constrained by governance policy.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: tools/orchestration/cli/main.py]
  - [x] Extend `tools/orchestration/tests/test_inspect_context_cli.py` with event and inspect assertions showing redaction or omission is visible, inspectable, and correlated to the active governance defaults without leaking removed rich content.  
        [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: tools/orchestration/history.py]

## Dev Notes

### Previous Story Intelligence

- Story 6.3 established `tools/orchestration/policy.py` as the shared repo-local policy seam and explicitly deferred governance expansion to Story 6.4. Reuse that seam rather than inventing a second controller policy subsystem.  
  [Source: _bmad-output/implementation-artifacts/stories/6-3-enforce-explicit-decision-rights-and-guarded-actions.md]
- Story 6.3 also hardened CLI output and structured errors around decision-rights metadata. Keep those top-level envelopes stable while adding governance context to result payloads or read surfaces.  
  [Source: _bmad-output/implementation-artifacts/stories/6-3-enforce-explicit-decision-rights-and-guarded-actions.md]
- Recent work stayed concentrated in `policy.py`, `cli/main.py`, `tasks.py`, `recovery.py`, and the existing CLI regression modules. Story 6.4 should extend those same brownfield seams first.  
  [Source: git log --oneline -5]

### Brownfield Reuse Guidance

- `tools/orchestration/policy.py` already bootstraps repo-local routing policy and records policy snapshots. The safest 6.4 path is to extend that module for governance defaults and audit-content policy evaluation instead of creating a separate manager.  
  [Source: tools/orchestration/policy.py]
- `tools/orchestration/session.py` already owns repo-local bootstrap. Keep governance-policy creation there so `setup init` remains the single authoritative repo-local initializer.  
  [Source: tools/orchestration/session.py]
- `tools/orchestration/routing.py` already records rejected workers and policy metadata. Governed-surface checks should become another controller-owned rejection reason in that same evaluation output.  
  [Source: tools/orchestration/routing.py]
- `tools/orchestration/store.py` already stores `redaction_level` per event. Use that existing schema to distinguish retained metadata from redacted or omitted rich content rather than adding a second event store.  
  [Source: tools/orchestration/store.py]
- `tools/orchestration/history.py` and `tools/orchestration/cli/main.py` already expose event payloads and `redaction_level`; extend those read paths to stay truthful about removed content.  
  [Source: tools/orchestration/history.py] [Source: tools/orchestration/cli/main.py]

### Technical Requirements

- Governance policy must remain repo-local under `.codex/orchestration` and controller-owned. No remote config fetch, central service, or adapter-authored policy source is allowed in this story.
- Governed-surface enforcement must be additive to current routing checks: state, freshness, interruptibility, required capabilities, privacy-sensitive local-only rules, and lock compatibility still apply.
- Audit-content policy must separate always-retained metadata from optional rich content and must apply redaction or omission before write-time persistence to SQLite and NDJSON export.
- Read surfaces must never synthesize omitted prompt, terminal, or tool-output content after policy has removed it.

### Architecture Compliance Notes

- Preserve the architecture’s write model: read authoritative state, validate invariants and policy, persist mutations and event records, then perform side effects or follow-up evidence handling.  
  [Source: _bmad-output/planning-artifacts/architecture.md#write-model]
- Treat adapters as semi-trusted evidence providers. They may declare governed surfaces, but they must not decide whether those surfaces are allowed.  
  [Source: _bmad-output/planning-artifacts/architecture.md#trust-boundaries] [Source: _bmad-output/project-context.md#framework-specific-rules]
- Keep privacy-sensitive routing conservative by default: local or runtime-neutral first unless policy explicitly relaxes it.  
  [Source: _bmad-output/planning-artifacts/architecture.md#repository-default-decisions]

### File Structure Requirements

- Prefer extending these files before introducing new modules:
  - `tools/orchestration/policy.py`
  - `tools/orchestration/session.py`
  - `tools/orchestration/routing.py`
  - `tools/orchestration/adapters/base.py`
  - `tools/orchestration/adapters/registry.py`
  - `tools/orchestration/store.py`
  - `tools/orchestration/history.py`
  - `tools/orchestration/cli/main.py`
  - `tools/orchestration/tests/test_setup_init.py`
  - `tools/orchestration/tests/test_task_lifecycle_cli.py`
  - `tools/orchestration/tests/test_inspect_context_cli.py`
- Only add a new module if the policy or redaction helper becomes materially clearer there; otherwise keep the change set close to the existing controller seams.

### Testing Requirements

- Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused required validation surface.  
  [Source: _bmad-output/implementation-artifacts/stories/6-3-enforce-explicit-decision-rights-and-guarded-actions.md#debug-log-references]
- Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Add failure-containment coverage, not just happy paths: governed-surface rejection, privacy-sensitive routing blockers, and audit-content redaction or omission all need regression tests.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Keep Story 6.1 and 6.3 contract surfaces green so event inspection and action envelopes remain stable while governance metadata grows.  
  [Source: _bmad-output/implementation-artifacts/stories/6-1-persist-a-durable-event-trail-and-history-inspectors.md] [Source: _bmad-output/implementation-artifacts/stories/6-3-enforce-explicit-decision-rights-and-guarded-actions.md]

### Git Intelligence Summary

- `c3ccc6a` resolved the most recent review findings and kept changes inside controller-owned lifecycle and inspect seams.
- `51d2554` and `e474089` reinforced repo-local orchestration bootstrap and durable controller state as the preferred authority boundary.
- No recent commit suggests introducing third-party dependencies or a new config subsystem, which aligns with the conservative 6.4 path.

### Implementation Guardrails

- Do not broaden this story into Story 7.1 full configuration separation or editing UX.
- Do not implement actual MCP integrations, remote network operations, or automatic push or deploy behavior.
- Do not add a retention sweeper, transcript indexing, or a second rich-content database.
- Do not bypass or weaken existing decision-rights, rationale-causation links, or current routing explainability.
- Do not change adapter outputs into control-plane truth; governed-surface declarations are evidence, not authority.

### Project Structure Notes

- This remains a brownfield, shell-first orchestration controller with Python stdlib-only orchestration modules.
- The intended 6.4 footprint is a narrow governance-policy extension plus wiring through routing, inspect, and event persistence surfaces.
- Human-readable output should stay compact and explicit, while `--json` output should preserve current top-level envelope structure.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/planning-artifacts/sprint-plan-2026-04-09.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/6-3-enforce-explicit-decision-rights-and-guarded-actions.md`
- `_bmad-output/implementation-artifacts/stories/6-2-preserve-intervention-rationale-across-recovery-and-reassignment.md`
- `_bmad-output/implementation-artifacts/stories/3-2-record-explainable-assignment-decisions.md`
- `_bmad-output/implementation-artifacts/stories/3-1-configure-workflow-aware-routing-policy.md`
- `tools/orchestration/policy.py`
- `tools/orchestration/session.py`
- `tools/orchestration/routing.py`
- `tools/orchestration/store.py`
- `tools/orchestration/history.py`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/adapters/registry.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Bootstrap repo-local governance defaults first, then thread governed-surface policy into the narrowest routing and inspect seams.
- Add audit-content policy helpers in small red-green slices so metadata retention stays stable while optional rich content becomes policy-aware.
- Finish with the required validation commands and an explicit BMAD QA acceptance pass before marking the story done.

### Story Creation Notes

- Skill used: `bmad-create-story`
- Target story auto-discovered from `sprint-status.yaml` after Story 6.3 was completed.
- Inputs reviewed for this story: Epic 6 story definition, PRD governance and audit requirements, architecture repository defaults, audit-content policy and trust-boundary sections, sprint plan notes, Story 6.3 completion notes, recent git history, and the live brownfield seams in `policy.py`, `session.py`, `routing.py`, `store.py`, `history.py`, `cli/main.py`, adapter descriptors, and orchestration CLI tests.
- External web research was not required for this story because the implementation is repo-local, Python-stdlib-only controller work rather than version-sensitive third-party integration work.
- Validation pass applied against the BMAD create-story checklist before dev handoff: the story now includes previous-story intelligence, anti-scope guardrails, exact brownfield reuse seams, explicit bootstrap expectations for governance policy, and regression expectations for governed-surface routing plus audit redaction behavior.

### Debug Log References

- Story creation validation performed against `.agents/skills/bmad-create-story/checklist.md`
- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init`
- `python3 -m unittest discover -s tools/orchestration/tests`
- Explicit BMAD QA acceptance pass against Story 6.4 on 2026-04-10 found one pre-acceptance gap in regression proof for governed-surface pinning; a dedicated pinning contract test was added, both validation commands were rerun green, and no findings remained.

### Completion Notes List

- Added repo-local `governance-policy.json` bootstrap and snapshot capture alongside the existing routing policy without broadening into Story 7.1 configuration separation.
- Declared governed surfaces on governed adapters, enforced allowlist and pin checks during routing, persisted failed routing decisions for inspectability, and surfaced governance status through `setup init`, `adapter inspect`, `worker inspect`, `task inspect`, and routing error output.
- Added policy-aware audit-content handling for assignment prompt content, with omit, redact, and retain modes applied before event persistence and surfaced through `redaction_level` plus inspect output.
- Extended regression coverage for governance bootstrap, privacy-sensitive blocker reporting, governed-surface rejection and pinning, adapter governance inspection, and audit-content omission, retention, and redaction.
- Required validation and the explicit BMAD QA acceptance pass both finished green with no remaining findings.

### File List

- `_bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `tools/orchestration/policy.py`
- `tools/orchestration/session.py`
- `tools/orchestration/routing.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/history.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/adapters/codex.py`
- `tools/orchestration/adapters/registry.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_setup_init.py`

### Change Log

- 2026-04-10: Created Story 6.4 with repo-local governance policy scope, governed-surface routing guardrails, audit-content retention expectations, regression targets, and anti-scope boundaries.
- 2026-04-10: Implemented Story 6.4 governance policy bootstrap, governed-surface routing enforcement, audit-content redaction or omission handling, regression coverage, and post-fix BMAD QA acceptance.
