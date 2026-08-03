# Error Taxonomy

Use stable error codes and user-readable messages.

## Categories

- configuration
- authentication
- permission
- validation
- provider
- network
- storage
- indexing
- tool execution
- plugin
- MCP
- task orchestration
- migration
- security policy
- resource exhaustion
- internal defect

Every surfaced error must include:

- stable code
- concise description
- affected operation
- whether retry is safe
- suggested action
- correlation ID
- redacted technical details

Do not show raw stack traces to ordinary users. Preserve them in diagnostic bundles after secret redaction.
