# Dogfood Evidence Template

Use this for Epic 8.3 to record the reference four-worker orchestration scenario in the MACS repo.

## 1. Run Metadata

- Run ID:
- Date:
- Operator:
- Repository revision:
- Scenario definition reference:
- Outcome: `PASS | FAIL | PARTIAL | BLOCKED`

## 2. Worker Lineup

| Worker | Runtime | Adapter version | Initial readiness | Interruptibility | Notes |
| --- | --- | --- | --- | --- | --- |
| Codex |  |  |  |  |  |
| Claude |  |  |  |  |  |
| Gemini |  |  |  |  |  |
| Local |  |  |  |  |  |

## 3. Scenario Summary

- Workflow classes exercised:
- Tasks created:
- Protected surfaces involved:
- Planned intervention points:
- Planned recovery or reroute points:

## 4. Reference Timing Envelope

| Check | Target | Actual | Result |
| --- | --- | --- | --- |
| Worker discovery / inspection | <= 2s |  |  |
| Task assignment path | <= 5s |  |  |
| Degraded warning visibility | <= 10s |  |  |

## 5. Execution Record

| Step | Action | Expected result | Actual result | Outcome |
| --- | --- | --- | --- | --- |
| 1 | Start controller session |  |  |  |
| 2 | Confirm worker roster |  |  |  |
| 3 | Assign mixed-runtime tasks |  |  |  |
| 4 | Inspect ownership and locks |  |  |  |
| 5 | Review routing rationale |  |  |  |
| 6 | Exercise intervention |  |  |  |
| 7 | Exercise recovery or reroute |  |  |  |
| 8 | Close or archive tasks |  |  |  |

## 6. Evidence Summary

### Controller Facts

- Ownership remained explicit:
- Lock state remained inspectable:
- Event history remained inspectable:
- No task showed more than one active lease:

### Adapter Signals

| Worker | Capability evidence | Freshness evidence | Health evidence | Budget/session evidence | Notes |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

### Untrusted Claims or Operator Notes

- Claims that required corroboration:
- Notes about runtime asymmetry or degraded telemetry:

## 7. Story Acceptance Check

| Epic 8.3 expectation | Evidence | Result |
| --- | --- | --- |
| Mixed-runtime orchestration flow completed |  |  |
| Ownership was visible during the run |  |  |
| Locks were visible during the run |  |  |
| Routing rationale was visible during the run |  |  |
| Intervention support was usable |  |  |
| Artifacts are sufficient for repeatability and release review |  |  |

## 8. Artifact Inventory

- Machine-readable outputs:
- Human-readable summaries:
- Event IDs or trace references:
- Screens, snapshots, or pane captures:
- Related failure-drill reports:

## 9. Findings

| Finding | Severity | Affects Epic | Owner | Action |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## 10. Recommendation

- Dogfood run counts toward release gate:
- Caveats:
- Recommended next run or fix:
