# AgentStack Credential Guide

How AgentStack stores, adds, checks, and removes credentials — and why the
old ways were wrong. Implementation: `lib/secrets.js`; CLI: `bin/agentstack.js`
(`provider`, `secrets` commands).

## 1. Where secrets live

AgentStack keeps secrets in its **own** state directory
(`lib/paths.js` `agentStackHome()` — `AGENTSTACK_HOME` env var, default
`%LOCALAPPDATA%\Cyralyx\AgentStack` on Windows, `~/Library/Application
Support/AgentStack` on macOS, `$XDG_CONFIG_HOME/agentstack` on Linux):

| File | Contents | Protection |
|------|----------|------------|
| `secrets.enc` | Encrypted map of service name → secret | **AES-256-GCM** (`aes-256-gcm` cipher, random 12-byte IV, GCM auth tag); JSON `{iv, tag, cipher}`; written mode 0600 |
| `.machine-key` | 32 random bytes (base64) — the encryption key | Written mode 0600 on first use; **machine-local** — never committed, never synced |
| `config/providers.json` | Provider config | **Refs only** — `secret_ref: "keychain://agentstack/<name>"`, `base_url`, `enabled`; never the raw secret |

### How the encrypted store works

`lib/secrets.js` `encryptedStore()`:

1. Ensures `AGENTSTACK_HOME` exists; reads or creates `.machine-key`
   (`crypto.randomBytes(32)`, base64).
2. `read()`: JSON-parses `secrets.enc`, decrypts with `aes-256-gcm` using the
   key + stored IV, verifies the auth tag, returns the plaintext map.
3. `write()`: encrypts the whole map with a fresh random IV and stores
   `{iv, tag, cipher}` base64.

On platforms where a system credential store is detectable the code prefers
keytar (`systemStoreAvailable()`), but **the shipped, headless-safe path is the
encrypted file** — `cmdkey`/`security` CLIs are interactive on Windows, so the
encrypted fallback is used to stay non-interactive. **Treat the encrypted file
as the default backend today.**

> Honest caveat: the key file sits beside the box. This protects against
> casual reading and accidental commit — it is **not** protection against
> malware running as your user. The threat model (T2) documents this residual
> risk.

## 2. Adding a provider securely (recommended)

```bash
agentstack provider add openrouter
```

The command:

1. Prints `Enter the API key for openrouter (input hidden):`.
2. Captures input via `promptHidden()` (`lib/secrets.js`) — stdin switched to
   **raw mode, no echo**; backspace works, Ctrl-C aborts.
3. Validates with `validateKey()` — rejects empty, placeholder
   (`your_openrouter_key_here`, `sk-xxxx`, `replace_me`, …), and keys shorter
   than 16 chars.
4. Stores the secret: `setSecret(name, key)` → encrypted `secrets.enc`,
   returning ref `keychain://agentstack/openrouter`.
5. Writes config: `addProvider(name)` → `providers.json` entry
   `{ secret_ref: "keychain://agentstack/openrouter", base_url: "<default>",
   enabled: true }`. **No raw secret in the file.**
6. Runs a live connection test via `registry.getAdapter(name).test()`
   (GET `/models`); on success stamps `status: "valid"` into config.

Other provider subcommands:

```bash
agentstack provider list                       # status per provider
agentstack provider test <name>                # re-run live test
agentstack provider disable <name>             # keep config, mark disabled
agentstack provider remove <name>              # delete secret + config entry
```

`defaultBaseUrl()` knows: openrouter, openai, anthropic, gemini, deepseek,
xai, mistral, groq, together, fireworks, cerebras, ollama, lmstudio.

## 3. Why `--token` on the CLI is deprecated

`agentstack install --token sk-or-...` (and `install.sh --token`) put the key:

- in **shell history** (bash/zsh/PowerShell persist command lines),
- in **process listings** (`ps` / Task Manager shows argv),
- in **terminal scrollback and logs**.

The CLI prints an explicit warning and the flag is scheduled for removal in
**v0.3.0**:

> `WARNING: --token on the command line is DEPRECATED and insecure.`

Everything `--token` did is available through the secure path: `agentstack
provider add openrouter` (hidden input) or setting the env var yourself. The
`install` flow still writes/merges `$HERMES_HOME/.env` — **if you ever used
`--token`, rotate that key.**

## 4. Where provider config lives

- **File:** `config/providers.json` under `AGENTSTACK_HOME`
  (`lib/paths.js` `providersConfigPath()`).
- **Shape:**

```json
{
  "providers": {
    "openrouter": {
      "secret_ref": "keychain://agentstack/openrouter",
      "base_url": "https://openrouter.ai/api/v1",
      "enabled": true,
      "status": "valid"
    }
  }
}
```

- `loadProviderConfig()` / `saveProviderConfig()` in `lib/secrets.js` manage it
  (mode 0600).
- **Rule:** if a provider is `enabled: true` but no secret exists,
  `agentstack security config` flags it ("enabled but no secret stored").

## 5. Checking health: `agentstack secrets doctor`

```bash
agentstack secrets doctor
```

Reports:

- the active credential backend (`systemStoreAvailable()` result:
  `keytar` / `cmdkey` / `security` / `unencrypted` / `encrypted-file`),
- for every provider in the registry: whether a key is stored (✓/·) and its
  config-level status (`not_configured`, `configured`, …).

Note the status is **config-level, not validated** — it prints `(key stored,
not validated)` unless you run `agentstack provider test <name>` for a live
check.

## 6. Related audit commands

- `agentstack security secrets` — scan the repo for committed secrets
  (`sk-`, `ghp_`, `AIza`, `xox`, `AKIA`, private keys; findings redacted).
- `agentstack security config` — raw-secret-in-config and
  enabled-without-key checks.
- `agentstack security full` — everything (also permissions + skills).

## 7. Do / Don't

| Do | Don't |
|----|-------|
| `agentstack provider add <name>` (hidden input) | `install --token …` / `--token` anywhere (remove in v0.3.0) |
| Keep `AGENTSTACK_HOME` on an encrypted volume | Commit `.machine-key`, `secrets.enc`, or `providers.json` |
| Rotate any key that ever touched a CLI/history/log | Store keys in the vault, notes, or chat |
| Use `secrets doctor` + `security full` in your routine | Paste keys into the API/UI — statuses only cross the boundary |

## 8. See also

- `docs/security/THREAT_MODEL.md` — T1/T2/T5 detail + residual risk.
- `docs/architecture/ARCHITECTURE.md` — `lib/secrets.js` in context.
