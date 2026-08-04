#!/usr/bin/env bash
# =============================================================================
#  package-app.sh — build the AgentStack desktop app (Win x64) and bundle the
#  backend (lib/, council/, modules/, bin/, bridges/, skills/, config/) into
#  the packaged resources so the app is fully functional.
#
#  Produces:  app/release/AgentStack-win32-x64/
#  Then run:  install-app.sh   (or copy that folder to %LOCALAPPDATA%/Programs)
# =============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/app"
cd "$APP"

echo "==> Packing AgentStack app (electron-packager)"
npx electron-packager . AgentStack --platform=win32 --arch=x64 \
  --out="$APP/release" --overwrite --icon=logo.ico --app-version=0.2.0 \
  --ignore="^/(?!main\.js|preload\.js|index\.html|styles\.css|renderer\.js|logo\.(png|ico)$|package\.json)"

PKG="$APP/release/AgentStack-win32-x64/resources/app"
echo "==> Bundling backend into $PKG"
for d in lib council modules bin bridges skills config; do
  if [ -d "$ROOT/$d" ]; then cp -r "$ROOT/$d" "$PKG/"; echo "  bundled $d"; fi
done

echo
echo "==> Done. App at: $APP/release/AgentStack-win32-x64/AgentStack.exe"
echo "   To install:  bash scripts/install-app.sh"
