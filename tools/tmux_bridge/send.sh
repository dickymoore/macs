#!/usr/bin/env bash
# MACS - Send commands to worker terminal
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
label="${TARGET_PANE_LABEL:-worker}"
message=""
expand_escapes=0
submit_after="${TARGET_PANE_SUBMIT_AFTER:-1}"
line_mode=0
submit_keys="${TARGET_PANE_SUBMIT_KEYS:-Enter}"
submit_repeat="${TARGET_PANE_SUBMIT_REPEAT:-1}"
submit_delay_ms="${TARGET_PANE_SUBMIT_DELAY_MS:-200}"
type_delay_ms="${TARGET_PANE_TYPE_DELAY_MS:-400}"
literal_mode=0
guard_busy="${TARGET_PANE_GUARD_BUSY:-1}"
force_send=0
socket="${TMUX_SOCKET:-}"
tmux_socket_args=()
submit_key=""

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
    --label)
      label="$2"
      shift 2
      ;;
    --expand-escapes)
      expand_escapes=1
      shift
      ;;
    --submit-after)
      submit_after=1
      shift
      ;;
    --line-mode)
      line_mode=1
      submit_after=0
      shift
      ;;
    --submit-key)
      submit_keys="$2"
      shift 2
      ;;
    --submit-keys)
      submit_keys="$2"
      shift 2
      ;;
    --socket)
      socket="$2"
      tmux_socket_args=(-S "$socket")
      shift 2
      ;;
    --submit-repeat)
      submit_repeat="$2"
      shift 2
      ;;
    --submit-delay-ms)
      submit_delay_ms="$2"
      shift 2
      ;;
    --type-delay-ms)
      type_delay_ms="$2"
      shift 2
      ;;
    --literal)
      literal_mode=1
      shift
      ;;
    --force)
      force_send=1
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--session NAME] [--pane %X] [--label TEXT] [--socket PATH] [message...]" >&2
      exit 0
      ;;
    *)
      message="${message:+$message }$1"
      shift
      ;;
  esac
done

if [ -z "$message" ]; then
  if [ -t 0 ]; then
    echo "No message provided." >&2
    exit 1
  fi
  message="$(cat)"
fi

if [ "$expand_escapes" -eq 1 ]; then
  message="$(printf "%b" "$message")"
else
  if printf "%s" "$message" | grep -q '\\n' && ! printf "%s" "$message" | grep -q $'\n'; then
    message="$(printf "%b" "$message")"
  fi
fi

submit_key="${submit_keys%%,*}"
if [ -z "$submit_key" ]; then
  submit_key="Enter"
fi

# Trim leading blank lines to avoid sending accidental empty submits.
while [ -n "$message" ] && [ "${message%%$'\n'*}" = "" ]; do
  message="${message#"$'\n'"}"
done
# Trim trailing newlines to avoid extra submits.
while [ -n "$message" ] && [ "${message##*$'\n'}" = "" ]; do
  message="${message%$'\n'}"
done

rg_cmd="rg"
if ! command -v rg >/dev/null 2>&1; then
  rg_cmd="grep -i"
fi

list_scope=("-a")
if [ -n "$session" ]; then
  list_scope=("-t" "$session")
fi

list_panes() {
  tmux_cmd list-panes "${list_scope[@]}" -F '#{pane_id} #{window_name} #{pane_title} #{pane_current_command}' 2>&1
}

if [ -z "$pane" ]; then
  pinned_pane="$(read_pinned_target_pane)"
  if [ -n "$pinned_pane" ]; then
    pane_listing="$(list_panes)" || {
      tmux_fail "$pane_listing"
      exit 1
    }
    if pane_in_listing "$pinned_pane" "$pane_listing"; then
      pane="$pinned_pane"
    fi
  fi
fi
if [ -z "$pane" ]; then
  if [ -z "${pane_listing:-}" ]; then
    pane_listing="$(list_panes)" || {
      tmux_fail "$pane_listing"
      exit 1
    }
  fi
  pane="$(printf "%s\n" "$pane_listing" | $rg_cmd "$label" | head -n1 | awk '{print $1}' || true)"
fi
if [ -z "$pane" ] && [ "$label" != "codex" ]; then
  if [ -z "${pane_listing:-}" ]; then
    pane_listing="$(list_panes)" || {
      tmux_fail "$pane_listing"
      exit 1
    }
  fi
  pane="$(printf "%s\n" "$pane_listing" | $rg_cmd "$label" | head -n1 | awk '{print $1}' || true)"
fi

if [ -z "$pane" ]; then
  echo "Unable to find target pane. Provide --pane or set TARGET_PANE_LABEL." >&2
  exit 1
fi

if [ "$guard_busy" -eq 1 ] && [ "$force_send" -eq 0 ]; then
  if "$ROOT_DIR/status.sh" --pane "$pane" --exit-code ${socket:+--socket "$socket"} >/dev/null 2>&1; then
    true
  else
    echo "Worker is busy (esc to interrupt). Refusing to send. Use --force to override." >&2
    exit 2
  fi
fi

send_line() {
  local pane_id="$1"
  local line="$2"
  if [ ${#line} -le 1000 ]; then
    tmux_cmd send-keys -t "$pane_id" -- "$line" "$submit_key"
    return
  fi
  local buf_name="macs-bridge-$$"
  printf "%s" "$line" | tmux_cmd load-buffer -b "$buf_name" -
  tmux_cmd paste-buffer -t "$pane_id" -b "$buf_name"
  tmux_cmd delete-buffer -b "$buf_name" >/dev/null 2>&1 || true
  tmux_cmd send-keys -t "$pane_id" "$submit_key"
}

if [ "$line_mode" -eq 1 ]; then
  while IFS= read -r line; do
    send_line "$pane" "$line"
  done <<<"$message"
elif [ "$submit_after" -eq 1 ]; then
  if [ "$literal_mode" -eq 1 ] || [ "${#message}" -le 4000 ]; then
    tmux_cmd send-keys -t "$pane" -l -- "$message"
  else
    buf_name="macs-bridge-$$"
    printf "%s" "$message" | tmux_cmd load-buffer -b "$buf_name" -
    tmux_cmd paste-buffer -t "$pane" -b "$buf_name"
    tmux_cmd delete-buffer -b "$buf_name" >/dev/null 2>&1 || true
  fi
  if [ "$type_delay_ms" -gt 0 ]; then
    sleep "$(awk "BEGIN {print $type_delay_ms/1000}")"
  fi
  i=0
  while [ "$i" -lt "$submit_repeat" ]; do
    IFS=',' read -r -a submit_list <<<"$submit_keys"
    for key in "${submit_list[@]}"; do
      tmux_cmd send-keys -t "$pane" "$key"
      if [ "$submit_delay_ms" -gt 0 ]; then
        sleep "$(awk "BEGIN {print $submit_delay_ms/1000}")"
      fi
    done
    i=$((i + 1))
  done
else
  send_line "$pane" "$message"
fi
