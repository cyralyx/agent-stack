#!/usr/bin/env bash
# =============================================================================
#  install-app.sh — install the packaged AgentStack desktop app per-user
#  (no admin). Copies app/release/AgentStack-win32-x64/* to
#  %LOCALAPPDATA%/Programs/AgentStack and (re)creates the desktop shortcut
#  with the AgentStack logo.
# =============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/app/release/AgentStack-win32-x64"

if [ ! -d "$SRC" ] || [ ! -f "$SRC/AgentStack.exe" ]; then
  echo "!! Package not found at $SRC — run scripts/package-app.sh first" >&2
  exit 1
fi

DEST="${LOCALAPPDATA:-$HOME/AppData/Local}/Programs/AgentStack"
echo "==> Installing to $DEST"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -r "$SRC/." "$DEST/"
cp "$ROOT/app/logo.ico" "$DEST/logo.ico" 2>/dev/null || true

echo "==> Creating desktop shortcut"
VBS="$(cygpath -w "$ROOT/app/create_shortcut.vbs")"
if command -v cscript >/dev/null 2>&1; then
  cscript //nologo "$VBS" || true
fi

echo
echo "==> Installed. Launch:"
echo "    \"$DEST/AgentStack.exe\""
