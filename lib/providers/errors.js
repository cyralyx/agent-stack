'use strict';
// errors.js — provider error taxonomy (mission §6).
const ERROR_CODES = {
  AUTHENTICATION_FAILED: 'AUTHENTICATION_FAILED',
  RATE_LIMITED: 'RATE_LIMITED',
  PROVIDER_UNAVAILABLE: 'PROVIDER_UNAVAILABLE',
  INVALID_REQUEST: 'INVALID_REQUEST',
  MODEL_NOT_FOUND: 'MODEL_NOT_FOUND',
  TOOL_CALL_UNSUPPORTED: 'TOOL_CALL_UNSUPPORTED',
  CONTEXT_LIMIT_EXCEEDED: 'CONTEXT_LIMIT_EXCEEDED',
  TIMEOUT: 'TIMEOUT',
  CANCELLED: 'CANCELLED',
  MALFORMED_RESPONSE: 'MALFORMED_RESPONSE',
  UNKNOWN_PROVIDER_ERROR: 'UNKNOWN_PROVIDER_ERROR',
};

// Map a provider status to a typed code + message.
function toTypedError(status, detail) {
  const map = {
    authentication_failed: ERROR_CODES.AUTHENTICATION_FAILED,
    unauthorized: ERROR_CODES.AUTHENTICATION_FAILED,
    unauthorised: ERROR_CODES.AUTHENTICATION_FAILED,
    401: ERROR_CODES.AUTHENTICATION_FAILED,
    rate_limited: ERROR_CODES.RATE_LIMITED,
    429: ERROR_CODES.RATE_LIMITED,
    unavailable: ERROR_CODES.PROVIDER_UNAVAILABLE,
    503: ERROR_CODES.PROVIDER_UNAVAILABLE,
    502: ERROR_CODES.PROVIDER_UNAVAILABLE,
    model_not_found: ERROR_CODES.MODEL_NOT_FOUND,
    404: ERROR_CODES.MODEL_NOT_FOUND,
    context_limit: ERROR_CODES.CONTEXT_LIMIT_EXCEEDED,
    400: ERROR_CODES.CONTEXT_LIMIT_EXCEEDED,
  };
  const code = map[String(status).toLowerCase()] || ERROR_CODES.UNKNOWN_PROVIDER_ERROR;
  return { code, message: detail || code };
}

class ProviderError extends Error {
  constructor(code, message, meta = {}) {
    super(message || code);
    this.code = code;
    this.meta = meta;
  }
}

module.exports = { ERROR_CODES, toTypedError, ProviderError };
