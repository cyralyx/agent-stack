# Secrets and Sandbox

## Secrets

- OS keychain where available
- encrypted fallback store
- never expose raw keys to UI logs
- redact output
- rotate and delete
- project/provider scoping

## Sandbox

Use the strongest practical sandbox per platform.

At minimum:

- workspace-scoped filesystem
- restricted environment variables
- restricted network
- CPU and memory limits
- timeout
- process tree termination
- audit logs
- disposable execution environment for untrusted skills
