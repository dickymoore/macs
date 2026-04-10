# Story 4.1: Provide compact list and inspect commands for control-plane objects

Status: done

## Completion Notes List

- Added controller-first list and inspect commands for tasks, locks, leases, events, and overview summaries in `tools/orchestration/cli/main.py`.
- Added authoritative read helpers in `tools/orchestration/history.py` and `tools/orchestration/overview.py` so common orchestration questions resolve from SQLite state rather than raw pane output.
- Added regression coverage walking from assignment to lease/event inspection and overview summarization.

## File List

- `_bmad-output/implementation-artifacts/stories/4-1-provide-compact-list-and-inspect-commands-for-control-plane-objects.md`
- `tools/orchestration/history.py`
- `tools/orchestration/overview.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_setup_init.py`
