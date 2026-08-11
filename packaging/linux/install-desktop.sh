#!/bin/sh
# Optional: register a per-user desktop entry pointing at this directory.
# Nothing is installed system wide and no root access is needed - the app keeps
# running from wherever you extracted it. Re-run this if you move the folder.
set -e

APP_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

# Snap confined terminals (the VS Code snap, for one) export an XDG_DATA_HOME
# pointing inside their own sandbox, e.g. ~/snap/code/254/.local/share. The
# desktop shell never scans those, so the entry would install but never appear.
# Fall back to the real per-user location.
case "$DATA_HOME" in
    "$HOME"/snap/*) DATA_HOME="$HOME/.local/share" ;;
esac
if [ -n "${SNAP:-}" ]; then
    DATA_HOME="$HOME/.local/share"
fi

DEST="$DATA_HOME/applications"
ENTRY="$DEST/joystick-diagrams.desktop"

mkdir -p "$DEST"
sed "s|@APP_DIR@|$APP_DIR|g" "$APP_DIR/joystick-diagrams.desktop.in" > "$ENTRY"
chmod 644 "$ENTRY"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DEST" >/dev/null 2>&1 || true
fi

echo "Installed $ENTRY"
