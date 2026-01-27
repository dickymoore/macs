#!/usr/bin/env bash
set -euo pipefail

# Non-blocking notification to alert the human.
# Plays a sound on Windows (PowerShell) or terminal bell elsewhere.

if command -v powershell.exe >/dev/null 2>&1; then
  # Windows: play a short melody
  powershell.exe -c "Start-Job -ScriptBlock { \$seq=@(@(659,90),@(784,70),@(880,90),@(988,80),@(784,60),@(740,70),@(659,90),@(587,70),@(659,60),@(784,90),@(880,70),@(988,80),@(1175,120),@(988,60),@(880,80),@(880,50),@(988,50),@(1175,60),@(988,50),@(880,50),@(740,50),@(659,60),@(740,50),@(880,50)); foreach(\$n in \$seq){[console]::beep(\$n[0],\$n[1])} } | Out-Null" >/dev/null 2>&1 && exit 0
  # Fallback: single beep
  powershell.exe -c "Start-Job -ScriptBlock { [console]::beep(880,120) } | Out-Null" >/dev/null 2>&1 && exit 0
  # Fallback: Windows sound file
  powershell.exe -c "Start-Job -ScriptBlock { (New-Object Media.SoundPlayer 'C:\\Windows\\Media\\Windows Notify.wav').PlaySync() } | Out-Null" >/dev/null 2>&1 && exit 0
fi

# Unix/Mac: terminal bell
printf '\a' >/dev/null 2>&1 || true
