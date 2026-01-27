#!/usr/bin/env bash
# MACS - Start the controller Codex session in the current terminal
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC_PROMPT="${MACS_CONTROLLER_PROMPT:-$ROOT_DIR/.codex/prompts/controller.md}"
SRC_SKILLS_DIR="${MACS_SKILLS_DIR:-$ROOT_DIR/.codex/skills}"
TARGET_DIR="$PWD"
FORCE=0
SKIP_SKILLS=0
TMUX_SOCKET_OVERRIDE=""
TMUX_SESSION=""
TMUX_DETECT=1
RUN_CODEX=1
CODEX_ARGS_RAW="${MACS_CODEX_ARGS:-}"
CODEX_ARGS=()

usage() {
  echo "Usage: $0 [--repo PATH] [--prompt PATH] [--skills PATH] [--skip-skills] [--force] [--tmux-socket PATH] [--tmux-session NAME] [--no-tmux-detect] [--codex-args \"...\"] [--no-codex]" >&2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --repo)
      if [ $# -lt 2 ]; then
        echo "Missing value for --repo" >&2
        usage
        exit 1
      fi
      TARGET_DIR="$2"
      shift 2
      ;;
    --prompt)
      if [ $# -lt 2 ]; then
        echo "Missing value for --prompt" >&2
        usage
        exit 1
      fi
      SRC_PROMPT="$2"
      shift 2
      ;;
    --skills)
      if [ $# -lt 2 ]; then
        echo "Missing value for --skills" >&2
        usage
        exit 1
      fi
      SRC_SKILLS_DIR="$2"
      shift 2
      ;;
    --tmux-socket)
      if [ $# -lt 2 ]; then
        echo "Missing value for --tmux-socket" >&2
        usage
        exit 1
      fi
      TMUX_SOCKET_OVERRIDE="$2"
      shift 2
      ;;
    --tmux-session)
      if [ $# -lt 2 ]; then
        echo "Missing value for --tmux-session" >&2
        usage
        exit 1
      fi
      TMUX_SESSION="$2"
      shift 2
      ;;
    --no-tmux-detect)
      TMUX_DETECT=0
      shift
      ;;
    --codex-args)
      if [ $# -lt 2 ]; then
        echo "Missing value for --codex-args" >&2
        usage
        exit 1
      fi
      CODEX_ARGS_RAW="$2"
      shift 2
      ;;
    --codex-arg)
      if [ $# -lt 2 ]; then
        echo "Missing value for --codex-arg" >&2
        usage
        exit 1
      fi
      CODEX_ARGS+=("$2")
      shift 2
      ;;
    --no-codex)
      RUN_CODEX=0
      shift
      ;;
    --skip-skills)
      SKIP_SKILLS=1
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [ ! -d "$TARGET_DIR" ]; then
  echo "Repo path not found: $TARGET_DIR" >&2
  exit 1
fi

if [ ! -f "$SRC_PROMPT" ]; then
  echo "Controller prompt not found: $SRC_PROMPT" >&2
  exit 1
fi

if [ "$RUN_CODEX" -eq 1 ]; then
  if ! command -v codex >/dev/null 2>&1; then
    echo "codex not found in PATH" >&2
    exit 1
  fi
fi

mkdir -p "$TARGET_DIR/.codex/prompts"
TARGET_PROMPT="$TARGET_DIR/.codex/prompts/controller.md"
MACS_PATH_FILE="$TARGET_DIR/.codex/macs-path.txt"
MACS_BRIDGE_NOTE="$TARGET_DIR/.codex/macs-tmux-bridge.txt"
TMUX_SOCKET_FILE="$TARGET_DIR/.codex/tmux-socket.txt"
TMUX_SESSION_FILE="$TARGET_DIR/.codex/tmux-session.txt"

if [ -z "$TMUX_SESSION" ] && [ -f "$TMUX_SESSION_FILE" ]; then
  TMUX_SESSION="$(cat "$TMUX_SESSION_FILE")"
fi
if [ -z "$TMUX_SOCKET_OVERRIDE" ] && [ -f "$TMUX_SOCKET_FILE" ]; then
  TMUX_SOCKET_OVERRIDE="$(cat "$TMUX_SOCKET_FILE")"
fi

if [ -f "$TARGET_PROMPT" ]; then
  if ! cmp -s "$SRC_PROMPT" "$TARGET_PROMPT"; then
    if [ "$FORCE" -eq 1 ]; then
      cp "$SRC_PROMPT" "$TARGET_PROMPT"
      echo "Updated controller prompt in $TARGET_PROMPT"
    else
      echo "Controller prompt already exists and differs: $TARGET_PROMPT" >&2
      echo "Run with --force to overwrite." >&2
    fi
  fi
else
  cp "$SRC_PROMPT" "$TARGET_PROMPT"
  echo "Installed controller prompt in $TARGET_PROMPT"
fi

# Record the MACS repo path so the controller can locate tmux_bridge tools.
echo "$ROOT_DIR" > "$MACS_PATH_FILE"
echo "Recorded MACS path in $MACS_PATH_FILE"

cat > "$MACS_BRIDGE_NOTE" <<EOF
If ./tools/tmux_bridge is missing in this repo, use:
  $ROOT_DIR/tools/tmux_bridge/<script>
Set TMUX_BRIDGE accordingly before running snapshot/send/status/set_target/notify.
EOF

detect_tmux_socket() {
  if [ -n "$TMUX_SOCKET_OVERRIDE" ]; then
    if [ -S "$TMUX_SOCKET_OVERRIDE" ] && tmux -S "$TMUX_SOCKET_OVERRIDE" list-sessions >/dev/null 2>&1; then
      export TMUX_SOCKET="$TMUX_SOCKET_OVERRIDE"
      echo "$TMUX_SOCKET_OVERRIDE" > "$TMUX_SOCKET_FILE"
      echo "Recorded tmux socket in $TMUX_SOCKET_FILE"
      return 0
    fi
    echo "Provided --tmux-socket is not accessible: $TMUX_SOCKET_OVERRIDE" >&2
  fi

  if [ -n "${TMUX_SOCKET:-}" ] && [ -S "${TMUX_SOCKET:-}" ]; then
    if tmux -S "$TMUX_SOCKET" list-sessions >/dev/null 2>&1; then
      echo "$TMUX_SOCKET" > "$TMUX_SOCKET_FILE"
      echo "Recorded tmux socket in $TMUX_SOCKET_FILE"
      return 0
    else
      echo "TMUX_SOCKET is set but not accessible: $TMUX_SOCKET" >&2
    fi
  fi
  if ! command -v tmux >/dev/null 2>&1; then
    return 1
  fi

  collect_candidates() {
    local uid
    uid="$(id -u)"
    local dirs=()
    if [ -n "${TMUX_TMPDIR:-}" ]; then
      dirs+=("$TMUX_TMPDIR")
    fi
    if [ -n "${XDG_RUNTIME_DIR:-}" ]; then
      dirs+=("$XDG_RUNTIME_DIR")
    fi
    dirs+=("/tmp" "/var/tmp" "/run/user/$uid" "/run/user")

    local cand
    local -a out=()
    if [ -n "${TMUX:-}" ]; then
      out+=("${TMUX%%,*}")
    fi
    local old_shopt
    old_shopt="$(shopt -p nullglob)"
    shopt -s nullglob
    for d in "${dirs[@]}"; do
      out+=("$d"/tmux-"$uid"/*)
      out+=("$d"/tmux-*/default)
    done
    eval "$old_shopt"
    printf "%s\n" "${out[@]}" | awk 'NF' | awk '!seen[$0]++'
  }

  find_socket_candidates() {
    local uid
    uid="$(id -u)"
    local roots=()
    if [ -n "${TMUX_TMPDIR:-}" ]; then
      roots+=("$TMUX_TMPDIR")
    fi
    if [ -n "${XDG_RUNTIME_DIR:-}" ]; then
      roots+=("$XDG_RUNTIME_DIR")
    fi
    roots+=("/tmp" "/var/tmp" "/run/user/$uid" "/run/user")
    local root
    for root in "${roots[@]}"; do
      [ -d "$root" ] || continue
      find "$root" -maxdepth 3 -type s -name 'default' -path '*tmux*' 2>/dev/null || true
    done | awk 'NF' | awk '!seen[$0]++'
  }

  try_socket() {
    local cand="$1"
    [ -S "$cand" ] || return 1
    tmux -S "$cand" list-sessions >/dev/null 2>&1 || return 1
    if [ -n "$TMUX_SESSION" ]; then
      tmux -S "$cand" has-session -t "$TMUX_SESSION" >/dev/null 2>&1 || return 1
    fi
    return 0
  }

  local cand
  local -a accessible=()
  while IFS= read -r cand; do
    if [ -z "$cand" ]; then
      continue
    fi
    if try_socket "$cand"; then
      accessible+=("$cand")
    fi
  done < <(collect_candidates)

  if [ "${#accessible[@]}" -eq 0 ]; then
    while IFS= read -r cand; do
      if [ -z "$cand" ]; then
        continue
      fi
      if try_socket "$cand"; then
        accessible+=("$cand")
      fi
    done < <(find_socket_candidates)
  fi

  if [ -n "$TMUX_SESSION" ] && [ "${#accessible[@]}" -gt 0 ]; then
    export TMUX_SOCKET="${accessible[0]}"
    echo "${accessible[0]}" > "$TMUX_SOCKET_FILE"
    echo "Recorded tmux socket in $TMUX_SOCKET_FILE"
    return 0
  fi

  if [ "${#accessible[@]}" -gt 0 ] && [ -z "$TMUX_SESSION" ]; then
    # Prefer socket that hosts session "macs" if present.
    for cand in "${accessible[@]}"; do
      if tmux -S "$cand" has-session -t macs >/dev/null 2>&1; then
        export TMUX_SOCKET="$cand"
        echo "$cand" > "$TMUX_SOCKET_FILE"
        echo "Recorded tmux socket in $TMUX_SOCKET_FILE"
        return 0
      fi
    done
    if [ "${#accessible[@]}" -eq 1 ]; then
      export TMUX_SOCKET="${accessible[0]}"
      echo "${accessible[0]}" > "$TMUX_SOCKET_FILE"
      echo "Recorded tmux socket in $TMUX_SOCKET_FILE"
      return 0
    fi
  fi

  local sock=""
  if [ -n "${TMUX:-}" ]; then
    sock="$(tmux display-message -p '#{socket_path}' 2>/dev/null || true)"
    if [ -n "$sock" ] && tmux -S "$sock" list-sessions >/dev/null 2>&1; then
      export TMUX_SOCKET="$sock"
      echo "$sock" > "$TMUX_SOCKET_FILE"
      echo "Recorded tmux socket in $TMUX_SOCKET_FILE"
      return 0
    fi
    sock=""
  fi
  if [ -z "$sock" ]; then
    sock="$(tmux display-message -p '#{socket_path}' 2>/dev/null || true)"
    if [ -n "$sock" ] && tmux -S "$sock" list-sessions >/dev/null 2>&1; then
      export TMUX_SOCKET="$sock"
      echo "$sock" > "$TMUX_SOCKET_FILE"
      echo "Recorded tmux socket in $TMUX_SOCKET_FILE"
      return 0
    fi
    sock=""
  fi
  if [ -z "$sock" ]; then
    local cand
    local found_sock=""
    local found_count=0
    local macs_sock=""
    for cand in /tmp/tmux-$(id -u)/*; do
      [ -S "$cand" ] || continue
      if tmux -S "$cand" list-sessions >/dev/null 2>&1; then
        found_sock="$cand"
        found_count=$((found_count + 1))
        if tmux -S "$cand" has-session -t macs >/dev/null 2>&1; then
          macs_sock="$cand"
        fi
      fi
    done
    if [ -n "$macs_sock" ]; then
      sock="$macs_sock"
    elif [ "$found_count" -eq 1 ]; then
      sock="$found_sock"
    fi
  fi
  if [ -n "$sock" ] && [ -S "$sock" ]; then
    export TMUX_SOCKET="$sock"
    echo "$sock" > "$TMUX_SOCKET_FILE"
    echo "Recorded tmux socket in $TMUX_SOCKET_FILE"
    return 0
  fi
  return 1
}

if [ "$TMUX_DETECT" -eq 1 ]; then
  if ! detect_tmux_socket; then
    echo "Error: Could not auto-detect an accessible tmux socket." >&2
    echo "Re-run with one of:" >&2
    echo "  $0 --tmux-session <session>  (e.g. --tmux-session macs)" >&2
    echo "  $0 --tmux-socket /tmp/tmux-<uid>/default" >&2
    echo "If tmux was started by another user or in a different namespace, run this script inside that tmux session." >&2
    echo "To bypass detection (not recommended): --no-tmux-detect" >&2
    exit 2
  fi
fi

if [ -z "$TMUX_SESSION" ] && [ -n "${TMUX_SOCKET:-}" ] && [ -S "${TMUX_SOCKET:-}" ]; then
  session_list="$(tmux -S "$TMUX_SOCKET" list-sessions -F '#S' 2>/dev/null || true)"
  session_count="$(printf "%s\n" "$session_list" | sed '/^$/d' | wc -l | tr -d ' ')"
  if [ "$session_count" -eq 1 ]; then
    TMUX_SESSION="$(printf "%s\n" "$session_list" | head -n1)"
  fi
fi

if [ -n "$TMUX_SESSION" ]; then
  echo "$TMUX_SESSION" > "$TMUX_SESSION_FILE"
  echo "Recorded tmux session in $TMUX_SESSION_FILE"
fi

if [ "$SKIP_SKILLS" -eq 0 ] && [ -d "$SRC_SKILLS_DIR" ]; then
  TARGET_SKILLS_DIR="$TARGET_DIR/.codex/skills"
  mkdir -p "$TARGET_SKILLS_DIR"
  for src in "$SRC_SKILLS_DIR"/*; do
    [ -d "$src" ] || continue
    name="$(basename "$src")"
    case "$name" in
      .* ) continue ;;
    esac
    dest="$TARGET_SKILLS_DIR/$name"
    if [ -d "$dest" ]; then
      if [ "$FORCE" -eq 1 ]; then
        rm -rf "$dest"
        cp -R "$src" "$dest"
        echo "Updated skill: $name"
      fi
    else
      cp -R "$src" "$dest"
      echo "Installed skill: $name"
    fi
  done
elif [ "$SKIP_SKILLS" -eq 0 ]; then
  echo "Skills directory not found: $SRC_SKILLS_DIR" >&2
fi

cd "$TARGET_DIR"
if [ "$RUN_CODEX" -eq 1 ]; then
  if [ "${#CODEX_ARGS[@]}" -eq 0 ] && [ -n "$CODEX_ARGS_RAW" ]; then
    read -r -a CODEX_ARGS <<< "$CODEX_ARGS_RAW"
  fi
  exec codex "${CODEX_ARGS[@]}" "/prompts:controller"
fi
echo "Controller setup complete. Skipping codex launch (--no-codex)."
