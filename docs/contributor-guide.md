# MACS Contributor Guide

This guide is for contributors changing MACS itself: controller behavior, CLI surfaces, adapters, tests, docs, or release-readiness evidence.

If you only need to extend a runtime adapter, read [Adapter Contributor Guide](./adapter-contributor-guide.md) alongside this guide.

## Before You Change Anything

- Read [Architecture](./architecture.md) first.
- Treat the live CLI help surface as authoritative for flags and verbs.
- Preserve controller authority over `worker`, `task`, `lease`, `lock`, and `event`.
- Keep the repo brownfield-safe: extend existing seams instead of replacing working operator paths.

## Repository Map

| Path | What lives there |
| --- | --- |
| `README.md` | Project overview, quick start, and top-level validation entry points |
| `docs/` | End-user and contributor documentation |
| `tools/orchestration/cli/main.py` | CLI family and verb wiring |
| `tools/orchestration/setup.py` | Guided onboarding, bootstrap, setup check, dry-run, and setup validation |
| `tools/orchestration/tasks.py` | Task lifecycle, assignment, pause or resume, and intervention actions |
| `tools/orchestration/workers.py` | Worker discovery, registration, and governance |
| `tools/orchestration/routing.py` | Worker selection and routing decisions |
| `tools/orchestration/recovery.py` | Recovery inspection, retry, and reconciliation |
| `tools/orchestration/locks.py` | Protected-surface inspection and exception handling |
| `tools/orchestration/history.py` | Event and history read surfaces |
| `tools/orchestration/store.py` | Durable control-plane storage |
| `tools/orchestration/adapters/` | Shared adapter contract plus runtime implementations |
| `tools/orchestration/tests/` | Deterministic suites, CLI regressions, failure drills, dogfood, and release-gate coverage |
| `tools/tmux_bridge/` | Bridge-era helpers, launchers, and smoke tests |
| `_bmad-output/` | Planning artifacts, implementation artifacts, retrospectives, and release evidence |

## Contribution Workflow

### 1. Start from the live behavior

Use `./macs --help` and the family-level `--help` surfaces before you edit docs or examples. For setup and onboarding work, inspect `./macs setup --help` and `./macs setup guide` first. Planning artifacts are useful context, but examples must match what actually shipped.

### 2. Change the narrowest seam

Examples:

- CLI wording or command routing: start in `tools/orchestration/cli/main.py`
- setup and onboarding behavior: start in `tools/orchestration/setup.py`
- task lifecycle and intervention: start in `tools/orchestration/tasks.py`
- routing or worker selection: start in `tools/orchestration/routing.py`
- recovery state: start in `tools/orchestration/recovery.py`
- adapter contract or runtime integration: start in `tools/orchestration/adapters/`

### 3. Add or update regression coverage

The current test layout is intentional:

- `test_controller_invariants.py` for deterministic controller state and invariant rules
- `test_adapter_contracts.py` for shared adapter contract coverage
- `test_setup_init.py` for setup, bootstrap, restart, and shared inspect behavior
- `test_task_lifecycle_cli.py` for task and intervention CLI behavior
- `test_inspect_context_cli.py` for read-side human and JSON surfaces
- `test_failure_drills_cli.py` for mandatory failure classes
- `test_reference_dogfood_cli.py` for the four-worker dogfood scenario
- `test_release_gate_cli.py` for evidence aggregation and release-gate output

### 4. Update docs with behavior

If you change a user-facing command, inspect surface, adapter contract, or release-readiness rule, update the relevant docs in the same change.

Most common pairings:

- onboarding or setup changes: `README.md`, `docs/getting-started.md`, `docs/how-tos.md`
- task and recovery changes: `docs/user-guide.md`, `docs/how-tos.md`, `docs/architecture.md`
- adapter changes: `docs/adapter-contributor-guide.md`, `docs/contributor-guide.md`
- repo-local policy or config changes: `docs/customization.md`

### 5. Rebuild release evidence only when the change requires it

The release-gate path is:

```bash
./macs setup validate --release-gate
```

Run it when your change affects release-readiness criteria, release evidence shape, dogfood output, failure-drill expectations, or the summary pack under `_bmad-output/release-evidence/`.

## Baseline Validation Commands

Use the smallest meaningful suite first, then broaden if the change spans multiple surfaces.

```bash
python3 -m unittest tools.orchestration.tests.test_controller_invariants
python3 -m unittest tools.orchestration.tests.test_adapter_contracts
python3 -m unittest tools.orchestration.tests.test_setup_init
python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli
python3 -m unittest tools.orchestration.tests.test_inspect_context_cli
python3 -m unittest discover -s tools/orchestration/tests
bash tools/tmux_bridge/tests/smoke.sh
```

For release-oriented work, also run:

```bash
python3 -m unittest tools.orchestration.tests.test_failure_drills_cli
python3 -m unittest tools.orchestration.tests.test_reference_dogfood_cli
python3 -m unittest tools.orchestration.tests.test_release_gate_cli
./macs setup validate --release-gate
```

## Documentation Maintenance Rules

- Keep examples copy-pasteable.
- Prefer the canonical singular command families: `worker`, `task`, `lease`, `lock`, `event`, `adapter`.
- Show controller truth before runtime evidence.
- Call out degraded or best-effort behavior explicitly.
- Do not document planning-only flags or verbs that the live CLI does not support.
- Keep bridge compatibility documented, but do not present raw tmux surgery as the normal operator path.

## When to Touch Which Docs

| If you changed... | Update these docs |
| --- | --- |
| bootstrap, onboarding, or validation | `README.md`, `docs/getting-started.md`, `docs/how-tos.md` |
| command examples or operator workflows | `docs/user-guide.md`, `docs/how-tos.md` |
| control-plane mental model | `docs/architecture.md` |
| repo-local config or policy files | `docs/customization.md` |
| contributor workflow or repository map | `docs/contributor-guide.md` |
| adapter contract, qualification, or degraded behavior | `docs/adapter-contributor-guide.md` |

## Anti-Patterns

- Do not make adapters the source of truth for routing, ownership, or recovery.
- Do not add new commands to docs before they exist in the live CLI.
- Do not leave human-readable output undocumented when JSON changes.
- Do not update release evidence by hand when the release-gate command should produce it.
- Do not treat planning artifacts as a substitute for inspecting the implemented command surface.

## Next Reads

- [Architecture](./architecture.md)
- [Using MACS](./user-guide.md)
- [Adapter Contributor Guide](./adapter-contributor-guide.md)
- [Customization](./customization.md)
