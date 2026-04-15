# Story 2.3: Deliver the Codex adapter as the reference worker

Status: done

## Story

As a maintainer,
I want Codex CLI to be a first-class default worker in this repository,
so that the reference repo dogfoods the control plane with its primary runtime.

## Acceptance Criteria

1. Given a valid Codex CLI environment, when I register or discover a Codex worker, then the worker exposes required identity, capability, freshness, interruptibility, and supported permission-surface signals through the adapter contract.
2. Missing optional telemetry degrades safely instead of blocking worker registration.

## Completion Notes List

- Added a Codex-specific adapter in `tools/orchestration/adapters/codex.py` and promoted its qualification status to the repo’s reference adapter.
- Codex probe now augments the shared evidence envelope with permission-surface claims derived from live tmux pane capture, including approval mode, sandbox mode, and model when those flags are visible.
- Missing Codex-specific flags degrade cleanly to `unknown` values with reduced confidence instead of blocking probe or worker registration.
- Added a live tmux-backed regression proving Codex permission-surface parsing from the pane capture path used by the controller.

## File List

- `_bmad-output/implementation-artifacts/stories/2-3-deliver-the-codex-adapter-as-the-reference-worker.md`
- `README.md`
- `tools/orchestration/adapters/codex.py`
- `tools/orchestration/adapters/registry.py`
- `tools/orchestration/tests/test_setup_init.py`
