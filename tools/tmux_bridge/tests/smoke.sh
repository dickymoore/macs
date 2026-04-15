#!/usr/bin/env bash
set -euo pipefail

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not found; skipping tmux_bridge smoke tests." >&2
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT_DIR/../.." && pwd)"
RG_CMD="rg"
if ! command -v rg >/dev/null 2>&1; then
  RG_CMD="grep -E"
fi

TMP_DIR="$(mktemp -d)"
REPO_DIR="$(mktemp -d)"
SESSION="macs-test-$$"
SOCKET="$TMP_DIR/tmux.sock"
WORKER_SOCKET="$TMP_DIR/worker.sock"
WORKER_SESSION="macs-worker-$$"
WORKER_CONFIG="$TMP_DIR/tmux-worker.env"
TARGET_FILE="$REPO_ROOT/.codex/target-pane.txt"
LEGACY_TARGET_FILE="$ROOT_DIR/target_pane.txt"
TARGET_BACKUP=""
LEGACY_TARGET_BACKUP=""

cleanup() {
  tmux -S "$SOCKET" kill-server >/dev/null 2>&1 || true
  tmux -S "$WORKER_SOCKET" kill-server >/dev/null 2>&1 || true
  if [ -n "$TARGET_BACKUP" ] && [ -f "$TARGET_BACKUP" ]; then
    mv -f "$TARGET_BACKUP" "$TARGET_FILE"
  else
    rm -f "$TARGET_FILE" >/dev/null 2>&1 || true
  fi
  if [ -n "$LEGACY_TARGET_BACKUP" ] && [ -f "$LEGACY_TARGET_BACKUP" ]; then
    mv -f "$LEGACY_TARGET_BACKUP" "$LEGACY_TARGET_FILE"
  else
    rm -f "$LEGACY_TARGET_FILE" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR" "$REPO_DIR"
}
trap cleanup EXIT

mkdir -p "$(dirname "$TARGET_FILE")"
if [ -f "$TARGET_FILE" ]; then
  TARGET_BACKUP="$TMP_DIR/target-pane.txt.bak"
  cp "$TARGET_FILE" "$TARGET_BACKUP"
fi
if [ -f "$LEGACY_TARGET_FILE" ]; then
  LEGACY_TARGET_BACKUP="$TMP_DIR/target_pane.txt.bak"
  cp "$LEGACY_TARGET_FILE" "$LEGACY_TARGET_BACKUP"
fi
rm -f "$TARGET_FILE" "$LEGACY_TARGET_FILE"

# Start a dedicated tmux server for tests.
tmux -S "$SOCKET" new-session -d -s "$SESSION" -n worker
PANE_ID="$(tmux -S "$SOCKET" list-panes -t "$SESSION" -F '#{pane_id}' | head -n1)"
if [ -z "$PANE_ID" ]; then
  echo "Failed to locate tmux pane for test session." >&2
  exit 1
fi

tmux -S "$SOCKET" send-keys -t "$PANE_ID" "echo tmux-bridge-smoke" Enter

printf '%s\n' "$PANE_ID" > "$LEGACY_TARGET_FILE"
LEGACY_SNAPSHOT="$("$ROOT_DIR/snapshot.sh" --socket "$SOCKET" --session "$SESSION" --lines 20)"
echo "$LEGACY_SNAPSHOT" | $RG_CMD -q "tmux-bridge-smoke"
rm -f "$LEGACY_TARGET_FILE"

"$ROOT_DIR/set_target.sh" --socket "$SOCKET" --pane "$PANE_ID" >/dev/null
test -f "$TARGET_FILE"
$RG_CMD -q "^$PANE_ID$" "$TARGET_FILE"
test ! -f "$LEGACY_TARGET_FILE"

sleep 0.2
SNAPSHOT_1="$("$ROOT_DIR/snapshot.sh" --socket "$SOCKET" --session "$SESSION" --lines 20)"
echo "$SNAPSHOT_1" | $RG_CMD -q "tmux-bridge-smoke"

STATUS_OUT="$("$ROOT_DIR/status.sh" --socket "$SOCKET" --session "$SESSION")"
echo "$STATUS_OUT" | $RG_CMD -q "IDLE|BUSY"

"$ROOT_DIR/send.sh" --socket "$SOCKET" --session "$SESSION" "echo tmux-bridge-send" >/dev/null
sleep 0.2
SNAPSHOT_2="$("$ROOT_DIR/snapshot.sh" --socket "$SOCKET" --session "$SESSION" --lines 20)"
echo "$SNAPSHOT_2" | $RG_CMD -q "tmux-bridge-send"

printf '%%9999\n' > "$TARGET_FILE"
"$ROOT_DIR/send.sh" --socket "$SOCKET" --session "$SESSION" "echo tmux-bridge-stale-fallback" >/dev/null
sleep 0.2
SNAPSHOT_STALE="$("$ROOT_DIR/snapshot.sh" --socket "$SOCKET" --session "$SESSION" --lines 20)"
echo "$SNAPSHOT_STALE" | $RG_CMD -q "tmux-bridge-stale-fallback"

ALT_SESSION="${SESSION}-alt"
tmux -S "$SOCKET" new-session -d -s "$ALT_SESSION" -n worker
ALT_PANE_ID="$(tmux -S "$SOCKET" list-panes -t "$ALT_SESSION" -F '#{pane_id}' | head -n1)"
if [ -z "$ALT_PANE_ID" ]; then
  echo "Failed to locate tmux pane for alternate session." >&2
  exit 1
fi
printf '%s\n' "$ALT_PANE_ID" > "$TARGET_FILE"
"$ROOT_DIR/send.sh" --socket "$SOCKET" --session "$SESSION" "echo tmux-bridge-session-fallback" >/dev/null
sleep 0.2
SESSION_SNAPSHOT="$("$ROOT_DIR/snapshot.sh" --socket "$SOCKET" --session "$SESSION" --lines 20)"
ALT_SNAPSHOT="$(TMUX_SOCKET="$SOCKET" "$ROOT_DIR/snapshot.sh" --session "$ALT_SESSION" --lines 20)"
echo "$SESSION_SNAPSHOT" | $RG_CMD -q "tmux-bridge-session-fallback"
if echo "$ALT_SNAPSHOT" | $RG_CMD -q "tmux-bridge-session-fallback"; then
  echo "Cross-session contamination detected." >&2
  exit 1
fi
STATUS_OUT="$("$ROOT_DIR/status.sh" --socket "$SOCKET" --session "$SESSION")"
echo "$STATUS_OUT" | $RG_CMD -q "IDLE|BUSY"

"$ROOT_DIR/start_controller.sh" --repo "$REPO_DIR" --tmux-socket "$SOCKET" --tmux-session "$SESSION" --skip-skills --no-codex >/dev/null

test -f "$REPO_DIR/.codex/tmux-socket.txt"
$RG_CMD -q "^$SOCKET$" "$REPO_DIR/.codex/tmux-socket.txt"
test -f "$REPO_DIR/.codex/tmux-session.txt"
$RG_CMD -q "^$SESSION$" "$REPO_DIR/.codex/tmux-session.txt"
test -x "$REPO_DIR/.codex/tmux-bridge.sh"

(
  cd "$REPO_DIR"
  TMUX_SOCKET="" ./.codex/tmux-bridge.sh set_target --pane "$PANE_ID" >/dev/null
)
test -f "$REPO_DIR/.codex/target-pane.txt"
$RG_CMD -q "^$PANE_ID$" "$REPO_DIR/.codex/target-pane.txt"
test ! -f "$ROOT_DIR/target_pane.txt"

WRAP_SNAPSHOT="$(cd "$REPO_DIR" && TMUX_SOCKET="" ./.codex/tmux-bridge.sh snapshot --lines 20)"
echo "$WRAP_SNAPSHOT" | $RG_CMD -q "tmux-bridge-send"

OTHER_SOCKET="$TMP_DIR/other.sock"
OTHER_SESSION="${SESSION}-other"
tmux -S "$OTHER_SOCKET" new-session -d -s "$OTHER_SESSION" -n worker
OTHER_PANE_ID="$(tmux -S "$OTHER_SOCKET" list-panes -t "$OTHER_SESSION" -F '#{pane_id}' | head -n1)"
if [ -z "$OTHER_PANE_ID" ]; then
  echo "Failed to locate tmux pane for other session." >&2
  exit 1
fi
tmux -S "$OTHER_SOCKET" send-keys -t "$OTHER_PANE_ID" "echo tmux-bridge-other-socket" Enter
printf '%s\n' "$OTHER_SOCKET" > "$REPO_DIR/.codex/tmux-socket.txt"
WRAP_SNAPSHOT_LIVE_ENV="$(cd "$REPO_DIR" && TMUX_SOCKET="$SOCKET" ./.codex/tmux-bridge.sh snapshot --lines 20)"
echo "$WRAP_SNAPSHOT_LIVE_ENV" | $RG_CMD -q "tmux-bridge-send"
if echo "$WRAP_SNAPSHOT_LIVE_ENV" | $RG_CMD -q "tmux-bridge-other-socket"; then
  echo "Wrapper preferred cached socket over live TMUX_SOCKET." >&2
  exit 1
fi

printf 'bogus\n' > "$REPO_DIR/.codex/tmux-socket.txt"
WRAP_SNAPSHOT_FALLBACK="$(cd "$REPO_DIR" && TMUX_SOCKET="$SOCKET" ./.codex/tmux-bridge.sh snapshot --lines 20)"
echo "$WRAP_SNAPSHOT_FALLBACK" | $RG_CMD -q "tmux-bridge-send"

cat > "$WORKER_CONFIG" <<EOF
TMUX_MOUSE=off
TMUX_HISTORY_LIMIT=12345
TMUX_SOCKET=$WORKER_SOCKET
EOF

(cd "$REPO_DIR" && TMUX_SOCKET="" "$ROOT_DIR/start_worker.sh" --session "$WORKER_SESSION" --tmux-config "$WORKER_CONFIG" --no-attach --no-codex >/dev/null)

mouse_value="$(tmux -S "$WORKER_SOCKET" show-options -t "$WORKER_SESSION" -v mouse)"
history_value="$(tmux -S "$WORKER_SOCKET" show-options -t "$WORKER_SESSION" -v history-limit)"
test "$mouse_value" = "off"
test "$history_value" = "12345"

test -f "$REPO_DIR/.codex/tmux-socket.txt"
$RG_CMD -q "^$WORKER_SOCKET$" "$REPO_DIR/.codex/tmux-socket.txt"
test -f "$REPO_DIR/.codex/tmux-session.txt"
$RG_CMD -q "^$WORKER_SESSION$" "$REPO_DIR/.codex/tmux-session.txt"

echo "OK: tmux_bridge smoke tests passed."
