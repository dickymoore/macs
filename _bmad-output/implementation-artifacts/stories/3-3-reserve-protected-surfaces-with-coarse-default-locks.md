# Story 3.3: Reserve protected surfaces with coarse default locks

Status: done

## Completion Notes List

- Added coarse lock normalization and reservation in `tools/orchestration/locks.py` for file, directory, and logical surfaces with `exclusive_write` as the default mode.
- Task assignment now reserves protected surfaces before work activation and persists task, lease, and policy-origin metadata on locks.
- Added `macs lock list` and regression coverage proving locks are durably recorded during assignment.

## File List

- `_bmad-output/implementation-artifacts/stories/3-3-reserve-protected-surfaces-with-coarse-default-locks.md`
- `tools/orchestration/locks.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_setup_init.py`
