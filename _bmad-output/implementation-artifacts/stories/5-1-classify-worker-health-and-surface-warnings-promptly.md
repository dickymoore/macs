# Story 5.1: Classify worker health and surface warnings promptly

Status: done

## Completion Notes List

- Added freshness-driven worker health classification in `tools/orchestration/health.py`, reclassifying stale workers to `degraded` or `unavailable` under controller control.
- Overview and worker inspection surfaces now trigger classification before presenting state, and routing automatically excludes degraded workers where policy disallows them.
- Added regression coverage proving stale workers are reclassified and excluded from assignment.

## File List

- `_bmad-output/implementation-artifacts/stories/5-1-classify-worker-health-and-surface-warnings-promptly.md`
- `tools/orchestration/health.py`
- `tools/orchestration/overview.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_setup_init.py`
