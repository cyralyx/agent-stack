'use strict';
// bridges/schema.js — typed bridge contract (mission §10).
// Every bridge invocation produces this envelope and validates against it.
const STATUS = ['success', 'partial', 'failed', 'cancelled', 'timed_out', 'awaiting_approval'];
const PROTOCOL_VERSION = '1.0';

function newRequestId() {
  return require('crypto').randomUUID();
}

// Validate an output envelope against the contract. Returns { valid, errors }.
function validate(envelope) {
  const errors = [];
  if (!envelope) return { valid: false, errors: ['envelope is null'] };
  if (envelope.version !== PROTOCOL_VERSION) errors.push(`version mismatch: ${envelope.version} !== ${PROTOCOL_VERSION}`);
  if (typeof envelope.request_id !== 'string' || !envelope.request_id) errors.push('missing request_id');
  if (!envelope.bridge) errors.push('missing bridge');
  if (!STATUS.includes(envelope.status)) errors.push(`invalid status: ${envelope.status}`);
  if (envelope.result && typeof envelope.result !== 'object') errors.push('result must be an object');
  if (envelope.errors && !Array.isArray(envelope.errors)) errors.push('errors must be an array');
  if (envelope.usage && typeof envelope.usage !== 'object') errors.push('usage must be an object');
  return { valid: errors.length === 0, errors };
}

// Build a success envelope.
function success({ bridge, task, summary, output, artifacts = [], usage = {} }) {
  const now = new Date().toISOString();
  return {
    version: PROTOCOL_VERSION,
    request_id: newRequestId(),
    bridge,
    status: 'success',
    started_at: now,
    completed_at: now,
    input: { task },
    result: { summary, output, artifacts },
    usage,
    errors: [],
  };
}

// Build a failure envelope.
function failure({ bridge, task, message, code = null }) {
  const now = new Date().toISOString();
  return {
    version: PROTOCOL_VERSION,
    request_id: newRequestId(),
    bridge,
    status: 'failed',
    started_at: now,
    completed_at: now,
    input: { task },
    result: { summary: '', output: '', artifacts: [] },
    usage: {},
    errors: [{ code, message }],
  };
}

// Build a timed_out envelope.
function timedOut({ bridge, task, timeoutMs }) {
  const now = new Date().toISOString();
  return {
    version: PROTOCOL_VERSION,
    request_id: newRequestId(),
    bridge,
    status: 'timed_out',
    started_at: now,
    completed_at: now,
    input: { task },
    result: { summary: '', output: '', artifacts: [] },
    usage: {},
    errors: [{ code: 'TIMEOUT', message: `exceeded ${timeoutMs}ms` }],
  };
}

module.exports = { PROTOCOL_VERSION, STATUS, newRequestId, validate, success, failure, timedOut };
