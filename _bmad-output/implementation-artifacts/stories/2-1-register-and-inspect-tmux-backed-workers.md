# Story 2.1: Register and inspect tmux-backed workers

Status: done

## Story

As an operator,
I want to discover, register, enable, disable, and inspect local workers,
so that the controller knows which execution endpoints are available for governed work.

## Acceptance Criteria

1. Given one or more tmux-backed runtime sessions on the local host, when I run worker discovery or registration commands, then MACS records stable worker identities with runtime, pane, and availability metadata.
2. I can enable, disable, or inspect a worker without editing state files manually.

## Completion Notes List

- Added a controller-owned worker roster layer in `tools/orchestration/workers.py` that discovers panes from the repo’s tmux socket/session metadata, infers runtime type conservatively, and persists stable worker identities in SQLite.
- Added `macs worker list|discover|inspect|register|enable|disable|quarantine` to the orchestration CLI with both human-readable and `--json` output paths aligned to the operator contract.
- Discovery now refreshes availability state for tmux-backed workers without trusting tmux output as authority beyond direct pane presence, and preserves manual disable or quarantine choices across refreshes.
- Seeded runtime capability defaults from the repo research guidance so discovered workers expose useful capability metadata before the richer adapter contract arrives.
- Added live tmux-backed regression coverage for multi-window discovery plus worker registration and state transitions.

## File List

- `_bmad-output/implementation-artifacts/stories/2-1-register-and-inspect-tmux-backed-workers.md`
- `README.md`
- `docs/getting-started.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/session.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/workers.py`
