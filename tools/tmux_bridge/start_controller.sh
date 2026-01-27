#!/usr/bin/env bash
# MACS - Start the controller terminal
set -euo pipefail

SESSION="${1:-macs}"
WINDOW="controller"

# Create session if it doesn't exist
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux new-session -d -s "$SESSION" -n "$WINDOW"
else
  tmux new-window -t "$SESSION" -n "$WINDOW" 2>/dev/null || true
fi

# Set window/pane title
tmux select-window -t "$SESSION:$WINDOW"
tmux send-keys -t "$SESSION:$WINDOW" "printf '\\033]2;controller\\033\\\\'" Enter

echo "Controller window ready in session: $SESSION"
echo "To attach: tmux attach -t $SESSION"
echo "To start codex: codex"
echo "To load controller prompt: /prompts:controller"
