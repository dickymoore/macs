#!/usr/bin/env bash
# MACS - Check if worker is busy or idle
set -euo pipefail

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not found in PATH" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "$ROOT_DIR/common.sh"
tmux_bridge_init_state "$ROOT_DIR"
session=""
pane=""
pane_explicit=0
lines="${TARGET_PANE_LINES:-200}"
busy_lines="${TARGET_PANE_BUSY_LINES:-40}"
label="${TARGET_PANE_LABEL:-worker}"
exit_code=0
socket="${TMUX_SOCKET:-}"
resolved_session=""
tmux_socket_args=()
rg_cmd="rg"
pane_format="$(printf '#{pane_id}\t#{session_name}\t#{window_name}\t#{pane_title}\t#{pane_current_command}')"

if [ -n "$socket" ]; then
  tmux_socket_args=(-S "$socket")
fi

if ! command -v rg >/dev/null 2>&1; then
  rg_cmd="grep -i"
fi

tmux_cmd() {
  tmux "${tmux_socket_args[@]}" "$@"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --session)
      session="$2"
      shift 2
      ;;
    --pane)
      pane="$2"
      pane_explicit=1
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
    --exit-code)
      exit_code=1
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--session NAME] [--pane %X] [--lines N] [--label TEXT] [--socket PATH] [--exit-code]" >&2
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

resolve_status_target() {
  local list_scope=("-a")
  local pane_listing=""

  if [ -n "$session" ]; then
    list_scope=("-t" "$session")
  fi

  pane_listing="$(tmux_cmd list-panes "${list_scope[@]}" -F "$pane_format" 2>/dev/null || true)"
  if [ -z "$pane_listing" ]; then
    return 0
  fi

  if [ -n "$pane" ]; then
    :
  else
    pinned_pane="$(read_pinned_target_pane)"
    if [ -n "$pinned_pane" ] && pane_in_listing "$pinned_pane" "$pane_listing"; then
      pane="$pinned_pane"
    else
      pane="$(printf "%s\n" "$pane_listing" | $rg_cmd "$label" | head -n1 | awk -F '\t' '{print $1}' || true)"
    fi
  fi

  if [ -n "$pane" ]; then
    resolved_session="$(pane_session_from_listing "$pane" "$pane_listing" || true)"
  fi
}

resolve_status_target

snapshot="$("$ROOT_DIR/snapshot.sh" --session "$session" --pane "$pane" --lines "$lines" --label "$label" ${socket:+--socket "$socket"})"

recent="$(printf "%s\n" "$snapshot" | tail -n "$busy_lines")"
if printf "%s\n" "$recent" | grep -qi "esc to interrupt"; then
  if [ "$exit_code" -eq 1 ]; then
    exit 1
  fi
  if [ -n "$pane" ]; then
    echo "Resolved target: session=${resolved_session:-unknown} pane=$pane"
  fi
  echo "BUSY"
else
  if [ "$exit_code" -eq 1 ]; then
    exit 0
  fi
  if [ -n "$pane" ]; then
    echo "Resolved target: session=${resolved_session:-unknown} pane=$pane"
  fi
  echo "IDLE"
fi
