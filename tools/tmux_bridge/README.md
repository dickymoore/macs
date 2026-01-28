# MACS TMux Bridge

The tmux bridge enables multi-terminal AI agent orchestration by monitoring communication between a controller and worker terminal.

## Scripts

| Script | Purpose |
|--------|---------|
| `bridge.py` | Main orchestration bridge (Python) |
| `snapshot.sh` | Capture recent output from worker terminal |
| `send.sh` | Send text/commands to worker terminal |
| `status.sh` | Check if worker is busy or idle |
| `set_target.sh` | Pin the target pane for subsequent commands |
| `start_controller.sh` | Install controller prompt + skills into a repo and launch Codex with `/prompts:controller` |
| `start_worker.sh` | Create/select worker window in tmux |
| `controller_prompt.txt` | System prompt for controller LLM |

## Quick Start

```bash
# 1. Start tmux session with a worker window
./start_worker.sh macs

# start_worker auto-attaches by default; use --no-attach to skip
# start_worker auto-launches codex in a new worker pane:
#   CODEX_HOME="<repo>/.codex" codex --yolo
# use --no-codex to skip or --start-codex to force in an existing pane
# use --reset-session to clear an existing tmux session first

# 2. In worker window: start codex
codex

# 3. In a controller terminal/window (from your project repo root):
/path/to/macs/tools/tmux_bridge/start_controller.sh
# or, if you copied the scripts into your repo:
# ./tools/tmux_bridge/start_controller.sh
# or from anywhere:
# /path/to/macs/tools/tmux_bridge/start_controller.sh --repo /path/to/your-repo
# skip copying skills:
# /path/to/macs/tools/tmux_bridge/start_controller.sh --skip-skills
# if tmux socket auto-detect fails:
# /path/to/macs/tools/tmux_bridge/start_controller.sh --tmux-session macs
# /path/to/macs/tools/tmux_bridge/start_controller.sh --tmux-socket /tmp/tmux-<uid>/default
# to bypass tmux detection (not recommended):
# /path/to/macs/tools/tmux_bridge/start_controller.sh --no-tmux-detect
# if Codex can't access the tmux socket from inside its sandbox:
# /path/to/macs/tools/tmux_bridge/start_controller.sh --codex-args "--sandbox danger-full-access"
# or set MACS_CODEX_ARGS="--sandbox danger-full-access"
# to only install prompts/skills without launching Codex:
# /path/to/macs/tools/tmux_bridge/start_controller.sh --no-codex

# This writes .codex/macs-path.txt so the controller can find tmux_bridge tools.
# If you pass --tmux-session it writes .codex/tmux-session.txt for auto-targeting.

# The controller prompt also installs a wrapper for cleaner commands:
# ./.codex/tmux-bridge.sh snapshot|send|status|set_target|notify

# 4. From a separate terminal: start the bridge
./bridge.py --session macs
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_PANE_LABEL` | `worker` | Label to search for when discovering panes |
| `TARGET_PANE_LINES` | `200` | Lines to capture in snapshots |
| `TARGET_PANE_BUSY_LINES` | `40` | Recent lines to check for busy indicator |
| `TARGET_PANE_SUBMIT_KEYS` | `Enter,C-m` | Keys to send after input |
| `TARGET_PANE_TYPE_DELAY_MS` | `400` | Delay after typing before submit |
| `TARGET_PANE_GUARD_BUSY` | `1` | Refuse to send if worker is busy |
| `TMUX_SOCKET` | (unset) | Optional tmux socket path for all scripts (`--socket` flag) |
| `MACS_CODEX_ARGS` | (unset) | Extra args to pass to `codex` from `start_controller.sh` |
| `MACS_CODEX_HOME` | (unset) | Override `CODEX_HOME` when `start_worker.sh` auto-launches Codex |

## Bridge Modes

### Auto Mode (default)
The bridge automatically invokes the controller agent via Codex when requests are detected.

```bash
./bridge.py --mode auto --controller-backend codex-interactive
```

### Manual Mode
The bridge writes requests to `inbox/` and waits for response files in `outbox/`.

```bash
./bridge.py --mode manual
```

### Dry Run
Test request detection without sending responses.

```bash
./bridge.py --dry-run
```

## Request/Response Protocol

Worker agents can request controller input using delimited blocks:

```
<<CONTROLLER_REQUEST>>
I've completed the authentication changes.
Should I proceed to implement the rate limiting?
<<CONTROLLER_REQUEST_END>>
```

The controller responds with:

```
<<CONTROLLER_RESPONSE>>
WORKER INSTRUCTIONS:
Yes, proceed with rate limiting.
Use the token bucket algorithm.
Limit to 100 requests per minute per user.

NOTES:
Good progress. The auth changes look correct.
<<CONTROLLER_RESPONSE_END>>
```

## Heuristic Mode

When `--heuristic` is enabled (default), the bridge also triggers on:
- Lines ending with `?`
- Phrases like "what would you like", "should i", "ready to proceed"
- Completion indicators like "done", "complete", "finished"

Disable with `--no-heuristic`.

## Directories

- `inbox/` - Incoming requests (written by bridge)
- `outbox/` - Responses (read by bridge in manual mode)
- `archive/` - Historical requests and responses

## Testing

Run the tmux bridge smoke test (creates a temporary tmux server and cleans up after itself):

```bash
./tools/tmux_bridge/tests/smoke.sh
```
