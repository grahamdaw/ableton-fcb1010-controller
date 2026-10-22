#!/usr/bin/env bash
# Follow Live's Log.txt, showing only this script's lines.
set -euo pipefail
LOG=$(ls -t "$HOME"/Library/Preferences/Ableton/Live\ */Log.txt 2>/dev/null | head -1)
[ -n "$LOG" ] || { echo "Live's Log.txt not found" >&2; exit 1; }
echo "Following $LOG" >&2
tail -n 0 -F "$LOG" | grep --line-buffered "FCB1010:"
