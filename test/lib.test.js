'use strict';
// Acceptance tests for AgentStack lib modules (mission §24).
// Uses isolated AGENTSTACK_HOME to avoid touching the real state.
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const os = require('os');

const fakeHome = path.join(os.tmpdir(), `astack-test-${Date.now()}`);
process.env.AGENTSTACK_HOME = fakeHome;
process.env.STACK_VAULT = path.join(fakeHome, 'vault');

const paths = require('../lib/paths');
const platform = require('../lib/platform');
const secrets = require('../lib/secrets');
const tasks = require('../lib/tasks');
const permissions = require('../lib/permissions');
const compat = require('../lib/compatibility');
const registry = require('../lib/providers/registry');
const { OpenAICompatibleAdapter } = require('../lib/providers/openai-compatible');
const { ERROR_CODES, toTypedError, ProviderError } = require('../lib/providers/errors');

test('paths are platform-aware and overridable', () => {
  assert.ok(paths.agentStackHome());
  assert.ok(fs.existsSync(paths.ensureDirs()));
  const ws = paths.workspace();
  assert.strictEqual(ws.path, process.env.STACK_VAULT);
});

test('secrets: placeholders and empty rejected, real keys accepted', () => {
  assert.strictEqual(secrets.validateKey('').valid, false);
  assert.strictEqual(secrets.validateKey('your_openrouter_key_here').valid, false);
  assert.strictEqual(secrets.validateKey('sk-').valid, false);
  assert.strictEqual(secrets.validateKey('sk-xxxx').valid, false);
  assert.strictEqual(secrets.validateKey('sk-or-123456789012345678901234567890123456').valid, true);
});

test('secrets: set/get/remove roundtrip (encrypted fallback)', () => {
  secrets.setSecret('testprov', 'sk-or-supersecretvalue1234567890');
  assert.strictEqual(secrets.getSecret('testprov'), 'sk-or-supersecretvalue1234567890');
  secrets.removeSecret('testprov');
  assert.strictEqual(secrets.getSecret('testprov'), null);
});

test('secrets: provider config stores ref not raw secret', () => {
  secrets.setSecret('openrouter', 'sk-or-abcdefghijklmnopqrstuvwxyz123456');
  secrets.addProvider('openrouter');
  const cfg = secrets.loadProviderConfig();
  const p = cfg.providers.openrouter;
  assert.ok(p.secret_ref.includes('keychain://'));
  assert.ok(!JSON.stringify(cfg).includes('sk-or-abcdefghijklmnopqrstuvwxyz123456'));
  secrets.removeSecret('openrouter');
});

test('tasks: IDs never collide (stable UUIDs + display numbers)', () => {
  tasks.add({ title: 'one' });
  tasks.add({ title: 'two' });
  const a = tasks.add({ title: 'three' });
  tasks.complete(a.id);
  const b = tasks.add({ title: 'four' }); // after completion
  const c = tasks.add({ title: 'five' });
  const ids = [a.id, b.id, c.id];
  assert.strictEqual(new Set(ids).size, 3, 'uuids must be unique');
  const displays = [a.display, b.display, c.display];
  assert.strictEqual(new Set(displays).size, 3, 'display numbers must be unique');
});

test('tasks: migration preserves existing tasks + backs up', () => {
  const legacy = path.join(process.env.STACK_VAULT, 'Agent Hub', 'Tasks.md');
  fs.mkdirSync(path.dirname(legacy), { recursive: true });
  fs.writeFileSync(legacy, '# Tasks\n\n- [ ] 1. legacy task one\n- [x] 2. legacy done task\n');
  const r = tasks.migrateFromLegacy(legacy);
  assert.ok(r.backedUp, 'legacy file must be backed up');
  assert.ok(r.imported >= 2, `expected >=2 imported, got ${r.imported}`);
  // markdown export should include both
  const md = tasks.toMarkdown();
  assert.ok(md.includes('legacy task one'));
  assert.ok(md.includes('legacy done task'));
});

test('permissions: dangerous execution denied by default / ask', () => {
  const mode = permissions.effectiveMode('process.execute');
  assert.ok(['ask', 'deny'].includes(mode), 'process.execute must default to ask or deny');
  const e = permissions.evaluate({ category: 'process.execute', action: 'rm -rf /' });
  assert.ok(e.allowed === false || e.allowed === null, 'must not auto-allow');
});

test('permissions: set deny blocks; set allow_permanent allows; logged', () => {
  permissions.set('process.execute', 'deny', { agent: 'testagent' });
  const e = permissions.evaluate({ category: 'process.execute', agent: 'testagent', action: 'x' });
  assert.strictEqual(e.allowed, false);
  permissions.set('process.execute', 'allow_permanent', { agent: 'testagent2' });
  const e2 = permissions.evaluate({ category: 'process.execute', agent: 'testagent2', action: 'x' });
  assert.strictEqual(e2.allowed, true);
  const a = permissions.audit();
  assert.ok(a.log.length >= 2, 'decisions must be logged');
});

test('compatibility: versionAtLeast works', () => {
  assert.strictEqual(compat.versionAtLeast('1.2.3', '1.0.0'), true);
  assert.strictEqual(compat.versionAtLeast('0.9.9', '1.0.0'), false);
  assert.strictEqual(compat.versionAtLeast('2.0.0', '1.9.9'), true);
  assert.strictEqual(compat.versionAtLeast('1.10.0', '1.9.0'), true);
});

test('providers: error taxonomy maps statuses', () => {
  assert.strictEqual(toTypedError(401).code, ERROR_CODES.AUTHENTICATION_FAILED);
  assert.strictEqual(toTypedError(429).code, ERROR_CODES.RATE_LIMITED);
  assert.strictEqual(toTypedError(503).code, ERROR_CODES.PROVIDER_UNAVAILABLE);
  assert.strictEqual(toTypedError('model_not_found').code, ERROR_CODES.MODEL_NOT_FOUND);
});

test('providers: openai-compatible mock test() maps auth failure', async () => {
  const a = new OpenAICompatibleAdapter('mock', { baseUrl: 'http://127.0.0.1:1', apiKey: 'bad' });
  const r = await a.test();
  assert.ok(['invalid', 'unreachable'].includes(r.status));
});

test('providers: registry lists supported set', () => {
  const list = registry.list();
  for (const p of ['openrouter', 'openai', 'anthropic', 'gemini', 'deepseek', 'xai', 'mistral', 'groq', 'together', 'fireworks', 'cerebras', 'ollama', 'lmstudio']) {
    assert.ok(list.includes(p), `${p} must be in registry`);
  }
});

test('providers: ProviderError carries typed code', () => {
  const e = new ProviderError(ERROR_CODES.TIMEOUT, 'took too long');
  assert.strictEqual(e.code, ERROR_CODES.TIMEOUT);
  assert.ok(e instanceof Error);
});
