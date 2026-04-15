# Story 6.1: Persist a durable event trail and history inspectors

Status: done

## Completion Notes List

- Extended the authoritative event trail with list and inspect readers over the SQLite `events` table and kept NDJSON as export-only audit output.
- Added lease history inspection so task and worker ownership history can be read without pane archaeology.
- Added regression coverage proving assignment actions remain inspectable through lease and event history surfaces.

## File List

- `_bmad-output/implementation-artifacts/stories/6-1-persist-a-durable-event-trail-and-history-inspectors.md`
- `tools/orchestration/history.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_setup_init.py`
