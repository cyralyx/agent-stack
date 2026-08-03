#!/usr/bin/env bash
# flow: research → learn → note
# Usage: stack flow research "topic"
set -euo pipefail
topic="${1:?usage: stack flow research \"topic\"}"
echo "→ 1/3 researching: $topic"
echo "→ 2/3 logging learning (task-learning)"
echo "→ 3/3 saving note to vault"
# placeholder — real flow calls bridges:
#   stack openclaw "research $topic"
#   stack note "learning: $topic — <what worked>"
echo "flow complete (research pipeline stubbed; wire bridges to activate)"
