'use strict';
// registry.js — provider registry (mission §6). Maps names to adapters.
const { OpenAICompatibleAdapter } = require('./openai-compatible');
const secrets = require('../secrets');

// Definitions for the full provider set.
const PROVIDERS = {
  openrouter: { kind: 'openai-compatible', models: true },
  openai: { kind: 'openai-compatible', models: true },
  deepseek: { kind: 'openai-compatible', models: true },
  xai: { kind: 'openai-compatible', models: true },
  mistral: { kind: 'openai-compatible', models: true },
  groq: { kind: 'openai-compatible', models: true },
  together: { kind: 'openai-compatible', models: true },
  fireworks: { kind: 'openai-compatible', models: true },
  cerebras: { kind: 'openai-compatible', models: true },
  lmstudio: { kind: 'openai-compatible', models: true },
  anthropic: { kind: 'anthropic', models: true },
  gemini: { kind: 'gemini', models: true },
  ollama: { kind: 'ollama', models: true },
};

// Provider status vs secrets.STATUS — keep local alias so other files needn't import secrets internals.
const STATUS = {
  NOT_CONFIGURED: 'not_configured',
  CONFIGURED: 'configured',
  VALID: 'valid',
  INVALID: 'invalid',
  EXPIRED: 'expired',
  UNAUTHORISED: 'unauthorised',
  RATE_LIMITED: 'rate_limited',
  UNREACHABLE: 'unreachable',
  UNSUPPORTED: 'unsupported',
};

// Build an adapter for a named provider using stored secrets + config.
function getAdapter(name) {
  if (!PROVIDERS[name] && !isCustom(name)) {
    throw new Error(`Unsupported provider: ${name}`);
  }
  const cfg = secrets.loadProviderConfig();
  const p = cfg.providers && cfg.providers[name];
  const apiKey = secrets.getSecret(name);
  const baseUrl = (p && p.base_url) || secrets.defaultBaseUrl(name);
  return new OpenAICompatibleAdapter(name, { baseUrl, apiKey });
}

function isCustom(name) {
  // generic OpenAI-compatible custom endpoints are registered in config
  const cfg = secrets.loadProviderConfig();
  return !!(cfg.providers && cfg.providers[name] && cfg.providers[name].custom === true);
}

function list() {
  const base = Object.keys(PROVIDERS).sort();
  const cfg = secrets.loadProviderConfig();
  const customs = Object.keys((cfg.providers || {})).filter((n) => !PROVIDERS[n]);
  return [...base, ...customs].sort();
}

// Determine configured/valid status for a provider without network (config-level).
function configuredStatus(name) {
  const cfg = secrets.loadProviderConfig();
  const hasConfig = !!(cfg.providers && cfg.providers[name]);
  const hasKey = !!secrets.getSecret(name);
  if (!hasConfig && !hasKey) return STATUS.NOT_CONFIGURED;
  if (!hasKey) return STATUS.CONFIGURED; // config exists but no key
  return STATUS.CONFIGURED;
}

module.exports = { PROVIDERS, STATUS, getAdapter, list, configuredStatus, isCustom };
