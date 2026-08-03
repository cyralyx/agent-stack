# MCP Diagnostics

Procedural skill for diagnosing MCP session issues.

## Triggers
- "MCP not connecting"
- "Tools not found"

## Steps
1. Check process state (health())
2. Check initialize response
3. Check tools/list response
4. Check stderr buffer
5. Distinguish: process vs protocol vs tool availability
