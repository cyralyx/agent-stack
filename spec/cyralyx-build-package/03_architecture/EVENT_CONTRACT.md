# Event Contract

All agent, task, tool, provider, permission, and automation activity must flow through a typed event stream. The event stream powers the UI timeline, recovery, auditing, and tests.

## Event envelope

```json
{
  "event_id": "uuid",
  "schema_version": 1,
  "project_id": "uuid",
  "task_id": "uuid-or-null",
  "sequence": 42,
  "type": "tool.execution.completed",
  "actor": {"type": "agent", "id": "uuid"},
  "occurred_at": "ISO-8601 UTC",
  "visibility": "user",
  "payload": {},
  "correlation_id": "uuid",
  "causation_id": "uuid-or-null"
}
```

## Required event families

- project.created, project.updated, project.archived
- conversation.message.created, conversation.branch.created
- task.created, task.state.changed, task.checkpoint.saved
- agent.assigned, agent.delegated, agent.status.changed
- provider.request.started, provider.request.completed, provider.request.failed
- tool.permission.requested, tool.permission.decided
- tool.execution.started, tool.execution.output, tool.execution.completed, tool.execution.failed
- file.read, file.changed, file.deleted
- memory.proposed, memory.approved, memory.rejected, memory.updated
- skill.scan.started, skill.scan.completed, skill.installed, skill.disabled
- automation.scheduled, automation.started, automation.completed, automation.missed
- security.policy.blocked

## Guarantees

- Sequence numbers are monotonic within a task.
- Duplicate delivery is tolerated through idempotent consumers.
- Tool output events may be chunked but must preserve order.
- Sensitive payload fields are redacted before user-visible persistence.
- Unknown event versions are preserved and ignored safely rather than crashing clients.
