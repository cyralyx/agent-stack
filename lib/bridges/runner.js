'use strict';
// bridges/runner.js — bridge adapters (mission §10).
// Hermes / OpenClaw / mock adapters that produce a validated typed envelope.
const { spawnSync } = require('child_process');
const schema = require('./schema');
const platform = require('../platform');
const paths = require('../paths');

// Generic runner: execute a command with timeout, wrap in typed envelope.
function runBridge({ bridge, task, cmd, args, timeoutMs = 120000, signal }) {
  const opts = { encoding: 'utf8', shell: false, timeout: timeoutMs, maxBuffer: 10 * 1024 * 1024 };
  if (signal) opts.signal = signal;
  let r;
  try {
    r = spawnSync(cmd, args, opts);
  } catch (e) {
    if (e.killed || (signal && signal.aborted)) {
      return schema.failure({ bridge, task, message: 'cancelled', code: 'CANCELLED' });
    }
    return schema.failure({ bridge, task, message: e.message, code: 'PROVIDER_UNAVAILABLE' });
  }
  if (r.status === null || r.signal || r.error) {
    const timedOut = !!r.error && r.error.code === 'ETIMEDOUT';
    return timedOut
      ? schema.timedOut({ bridge, task, timeoutMs })
      : schema.failure({ bridge, task, message: r.error ? r.error.message : 'timed out or killed', code: timedOut ? 'TIMEOUT' : 'PROVIDER_UNAVAILABLE' });
  }
  if (r.status !== 0) {
    return schema.failure({ bridge, task, message: (r.stderr || r.stdout || '').trim().slice(0, 500), code: 'BRIDGE_ERROR' });
  }
  const out = (r.stdout || '').trim();
  return schema.success({ bridge, task, summary: out.slice(0, 200), output: out });
}

// Hermes adapter.
function hermes(task, opts = {}) {
  const bin = opts.hermesBin || findHermes();
  if (!bin) return schema.failure({ bridge: 'hermes', task, message: 'hermes not found', code: 'PROVIDER_UNAVAILABLE' });
  const args = ['chat', '-Q', '-q', task, '--provider', opts.provider || 'openrouter', '--model', opts.model || 'openai/gpt-4o-mini', '--source', 'agentstack-bridge'];
  return runBridge({ bridge: 'hermes', task, cmd: bin, args, timeoutMs: opts.timeoutMs, signal: opts.signal });
}

// OpenClaw adapter (permission-gated upstream by caller).
function openclaw(task, opts = {}) {
  const bin = opts.openclawBin || findOpenClaw();
  if (!bin) return schema.failure({ bridge: 'openclaw', task, message: 'openclaw not found', code: 'PROVIDER_UNAVAILABLE' });
  const args = [bin, task];
  return runBridge({ bridge: 'openclaw', task, cmd: bin, args, timeoutMs: opts.timeoutMs, signal: opts.signal });
}

// Mock adapter for tests (deterministic).
function mock(task, { mode = 'success', timeoutMs = 1000 } = {}) {
  if (mode === 'timeout') {
    // simulate a timeout envelope
    return schema.timedOut({ bridge: 'mock', task, timeoutMs });
  }
  if (mode === 'failure') {
    return schema.failure({ bridge: 'mock', task, message: 'mock failure', code: 'BRIDGE_ERROR' });
  }
  return schema.success({ bridge: 'mock', task, summary: 'mock ok', output: `mock result for: ${task}` });
}

function findHermes() {
  const home = paths.hermesHome();
  const cands = [
    require('path').join(home, 'hermes-agent', 'venv', 'Scripts', 'hermes.exe'),
    require('path').join(home, 'venv', 'Scripts', 'hermes.exe'),
    require('path').join(home, 'hermes-agent', 'venv', 'bin', 'hermes'),
  ];
  for (const c of cands) if (require('fs').existsSync(c)) return c;
  return platform.resolveCommand('hermes');
}

function findOpenClaw() {
  return platform.resolveCommand('openclaw');
}

module.exports = { hermes, openclaw, mock, runBridge, schema };
