# Privacy and Retention

Cyralyx must make data movement visible.

## Data classes

- public project data
- private project data
- credentials and secrets
- provider request content
- tool output
- telemetry
- audit events
- generated memory

## Rules

- Cloud requests must show which provider receives the data.
- Local-only mode must block cloud providers and remote telemetry.
- Telemetry is opt-in and documented field by field.
- Provider request logging defaults to metadata only; prompt bodies require explicit diagnostic mode.
- Users can configure retention by data class.
- Export and deletion must include derived indexes and embeddings.
- Deleting a project must identify external copies that Cyralyx cannot delete, such as provider logs.
- Incognito sessions must not create long-term memory and must use an explicit retention policy.
- Backups containing secrets must be encrypted or exclude secrets.
