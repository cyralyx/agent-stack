#!/usr/bin/env bash
# =============================================================================
#  package.sh — build the AgentStack installer package (zip + tar.gz).
#
#  Produces, in dist/:
#    agentstack-<version>.zip         Windows-friendly (git-bash, msys)
#    agentstack-<version>.tar.gz      POSIX-friendly
#    agentstack-latest.zip            convenience alias
#
#  The package contains the full repo minus git history, .git, dist/, secrets,
#  and runtime DBs. It is the "installer package": a user downloads one file,
#  extracts it, runs ./install.sh [--token ...], done.
#
#  Usage:  ./scripts/package.sh [version]
#  Version defaults to the latest git tag, or "0.1.0" if none.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# version resolution
VERSION="${1:-}"
if [ -z "$VERSION" ]; then
  VERSION="$(git describe --tags --abbrev=0 2>/dev/null || echo '0.1.0')"
fi
VERSION="${VERSION#v}"
OUT_DIR="$ROOT/dist"
STAGING="$OUT_DIR/agentstack-$VERSION"

echo "==> Packaging AgentStack $VERSION"

# --- collect files (exclude git, dist, secrets, runtime) ---------------------
INCLUDES=(README.md CHANGELOG.md VISION.md LICENSE bin bridges config council
          docs flows hooks install.sh setup.sh skills terminal .gitignore)
EXCLUDES=(--exclude='.git' --exclude='dist' --exclude='*.db'
          --exclude='.env' --exclude='*.env' --exclude='__pycache__'
          --exclude='*.pyc' --exclude='*.log' --exclude='*.pid')

echo "==> Staging: $STAGING"
rm -rf "$STAGING" "$OUT_DIR"
mkdir -p "$STAGING"

for item in "${INCLUDES[@]}"; do
  [ -e "$item" ] || continue
  cp -r "$item" "$STAGING/" 2>/dev/null || true
done

# strip any stray junk from staging
for bad in dist .git "*.db" ".env" "*.pyc" "__pycache__"; do
  find "$STAGING" -name "$bad" -prune -exec rm -rf {} + 2>/dev/null || true
done

# write a VERSION file the installer can read
echo "$VERSION" > "$STAGING/VERSION"

mkdir -p "$OUT_DIR"

# --- archive ---------------------------------------------------------------
echo "==> Building archives"
(
  cd "$OUT_DIR"
  tar --exclude='.git' -czf "agentstack-$VERSION.tar.gz" "agentstack-$VERSION"
  # zip: use powershell if available, else python zipfile
  if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -Command \
      "Compress-Archive -Path 'agentstack-$VERSION/*' -DestinationPath 'agentstack-$VERSION.zip' -Force" >/dev/null
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c "import shutil,sys; shutil.make_archive('agentstack-$VERSION','zip','agentstack-$VERSION')"
  elif command -v zip >/dev/null 2>&1; then
    zip -qr "agentstack-$VERSION.zip" "agentstack-$VERSION"
  else
    echo "!! no zip tool — only tar.gz built" >&2
  fi
)

# convenience alias
cp "$OUT_DIR/agentstack-$VERSION.zip" "$OUT_DIR/agentstack-latest.zip" 2>/dev/null || true

echo
echo "==> Package complete:"
ls -lh "$OUT_DIR"/*.zip "$OUT_DIR"/*.tar.gz 2>/dev/null
echo
echo "==> SHA256 checksums:"
( cd "$OUT_DIR" && sha256sum *.zip *.tar.gz 2>/dev/null || shasum -a 256 *.zip *.tar.gz 2>/dev/null || true ) | tee "$OUT_DIR/checksums.sha256"
echo
echo "Usage: extract + run ./install.sh [--token sk-or-...]"
