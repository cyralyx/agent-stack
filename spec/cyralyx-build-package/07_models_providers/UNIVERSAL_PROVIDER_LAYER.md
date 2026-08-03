# Universal Provider Layer

The user must be able to connect any supported cloud provider using an API key and any supported local provider using an endpoint.

## First-class providers

- OpenAI
- Anthropic
- Google Gemini
- OpenRouter
- DeepSeek
- xAI
- Mistral
- Cohere
- Together AI
- Fireworks AI
- Groq
- Cerebras
- SambaNova
- Nebius
- Hugging Face Inference
- Novita
- Nous Portal where available
- Ollama
- LM Studio
- llama.cpp
- vLLM
- SGLang
- LiteLLM gateways
- generic OpenAI-compatible endpoints

## Adapter contract

Every provider adapter should expose where supported:

- list models
- chat
- streaming
- tool calls
- structured output
- vision
- embeddings
- image generation
- audio input/output
- batch requests
- rate-limit information
- token usage
- cost metadata
- health check

## Provider setup

The UI must support:

- provider name
- API key
- base URL
- organisation/project identifier where needed
- custom headers
- test connection
- list models
- capability detection
- save encrypted credential
- per-project availability
- spending limit
- disable provider
- delete credentials

Never hard-code secrets.
