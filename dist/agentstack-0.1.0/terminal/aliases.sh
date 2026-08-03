#!/usr/bin/env bash
# AgentStack aliases + macros. Source from ~/.bashrc (git-bash) or ~/.zshrc.
#   source /c/Users/willi/Documents/ai\ agents/agent-stack/terminal/aliases.sh
STACK_ROOT="${STACK_ROOT:-/c/Users/willi/Documents/ai agents/agent-stack}"
export STACK_ROOT

# --- speed aliases (2-char) -------------------------------------------------
alias rg='rg'                    # rg already fast
alias fd='fd'                    # fd already fast
alias g='git'
alias gs='git status --short'
alias gl='git log --oneline -10 | cat'
alias gc='git commit -m'
alias gp='git push'
alias la='ls -la'

# --- stack shortcuts ---------------------------------------------------------
alias s='bash "$STACK_ROOT/bin/stack"'
alias sst='bash "$STACK_ROOT/bin/stack" status'
alias sdoc='bash "$STACK_ROOT/bin/stack" doctor'
alias sto='bash "$STACK_ROOT/bin/stack" todo list'
alias scost='bash "$STACK_ROOT/bin/stack" cost'
alias scouncil='bash "$STACK_ROOT/bin/stack" council'

# --- macros (multi-step in one shot) ----------------------------------------
mkskill() {
  # make a new skill skeleton: mkskill my-skill "description"
  local name="$1" desc="$2"
  [ -n "$name" ] || { echo "usage: mkskill <name> \"<description>\""; return 1; }
  local dir="$HOME/AppData/Local/hermes/skills/$name"
  mkdir -p "$dir"
  cat > "$dir/SKILL.md" <<EOF
---
name: $name
description: "${desc:-TODO}"
---
# $name
EOF
  echo "created $dir/SKILL.md"
}

quicknote() {
  # quick note to vault: quicknote "text"
  bash "$STACK_ROOT/bin/stack" note "$*"
}

pushit() {
  # commit + push current repo with a message
  git add -A && git commit -m "$1" && git push
}

skillsearch() {
  hermes skills search "$*" 2>&1 | head -25
}

echo "AgentStack aliases loaded (s, sst, sdoc, sto, scost, scouncil, mkskill, quicknote, pushit)"
