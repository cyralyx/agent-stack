# Threat Model

Protect against:

- prompt injection
- indirect prompt injection
- malicious attachments
- poisoned notes
- poisoned skills
- malicious MCP servers
- command injection
- path traversal
- SSRF
- secret leakage
- cross-project leakage
- dependency confusion
- privilege escalation
- unsafe model output
- runaway agents
- cost escalation
- destructive repair loops

External content must be treated as untrusted data, not instructions.
