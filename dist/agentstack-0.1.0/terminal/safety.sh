#!/usr/bin/env bash
# Command-safety linter — warn before dangerous commands.
# Usage: safety "rm -rf ~/x"   → prints warning + requires confirmation
#        safety --check "cmd"  → exit 1 if dangerous
set -euo pipefail

DANGEROUS_PATTERNS=(
  'rm -rf /'            # root wipe
  'rm -rf \$HOME'       # home wipe
  'chmod 777'          # world-writable
  'sudo pip'           # pip as root (user rule)
  '> /dev/sda'         # raw disk write
  'mkfs\.'             # filesystem format
  ':(){'               # fork bomb
)

warn() {
  echo "⚠  DANGEROUS COMMAND DETECTED:" >&2
  echo "   $1" >&2
  echo "   Are you sure? (y/N)" >&2
  read -r ans
  [[ "$ans" =~ ^[yY]$ ]] || { echo "aborted."; exit 1; }
}

check() {
  local cmd="$1"
  for pat in "${DANGEROUS_PATTERNS[@]}"; do
    if echo "$cmd" | grep -qE "$pat"; then
      warn "$cmd"
      return 1
    fi
  done
  return 0
}

if [ "${1:-}" = "--check" ]; then
  check "${2:?usage: safety --check \"command\"}"
  echo "safe."
else
  check "${1:?usage: safety \"command\" | safety --check \"command\"}"
fi
