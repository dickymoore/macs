# Story 2.2: Implement the shared adapter contract and evidence envelope

Status: done

## Story

As a contributor,
I want a base adapter contract that normalizes identity, capability, health, and intervention signals,
so that new runtimes can integrate without changing controller authority rules.

## Acceptance Criteria

1. Given an adapter implementation, when it reports worker evidence to the controller, then the evidence is normalized into required signals, optional enrichment, timestamps, and confidence or freshness metadata.
2. The adapter cannot mutate authoritative task, lease, lock, or routing state directly.

## Completion Notes List

- Added a shared tmux-backed adapter contract in `tools/orchestration/adapters/base.py` with explicit required operations, unsupported-feature declarations, degraded-mode descriptions, and normalized evidence-envelope output.
- Added an adapter registry in `tools/orchestration/adapters/registry.py` covering `codex`, `claude`, `gemini`, and `local` so later runtime-specific work plugs into one controller-owned shape.
- Added `macs adapter list|inspect|probe|validate` commands and black-box tests proving descriptor output, contract validation, and normalized evidence envelopes.
- Kept authority boundaries intact: adapters can dispatch, capture, interrupt, and acknowledge delivery through tmux, but they do not mutate authoritative control-plane tables directly.

## File List

- `_bmad-output/implementation-artifacts/stories/2-2-implement-the-shared-adapter-contract-and-evidence-envelope.md`
- `README.md`
- `tools/orchestration/adapters/__init__.py`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/adapters/registry.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/workers.py`
