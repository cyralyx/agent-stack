# Security

## Rules that govern this repo and the stack

1. **No secrets in this repo, ever.** Tokens, API keys, passwords, private
   keys stay in each agent's own env file / secret store. This repo ships only
   the *names* of the env vars you need to fill in (see
   `config/hermes.env.example`).
2. **No secrets in the Obsidian vault.** The vault's `AGENTS.md` contract
   forbids storing tokens/keys in notes. Reference env/secret-store instead.
3. **Vault MCP is read+write but never delete** (the running OpenClaw
   `obsidian-brain` MCP is configured with no delete capability).
4. **Never `sudo pip`.** Install Python packages into a venv/user context.
5. **Never `chmod 777`.** The scripts use safe `chmod +x` only.
6. **Verify openings:** if a bridge/hook proposes sending data over the
   network to an unexpected place, stop and check before it runs.

## What an agent (Hermes or OpenClaw) is allowed to do

- Read/write the shared Obsidian vault (brain).
- Run terminal commands the operator approves.
- Delegate tasks through the bridges.
- Do **not** exfiltrate vault contents or broadcast secrets anywhere.

## Handling leaked secrets

If you ever paste a token into chat or a note by accident, rotate it and
remove it from history/notes. The vault has no delete from the MCP side, so
manual cleanup + rotation is the fix.

## Threat model / good practice (from the OpenClaw research)

- OpenClaw has demonstrated skill-based prompt-injection attack surface —
  treat downloaded skills as untrusted until vetted.
- Pairing approval + sandboxing are mitigations; keep them enabled.
- Review what both agents write to the shared brain; the `openclaw-wife-reviewer`
  hook is one self-check.
