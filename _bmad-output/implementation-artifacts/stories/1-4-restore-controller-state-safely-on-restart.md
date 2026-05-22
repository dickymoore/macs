# Story 1.4: Restore controller state safely on restart

Status: done

## Story

As a maintainer,
I want controller startup to restore persisted state before any new routing occurs,
so that recovery begins from authoritative records rather than runtime guesswork.

## Acceptance Criteria

1. Given a prior session with persisted tasks, leases, and locks, when the controller restarts, then it reloads the persisted state and marks any previously live ownership as pending reconciliation before accepting new assignments.
2. The operator can see a startup summary of restored entities and unresolved anomalies.

## Completion Notes List

- Added controller-owned startup recovery logic in `tools/orchestration/recovery.py` and wired it into `setup init` so bootstrap now restores persisted authoritative state on every start.
- Startup recovery scans persisted workers, tasks, leases, locks, and events; moves active or paused leases to `suspended`; marks affected tasks as `reconciliation`; and preserves unreleased locks for later operator-mediated recovery.
- Bootstrap now records `assignments_blocked`, `startup_summary`, `last_startup_at`, and `last_recovery_run_id` metadata, inserts a `recovery_runs` record when unresolved live ownership exists, and appends a controller startup-recovery event to both SQLite and NDJSON.
- CLI output now includes a compact startup summary, and JSON mode exposes restored-entity counts plus unresolved anomaly details for later operator surfaces and black-box tests.
- Added regression coverage for clean startup summaries and restart flows that freeze prior live ownership without clearing task ownership pointers or releasing locks prematurely.

## File List

- `_bmad-output/implementation-artifacts/stories/1-4-restore-controller-state-safely-on-restart.md`
- `README.md`
- `docs/getting-started.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/recovery.py`
- `tools/orchestration/session.py`
- `tools/orchestration/tests/test_setup_init.py`
