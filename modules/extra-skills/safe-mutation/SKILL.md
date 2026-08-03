# Safe System Mutation

Procedural skill for making verified system changes.

## Triggers
- "Modify this file"
- "Update configuration"

## Steps
1. Capture before state (hash/timestamp)
2. Verify write-safe path
3. Make atomic change
4. Verify after state
5. Only claim MODIFIED/FIXED/CREATED with before/after evidence
