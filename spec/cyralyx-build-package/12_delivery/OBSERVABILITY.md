# Observability

Provide local-first diagnostics without forcing telemetry.

## Metrics

- task success and failure
- task duration
- provider latency
- token and cost usage
- tool failures
- queue depth
- indexing progress
- retrieval hit quality
- memory proposal acceptance
- plugin and MCP health
- CPU, RAM, GPU, VRAM where available

## Logs

- structured
- correlation IDs
- severity levels
- redacted secrets
- bounded retention
- exportable diagnostic bundle

## Traces

Trace task, provider, tool, and validation stages. Do not record hidden chain-of-thought. Record observable decisions, inputs after redaction, outputs, timings, and state transitions.
