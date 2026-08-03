# Server Diagnostics

Procedural skill for checking server health.

## Triggers
- "Check server"
- "Is the server healthy?"

## Steps
1. Run `doctor_host` for CPU/RAM/GPU/OS
2. Run `doctor_port <key_port>` for critical services
3. Run `doctor_docker` for container status
4. Aggregate probe results into summary
5. Only escalate to LLM for failed probes
