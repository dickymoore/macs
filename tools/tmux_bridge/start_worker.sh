#!/usr/bin/env bash
# MACS - Start the worker terminal
set -euo pipefail

SESSION="macs"
WINDOW="worker"
ATTACH=1
RESET_SESSION=0
session_set=0

usage() {
  echo "Usage: $0 [--session NAME] [--no-attach|--detach] [--reset-session] [SESSION]" >&2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --session)
      if [ $# -lt 2 ]; then
        echo "Missing value for --session" >&2
        usage
        exit 1
      fi
      SESSION="$2"
      session_set=1
      shift 2
      ;;
    --no-attach|--detach)
      ATTACH=0
      shift
      ;;
    --reset-session|--clean-session)
      RESET_SESSION=1
      shift
      ;;
    --attach)
      ATTACH=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      if [ "$session_set" -eq 0 ]; then
        SESSION="$1"
        session_set=1
        shift
      else
        echo "Unknown arg: $1" >&2
        usage
        exit 1
      fi
      ;;
  esac
done

if [ "$RESET_SESSION" -eq 1 ]; then
  tmux kill-session -t "$SESSION" 2>/dev/null || true
fi

# Create session/window if missing and capture a stable pane id.
pane_id=""
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  pane_id="$(tmux new-session -d -s "$SESSION" -n "$WINDOW" -P -F '#{pane_id}')"
else
  # Prefer a pane already labeled via pane_title.
  pane_id="$(
    tmux list-panes -t "$SESSION" -F '#{pane_id}\t#{pane_title}' |
      awk -F '\t' -v label="$WINDOW" '$2==label {print $1; exit}'
  )"
  if [ -z "$pane_id" ]; then
    window_id="$(
      tmux list-windows -t "$SESSION" -F '#{window_id}\t#{window_name}\t#{window_active}\t#{window_index}' |
        awk -F '\t' -v name="$WINDOW" '
          $2==name {
            if ($3==1) {active=$1}
            if ($4+0 >= max) {max=$4+0; win=$1}
          }
          END {
            if (active!="") print active;
            else if (win!="") print win;
          }
        '
    )"
    if [ -n "${window_id:-}" ]; then
      pane_id="$(tmux list-panes -t "$window_id" -F '#{pane_id}' | head -n1)"
    else
      pane_id="$(tmux new-window -t "$SESSION" -n "$WINDOW" -P -F '#{pane_id}')"
    fi
  fi
fi

if [ -z "$pane_id" ]; then
  echo "Unable to find or create a pane for window '$WINDOW' in session '$SESSION'." >&2
  exit 1
fi

# Set window/pane title
tmux send-keys -t "$pane_id" "printf '\\033]2;worker\\033\\\\'" Enter

echo "Worker window ready in session: $SESSION"
echo "To start codex: codex"

if [ "$ATTACH" -eq 1 ]; then
  if [ -n "${TMUX:-}" ]; then
    echo "Switching to session: $SESSION"
    tmux switch-client -t "$SESSION"
  else
    echo "Attaching to session: $SESSION"
    tmux attach -t "$SESSION"
  fi
else
  echo "To attach: tmux attach -t $SESSION"
fi
