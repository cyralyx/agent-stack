# Releasing AgentStack

AgentStack ships as a **one-line bootstrap installer** plus release archives.

## One-line install (end user)

```bash
# latest release
bash <(curl -fsSL https://raw.githubusercontent.com/cyralyx/agent-stack/master/scripts/bootstrap.sh) --token sk-or-...

# specific version
AGENTSTACK_VERSION=v0.1.0 bash <(curl -fsSL https://raw.githubusercontent.com/cyralyx/agent-stack/master/scripts/bootstrap.sh) --token sk-or-...
```

What it does: downloads the release archive from GitHub Releases, extracts to
`~/.agentstack`, runs `install.sh --token <key>`. Done.

## How a release is made

1. Tag a commit: `git tag v0.1.0 && git push origin v0.1.0`
2. GitHub Actions (`.github/workflows/release.yml`) runs `scripts/package.sh`,
   builds `dist/agentstack-<ver>.{zip,tar.gz}` + checksums, and attaches them
   to a new release with auto-generated notes.
3. The `latest` convenience URL resolves to the newest release.

## Local package build (no GitHub needed)

```bash
./scripts/package.sh            # uses latest git tag, or 0.1.0
./scripts/package.sh 0.2.0      # explicit version
```

Outputs in `dist/`:
- `agentstack-<ver>.zip` (Windows-friendly)
- `agentstack-<ver>.tar.gz` (POSIX)
- `agentstack-latest.zip` (alias for the latest URL)
- `checksums.sha256`

## What's in the package

Full repo minus: `.git/`, `dist/`, `*.db` runtime state, `.env`/secrets,
`__pycache__`, logs. It's the same tree the installer knows how to consume.

## Testing a package before release

```bash
./scripts/package.sh 0.1.0
cd dist && tar -xzf agentstack-0.1.0.tar.gz
cd agentstack-0.1.0 && ./install.sh --token <test-key>
stack status
```
