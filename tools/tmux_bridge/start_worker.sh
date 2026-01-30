#!/usr/bin/env bash
# MACS - Start the worker terminal
set -euo pipefail

SESSION="macs"
WINDOW="worker"
ATTACH=1
RESET_SESSION=0
session_set=0
START_CODEX=1
FORCE_CODEX=0
CODEX_HOME_DIR="${MACS_CODEX_HOME:-$PWD/.codex}"
STATE_DIR="$PWD/.codex"
DEFAULT_SOCKET_PATH="$STATE_DIR/tmux.sock"
TMUX_SOCKET_ENV="${TMUX_SOCKET:-}"
TMUX_SOCKET_OVERRIDE="$TMUX_SOCKET_ENV"
TMUX_CONFIG_PATH="${MACS_TMUX_CONFIG:-}"
TMUX_MOUSE="${MACS_TMUX_MOUSE:-on}"
TMUX_HISTORY_LIMIT="${MACS_TMUX_HISTORY_LIMIT:-100000}"
MOUSE_SET=0
HISTORY_SET=0
SOCKET_SET=0

usage() {
  echo "Usage: $0 [--session NAME] [--no-attach|--detach] [--reset-session] [--no-codex|--start-codex] [--tmux-config PATH] [--mouse|--no-mouse] [--history-limit N] [--tmux-socket PATH] [SESSION]" >&2
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
    --tmux-config|--config)
      if [ $# -lt 2 ]; then
        echo "Missing value for --tmux-config" >&2
        usage
        exit 1
      fi
      TMUX_CONFIG_PATH="$2"
      shift 2
      ;;
    --tmux-socket)
      if [ $# -lt 2 ]; then
        echo "Missing value for --tmux-socket" >&2
        usage
        exit 1
      fi
      TMUX_SOCKET_OVERRIDE="$2"
      SOCKET_SET=1
      shift 2
      ;;
    --mouse)
      TMUX_MOUSE="on"
      MOUSE_SET=1
      shift
      ;;
    --no-mouse)
      TMUX_MOUSE="off"
      MOUSE_SET=1
      shift
      ;;
    --history-limit)
      if [ $# -lt 2 ]; then
        echo "Missing value for --history-limit" >&2
        usage
        exit 1
      fi
      TMUX_HISTORY_LIMIT="$2"
      HISTORY_SET=1
      shift 2
      ;;
    --no-codex)
      START_CODEX=0
      shift
      ;;
    --start-codex)
      FORCE_CODEX=1
      START_CODEX=1
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

if [ -n "$TMUX_CONFIG_PATH" ] && [ ! -f "$TMUX_CONFIG_PATH" ]; then
  echo "tmux config not found: $TMUX_CONFIG_PATH" >&2
  exit 1
fi

if [ -z "$TMUX_CONFIG_PATH" ]; then
  if [ -f "$PWD/.codex/tmux-worker.env" ]; then
    TMUX_CONFIG_PATH="$PWD/.codex/tmux-worker.env"
  elif [ -f "$HOME/.config/macs/tmux-worker.env" ]; then
    TMUX_CONFIG_PATH="$HOME/.config/macs/tmux-worker.env"
  fi
fi

if [ -n "$TMUX_CONFIG_PATH" ] && [ -f "$TMUX_CONFIG_PATH" ]; then
  TMUX_MOUSE_BEFORE="$TMUX_MOUSE"
  TMUX_HISTORY_LIMIT_BEFORE="$TMUX_HISTORY_LIMIT"
  TMUX_SOCKET_BEFORE="$TMUX_SOCKET_OVERRIDE"
  # shellcheck disable=SC1090
  . "$TMUX_CONFIG_PATH"
  if [ "$MOUSE_SET" -eq 1 ]; then
    TMUX_MOUSE="$TMUX_MOUSE_BEFORE"
  fi
  if [ "$HISTORY_SET" -eq 1 ]; then
    TMUX_HISTORY_LIMIT="$TMUX_HISTORY_LIMIT_BEFORE"
  fi
  if [ "$SOCKET_SET" -eq 0 ] && [ -z "$TMUX_SOCKET_ENV" ] && [ -n "${TMUX_SOCKET:-}" ]; then
    TMUX_SOCKET_OVERRIDE="$TMUX_SOCKET"
  else
    TMUX_SOCKET_OVERRIDE="$TMUX_SOCKET_BEFORE"
  fi
fi

case "$TMUX_MOUSE" in
  1|on|true|yes|ON|TRUE|YES)
    TMUX_MOUSE="on"
    ;;
  0|off|false|no|OFF|FALSE|NO)
    TMUX_MOUSE="off"
    ;;
  *)
    echo "Invalid TMUX_MOUSE value: $TMUX_MOUSE (use on/off)" >&2
    exit 1
    ;;
esac

case "$TMUX_HISTORY_LIMIT" in
  ''|*[!0-9]*)
    echo "Invalid TMUX_HISTORY_LIMIT: $TMUX_HISTORY_LIMIT (use a number)" >&2
    exit 1
    ;;
esac

mkdir -p "$STATE_DIR"

if [ -z "$TMUX_SOCKET_OVERRIDE" ]; then
  TMUX_SOCKET_OVERRIDE="$DEFAULT_SOCKET_PATH"
fi

tmux_socket_args=()
if [ -n "$TMUX_SOCKET_OVERRIDE" ]; then
  tmux_socket_args=(-S "$TMUX_SOCKET_OVERRIDE")
fi

tmux_cmd() {
  tmux "${tmux_socket_args[@]}" "$@"
}

if [ "$RESET_SESSION" -eq 1 ]; then
  tmux_cmd kill-session -t "$SESSION" 2>/dev/null || true
fi

# Create session/window if missing and capture a stable pane id.
pane_id=""
created_new=0
if ! tmux_cmd has-session -t "$SESSION" 2>/dev/null; then
  pane_id="$(tmux_cmd new-session -d -s "$SESSION" -n "$WINDOW" -P -F '#{pane_id}')"
  created_new=1
else
  # Prefer a pane already labeled via pane_title.
  pane_id="$(
    tmux_cmd list-panes -t "$SESSION" -F '#{pane_id}\t#{pane_title}' |
      awk -F '\t' -v label="$WINDOW" '$2==label {print $1; exit}'
  )"
  if [ -z "$pane_id" ]; then
    window_id="$(
      tmux_cmd list-windows -t "$SESSION" -F '#{window_id}\t#{window_name}\t#{window_active}\t#{window_index}' |
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
      pane_id="$(tmux_cmd list-panes -t "$window_id" -F '#{pane_id}' | head -n1)"
    else
      pane_id="$(tmux_cmd new-window -t "$SESSION" -n "$WINDOW" -P -F '#{pane_id}')"
      created_new=1
    fi
  fi
fi

if [ -z "$pane_id" ]; then
  echo "Unable to find or create a pane for window '$WINDOW' in session '$SESSION'." >&2
  exit 1
fi

mkdir -p "$STATE_DIR"
echo "$SESSION" > "$STATE_DIR/tmux-session.txt"

socket_path="$TMUX_SOCKET_OVERRIDE"
if [ -z "$socket_path" ]; then
  socket_path="$(tmux_cmd display-message -p '#{socket_path}' 2>/dev/null || true)"
fi
if [ -n "$socket_path" ]; then
  echo "$socket_path" > "$STATE_DIR/tmux-socket.txt"
fi

tmux_cmd set-option -t "$SESSION" mouse "$TMUX_MOUSE" >/dev/null
tmux_cmd set-option -t "$SESSION" history-limit "$TMUX_HISTORY_LIMIT" >/dev/null

# Set window/pane title
tmux_cmd send-keys -t "$pane_id" "printf '\\033]2;worker\\033\\\\'" Enter

echo "Worker window ready in session: $SESSION"

pane_cmd="$(tmux_cmd display-message -p -t "$pane_id" '#{pane_current_command}' 2>/dev/null || true)"
if [ "$START_CODEX" -eq 1 ] && { [ "$created_new" -eq 1 ] || [ "$FORCE_CODEX" -eq 1 ]; }; then
  if [ "$pane_cmd" = "codex" ] && [ "$FORCE_CODEX" -eq 0 ]; then
    echo "Codex already running in pane: $pane_id"
  else
    tmux_cmd send-keys -t "$pane_id" -l "CODEX_HOME=\"$CODEX_HOME_DIR\" codex --yolo" C-m
    echo "Starting codex in pane: $pane_id"
  fi
else
  echo "To start codex: CODEX_HOME=\"$CODEX_HOME_DIR\" codex --yolo"
fi

if [ "$ATTACH" -eq 1 ]; then
  if [ -n "${TMUX:-}" ] && [ -z "$TMUX_SOCKET_OVERRIDE" ]; then
    echo "Switching to session: $SESSION"
    tmux_cmd switch-client -t "$SESSION"
  else
    echo "Attaching to session: $SESSION"
    tmux_cmd attach -t "$SESSION"
  fi
else
  if [ -n "$TMUX_SOCKET_OVERRIDE" ]; then
    echo "To attach: tmux -S \"$TMUX_SOCKET_OVERRIDE\" attach -t $SESSION"
  else
    echo "To attach: tmux attach -t $SESSION"
  fi
fi
