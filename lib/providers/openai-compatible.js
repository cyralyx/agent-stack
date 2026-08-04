'use strict';
// openai-compatible.js — generic OpenAI-compatible adapter.
// Covers: OpenAI, DeepSeek, xAI, Mistral, Groq, Together, Fireworks, Cerebras,
// LM Studio, and any OpenAI-compatible endpoint.
const { Adapter } = require('./adapter');

class OpenAICompatibleAdapter extends Adapter {
  capabilities() {
    return {
      listModels: true,
      chat: true,
      streaming: true,
      toolCalling: true,
      structuredOutput: true,
      vision: true,
      embeddings: true,
      usage: true,
      rateLimitMetadata: true,
    };
  }

  _authHeaders() {
    const h = { 'Content-Type': 'application/json' };
    if (this.apiKey) h['Authorization'] = `Bearer ${this.apiKey}`;
    return h;
  }

  async test() {
    try {
      const r = await this._request(`${this.baseUrl}/models`, { headers: this._authHeaders() });
      return { status: 'valid', message: `${this.name}: ok (${(r.json && r.json.data && r.json.data.length) || 'n'} models)` };
    } catch (e) {
      return { status: e.code === 'AUTHENTICATION_FAILED' ? 'invalid' : 'unreachable', message: e.message };
    }
  }

  async listModels() {
    const r = await this._request(`${this.baseUrl}/models`, { headers: this._authHeaders() });
    const data = (r.json && r.json.data) || [];
    return data.map((m) => m.id);
  }

  async chat(req) {
    const body = {
      model: req.model,
      messages: req.messages,
      temperature: req.temperature,
      max_tokens: req.max_tokens,
    };
    if (req.stream) body.stream = true;
    if (req.tools) body.tools = req.tools;
    if (req.response_format) body.response_format = req.response_format;
    const r = await this._request(`${this.baseUrl}/chat/completions`, { method: 'POST', headers: this._authHeaders(), body });
    const c = r.json && r.json.choices && r.json.choices[0];
    const usage = r.json && r.json.usage;
    return {
      text: c && c.message && c.message.content,
      toolCalls: c && c.message && c.message.tool_calls,
      usage: usage ? { input_tokens: usage.prompt_tokens, output_tokens: usage.completion_tokens, total_tokens: usage.total_tokens } : null,
      model: r.json && r.json.model,
    };
  }
}

module.exports = { OpenAICompatibleAdapter };
