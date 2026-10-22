#!/usr/bin/env bash
# Install or update the FCB1010 Remote Script for Ableton Live.
#
#   curl -fsSL https://raw.githubusercontent.com/grahamdaw/ableton-fcb1010-controller/main/install.sh | bash
#
# Clones the repo (or pulls if already cloned) and links its FCB1010 folder
# into Live's User Library Remote Scripts. Running it again updates in place.
# With FCB1010_DEV=1, run from a checkout, it links that checkout instead
# and leaves git alone (the dev loop: edit, re-select the control surface).
set -euo pipefail

REPO_URL="${FCB1010_REPO_URL:-https://github.com/grahamdaw/ableton-fcb1010-controller.git}"
CLONE_DIR="${FCB1010_CLONE_DIR:-$HOME/.local/share/ableton-fcb1010-controller}"
REMOTE_SCRIPTS="${FCB1010_REMOTE_SCRIPTS:-$HOME/Music/Ableton/User Library/Remote Scripts}"
LINK="$REMOTE_SCRIPTS/FCB1010"

command -v git >/dev/null || { echo "git is required" >&2; exit 1; }

if [ -n "${FCB1010_DEV:-}" ]; then
  CLONE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  echo "Dev mode: linking $CLONE_DIR"
elif [ -d "$CLONE_DIR/.git" ]; then
  echo "Updating $CLONE_DIR"
  git -C "$CLONE_DIR" pull --ff-only
else
  echo "Cloning into $CLONE_DIR"
  mkdir -p "$(dirname "$CLONE_DIR")"
  git clone "$REPO_URL" "$CLONE_DIR"
fi

SCRIPT_DIR="$CLONE_DIR/FCB1010"
if [ ! -f "$SCRIPT_DIR/config.toml" ]; then
  cp "$SCRIPT_DIR/config.example.toml" "$SCRIPT_DIR/config.toml"
  echo "Created $SCRIPT_DIR/config.toml from the example"
fi

mkdir -p "$REMOTE_SCRIPTS"
if [ -L "$LINK" ]; then
  ln -sfn "$SCRIPT_DIR" "$LINK"
elif [ -e "$LINK" ]; then
  echo "$LINK exists and is not a symlink; move it away and re-run" >&2
  exit 1
else
  ln -s "$SCRIPT_DIR" "$LINK"
fi
echo "Linked $LINK -> $SCRIPT_DIR"

cat <<MSG

Done. Next:
  1. Restart Live (only needed the first time).
  2. Preferences -> Link, Tempo & MIDI: Control Surface = FCB1010,
     Input = your USB-MIDI interface, Output = None.
  3. Turn the Track and Remote switches for that input port off.
MSG
