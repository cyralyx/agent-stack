# Core Data Model

The local database is the authoritative index for application state. User-authored notes and compatible attachments remain exportable files. Database rows must use stable UUIDs and timestamps in UTC.

## Core entities

### Workspace
- id
- name
- storage_path
- created_at
- updated_at
- schema_version

### Project
- id
- workspace_id
- name
- description
- status
- root_path
- default_provider_profile_id
- permission_profile_id
- created_at
- updated_at
- archived_at

### Conversation
- id
- project_id
- title
- active_branch_id
- created_at
- updated_at

### Message
- id
- conversation_id
- parent_message_id
- role
- content_json
- provider_id
- model_id
- token_usage_json
- cost_amount
- created_at

### Task
- id
- project_id
- parent_task_id
- objective
- state
- assigned_agent_id
- budget_json
- checkpoint_json
- started_at
- finished_at

### Event
- id
- project_id
- task_id
- sequence_number
- event_type
- actor_type
- actor_id
- payload_json
- visibility
- created_at

### Note
- id
- project_id
- relative_path
- content_hash
- frontmatter_json
- created_at
- updated_at
- deleted_at

### Memory
- id
- project_id
- scope
- content
- source_event_id
- confidence
- review_state
- version
- created_at
- updated_at

### ProviderProfile
- id
- provider_type
- display_name
- base_url
- secret_reference
- configuration_json
- enabled

### ModelCapability
- provider_profile_id
- model_id
- capability
- status: declared | verified | failed | unknown
- evidence_json
- checked_at

### PermissionGrant
- id
- subject_type
- subject_id
- project_id
- capability
- resource_pattern
- grant_scope
- decision
- expires_at
- created_at

### SkillInstallation
- id
- project_id
- skill_id
- version
- source
- provenance_json
- scan_report_json
- enabled
- installed_at

## Data rules

- Project deletion uses soft deletion followed by explicit purge.
- Secrets are never stored directly in ordinary database columns.
- Events are append-only except for retention or legally required deletion.
- File paths are stored relative to the workspace root where possible.
- Cross-project queries require an explicit global permission.
- Every schema change needs forward migration, rollback or recovery strategy, and fixtures.
