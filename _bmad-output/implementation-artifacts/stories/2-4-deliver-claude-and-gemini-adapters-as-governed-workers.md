# Story 2.4: Deliver Claude and Gemini adapters as governed workers

Status: done

## Story

As a maintainer,
I want Claude Code and Gemini CLI workers to integrate through the same skeptical contract,
so that mixed-runtime orchestration is a product behavior rather than a special-case hack.

## Acceptance Criteria

1. Given valid Claude Code or Gemini CLI environments, when I register the workers with MACS, then each worker is represented through the shared adapter contract with explicit support or degradation for optional signals.
2. Runtime-specific differences do not bypass controller-owned eligibility and health classification.

## Completion Notes List

- Exercised `claude` and `gemini` through the shared adapter registry rather than adding special controller paths, preserving one contract for worker discovery, inspection, probing, and validation.
- Explicit unsupported-feature declarations and degraded-mode behavior are now surfaced for both runtimes, so missing telemetry remains visible instead of weakening safety semantics silently.
- Added regression coverage proving Claude and Gemini workers validate against the shared adapter contract and emit the normalized evidence envelope through `macs adapter probe`.

## File List

- `_bmad-output/implementation-artifacts/stories/2-4-deliver-claude-and-gemini-adapters-as-governed-workers.md`
- `tools/orchestration/adapters/registry.py`
- `tools/orchestration/tests/test_setup_init.py`
