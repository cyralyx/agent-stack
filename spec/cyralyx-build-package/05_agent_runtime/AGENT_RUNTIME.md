# Agent Runtime

Required capabilities:

- persistent sessions
- durable goals
- resumable checkpoints
- task queue
- retries
- timeouts
- cancellation
- model switching
- tool calling
- worker delegation
- reviewer agents
- scheduled tasks
- messaging gateways
- human approval gates
- explicit memory proposals
- execution replay

## Task state machine

- created
- planning
- awaiting approval
- queued
- executing
- validating
- blocked
- retrying
- completed
- failed
- cancelled
- paused

Every transition must be recorded as an event.
