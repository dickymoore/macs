# Adapter Contributor Guide

This guide is the authoritative Phase 1 reference for adding or updating a MACS runtime adapter.

Use it together with the live adapter surfaces:

```bash
./macs adapter inspect --adapter <adapter-id>
./macs adapter inspect --adapter <adapter-id> --json
./macs adapter validate --adapter <adapter-id>
./macs adapter validate --adapter <adapter-id> --json
```

Those commands expose the same contract fields this guide describes. If the docs and live output drift, treat the live output and regression suite as the immediate source to reconcile.

## Design Boundary

Adapters are bounded evidence providers, not authority sources.

- The controller remains authoritative for `worker`, `task`, `lease`, `lock`, and `event` state.
- Adapters may discover workers, normalize evidence, dispatch work, capture output, and interrupt work.
- Adapters must not become the source of truth for routing, ownership, recovery, or audit history.

This is the governing extension rule for Phase 1. Contributor flexibility is intentional, but it stops at the controller trust boundary.

## Minimum Adapter Contract

Every adapter implements three contract areas.

### Required Facts

- `stable_worker_identity`
- `runtime_type`
- `tmux_location`
- `capability_declaration`
- `freshness_timestamp`
- `interruptibility_support`
- `degraded_mode_declaration`

In code, these facts are surfaced through the adapter descriptor and evidence envelope. At minimum, `probe(...)` must emit controller-usable evidence for pane presence, capability declaration, and current health or freshness context.

### Required Operations

- `discover_workers`
- `probe`
- `dispatch`
- `capture`
- `interrupt`
- `acknowledge_delivery`

MACS already centralizes the shared contract in [base.py](/home/codexuser/macs_dev/tools/orchestration/adapters/base.py). Extend `BaseTmuxAdapter` where possible instead of rebuilding these seams per runtime.

### Optional Enrichments

Optional enrichments improve operator visibility, but they do not replace required contract support.

Examples:

- token or session budget detail
- richer health telemetry
- runtime-native checkpoint hints
- structured progress
- richer intervention depth such as runtime-native pause or resume
- runtime permission or sandbox metadata

If an enrichment is implemented, declare it explicitly. If it is not supported, declare that explicitly too. Silent omission is not first-class support.

## Capability Model

Worker capabilities are declared as string labels on the worker record and surfaced in adapter evidence as `capability_decl`.

- declaration field: `capabilities`
- evidence name: `capability_decl`
- reference Phase 1 workflow vocabulary:
  - `documentation_context`
  - `planning_docs`
  - `solutioning`
  - `implementation`
  - `review`
  - `privacy_sensitive_offline`

These reference labels come from the repo-local routing defaults in [policy.py](/home/codexuser/macs_dev/tools/orchestration/policy.py). They are the safest vocabulary to use in contributor work because current policy, inspect surfaces, and regression coverage already reference them.

Adapters may expose additional capability strings where justified, but new labels should not force contributors to reverse-engineer hidden controller assumptions. If a runtime only partially supports a workflow class, keep that limitation explicit in unsupported features or degraded behavior.

## Degraded Mode Expectations

Degraded mode is not a failure to document. It is part of the contract.

Every adapter must declare how it behaves when runtime-native signals are absent, stale, or partial.

Contributor rules:

- Preserve controller authority semantics in degraded mode.
- Keep required tmux-backed facts available whenever possible.
- Distinguish unsupported features from broken required support.
- Surface missing optional signals as degraded or unavailable, not as false precision.
- Do not claim first-class support when a feature only works opportunistically.

In practice, this means the degraded-mode declaration should explain what MACS still trusts and what it intentionally falls back from. Existing adapters in [registry.py](/home/codexuser/macs_dev/tools/orchestration/adapters/registry.py) are the reference examples.

## Qualification Expectations

An adapter is only treated as first-class in Phase 1 when it satisfies the published qualification expectations:

- `shared_contract_suite`
- `unsupported_feature_declarations`
- `degraded_mode_behavior`
- `controller_mediated_intervention`
- `routing_evidence_support`
- `supported_feature_regressions`

These expectations align with the architecture and release-readiness plan:

- RG1: first-class qualification is evidence-based, not declarative
- RG8: contributor-facing guidance must match the real qualification workflow
- NFR22: extension points must remain explicit enough for contributors to extend safely

Do not upgrade an adapter to first-class by docs alone. Qualification is proven by contract visibility plus passing evidence.

## Shared Validation Workflow

Current shared validation commands:

```bash
python3 -m unittest tools.orchestration.tests.test_adapter_contracts
python3 -m unittest tools.orchestration.tests.test_controller_invariants
python3 -m unittest tools.orchestration.tests.test_setup_init
python3 -m unittest discover -s tools/orchestration/tests
./macs adapter inspect --adapter <adapter-id> --json
./macs adapter validate --adapter <adapter-id> --json
```

What each step proves:

- `test_adapter_contracts` locks the shared adapter contract, qualification gate, and evidence normalization seams directly.
- `test_controller_invariants` locks deterministic task, lease, lock, routing, and recovery invariants without requiring tmux-backed sessions.
- `test_setup_init` locks shared adapter inspect, validate, and probe behavior.
- full discovery catches drift across controller, routing, recovery, and inspect surfaces.
- `adapter inspect` shows the contributor-facing contract and qualification expectations.
- `adapter validate` confirms the shared contract shape exposed by the adapter implementation.

Phase 1 does not yet ship a separate adapter scaffold generator. The supported path is to update the adapter implementation, expose the descriptor cleanly, and validate it through the shared surfaces above.

## Practical Contributor Workflow

1. Inspect the live contract with `macs adapter inspect --adapter <adapter-id> --json`.
2. Update the runtime adapter implementation and descriptor.
3. Keep required facts and required operations intact.
4. Declare implemented optional enrichments and unsupported features explicitly.
5. Write or update the degraded-mode declaration so fallback behavior is legible.
6. Run `macs adapter validate --adapter <adapter-id> --json`.
7. Run the focused and full regression suites.
8. Review whether the adapter actually meets the qualification expectations, not just whether it compiles.

## Files You Will Usually Touch

- [base.py](/home/codexuser/macs_dev/tools/orchestration/adapters/base.py)
- [registry.py](/home/codexuser/macs_dev/tools/orchestration/adapters/registry.py)
- adapter implementation files under [adapters](/home/codexuser/macs_dev/tools/orchestration/adapters)
- [main.py](/home/codexuser/macs_dev/tools/orchestration/cli/main.py) if contributor-facing adapter output needs to surface new declared metadata
- [test_adapter_contracts.py](/home/codexuser/macs_dev/tools/orchestration/tests/test_adapter_contracts.py) for deterministic shared contract coverage
- [test_controller_invariants.py](/home/codexuser/macs_dev/tools/orchestration/tests/test_controller_invariants.py) when adapter work changes controller-facing invariants or qualification expectations
- [test_setup_init.py](/home/codexuser/macs_dev/tools/orchestration/tests/test_setup_init.py) for shared adapter contract regressions

## Anti-Patterns

- Do not hide adapter assumptions in controller-only code.
- Do not add runtime-specific power that bypasses controller authority.
- Do not treat unsupported features as implicit or undocumented.
- Do not add new capability labels casually when current workflow-class labels already fit.
- Do not call an adapter first-class without shared validation evidence.
