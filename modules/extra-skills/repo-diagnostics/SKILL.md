# Repository Diagnostics

Procedural skill for diagnosing git repository state.

## Triggers
- "Why is this repo broken?"
- "Check repo health"

## Steps
1. Run `doctor_repo` to check origin, branch, status
2. If detached HEAD: suggest `git checkout`
3. If dirty worktree: check with `git status`
4. If remote missing: check `git remote -v`
5. Verify with ToolForge
