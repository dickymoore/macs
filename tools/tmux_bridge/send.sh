#!/usr/bin/env bash
# MACS - Send commands to worker terminal
set -euo pipefail

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not found in PATH" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
session=""
pane=""
label="${TARGET_PANE_LABEL:-worker}"
message=""
expand_escapes=0
submit_after="${TARGET_PANE_SUBMIT_AFTER:-1}"
line_mode=0
submit_keys="${TARGET_PANE_SUBMIT_KEYS:-Enter,C-m}"
submit_repeat="${TARGET_PANE_SUBMIT_REPEAT:-1}"
submit_delay_ms="${TARGET_PANE_SUBMIT_DELAY_MS:-200}"
type_delay_ms="${TARGET_PANE_TYPE_DELAY_MS:-400}"
literal_mode=0
guard_busy="${TARGET_PANE_GUARD_BUSY:-1}"
force_send=0

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
      echo "Usage: $0 [--session NAME] [--pane %X] [--label TEXT] [message...]" >&2
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

if [ -z "$pane" ]; then
  if [ -f "$ROOT_DIR/target_pane.txt" ]; then
    pane="$(cat "$ROOT_DIR/target_pane.txt" | head -n1)"
  fi
fi
if [ -z "$pane" ]; then
  pane="$(tmux list-panes "${list_scope[@]}" -F '#{pane_id} #{window_name} #{pane_title} #{pane_current_command}' | $rg_cmd "$label" | head -n1 | awk '{print $1}' || true)"
fi
if [ -z "$pane" ] && [ "$label" != "codex" ]; then
  pane="$(tmux list-panes "${list_scope[@]}" -F '#{pane_id} #{pane_current_command}' | $rg_cmd "$label" | head -n1 | awk '{print $1}' || true)"
fi

if [ -z "$pane" ]; then
  echo "Unable to find target pane. Provide --pane or set TARGET_PANE_LABEL." >&2
  exit 1
fi

if [ "$guard_busy" -eq 1 ] && [ "$force_send" -eq 0 ]; then
  if "$ROOT_DIR/status.sh" --pane "$pane" --exit-code >/dev/null 2>&1; then
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
    tmux send-keys -t "$pane_id" -- "$line" "$submit_key"
    return
  fi
  local buf_name="macs-bridge-$$"
  printf "%s" "$line" | tmux load-buffer -b "$buf_name" -
  tmux paste-buffer -t "$pane_id" -b "$buf_name"
  tmux delete-buffer -b "$buf_name" >/dev/null 2>&1 || true
  tmux send-keys -t "$pane_id" "$submit_key"
}

if [ "$line_mode" -eq 1 ]; then
  while IFS= read -r line; do
    send_line "$pane" "$line"
  done <<<"$message"
elif [ "$submit_after" -eq 1 ]; then
  if [ "$literal_mode" -eq 1 ] || [ "${#message}" -le 4000 ]; then
    tmux send-keys -t "$pane" -l -- "$message"
  else
    buf_name="macs-bridge-$$"
    printf "%s" "$message" | tmux load-buffer -b "$buf_name" -
    tmux paste-buffer -t "$pane" -b "$buf_name"
    tmux delete-buffer -b "$buf_name" >/dev/null 2>&1 || true
  fi
  if [ "$type_delay_ms" -gt 0 ]; then
    sleep "$(awk "BEGIN {print $type_delay_ms/1000}")"
  fi
  i=0
  while [ "$i" -lt "$submit_repeat" ]; do
    IFS=',' read -r -a submit_list <<<"$submit_keys"
    for key in "${submit_list[@]}"; do
      tmux send-keys -t "$pane" "$key"
      if [ "$submit_delay_ms" -gt 0 ]; then
        sleep "$(awk "BEGIN {print $submit_delay_ms/1000}")"
      fi
    done
    i=$((i + 1))
  done
else
  send_line "$pane" "$message"
fi
