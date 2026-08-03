# Provider Adapter Specification

"Every provider works" means Cyralyx provides a stable adapter framework, first-class tested adapters for major providers, and a generic OpenAI-compatible adapter for compatible services. It does not mean unsupported APIs are assumed compatible.

## Adapter interface

Each adapter must implement:

- validateConfiguration
- testConnection
- listModels
- getDeclaredCapabilities
- probeCapabilities
- createChatCompletion
- streamChatCompletion
- createEmbedding where supported
- estimateTokens where supported
- normaliseUsage
- mapProviderError
- cancelRequest

Optional methods may cover images, audio, batches, files, and fine-tuning.

## Capability statuses

- declared: provider documentation claims support
- verified: Cyralyx probe or test passed
- failed: probe failed
- unknown: not tested or cannot be tested safely

The router must prefer verified capabilities and never treat declared support as proof.

## API key flow

1. User selects provider or Generic OpenAI-Compatible.
2. User enters key and optional base URL.
3. Key is written directly to the OS secret store.
4. UI receives only a secret reference.
5. Backend tests a minimal request.
6. Model list is fetched or manually configured.
7. Capabilities are declared and optionally probed.
8. User selects project scope and budget.

## Error normalisation

Map provider responses to stable categories:

- authentication_failed
- permission_denied
- model_not_found
- unsupported_capability
- invalid_request
- context_limit
- rate_limited
- quota_exceeded
- provider_unavailable
- timeout
- content_blocked
- malformed_response
- cancelled
- unknown_provider_error

Preserve redacted provider details for diagnosis.

## Conformance tests

Every first-class adapter must pass:

- invalid key
- valid key
- model listing
- streaming
- cancellation
- timeout
- rate-limit parsing
- usage normalisation
- context-limit handling
- tool-call round trip where supported
- structured output where supported
