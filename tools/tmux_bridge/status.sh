#!/usr/bin/env bash
# MACS - Check if worker is busy or idle
set -euo pipefail

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not found in PATH" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
session=""
pane=""
lines="${TARGET_PANE_LINES:-200}"
busy_lines="${TARGET_PANE_BUSY_LINES:-40}"
label="${TARGET_PANE_LABEL:-worker}"
exit_code=0
socket="${TMUX_SOCKET:-}"

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

snapshot="$("$ROOT_DIR/snapshot.sh" --session "$session" --pane "$pane" --lines "$lines" --label "$label" ${socket:+--socket "$socket"})"

recent="$(printf "%s\n" "$snapshot" | tail -n "$busy_lines")"
if printf "%s\n" "$recent" | grep -qi "esc to interrupt"; then
  if [ "$exit_code" -eq 1 ]; then
    exit 1
  fi
  echo "BUSY"
else
  if [ "$exit_code" -eq 1 ]; then
    exit 0
  fi
  echo "IDLE"
fi
