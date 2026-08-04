'use strict';
// adapter.js — base adapter interface for providers (mission §6).
const { ProviderError, ERROR_CODES } = require('./errors');

class Adapter {
  constructor(name, opts = {}) {
    this.name = name;
    this.baseUrl = opts.baseUrl || '';
    this.apiKey = opts.apiKey || null;
    this.timeoutMs = opts.timeoutMs || 60000;
  }

  // Capability flags — overridden by subclasses.
  capabilities() {
    return {
      listModels: false,
      chat: false,
      streaming: false,
      toolCalling: false,
      structuredOutput: false,
      vision: false,
      embeddings: false,
      usage: false,
      rateLimitMetadata: false,
    };
  }

  // Test connectivity + auth. Returns { status, message } using secrets.STATUS.
  async test() {
    throw new ProviderError(ERROR_CODES.UNKNOWN_PROVIDER_ERROR, `${this.name}: test not implemented`);
  }

  // List models. Returns array.
  async listModels() {
    if (!this.capabilities().listModels) {
      throw new ProviderError(ERROR_CODES.PROVIDER_UNAVAILABLE, `${this.name}: listModels unsupported`);
    }
    return [];
  }

  // Chat completion.
  async chat(_req) {
    throw new ProviderError(ERROR_CODES.INVALID_REQUEST, `${this.name}: chat not implemented`);
  }

  // Helper: timed fetch with cancellation + normalized errors.
  async _request(url, { method = 'GET', headers = {}, body = null, signal } = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    const onSigAbort = () => controller.abort();
    if (signal) {
      if (signal.aborted) { clearTimeout(timer); throw new ProviderError(ERROR_CODES.CANCELLED, 'cancelled'); }
      signal.addEventListener('abort', onSigAbort, { once: true });
    }
    try {
      const res = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined, signal: controller.signal });
      const text = await res.text();
      let json = null;
      try { json = text ? JSON.parse(text) : null; } catch {}
      if (res.status === 401) throw new ProviderError(ERROR_CODES.AUTHENTICATION_FAILED, 'authentication failed');
      if (res.status === 403) throw new ProviderError(ERROR_CODES.AUTHENTICATION_FAILED, 'unauthorised');
      if (res.status === 429) throw new ProviderError(ERROR_CODES.RATE_LIMITED, 'rate limited');
      if (res.status === 404) throw new ProviderError(ERROR_CODES.MODEL_NOT_FOUND, 'model/endpoint not found');
      if (res.status === 502 || res.status === 503) throw new ProviderError(ERROR_CODES.PROVIDER_UNAVAILABLE, `provider unavailable (${res.status})`);
      if (res.status >= 400) throw new ProviderError(ERROR_CODES.INVALID_REQUEST, `bad request (${res.status}): ${text.slice(0, 200)}`);
      return { status: res.status, json, text };
    } catch (e) {
      if (e instanceof ProviderError) throw e;
      if (e.name === 'AbortError') {
        throw new ProviderError(signal && signal.aborted ? ERROR_CODES.CANCELLED : ERROR_CODES.TIMEOUT, 'request timed out');
      }
      throw new ProviderError(ERROR_CODES.PROVIDER_UNAVAILABLE, `network error: ${e.message}`);
    } finally {
      clearTimeout(timer);
      if (signal) signal.removeEventListener('abort', onSigAbort);
    }
  }
}

module.exports = { Adapter };
