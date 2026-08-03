# Setup Guide — bring up the whole stack on a fresh machine

This replicates the current machine: **Hermes (brain) + OpenClaw (hands) +
Obsidian (shared brain)**, all reachable from the terminal and from Telegram.

---

## 0. Prerequisites

| Tool | Why | Version |
|------|-----|---------|
| Node.js | OpenClaw runtime | **>=22.22.3** (Node 26 recommended) |
| Python 3.10+ | Hermes runtime | any recent |
| Git | versioning the repo | any |
| Obsidian | the shared brain vault | any (not strictly required) |

Check:
```bash
node -v    # >= v22.22.3
python --version
git --version
```

---

## 1. Install Hermes (the brain)

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
# or
pip install hermes-agent
```

Verify: `hermes --version`
Then pick a provider/model (uses OpenRouter by default):
```bash
hermes setup
hermes model
```

---

## 2. Install OpenClaw (the hands)

```bash
npm i -g openclaw
```

Verify the package entry exists:
```bash
ls "$APPDATA/npm/node_modules/openclaw/openclaw.mjs"
# or
ls "$HOME/AppData/Roaming/npm/node_modules/openclaw/openclaw.mjs"
```
(If the `.cmd` shim misbehaves on Windows, the bridge scripts call node+the
`.mjs` entry directly, which sidesteps the broken shim.)

---

## 3. Prepare the Obsidian vault (shared brain)

Use your existing vault (default path `C:\Users\willi\Documents\Obsidian Vault`).
It should contain an `AGENTS.md` contract that all agents agree to, plus an
`Agent Hub/` for coordination. The hooks/bridges reference this path.

Override with the `STACK_VAULT` env var if your vault lives elsewhere.

---

## 4. Provision the stack

From this repo:
```bash
./setup.sh                 # all steps (idempotent)
./setup.sh --only hermes   # just one step
```

This:
- confirms/detects all three agents,
- links the `stack` CLI and the bridges into `~/bin`,
- reminds you how to wire Telegram.

---

## 5. Wire Telegram

With Hermes installed, connect your bot (the bot token lives in
`$HERMES_HOME/.env` as `TELEGRAM_BOT_TOKEN` — never commit it):

```bash
hermes gateway setup       # pick Telegram, paste your token
hermes gateway start       # start the gateway
stack telegram status      # verify
```

Now message **@<your-bot>** on Telegram → it reaches Hermes (the brain).
Ask Hermes to delegate to OpenClaw and it hands the task over via the bridge.

---

## 6. Meet the `stack` CLI

```bash
stack status                 # health of everything
stack hermes "summarise my vault notes"
stack openclaw "list the files in ~/projects"
stack note "remember: we shipped v2 on Aug 3"
stack telegram status
```

See [CLI.md](CLI.md) for the full reference.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `stack` says Hermes not found | Install Hermes; or set `HERMES_BIN` |
| OpenClaw `.cmd` shim corrupts prompts | Bridges use node + `.mjs` directly (already done) |
| Gateway not running | `stack telegram on` or `hermes gateway start` |
| Vault path wrong | `export STACK_VAULT=...` and re-run |
| Node too old for OpenClaw | Upgrade to Node >=22.22.3 (26 recommended) |
