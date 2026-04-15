# Story 3.1: Configure workflow-aware routing policy

Status: done

## Completion Notes List

- Added repo-local routing policy bootstrap in `tools/orchestration/policy.py`, persisted under `.codex/orchestration/routing-policy.json` and mirrored into `policy_snapshots`.
- Implemented workflow-aware worker evaluation in `tools/orchestration/routing.py`, covering preferred runtimes, required capabilities, interruptibility requirements, privacy-sensitive local-only routing, and disallowed worker states.
- Added task creation and assignment paths that apply the policy before routing work.

## File List

- `_bmad-output/implementation-artifacts/stories/3-1-configure-workflow-aware-routing-policy.md`
- `tools/orchestration/policy.py`
- `tools/orchestration/routing.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/session.py`
- `tools/orchestration/tests/test_setup_init.py`
