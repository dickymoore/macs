# Failure-Mode Matrix Report

## 1. Run Metadata

- Report date: 2026-04-10T17:51:11+00:00
- Owner: qa
- Outcome: `PASS`

## 2. Mandatory Failure Classes

| Failure class | Evidence source | Result |
| --- | --- | --- |
| worker_disconnect | `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli` | PASS |
| stale_lease_divergence | `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli` | PASS |
| duplicate_claim | `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli` | PASS |
| split_brain_startup_recovery | `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli` | PASS |
| lock_collision | `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli` | PASS |
| misleading_health_evidence | `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli` | PASS |
| surfaced_budget_exhaustion | `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli` | PASS |
| interrupted_recovery | `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli` | PASS |

## 3. Suite Evidence

- Command: `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli`
- Return code: 0
- stdout tail: none
- stderr tail: ........, ----------------------------------------------------------------------, Ran 8 tests in 3.310s, OK

## 4. Sign-Off

- Mandatory matrix complete: yes
- Recommended disposition: `accept`
