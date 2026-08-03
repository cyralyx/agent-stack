#!/usr/bin/env bash
# =============================================================================
#  setup.sh — provision the full agent stack on a (fresh) machine.
#
#  Installs / verifies:
#    1. Hermes   (the brain)  — pip / curl installer, Telegram gateway
#    2. OpenClaw (the hands)  — npm global install
#    3. Obsidian vault        — detect shared brain, or init one
#    4. Bridges + `stack` CLI — link into PATH
#
#  Safe: idempotent, never chmod 777, never sudo pip, no secrets committed.
#  Run:  ./setup.sh            (all steps)
#        ./setup.sh --only hermes|openclaw|vault (a single step)
# =============================================================================
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_LINK_DIR="${BIN_LINK_DIR:-$HOME/bin}"
VAULT="${STACK_VAULT:-$HOME/Documents/Obsidian Vault}"
HERMES_HOME="${HERMES_HOME:-$HOME/AppData/Local/hermes}"

YELLOW=$'\e[33m'; GREEN=$'\e[32m'; CYAN=$'\e[36m'; RESET=$'\e[0m'
info(){ echo "${CYAN}==>${RESET} $*"; }
ok(){   echo "  ${GREEN}✓${RESET} $*"; }
warn(){ echo "  ${YELLOW}!${RESET} $*"; }

ONLY="${2:-all}"

# ---------------------------------------------------------------------------
install_hermes() {
  info "Hermes (the brain)"
  if command -v hermes >/dev/null 2>&1 \
     || [ -x "$HERMES_HOME/hermes-agent/venv/Scripts/hermes.exe" ] \
     || [ -x "$HERMES_HOME/venv/Scripts/hermes.exe" ]; then
    ok "Hermes already installed"
  else
    warn "Hermes not found. Install with one of:"
    printf '    %s\n' "curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash"
    printf '    %s\n' "pip install hermes-agent"
    warn "then re-run ./setup.sh"
  fi
}

install_openclaw() {
  info "OpenClaw (the hands)"
  local found=""
  for c in "$APPDATA/npm/node_modules/openclaw/openclaw.mjs" \
           "$HOME/AppData/Roaming/npm/node_modules/openclaw/openclaw.mjs"; do
    [ -f "$c" ] && found="$c"
  done
  if [ -n "$found" ]; then
    ok "OpenClaw already installed ($found)"
  else
    warn "OpenClaw not found. Install with:"
    printf '    %s\n' "npm i -g openclaw    # requires Node >=22.22.3"
    warn "then re-run ./setup.sh"
  fi
}

install_vault() {
  info "Obsidian vault (shared brain)"
  if [ -d "$VAULT" ]; then
    ok "Vault detected at $VAULT"
    [ -f "$VAULT/AGENTS.md" ] && ok "AGENTS.md contract present" \
                             || warn "No AGENTS.md in vault (optional but recommended)"
  else
    warn "No vault at $VAULT. Create one in Obsidian, or run:"
    printf '    %s\n' "mkdir -p '$VAULT' && touch '$VAULT/AGENTS.md'"
    warn "then re-run ./setup.sh"
  fi
}

link_bridges() {
  info "Linking bridges + stack CLI into PATH ($BIN_LINK_DIR)"
  mkdir -p "$BIN_LINK_DIR"
  local linked=0
  for src in "$STACK_ROOT/bin/stack" \
             "$STACK_ROOT/bridges/hermes-to-openclaw" \
             "$STACK_ROOT/bridges/hermes-worker" \
             "$STACK_ROOT/bridges/vault-note"; do
    [ -f "$src" ] || continue
    chmod +x "$src"
    local name; name="$(basename "$src")"
    local dst="$BIN_LINK_DIR/$name"
    if [ -e "$dst" ] && [ "$(readlink -f "$dst" 2>/dev/null)" = "$(readlink -f "$src")" ]; then
      ok "already linked: $name"
    else
      ln -sf "$src" "$dst"
      ok "linked: $name -> $dst"
      linked=$((linked+1))
    fi
  done
}

setup_telegram() {
  info "Telegram gateway (on Hermes)"
  if [ -x "$HERMES_HOME/hermes-agent/venv/Scripts/hermes.exe" ] ||
     command -v hermes >/dev/null 2>&1; then
    warn "Run 'hermes gateway setup' to connect your Telegram bot, then:"
    printf '    %s\n' "hermes gateway start"
  else
    warn "Hermes not installed yet — Telegram setup after Hermes install."
  fi
}

install_skills() {
  info "Installing AgentStack skills into Hermes"
  local skills_root="$STACK_ROOT/skills"
  local dst="$HERMES_HOME/skills"
  mkdir -p "$dst"
  local n=0
  for sk in "$skills_root"/learning/* "$skills_root"/terminal/*; do
    [ -d "$sk" ] || continue
    local name; name="$(basename "$sk")"
    local target="$dst/$name"
    if [ -e "$target" ]; then
      ok "skill present: $name"
    else
      ln -sf "$sk" "$target" 2>/dev/null || cp -r "$sk" "$target"
      ok "skill installed: $name"
      n=$((n+1))
    fi
  done
  echo "  (linked $n new skills)"
}

# ---------------------------------------------------------------------------
case "$ONLY" in
  all)           install_hermes; install_openclaw; install_vault; link_bridges; setup_telegram; install_skills ;;
  hermes)        install_hermes ;;
  openclaw)      install_openclaw ;;
  vault)         install_vault ;;
  bridges)       link_bridges ;;
  telegram)      setup_telegram ;;
  skills)        install_skills ;;
  *) echo "Unknown: $ONLY"; exit 2 ;;
esac

echo
info "Done. Run:  stack status"
