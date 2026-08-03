#!/usr/bin/env bash
# =============================================================================
#  bootstrap.sh — one-line AgentStack installer for end users.
#
#  Usage (no clone needed):
#    bash <(curl -fsSL https://raw.githubusercontent.com/cyralyx/agent-stack/master/scripts/bootstrap.sh) --token sk-or-...
#
#  What it does:
#    1. Downloads the latest release package (zip or tar.gz)
#    2. Extracts to ~/.agentstack
#    3. Runs ./install.sh --token <your key>   (or interactive)
#
#  Safe: downloads only from the repo's own GitHub release; no curl|bash of
#  third-party scripts; checks nothing scary; keeps everything in ~/.agentstack.
# =============================================================================
set -euo pipefail

REPO="cyralyx/agent-stack"
BRANCH="master"
VERSION="${AGENTSTACK_VERSION:-latest}"
INSTALL_DIR="${AGENTSTACK_DIR:-$HOME/.agentstack}"

# --- parse args --------------------------------------------------------------
TOKEN=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --token) TOKEN="${2:-}"; shift 2 ;;
    --dir)   INSTALL_DIR="$2"; shift 2 ;;
    --version) VERSION="$2"; shift 2 ;;
    *) shift ;;
  esac
done

echo "==> AgentStack bootstrap"
echo "    repo:      $REPO"
echo "    version:   $VERSION"
echo "    install to: $INSTALL_DIR"

# --- pick archive ------------------------------------------------------------
OS="$(uname -s 2>/dev/null || echo Windows)"
EXT="zip"
case "$OS" in
  Linux|Darwin) EXT="tar.gz" ;;
esac

if [ "$VERSION" = "latest" ]; then
  URL="https://github.com/$REPO/releases/latest/download/agentstack-latest.$EXT"
else
  V="${VERSION#v}"
  URL="https://github.com/$REPO/releases/download/v$V/agentstack-$V.$EXT"
fi
echo "==> Downloading $URL"

mkdir -p "$INSTALL_DIR"
TMP="$(mktemp -d 2>/dev/null || echo "$INSTALL_DIR/tmp")"
mkdir -p "$TMP"
cd "$TMP"

if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$URL" -o "package.$EXT"
elif command -v wget >/dev/null 2>&1; then
  wget -q "$URL" -O "package.$EXT"
else
  echo "!! Need curl or wget" >&2; exit 1
fi

echo "==> Extracting"
case "$EXT" in
  zip)
    if command -v unzip >/dev/null 2>&1; then
      unzip -q -o "package.$EXT" -d "$INSTALL_DIR"
    else
      python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "package.$EXT" "$INSTALL_DIR"
    fi ;;
  tar.gz)
    tar -xzf "package.$EXT" -C "$INSTALL_DIR" ;;
esac

# find the extracted dir (agentstack-<ver>/)
PKG_DIR="$(find "$INSTALL_DIR" -maxdepth 1 -type d -name 'agentstack-*' | head -1)"
if [ -z "$PKG_DIR" ]; then
  echo "!! Could not locate extracted package" >&2; exit 1
fi

rm -rf "$TMP"

echo "==> Running installer"
if [ -n "$TOKEN" ]; then
  cd "$PKG_DIR" && bash install.sh --token "$TOKEN"
else
  cd "$PKG_DIR" && bash install.sh
fi

echo
echo "==> Done. The stack is at: $PKG_DIR"
echo "    Add to PATH:  echo 'export PATH=\"$PKG_DIR/bin:\$PATH\"' >> ~/.bashrc"
echo "    Then:         stack status"
