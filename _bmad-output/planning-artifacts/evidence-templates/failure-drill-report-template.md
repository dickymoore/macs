# Failure-Drill Report Template

Use this for Epic 8.2 mandatory failure classes. Complete one report per scenario execution.

## 1. Drill Metadata

- Failure class:
- Drill ID:
- Date:
- Operator:
- Repository and revision:
- Fixture or work surface:
- Runtime(s) involved:
- Outcome: `PASS | FAIL | PARTIAL | BLOCKED`

## 2. Scenario Definition

- Scenario objective:
- Trigger method:
- Preconditions:
- Expected safe behavior:
- Story or requirement targets:

## 3. Mandatory Failure Class

Mark one:

- [ ] worker disconnect
- [ ] stale lease divergence
- [ ] duplicate claim
- [ ] split-brain ownership
- [ ] lock collision
- [ ] misleading health evidence
- [ ] budget/session exhaustion
- [ ] interrupted recovery

## 4. Timeline

| Time | Action or event | Evidence source | Notes |
| --- | --- | --- | --- |
|  |  |  |  |

## 5. State Assertions

| Assertion | Expected result | Actual result | Outcome |
| --- | --- | --- | --- |
| At most one active lease exists |  |  |  |
| Ownership remains explicit |  |  |  |
| Unsafe progression is frozen when required |  |  |  |
| Relevant locks are preserved or reconciled safely |  |  |  |
| Recovery actions are evented and auditable |  |  |  |
| New assignments are blocked when they should be |  |  |  |

## 6. Evidence Layers

### Controller Facts

- Task state before drill:
- Task state after drill:
- Lease state before drill:
- Lease state after drill:
- Lock state before drill:
- Lock state after drill:
- Recovery run or hold state:

### Adapter Signals

| Worker | Signal | Before | During | After | Notes |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

### Untrusted Claims

- Runtime or pane claims that were not authoritative:
- How they were corroborated or rejected:

## 7. Event and Artifact References

- Event IDs:
- `events.ndjson` slice or export:
- State snapshot or DB query reference:
- tmux capture or snapshot path:
- Test command and output path:

## 8. Acceptance Result

| Required check | Evidence | Result |
| --- | --- | --- |
| Failure class was exercised intentionally |  |  |
| Assertions were made against authoritative state |  |  |
| Assertions were made against event traces |  |  |
| Recovery behavior matched documented semantics |  |  |
| No silent ownership transfer occurred |  |  |

## 9. Defects and Follow-Up

| Finding | Severity | Blocking release gate | Owner | Next step |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## 10. Verdict

- Drill verdict:
- Can this failure class count toward release readiness:
- Required rerun conditions:
