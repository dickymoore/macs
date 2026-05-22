# Story 3.4: Block conflicts and duplicate ownership claims

Status: done

## Completion Notes List

- Added conflict detection for overlapping file and directory surfaces plus logical-surface collisions in `tools/orchestration/locks.py`.
- Assignment now rejects conflicting protected-surface reservations before activating work, preserving one-owner semantics and surfacing structured conflict details.
- Regression coverage proves conflicting assignments fail closed instead of silently overlapping.

## File List

- `_bmad-output/implementation-artifacts/stories/3-4-block-conflicts-and-duplicate-ownership-claims.md`
- `tools/orchestration/locks.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/tests/test_setup_init.py`
