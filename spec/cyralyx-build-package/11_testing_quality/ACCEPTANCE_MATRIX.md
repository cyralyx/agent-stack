# Acceptance Matrix

Hermes must expand this into test cases with IDs and evidence links.

| Area | Minimum acceptance condition |
|---|---|
| Installer | Clean Windows install launches without Docker or manual Python setup |
| Projects | Project data remains isolated and reopens after restart |
| Providers | At least OpenAI, Anthropic, Gemini, OpenRouter, Ollama, and generic OpenAI-compatible adapters pass conformance tests |
| Chat | Streaming, cancellation, retries, branches, and usage capture work |
| Files | Selected folder sync detects create, edit, rename, and delete without duplicate indexing |
| Retrieval | Answer displays exact source passages and warns when evidence is insufficient |
| Memory | Proposed memory can be approved, edited, rejected, versioned, exported, and deleted |
| Tools | Command preview, approval, output streaming, timeout, cancellation, and exit code work |
| Recovery | Active task resumes or fails safely after forced process termination |
| Permissions | A denied capability cannot be bypassed through a plugin, MCP server, or nested tool |
| Skills | Malicious fixture is blocked and safe fixture installs in project scope only |
| Themes | User theme survives restart and invalid theme import fails safely |
| Export | Exported project can be imported into a clean installation with matching core data |
| Backup | Restore reproduces the pre-failure state |
| Accessibility | Main workflows are keyboard operable and pass selected automated checks |
