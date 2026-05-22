# Adapter Qualification Template

Use this for Epic 7.4 contributor guidance and Epic 8 qualification work. Complete one report per adapter implementation and version.

## 1. Adapter Identity

- Adapter name:
- Runtime type:
- Adapter version or revision:
- Maintainer:
- Qualification date:
- Outcome: `PASS | FAIL | PARTIAL | BLOCKED`
- Proposed status: `first-class | supported-not-first-class | experimental | rejected`

## 2. Scope

- Runtime binary or backend tested:
- Operating environment:
- Test fixtures used:
- Known unsupported features:

## 3. Contract Surface Check

| Contract area | Required expectation | Evidence | Result |
| --- | --- | --- | --- |
| Identity normalization | Stable worker identity exposed |  |  |
| Capability declaration | Required and optional capabilities separated |  |  |
| Health and freshness | Timestamps and freshness metadata exposed |  |  |
| Interruptibility | Supported actions or explicit unsupported declaration |  |  |
| Permission surface | Approval/sandbox signals preserved where available |  |  |
| Evidence envelope | Facts, soft signals, and claims remain bounded |  |  |
| Authority boundary | Adapter cannot mutate authoritative state |  |  |

## 4. First-Class Qualification Gates

### Required Contract Support

- Passes shared contract tests:
- Required signals exposed:
- Unsupported features declared explicitly:

### Degraded-Mode Behavior

- Missing signals render as `UNAVAILABLE` or `NOT EXPOSED`:
- Degraded health or stale evidence classification supported:
- Safe routing degradation documented:

### Intervention Support

- Interrupt support:
- Pause/hold support:
- Capture or inspection hooks:
- Unsupported intervention behaviors:

### Routing-Evidence Support

- Capability fit evidence:
- Freshness evidence:
- Health evidence:
- Budget/session evidence where available:
- Confidence or uncertainty markers:

### Validation Coverage

- Unit or contract coverage reference:
- Integration coverage reference:
- Failure-drill relevance covered:

## 5. Evidence Summary

### Controller Facts

- Worker registration result:
- Classification result:
- Eligibility for new assignments:

### Adapter Signals

| Signal | Value or status | Freshness | Required/optional | Notes |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

### Untrusted Claims or Manual Notes

- Runtime-reported claims needing corroboration:
- Operator observations outside contract:

## 6. Qualification Decision

| Decision point | Pass rule | Result | Notes |
| --- | --- | --- | --- |
| Minimum contract met | all required contract areas pass |  |  |
| Degraded mode safe | missing/weak signals do not weaken authority semantics |  |  |
| Intervention sufficient | supported operations are explicit and safe |  |  |
| Routing evidence usable | controller can rank or reject safely |  |  |
| Validation coverage sufficient | automated coverage exists and is linked |  |  |

## 7. Required Evidence Links

- Contract test output:
- Integration test output:
- Related failure-drill reports:
- Example inspector output:
- Contributor guidance or docs path:

## 8. Open Risks

| Risk | Impact | Mitigation | Owner |
| --- | --- | --- | --- |
|  |  |  |  |

## 9. Final Recommendation

- Recommended adapter status:
- Ship blocker:
- Follow-up work required before first-class support:
