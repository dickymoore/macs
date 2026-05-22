# Getting Started with MACS

This guide walks you through setting up MACS (Multi Agent Control System) for your project.

If you want the full documentation map first, start at [Documentation Home](./index.md).

## Prerequisites

- **tmux** - Terminal multiplexer
- **Python 3.8+** - For the bridge script
- **Codex CLI** - AI coding assistant

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_ORG/macs.git
cd macs
```

### 2. Copy Prompts to Codex

Copy the prompts to your global Codex prompts directory:

```bash
mkdir -p ~/.codex/prompts
cp .codex/prompts/*.md ~/.codex/prompts/
```

Or copy to your project's `.codex/prompts/` for project-specific use.

### 3. Make Scripts Executable

```bash
chmod +x tools/tmux_bridge/*.sh
chmod +x tools/tmux_bridge/*.py
```

## Basic Usage

### Step 1: Start a TMux Session (Worker)

From your project repo root:
```bash
# Create session with a worker window
../macs/start-worker.sh macs
# If you copied scripts into your repo:
# ./start-worker.sh macs
# start_worker auto-attaches by default; use --no-attach to skip
# start_worker auto-launches codex in a new worker pane:
#   CODEX_HOME="<repo>/.codex" codex --yolo
# use --no-codex to skip or --start-codex to force in an existing pane
# start_worker uses a repo-local tmux socket by default (./.codex/tmux.sock)
# start_worker enables tmux mouse + large scrollback by default
# use --no-mouse, --history-limit N, or --tmux-config PATH to override
```

### Step 2: Start Codex in the Worker Window

If `start_worker.sh` already launched codex, you can skip this. Otherwise in the **worker** window (`Ctrl+b` then `n` to switch):
```bash
CODEX_HOME="<repo>/.codex" codex --yolo
```

### Step 3: Start the Controller in a Separate Terminal

From your project repo root:
```bash
../macs/start-controller.sh
# If you copied the scripts into your repo:
# ./start-controller.sh
# Or from anywhere:
# /path/to/macs/start-controller.sh --repo /path/to/your-repo
# Skip copying skills:
# ../macs/start-controller.sh --skip-skills
#
# If tmux socket auto-detect fails:
# ../macs/start-controller macs
# ../macs/start-controller.sh --tmux-session macs
# ../macs/start-controller.sh --tmux-socket /tmp/tmux-<uid>/default
# To bypass tmux detection (not recommended):
# ../macs/start-controller.sh --no-tmux-detect
# If you don't pass a sandbox arg, start_controller.sh will prompt to add:
# --sandbox danger-full-access (needed for tmux sockets).
# You can also set MACS_CODEX_ARGS="--sandbox danger-full-access".
# To only install prompts/skills without launching Codex:
# ../macs/start-controller.sh --no-codex
```
This writes `.codex/macs-path.txt` in the repo so the controller can locate `tmux_bridge` tools even when they are not vendored.
It also attempts to record a tmux socket in `.codex/tmux-socket.txt` so controller commands can reach the correct tmux server.
If you pass `--tmux-session`, it records `.codex/tmux-session.txt` so commands can target the right session automatically.
Pinned panes are stored in `.codex/target-pane.txt`.
It launches controller Codex with `CODEX_HOME="<repo>/.codex"` automatically.
Controller bootstrap also creates `.codex/orchestration/state.db` as the authoritative control-plane store and `.codex/orchestration/events.ndjson` as the append-friendly audit export. On restart, the same bootstrap path restores persisted controller state, records a startup recovery summary, and moves any previously live ownership into reconciliation before new assignments proceed.
The same bootstrap now creates separate repo-local config files for controller defaults, adapter settings, routing policy, governance policy, and state layout under `.codex/orchestration/`.

The controller prompt also installs a wrapper for cleaner commands:
`./.codex/tmux-bridge.sh snapshot|send|status|set_target|notify`

For a read-only onboarding briefing from the canonical setup surface, start with:
```bash
./macs setup guide
./macs setup guide --json
```

`setup guide` is read-only. It summarizes the current repo-local onboarding state and labels recommended follow-up commands explicitly as `[READ-ONLY]` or `[ACTION]`.

After bootstrap, inspect the active config domains from the controller surface:
```bash
./macs setup check
./macs setup check --json
```

The default workflow class for `macs task create` comes from `.codex/orchestration/controller-defaults.json`. Adapter enablement and config references come from `.codex/orchestration/adapter-settings.json`. Store locations are described by `.codex/orchestration/state-layout.json` while existing bridge compatibility files such as `.codex/tmux-session.txt`, `.codex/tmux-socket.txt`, and `.codex/target-pane.txt` remain valid.

For current single-worker users, `setup check` also reports the migration boundary:
- no repo-local state migration is required
- single-worker mode is still supported
- `.codex/tmux-session.txt`, `.codex/tmux-socket.txt`, `.codex/target-pane.txt`, and `tools/tmux_bridge/target_pane.txt` remain readable compatibility inputs

To see the supported onboarding path before you mutate anything else, run:
```bash
./macs setup dry-run
./macs setup dry-run --json
```

`setup dry-run` is read-only and shows the conservative order MACS expects: bootstrap, config inspection, worker discovery, worker registration, readiness validation, intervention, and recovery.

It also spells out which bridge-era habits remain usable directly and which normal orchestration flows are now expected to move through `macs`.

A mixed-runtime local-host path now looks like this:
```bash
./macs setup init
./macs setup check --json
./macs worker discover --json
./macs worker register --worker <worker-id> --adapter codex --json
./macs worker register --worker <worker-id> --adapter local --json
./macs setup validate --json
```

`setup validate` reports `PASS`, `PARTIAL`, `FAIL`, or `BLOCKED` without asking you to inspect raw files or SQLite tables. It checks repo-local bootstrap, config-domain visibility, required local dependencies, enabled adapter runtime availability on `PATH`, current worker registration and readiness, and routing-default visibility. Runtime presence alone does not count as safe-ready-state; controller facts still need to show ready workers for the enabled adapters.

When you want the full Phase 1 release decision instead of only setup readiness, run the release-gate variant of the same command:
```bash
./macs setup validate --release-gate
./macs setup validate --release-gate --json
```

That invocation refreshes the release-evidence package under `_bmad-output/release-evidence/` and reports pass/fail status for setup readiness, adapter qualification, the mandatory failure matrix, restart recovery verification, and the four-worker reference scenario.

For the release-oriented reference scenario, MACS also ships a dedicated four-worker dogfood runner. It uses an isolated tmux server and a temporary repo-local work surface, then writes the RG4 evidence pack under `_bmad-output/release-evidence/`:
```bash
python3 -m tools.orchestration.dogfood
```

If you only want the regression suite around that scenario, run:
```bash
python3 -m unittest tools.orchestration.tests.test_reference_dogfood_cli
```

### Single-Worker Migration Boundary

Existing single-worker usage stays supported as a one-worker version of the same control-plane model. You do not need to migrate repo-local state before adopting the controller-owned commands.

Still supported unchanged:
- `../macs/start-worker.sh macs`
- `../macs/start-controller.sh`
- `./tools/tmux_bridge/snapshot.sh`
- `./tools/tmux_bridge/send.sh "<instruction>"`
- `./tools/tmux_bridge/status.sh`
- `./tools/tmux_bridge/set_target.sh --pane %X`

Superseded for normal orchestration:
- manual task ownership tracking outside controller state
- manual assignment notes in panes or shell history
- ad hoc intervention and recovery tracking outside `macs`

Use these commands instead:
```bash
./macs task create --summary "Single-worker migration check"
./macs task assign --task <task-id> --worker <worker-id>
./macs task inspect --task <task-id>
./macs worker inspect --worker <worker-id> --open-pane
./macs task pause --task <task-id> --confirm
./macs recovery inspect --task <task-id>
```

The one-worker path still uses the same bootstrap, discovery, registration, lifecycle, and recovery model as multi-worker usage.

Once tmux session metadata is present, you can discover repo-local workers with:
```bash
./macs worker discover --json
./macs worker list
./macs worker inspect --worker <worker-id> --json
./macs task inspect --task <task-id> --json
./macs task inspect --task <task-id> --open-pane
```

`--open-pane` reuses `tools/tmux_bridge/set_target.sh` and `.codex/target-pane.txt` rather than inventing a second targeting path. On the same tmux server it reports `opened`; otherwise it returns `pinned_only` plus a warning with the exact `tmux_session` and `tmux_pane` that were pinned for follow-up.

You can then stay on the controller-owned task lifecycle surface for normal orchestration work:

```bash
# Create a task with the contract-minimum input.
./macs task create --summary "Draft release notes"

# Assign by workflow policy or by explicit worker.
./macs task assign --task <task-id> --workflow-class implementation --json
./macs task assign --task <task-id> --worker <worker-id>

# Complete and archive without leaving the control plane.
./macs task close --task <task-id> --json
./macs task archive --task <task-id>
```

Task action JSON output follows the same envelope shape for every action:

```json
{
  "ok": true,
  "command": "macs task assign",
  "timestamp": "2026-04-10T08:00:00+01:00",
  "warnings": [],
  "errors": [],
  "data": {
    "result": {},
    "event": {}
  }
}
```

Operational notes for the task lifecycle path:
- `task assign` does not stop at durable reservation anymore; on success it dispatches through the selected worker adapter, marks the lease `active`, and activates any reserved locks.
- `task pause` moves an `active` task to `intervention_hold` and the current live lease to `paused` while keeping the same owner and lock footprint in place.
- `task resume` restores only an operator-paused task or lease pair back to `active` on the same lease.
- `task close` is the human verb for canonical task state `completed`; it completes the live lease and releases held locks.
- `task archive` is only valid after a task is already terminal.
- If the adapter does not advertise pause or resume depth, MACS still records the controller-owned pause and returns an explicit warning rather than hiding the limitation.
- Task action errors use stable exit codes: `4` for conflict or policy-blocked cases, `5` for degraded preconditions or still-unsupported verbs, and `6` when adapter side effects fail after the controller has restored an explicit safe state.

Pause and resume are now part of the controller-owned task surface:

```bash
./macs task pause --task <task-id> --json
./macs task resume --task <task-id> --json
./macs task inspect --task <task-id>
./macs lease inspect --lease <lease-id>
./macs recovery inspect --task <task-id>
./macs recovery retry --task <task-id> --confirm
./macs recovery reconcile --task <task-id> --confirm
./macs task reroute --task <task-id> --workflow-class implementation --json
./macs task abort --task <task-id> --json
```

`task reroute` and `task abort` still return structured `unsupported` responses until the later intervention and recovery stories land.

For assistive tooling, remote SSH sessions, or narrow tmux panes, the human-readable pause, task inspect, and lease inspect surfaces remain text-first and can be forced into the stacked layout with:

```bash
NO_COLOR=1 COLUMNS=80 ./macs task inspect --task <task-id>
```

Example narrow output:

```text
Task:
  task-123
Current Lease:
  lease-123 (paused)
Intervention Basis:
  operator_pause
```

Compatibility note: `./macs task assign --task <task-id>` without a selector still works as a temporary brownfield fallback that reuses the task's stored workflow class. Prefer the canonical documented forms with exactly one selector: `--worker` or `--workflow-class`.

### Step 4: Start the Bridge

From a separate terminal (or tmux pane):
```bash
./tools/tmux_bridge/bridge.py --session macs
```

The bridge will now monitor the worker terminal for requests and route them to the controller.

## Manual Workflow (Without Bridge)

You can also use MACS manually without the bridge:

1. **Worker** performs tasks and asks questions
2. **You** read worker output with `snapshot.sh`
3. **You** provide guidance via `send.sh`
4. Repeat

```bash
# Read recent worker output
./tools/tmux_bridge/snapshot.sh

# Send instructions to worker
./tools/tmux_bridge/send.sh "Proceed with the implementation"

# Check if worker is busy
./tools/tmux_bridge/status.sh
```

## Customizing for Your Project

### 1. Create Project-Specific Rules

Copy the controller prompt to your project and customize:

```bash
cp .codex/prompts/controller.md your-project/.codex/prompts/controller.md
```

Add your project-specific rules at the bottom:
- Repository structure
- CI/CD requirements
- Security policies
- Team conventions

See `examples/project-rules/` for examples.

### 2. Configure the Bridge

Common bridge options:

```bash
# Use a specific controller model
./tools/tmux_bridge/bridge.py --controller-model gpt-4

# Disable heuristic triggers
./tools/tmux_bridge/bridge.py --no-heuristic

# Increase context sent to controller
./tools/tmux_bridge/bridge.py --worker-context-lines 100
```

## Troubleshooting

### Bridge can't find panes

Ensure your tmux windows/panes have identifiable names:
```bash
# Set pane title manually
printf '\033]2;worker\033\\'
```

Or pin the pane explicitly:
```bash
./tools/tmux_bridge/set_target.sh --pane %3
```

From the controller-owned inspect surface, the equivalent flow is:
```bash
./macs worker inspect --worker <worker-id> --open-pane
./macs task inspect --task <task-id> --open-pane
```

### Worker appears busy when idle

The busy detection looks for "esc to interrupt" in recent output. If this persists in scrollback:
```bash
# Increase busy detection window
TARGET_PANE_BUSY_LINES=60 ./tools/tmux_bridge/status.sh
```

### Responses not being sent

Check if the worker is busy:
```bash
./tools/tmux_bridge/status.sh
```

Force send if needed:
```bash
./tools/tmux_bridge/send.sh --force "your message"
```

## Next Steps

- Read [Using MACS](./user-guide.md) for the operator command surface
- Use [How-To Recipes](./how-tos.md) for common setup, intervention, and recovery flows
- Read the [Architecture Guide](./architecture.md) to understand the control plane
- See [Customization Guide](./customization.md) for advanced configuration
- Read [Contributor Guide](./contributor-guide.md) if you are changing MACS itself
