# Restart Recovery Verification Report

## 1. Run Metadata

- Report date: 2026-04-10T17:51:12+00:00
- Owner: qa
- Outcome: `PASS`

## 2. Restart-Recovery Scenarios

| Scenario | Evidence source | Result |
| --- | --- | --- |
| tools.orchestration.tests.test_setup_init.SetupInitTests.test_restart_marks_live_ownership_for_reconciliation | `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_restart_marks_live_ownership_for_reconciliation tools.orchestration.tests.test_setup_init.SetupInitTests.test_restart_summary_surfaces_unresolved_task_scoped_recovery_runs tools.orchestration.tests.test_setup_init.SetupInitTests.test_assign_rejects_when_startup_recovery_blocks_assignments tools.orchestration.tests.test_controller_invariants.ControllerInvariantTests.test_inspect_recovery_context_reports_interrupted_retry_without_live_lease` | PASS |
| tools.orchestration.tests.test_setup_init.SetupInitTests.test_restart_summary_surfaces_unresolved_task_scoped_recovery_runs | `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_restart_marks_live_ownership_for_reconciliation tools.orchestration.tests.test_setup_init.SetupInitTests.test_restart_summary_surfaces_unresolved_task_scoped_recovery_runs tools.orchestration.tests.test_setup_init.SetupInitTests.test_assign_rejects_when_startup_recovery_blocks_assignments tools.orchestration.tests.test_controller_invariants.ControllerInvariantTests.test_inspect_recovery_context_reports_interrupted_retry_without_live_lease` | PASS |
| tools.orchestration.tests.test_setup_init.SetupInitTests.test_assign_rejects_when_startup_recovery_blocks_assignments | `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_restart_marks_live_ownership_for_reconciliation tools.orchestration.tests.test_setup_init.SetupInitTests.test_restart_summary_surfaces_unresolved_task_scoped_recovery_runs tools.orchestration.tests.test_setup_init.SetupInitTests.test_assign_rejects_when_startup_recovery_blocks_assignments tools.orchestration.tests.test_controller_invariants.ControllerInvariantTests.test_inspect_recovery_context_reports_interrupted_retry_without_live_lease` | PASS |
| tools.orchestration.tests.test_controller_invariants.ControllerInvariantTests.test_inspect_recovery_context_reports_interrupted_retry_without_live_lease | `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_restart_marks_live_ownership_for_reconciliation tools.orchestration.tests.test_setup_init.SetupInitTests.test_restart_summary_surfaces_unresolved_task_scoped_recovery_runs tools.orchestration.tests.test_setup_init.SetupInitTests.test_assign_rejects_when_startup_recovery_blocks_assignments tools.orchestration.tests.test_controller_invariants.ControllerInvariantTests.test_inspect_recovery_context_reports_interrupted_retry_without_live_lease` | PASS |

## 3. Suite Evidence

- Command: `python3 -m unittest tools.orchestration.tests.test_setup_init.SetupInitTests.test_restart_marks_live_ownership_for_reconciliation tools.orchestration.tests.test_setup_init.SetupInitTests.test_restart_summary_surfaces_unresolved_task_scoped_recovery_runs tools.orchestration.tests.test_setup_init.SetupInitTests.test_assign_rejects_when_startup_recovery_blocks_assignments tools.orchestration.tests.test_controller_invariants.ControllerInvariantTests.test_inspect_recovery_context_reports_interrupted_retry_without_live_lease`
- Return code: 0
- stdout tail: none
- stderr tail: ...., ----------------------------------------------------------------------, Ran 4 tests in 0.805s, OK

## 4. Sign-Off

- Restart recovery preserves zero-or-one active lease invariants: yes
- Recommended disposition: `accept`
