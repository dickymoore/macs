# Adapter Qualification Report

## 1. Adapter Identity

- Adapter name: claude
- Runtime type: claude
- Adapter version or revision: repo-local
- Maintainer: eng
- Qualification date: 2026-04-14T09:49:48+00:00
- Outcome: `PASS`
- Proposed status: `first-class`

## 2. Scope

- Runtime binary or backend tested: claude
- Operating environment: local-host Phase 1 release gate
- Test fixtures used: shared contract validation plus descriptor-driven qualification summary
- Known unsupported features: token_budget, structured_progress

## 3. Contract Surface Check

| Contract area | Required expectation | Evidence | Result |
| --- | --- | --- | --- |
| Identity normalization | Stable worker identity exposed | shared descriptor contract | PASS |
| Capability declaration | Required and optional capabilities separated | capability model and unsupported feature declaration | PASS |
| Health and freshness | Timestamps and freshness metadata exposed | required facts include freshness timestamp | PASS |
| Interruptibility | Supported actions or explicit unsupported declaration | supported operations list | PASS |
| Permission surface | Approval/sandbox signals preserved where available | optional enrichments: none | PASS |
| Evidence envelope | Facts, soft signals, and claims remain bounded | shared evidence envelope contract | PASS |
| Authority boundary | Adapter cannot mutate authoritative state | controller-owned store remains external to adapter | PASS |

## 4. First-Class Qualification Gates

### Required Contract Support

- Passes shared contract tests: yes
- Required signals exposed: yes
- Unsupported features declared explicitly: yes

### Degraded-Mode Behavior

- Missing signals render as `UNAVAILABLE` or `NOT EXPOSED`: yes
- Degraded health or stale evidence classification supported: yes
- Safe routing degradation documented: yes

### Intervention Support

- Interrupt support: yes
- Pause/hold support: controller-mediated
- Capture or inspection hooks: yes
- Unsupported intervention behaviors: token_budget, structured_progress

### Routing-Evidence Support

- Capability fit evidence: declared capabilities
- Freshness evidence: supported
- Health evidence: supported
- Budget/session evidence where available: declared via unsupported feature list when absent
- Confidence or uncertainty markers: controller-visible

### Validation Coverage

- Unit or contract coverage reference: `python3 -m unittest tools.orchestration.tests.test_adapter_contracts`
- Integration coverage reference: `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli`
- Failure-drill relevance covered: release gate references the shared failure-drill suite

## 5. Evidence Summary

### Controller Facts

- Worker registration result: declared by shared adapter descriptor
- Classification result: eligible for Phase 1 release gate
- Eligibility for new assignments: yes

### Adapter Signals

| Signal | Value or status | Freshness | Required/optional | Notes |
| --- | --- | --- | --- | --- |
| degraded_mode_behavior | Uses controller-observed tmux facts when Claude-specific telemetry is missing or stale. | n/a | required | shared contract declaration |
| unsupported_features | token_budget, structured_progress | n/a | optional | explicit unsupported declaration |

## 6. Qualification Decision

| Decision point | Pass rule | Result | Notes |
| --- | --- | --- | --- |
| Minimum contract met | all required contract areas pass | PASS | shared contract suite plus descriptor validation |
| Degraded mode safe | missing/weak signals do not weaken authority semantics | PASS | degraded mode declaration present |
| Intervention sufficient | supported operations are explicit and safe | PASS | shared required operations present |
| Routing evidence usable | controller can rank or reject safely | PASS | capability and freshness evidence declared |
| Validation coverage sufficient | automated coverage exists and is linked | PASS | shared contract suite completed |

## 7. Required Evidence Links

- Contract test output: `python3 -m unittest tools.orchestration.tests.test_adapter_contracts`
- Integration test output: `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli`
- Related failure-drill reports: `_bmad-output/release-evidence/failure-mode-matrix-report.md`
- Example inspector output: `macs adapter inspect --adapter claude --json`
- Contributor guidance or docs path: `docs/adapter-contributor-guide.md`

## 8. Open Risks

| Risk | Impact | Mitigation | Owner |
| --- | --- | --- | --- |
| Declared status is provisional while release eligibility is evidence-based. | medium | rely on the release-gate evidence rather than declaration alone | eng |

## 9. Final Recommendation

- Recommended adapter status: first-class
- Ship blocker: none
- Follow-up work required before first-class support: none
