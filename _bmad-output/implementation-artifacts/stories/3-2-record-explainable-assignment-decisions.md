# Story 3.2: Record explainable assignment decisions

Status: done

## Completion Notes List

- Added durable routing-decision persistence in `routing_decisions` with selected worker, ranked candidates, rejected workers, policy version, and lock-check result.
- `macs task inspect` now exposes the latest stored routing rationale without requiring pane inspection.
- Added regression coverage proving assignment records are inspectable and policy-driven.

## File List

- `_bmad-output/implementation-artifacts/stories/3-2-record-explainable-assignment-decisions.md`
- `tools/orchestration/routing.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_setup_init.py`
