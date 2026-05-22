# Story 2.5: Deliver the local adapter and first-class qualification checks

Status: done

## Story

As a contributor,
I want a runtime-neutral local adapter and a qualification path for first-class support,
so that privacy-sensitive or offline-capable orchestration remains a first-class product path.

## Acceptance Criteria

1. Given a runtime-neutral local worker, when I register or inspect it, then it is represented through the shared adapter contract with explicit degraded behavior for unsupported optional signals.
2. The system provides a qualification path that can prove required operations exist, unsupported features are declared, and degraded-mode behavior is documented before a runtime is treated as first-class.

## Completion Notes List

- The `local` adapter now ships in the shared registry with a runtime-neutral capability profile and explicit degraded-mode behavior suitable for privacy-sensitive or offline-first routing.
- `macs adapter validate` provides the first qualification path for adapters by checking required operation presence, unsupported-feature declarations, and degraded-mode documentation through one shared validator.
- Added regression coverage proving the local adapter validates cleanly and emits the normalized evidence envelope without claiming runtime-specific telemetry it does not have.

## File List

- `_bmad-output/implementation-artifacts/stories/2-5-deliver-the-local-adapter-and-first-class-qualification-checks.md`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/adapters/registry.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_setup_init.py`
