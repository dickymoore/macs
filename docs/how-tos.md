# MACS How-To Recipes

These recipes are short, task-oriented procedures for common operator workflows. They assume you are already inside a repo that contains the `macs` launcher.

## Bootstrap a Repo-Local Control Plane

1. Initialize the repo-local orchestration layout.

```bash
./macs setup init
```

2. Inspect what MACS created.

```bash
./macs setup check
./macs setup check --json
```

3. Review the conservative onboarding path before you mutate more state.

```bash
./macs setup dry-run
```

Use this recipe when you are onboarding a repo for the first time or verifying that controller-owned state still matches the checkout.

## Register a Worker and Confirm It Is Routable

1. Discover tmux-backed workers.

```bash
./macs worker discover --json
```

2. Register the worker under the intended adapter.

```bash
./macs worker register --worker <worker-id> --adapter codex
```

3. Inspect the worker and adapter views.

```bash
./macs worker inspect --worker <worker-id>
./macs adapter inspect --adapter codex
./macs adapter validate --adapter codex --json
```

4. Check setup readiness after registration.

```bash
./macs setup validate
```

This flow confirms both the worker record and the runtime contract before you assign real work.

## Assign Work with Routing Policy

1. Create a task.

```bash
./macs task create --summary "Implement controller health summary"
```

2. Assign by workflow class.

```bash
./macs task assign --task <task-id> --workflow-class implementation
```

3. Inspect the result.

```bash
./macs task inspect --task <task-id>
./macs event list
```

Use the workflow-class path when you want controller policy to choose the worker based on capabilities, governance, and current evidence.

## Assign Work to a Specific Worker

Use the explicit-worker path when the operator needs to choose the runtime directly:

```bash
./macs task create --summary "Review adapter contract wording"
./macs task assign --task <task-id> --worker <worker-id>
./macs task inspect --task <task-id>
./macs lease history --task <task-id>
```

This is the safest way to pin specialist work, reproduce a scenario, or keep a task on a known runtime.

## Open the Right Worker Pane from Controller Context

If you have the worker ID:

```bash
./macs worker inspect --worker <worker-id> --open-pane
```

If you are working from the task:

```bash
./macs task inspect --task <task-id> --open-pane
```

This reuses the controller-owned targeting path instead of requiring you to remember pane IDs or raw tmux commands.

## Pause, Inspect, and Resume a Task

1. Pause the task with explicit operator confirmation.

```bash
./macs task pause --task <task-id> --confirm --rationale "need manual review"
```

2. Inspect task and lease state.

```bash
./macs task inspect --task <task-id>
./macs lease inspect --lease <lease-id>
```

3. Resume when the task is safe to continue.

```bash
./macs task resume --task <task-id> --confirm
```

If the runtime adapter does not expose native pause depth, MACS still records the controller-owned intervention and tells you that runtime pause is best-effort.

## Inspect and Resolve Recovery

1. Start from recovery inspection.

```bash
./macs recovery inspect --task <task-id>
```

2. If the recovery run should continue, retry it.

```bash
./macs recovery retry --task <task-id> --confirm
```

3. If the current evidence needs an operator decision instead, reconcile it.

```bash
./macs recovery reconcile --task <task-id> --confirm
```

4. Review the durable history.

```bash
./macs event inspect --event <event-id>
./macs lease history --task <task-id>
```

Use this recipe whenever a task is blocked in reconciliation, a worker degraded mid-flight, or startup recovery marked prior ownership for review.

## Inspect Audit Trail and Lock State

For a broad event view:

```bash
./macs event list
```

For a specific decision:

```bash
./macs event inspect --event <event-id>
```

For protected-surface ownership:

```bash
./macs lock list
./macs lock inspect --lock <lock-id>
```

Only use override or release after inspection:

```bash
./macs lock override --lock <lock-id> --confirm
./macs lock release --lock <lock-id> --confirm
```

## Run the Phase 1 Release Gate

1. Run the release gate.

```bash
./macs setup validate --release-gate
```

2. Inspect the evidence package under `_bmad-output/release-evidence/`.

Look for:

- `setup-validation-report.md`
- `failure-mode-matrix-report.md`
- `restart-recovery-verification-report.md`
- `four-worker-dogfood-report.md`
- `release-gate-command-verification.md`
- `release-gate-summary.json`

3. If the outcome is `PARTIAL` or `FAIL`, fix the specific readiness gaps before treating the repo as operationally ready.

In this repository state, a `PARTIAL` result typically means environment readiness is incomplete, such as missing runtime binaries on `PATH` or no currently registered ready workers.

## Stay Compatible with Single-Worker Usage

Bridge-era workflows still work:

```bash
./tools/tmux_bridge/snapshot.sh
./tools/tmux_bridge/send.sh "continue"
./tools/tmux_bridge/status.sh
./tools/tmux_bridge/set_target.sh --pane %3
```

To adopt the controller-owned model without changing to multi-worker mode, keep one worker registered and use the normal task surface:

```bash
./macs task create --summary "Single-worker migration check"
./macs task assign --task <task-id> --worker <worker-id>
./macs task inspect --task <task-id>
./macs recovery inspect --task <task-id>
```

One-worker mode is the same control-plane model with a smaller roster, not a separate product mode.
