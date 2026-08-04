'use strict';
// Bridge contract + routing tests (mission §10, §11, §24).
const { test } = require('node:test');
const assert = require('node:assert');
const os = require('os');
const path = require('path');

const fakeHome = path.join(os.tmpdir(), `astack-bridge-test-${Date.now()}`);
process.env.AGENTSTACK_HOME = fakeHome;

const { validate, success, failure, timedOut, PROTOCOL_VERSION } = require('../lib/bridges/schema');
const bridges = require('../lib/bridges/runner');
const routing = require('../lib/routing');

test('bridge schema: valid success envelope passes', () => {
  const env = success({ bridge: 'hermes', task: 'hello', summary: 'hi', output: 'hi there' });
  const r = validate(env);
  assert.strictEqual(r.valid, true, JSON.stringify(r.errors));
  assert.strictEqual(env.version, PROTOCOL_VERSION);
});

test('bridge schema: malformed envelope fails safely', () => {
  const r = validate({ version: '9.9', status: 'bogus' });
  assert.strictEqual(r.valid, false);
  assert.ok(r.errors.length > 0);
  assert.strictEqual(validate(null).valid, false);
});

test('bridge schema: failure + timeout envelopes', () => {
  const f = failure({ bridge: 'x', task: 't', message: 'boom', code: 'BRIDGE_ERROR' });
  assert.strictEqual(validate(f).valid, true);
  assert.strictEqual(f.status, 'failed');
  const to = timedOut({ bridge: 'x', task: 't', timeoutMs: 100 });
  assert.strictEqual(to.status, 'timed_out');
});

test('bridge: mock success/failure/timeout', () => {
  assert.strictEqual(bridges.mock('do it', {}).status, 'success');
  assert.strictEqual(bridges.mock('do it', { mode: 'failure' }).status, 'failed');
  assert.strictEqual(bridges.mock('do it', { mode: 'timeout', timeoutMs: 100 }).status, 'timed_out');
});

test('routing: layered selection with explicit agent override', () => {
  const r1 = routing.route('Research the API', {});
  assert.strictEqual(r1.selected_target, 'hermes');
  const r2 = routing.route('create a new file called x', { agent: 'openclaw' });
  assert.strictEqual(r2.selected_target, 'openclaw');
});

test('routing: always returns structured reason + confidence', () => {
  const r = routing.route('Add tests for the module', {});
  assert.ok(r.reason);
  assert.ok(typeof r.confidence === 'number');
  assert.ok(Array.isArray(r.alternatives));
});

test('routing: deterministic rule routes execution verbs to openclaw', () => {
  const r = routing.route('install the package', {});
  assert.strictEqual(r.selected_target, 'openclaw');
});
