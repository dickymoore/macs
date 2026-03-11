#!/usr/bin/env bash

tmux_bridge_init_state() {
  local bridge_root="$1"
  local repo_root=""

  if [ -n "${MACS_REPO_ROOT:-}" ]; then
    repo_root="$MACS_REPO_ROOT"
  elif [ -n "${CODEX_HOME:-}" ]; then
    TARGET_STATE_DIR="$CODEX_HOME"
  else
    if command -v git >/dev/null 2>&1; then
      repo_root="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null || true)"
      if [ -z "$repo_root" ]; then
        repo_root="$(git -C "$bridge_root/../.." rev-parse --show-toplevel 2>/dev/null || true)"
      fi
    fi
  fi

  if [ -n "$repo_root" ]; then
    TARGET_STATE_DIR="$repo_root/.codex"
  fi

  if [ -z "${TARGET_STATE_DIR:-}" ]; then
    TARGET_STATE_DIR="$PWD/.codex"
  fi

  TARGET_PANE_STATE_FILE="$TARGET_STATE_DIR/target-pane.txt"
  LEGACY_TARGET_PANE_FILE="$bridge_root/target_pane.txt"
}

read_pinned_target_pane() {
  local candidate=""

  if [ -f "$TARGET_PANE_STATE_FILE" ]; then
    candidate="$(head -n1 < "$TARGET_PANE_STATE_FILE")"
  fi

  if [ -z "$candidate" ] && [ -f "$LEGACY_TARGET_PANE_FILE" ]; then
    candidate="$(head -n1 < "$LEGACY_TARGET_PANE_FILE")"
  fi

  printf "%s" "$candidate"
}

write_pinned_target_pane() {
  local pane="$1"

  mkdir -p "$TARGET_STATE_DIR"
  printf "%s\n" "$pane" > "$TARGET_PANE_STATE_FILE"
}

pane_in_listing() {
  local pane="$1"
  local listing="$2"

  if [ -z "$pane" ] || [ -z "$listing" ]; then
    return 1
  fi

  awk -v pane="$pane" '$1 == pane { found = 1 } END { exit(found ? 0 : 1) }' <<<"$listing"
}
