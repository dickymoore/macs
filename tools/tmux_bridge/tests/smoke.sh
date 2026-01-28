#!/usr/bin/env bash
set -euo pipefail

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not found; skipping tmux_bridge smoke tests." >&2
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RG_CMD="rg"
if ! command -v rg >/dev/null 2>&1; then
  RG_CMD="grep -E"
fi

TMP_DIR="$(mktemp -d)"
REPO_DIR="$(mktemp -d)"
SESSION="macs-test-$$"
SOCKET="$TMP_DIR/tmux.sock"
TARGET_FILE="$ROOT_DIR/target_pane.txt"
TARGET_BACKUP=""

cleanup() {
  tmux -S "$SOCKET" kill-server >/dev/null 2>&1 || true
  if [ -n "$TARGET_BACKUP" ] && [ -f "$TARGET_BACKUP" ]; then
    mv -f "$TARGET_BACKUP" "$TARGET_FILE"
  else
    rm -f "$TARGET_FILE" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR" "$REPO_DIR"
}
trap cleanup EXIT

if [ -f "$TARGET_FILE" ]; then
  TARGET_BACKUP="$TMP_DIR/target_pane.txt.bak"
  cp "$TARGET_FILE" "$TARGET_BACKUP"
fi

# Start a dedicated tmux server for tests.
tmux -S "$SOCKET" new-session -d -s "$SESSION" -n worker
PANE_ID="$(tmux -S "$SOCKET" list-panes -t "$SESSION" -F '#{pane_id}' | head -n1)"
if [ -z "$PANE_ID" ]; then
  echo "Failed to locate tmux pane for test session." >&2
  exit 1
fi

tmux -S "$SOCKET" send-keys -t "$PANE_ID" "echo tmux-bridge-smoke" Enter

"$ROOT_DIR/set_target.sh" --socket "$SOCKET" --pane "$PANE_ID" >/dev/null

sleep 0.2
SNAPSHOT_1="$($ROOT_DIR/snapshot.sh --socket "$SOCKET" --session "$SESSION" --lines 20)"
echo "$SNAPSHOT_1" | $RG_CMD -q "tmux-bridge-smoke"

STATUS_OUT="$($ROOT_DIR/status.sh --socket "$SOCKET" --session "$SESSION")"
echo "$STATUS_OUT" | $RG_CMD -q "IDLE|BUSY"

"$ROOT_DIR/send.sh" --socket "$SOCKET" --session "$SESSION" "echo tmux-bridge-send" >/dev/null
sleep 0.2
SNAPSHOT_2="$($ROOT_DIR/snapshot.sh --socket "$SOCKET" --session "$SESSION" --lines 20)"
echo "$SNAPSHOT_2" | $RG_CMD -q "tmux-bridge-send"

"$ROOT_DIR/start_controller.sh" --repo "$REPO_DIR" --tmux-socket "$SOCKET" --tmux-session "$SESSION" --skip-skills --no-codex >/dev/null

test -f "$REPO_DIR/.codex/tmux-socket.txt"
$RG_CMD -q "^$SOCKET$" "$REPO_DIR/.codex/tmux-socket.txt"
test -f "$REPO_DIR/.codex/tmux-session.txt"
$RG_CMD -q "^$SESSION$" "$REPO_DIR/.codex/tmux-session.txt"
test -x "$REPO_DIR/.codex/tmux-bridge.sh"

WRAP_SNAPSHOT="$(cd "$REPO_DIR" && ./.codex/tmux-bridge.sh snapshot --lines 20)"
echo "$WRAP_SNAPSHOT" | $RG_CMD -q "tmux-bridge-send"

echo "OK: tmux_bridge smoke tests passed."
