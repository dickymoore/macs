# Using MACS

This guide explains the operator-facing MACS surface after a repo has been bootstrapped. Use it as the day-to-day reference for command families, control-plane objects, and common command patterns.

## Mental Model

MACS is built around a small set of controller-owned objects.

| Object | What it means | Typical commands |
| --- | --- | --- |
| `worker` | A governed execution endpoint backed by an adapter and tmux location | `macs worker list`, `macs worker inspect` |
| `task` | A unit of work the controller tracks explicitly | `macs task create`, `macs task inspect` |
| `lease` | Current or past ownership record for a task | `macs lease inspect`, `macs lease history` |
| `lock` | Reservation or ownership over a protected surface | `macs lock list`, `macs lock inspect` |
| `event` | Durable audit trail for decisions and state changes | `macs event list`, `macs event inspect` |
| `adapter` | Runtime integration contract and capability depth | `macs adapter list`, `macs adapter inspect` |
| `recovery` | Controller-managed reconciliation state for degraded or interrupted work | `macs recovery inspect`, `macs recovery retry` |

The controller remains authoritative. Adapters and runtimes can provide evidence, delivery acknowledgments, and live session signals, but they do not become the source of truth for ownership or recovery.

## Command Families

| Family | Use it for | Common verbs |
| --- | --- | --- |
| `macs setup` | Repo bootstrap, guided onboarding, onboarding checks, and release-gate validation | `guide`, `init`, `check`, `validate`, `dry-run` |
| `macs worker` | Discover, register, inspect, and govern workers | `discover`, `register`, `inspect`, `enable`, `disable`, `quarantine` |
| `macs adapter` | Inspect contract shape and validate runtime support | `list`, `inspect`, `probe`, `validate` |
| `macs task` | Normal orchestration work | `create`, `assign`, `inspect`, `pause`, `resume`, `reroute`, `abort`, `close`, `archive` |
| `macs lease` | Inspect current and historical ownership | `inspect`, `history` |
| `macs lock` | Inspect and override protected-surface state | `list`, `inspect`, `override`, `release` |
| `macs event` | Inspect durable audit history | `list`, `inspect` |
| `macs overview` | See the current high-level control-plane summary | `show` |
| `macs recovery` | Inspect and resolve recovery state | `inspect`, `retry`, `reconcile` |

## Human-Readable vs JSON Output

Every top-level family accepts `--json` at the root command:

```bash
./macs --json task inspect --task task-123
./macs --json setup validate --release-gate
```

Use human-readable output for terminal operation and `--json` when you need scripting, stable fields, or structured evidence capture.

The task, lease, and pause-related human-readable surfaces are intentionally text-first. They stay usable under narrow terminals and with `NO_COLOR=1`.

```bash
NO_COLOR=1 COLUMNS=80 ./macs task inspect --task task-123
```

## Core Usage Patterns

### 1. Bootstrap and inspect the repo-local control plane

```bash
./macs setup guide
./macs setup init
./macs setup check
./macs overview show
```

Use `setup guide` first when you want the controller-owned, read-only onboarding briefing with explicit `[READ-ONLY]` versus `[ACTION]` follow-up labels.

Use `setup dry-run` before onboarding more workers if you want the conservative, read-only operator path:

```bash
./macs setup dry-run
```

### 2. Discover and register workers

```bash
./macs worker discover --json
./macs worker list
./macs worker register --worker <worker-id> --adapter codex
./macs worker inspect --worker <worker-id>
```

`worker inspect --open-pane` is the controller-owned way to pin and open the target pane without falling back to raw tmux navigation:

```bash
./macs worker inspect --worker <worker-id> --open-pane
```

### 3. Create and assign work

Create the task with the smallest required input:

```bash
./macs task create --summary "Draft release notes"
```

Route by policy:

```bash
./macs task assign --task <task-id> --workflow-class implementation
```

Or pin an explicit worker:

```bash
./macs task assign --task <task-id> --worker <worker-id>
```

Inspect the current controller truth:

```bash
./macs task inspect --task <task-id>
./macs lease inspect --lease <lease-id>
```

### 4. Pause, resume, reroute, or abort

Operator-confirmed actions stay on the task family:

```bash
./macs task pause --task <task-id> --confirm --rationale "unsafe write overlap"
./macs task resume --task <task-id> --confirm
./macs task reroute --task <task-id> --workflow-class implementation --confirm --rationale "worker degraded"
./macs task abort --task <task-id> --confirm
```

Pause moves the task to `intervention_hold` and keeps the same live lease in `paused`. If the runtime adapter does not advertise native pause or resume depth, MACS still records the controller-owned state transition and returns an explicit warning.

### 5. Close and archive completed work

```bash
./macs task checkpoint --task <task-id> --target-action task.close
./macs task close --task <task-id>
./macs task checkpoint --task <task-id> --target-action task.archive
./macs task archive --task <task-id>
```

`close` is the operator verb for the terminal task state `completed`, but it now fails closed unless MACS already has a current `task.close` checkpoint for the same task scope and repo state. `archive` requires its own `task.archive` checkpoint and is only valid after the task is already terminal.

## Inspect and Recover Controller-Owned State

Recovery flows are task-scoped. Start with inspection:

```bash
./macs recovery inspect --task <task-id>
```

If the controller has an interrupted or unresolved recovery run, choose one of the explicit follow-ups:

```bash
./macs recovery retry --task <task-id> --confirm
./macs recovery reconcile --task <task-id> --confirm
```

Use event and lease history when you need to understand why a task is blocked:

```bash
./macs event list
./macs event inspect --event <event-id>
./macs lease history --task <task-id>
```

## Working with Locks and Protected Surfaces

Inspect current lock state:

```bash
./macs lock list
./macs lock inspect --lock <lock-id>
```

High-consequence lock actions remain explicit:

```bash
./macs lock override --lock <lock-id> --confirm
./macs lock release --lock <lock-id> --confirm
```

Do not treat lock override as a convenience action. It is an operator exception path that should follow inspection and rationale capture.

## Adapter and Worker Governance

Use adapter surfaces to inspect what MACS thinks a runtime can really do:

```bash
./macs adapter list
./macs adapter inspect --adapter codex
./macs adapter probe --worker <worker-id> --json
./macs adapter validate --adapter codex --json
```

Use worker governance verbs to keep the roster trustworthy:

```bash
./macs worker enable --worker <worker-id>
./macs worker disable --worker <worker-id>
./macs worker quarantine --worker <worker-id>
```

## Release Readiness

For onboarding readiness only:

```bash
./macs setup validate
```

For the full Phase 1 evidence package:

```bash
./macs setup validate --release-gate
```

That release-gate path refreshes `_bmad-output/release-evidence/` and rolls up setup validation, adapter qualification, the mandatory failure matrix, restart recovery verification, and the four-worker reference dogfood scenario.

## When to Use the Bridge Scripts Directly

The `tools/tmux_bridge/` helpers remain valid, especially for compatibility and low-level troubleshooting. Normal orchestration should still stay on `macs`, but these helpers are still part of the supported system:

- `snapshot.sh`
- `send.sh`
- `status.sh`
- `set_target.sh`
- `bridge.py`

Use them when you are debugging pane targeting, testing bridge behavior directly, or preserving an existing single-worker workflow while you adopt the control plane.

## Next Reads

- [How-To Recipes](./how-tos.md) for step-by-step operator flows
- [Architecture](./architecture.md) for the control-plane model and Mermaid diagrams
- [Contributor Guide](./contributor-guide.md) if you are changing MACS itself
