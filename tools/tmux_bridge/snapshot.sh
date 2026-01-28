#!/usr/bin/env bash
# MACS - Capture recent output from worker terminal
set -euo pipefail

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not found in PATH" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
session=""
pane=""
lines="${TARGET_PANE_LINES:-200}"
label="${TARGET_PANE_LABEL:-worker}"
socket="${TMUX_SOCKET:-}"

tmux_socket_args=()
if [ -n "$socket" ]; then
  tmux_socket_args=(-S "$socket")
fi

tmux_cmd() {
  tmux "${tmux_socket_args[@]}" "$@"
}

tmux_fail() {
  local err="$1"
  echo "tmux error: $err" >&2
  if printf "%s" "$err" | grep -qi "operation not permitted"; then
    echo "Cannot connect to tmux server. This usually means the session was started by a different user or via sudo." >&2
    echo "Fix: run this script as the same user that started tmux, or set TMUX_SOCKET to the correct socket path." >&2
    echo "If you are inside tmux, you can run: tmux display-message -p '#{socket_path}'" >&2
  elif printf "%s" "$err" | grep -qi "no server running"; then
    echo "No tmux server running. Start tmux or create a session first." >&2
  fi
}

while [ $# -gt 0 ]; do
  case "$1" in
    --session)
      session="$2"
      shift 2
      ;;
    --pane)
      pane="$2"
      shift 2
      ;;
    --lines)
      lines="$2"
      shift 2
      ;;
    --label)
      label="$2"
      shift 2
      ;;
    --socket)
      socket="$2"
      tmux_socket_args=(-S "$socket")
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [--session NAME] [--pane %X] [--lines N] [--label TEXT] [--socket PATH]" >&2
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

rg_cmd="rg"
if ! command -v rg >/dev/null 2>&1; then
  rg_cmd="grep -i"
fi

list_scope=("-a")
if [ -n "$session" ]; then
  list_scope=("-t" "$session")
fi

if [ -z "$pane" ]; then
  if [ -f "$ROOT_DIR/target_pane.txt" ]; then
    pane="$(head -n1 < "$ROOT_DIR/target_pane.txt")"
  fi
fi
if [ -z "$pane" ]; then
  pane_listing="$(tmux_cmd list-panes "${list_scope[@]}" -F '#{pane_id} #{window_name} #{pane_title} #{pane_current_command}' 2>&1)" || {
    tmux_fail "$pane_listing"
    exit 1
  }
  pane="$(printf "%s\n" "$pane_listing" | $rg_cmd "$label" | head -n1 | awk '{print $1}' || true)"
fi
if [ -z "$pane" ] && [ "$label" != "codex" ]; then
  if [ -z "${pane_listing:-}" ]; then
    pane_listing="$(tmux_cmd list-panes "${list_scope[@]}" -F '#{pane_id} #{window_name} #{pane_title} #{pane_current_command}' 2>&1)" || {
      tmux_fail "$pane_listing"
      exit 1
    }
  fi
  pane="$(printf "%s\n" "$pane_listing" | $rg_cmd "$label" | head -n1 | awk '{print $1}' || true)"
fi

if [ -z "$pane" ]; then
  if [ -z "${pane_listing:-}" ]; then
    pane_listing="$(tmux_cmd list-panes "${list_scope[@]}" -F '#{pane_id} #{window_name} #{pane_title} #{pane_current_command}' 2>&1)" || {
      tmux_fail "$pane_listing"
      exit 1
    }
  fi
  pane_count="$(printf "%s\n" "$pane_listing" | sed '/^$/d' | wc -l | tr -d ' ')"
  if [ "$pane_count" -eq 1 ]; then
    pane="$(printf "%s\n" "$pane_listing" | head -n1 | awk '{print $1}')"
    echo "Auto-selected only pane: $pane" >&2
  else
    echo "Unable to find target pane. Provide --pane or set TARGET_PANE_LABEL." >&2
    if [ "$pane_count" -gt 0 ]; then
      echo "Available panes:" >&2
      printf "%s\n" "$pane_listing" >&2
    fi
    echo "Tip: $ROOT_DIR/set_target.sh --pane %X  (or --label worker)" >&2
    exit 1
  fi
fi

capture_out="$(tmux_cmd capture-pane -p -t "$pane" -S "-$lines" 2>&1)" || {
  tmux_fail "$capture_out"
  exit 1
}
printf "%s\n" "$capture_out"
