'use strict';
// Smoke tests for the AgentStack merged CLI.
const { test } = require('node:test');
const assert = require('node:assert');
const { spawnSync } = require('child_process');
const path = require('path');

const CLI = path.join(__dirname, '..', 'bin', 'agentstack.js');

function run(args, env = {}) {
  return spawnSync(process.execPath, [CLI, ...args], {
    encoding: 'utf8',
    timeout: 30000,
    env: { ...process.env, ...env },
  });
}

test('help exits 0 and lists commands', () => {
  const r = run(['help']);
  assert.strictEqual(r.status, 0);
  assert.match(r.stdout, /Usage: agentstack <command>/);
  assert.match(r.stdout, /install/);
  assert.match(r.stdout, /council/);
});

test('status reports all three agents', () => {
  const r = run(['status']);
  assert.strictEqual(r.status, 0);
  assert.match(r.stdout, /brain/);
  assert.match(r.stdout, /hands/);
  assert.match(r.stdout, /memory/);
});

test('skills lists bundled skills', () => {
  const r = run(['skills']);
  assert.strictEqual(r.status, 0);
  assert.match(r.stdout, /skills/);
});

test('todo add/list/done roundtrip in temp vault', () => {
  const fake = require('os').tmpdir() + '/astack-test-' + Date.now();
  const env = {
    HERMES_HOME: path.join(fake, 'hermes'),
    STACK_VAULT: path.join(fake, 'vault'),
    HOME: fake,
  };
  const add = run(['todo', 'add', 'test task'], env);
  assert.strictEqual(add.status, 0, add.stderr);
  const list = run(['todo', 'list'], env);
  assert.match(list.stdout, /test task/);
  const done = run(['todo', 'done', '1'], env);
  assert.strictEqual(done.status, 0, done.stderr);
  const list2 = run(['todo', 'list'], env);
  assert.match(list2.stdout, /No open tasks/);
});

test('unknown command exits 2', () => {
  const r = run(['does-not-exist']);
  assert.strictEqual(r.status, 2);
});
