#!/usr/bin/env bash
# flow: health check + report to vault
set -euo pipefail
echo "→ 1/2 running system health"
stack health 2>&1 | head -15
echo "→ 2/2 appending health snapshot to vault"
STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STACK_VAULT="${STACK_VAULT:-/c/Users/willi/Documents/Obsidian Vault}"
mkdir -p "$STACK_VAULT/Agent Hub/Health"
printf '\n## Health %s\n' "$(date '+%Y-%m-%d %H:%M')" >> "$STACK_VAULT/Agent Hub/Health/Health Log.md"
echo "flow complete — health logged"
