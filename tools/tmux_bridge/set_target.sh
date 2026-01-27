#!/usr/bin/env bash
# MACS - Pin the target pane for subsequent commands
set -euo pipefail

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not found in PATH" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
session=""
pane=""
label="${TARGET_PANE_LABEL:-worker}"
socket="${TMUX_SOCKET:-}"
tmux_socket_args=()

if [ -n "$socket" ]; then
  tmux_socket_args=(-S "$socket")
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
      echo "Usage: $0 [--session NAME] [--pane %X] [--label TEXT] [--socket PATH]" >&2
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
  pane_listing="$(tmux_cmd list-panes "${list_scope[@]}" -F '#{pane_id} #{window_name} #{pane_title} #{pane_current_command}' 2>&1)" || {
    echo "tmux error: $pane_listing" >&2
    exit 1
  }
  pane="$(printf "%s\n" "$pane_listing" | $rg_cmd "$label" | head -n1 | awk '{print $1}' || true)"
fi
if [ -z "$pane" ] && [ "$label" != "codex" ]; then
  if [ -z "${pane_listing:-}" ]; then
    pane_listing="$(tmux_cmd list-panes "${list_scope[@]}" -F '#{pane_id} #{window_name} #{pane_title} #{pane_current_command}' 2>&1)" || {
      echo "tmux error: $pane_listing" >&2
      exit 1
    }
  fi
  pane="$(printf "%s\n" "$pane_listing" | $rg_cmd "$label" | head -n1 | awk '{print $1}' || true)"
fi

if [ -z "$pane" ]; then
  echo "Unable to find target pane. Provide --pane or set TARGET_PANE_LABEL." >&2
  exit 1
fi

echo "$pane" > "$ROOT_DIR/target_pane.txt"
echo "Target pane set to: $pane"
