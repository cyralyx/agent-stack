# Implementation Playbook

Hermes must execute Cyralyx as a sequence of independently verifiable vertical slices. Do not build every backend subsystem before producing usable UI, and do not build a polished interface disconnected from real services.

## Vertical-slice order

1. Local project creation, persistence, reopening, and deletion.
2. Provider connection, model discovery, streaming chat, and usage capture.
3. Notes and files scoped to a project.
4. Tool execution with approval, event streaming, cancellation, and audit history.
5. Retrieval with visible citations and source inspection.
6. Durable task checkpoints and recovery after restart.
7. Skill and MCP installation through the permission pipeline.
8. Council delegation with measurable benefit over a single-agent baseline.
9. Automations and remote access.

Each slice must include UI, API, storage, permissions, failure handling, tests, and documentation.

## Required workflow for every feature

1. Create or update a feature specification.
2. Link requirement IDs.
3. Record assumptions.
4. Define data changes and migration needs.
5. Define threat cases.
6. Define acceptance tests before implementation.
7. Implement the smallest coherent slice.
8. Run static checks, unit tests, integration tests, and the relevant end-to-end scenario.
9. Capture evidence.
10. Update the requirements index and milestone report.

## Stop conditions

Stop and report BLOCKED when:

- a required external dependency is unavailable;
- a licence is incompatible or unclear;
- a migration could destroy data and no verified backup exists;
- a security boundary cannot be enforced on the target platform;
- a provider capability cannot be verified;
- tests reveal unrelated regressions;
- implementation would require silently broadening permissions.

Do not work around these conditions by weakening the requirement.
