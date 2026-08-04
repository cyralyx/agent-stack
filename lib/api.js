'use strict';
// api.js — localhost-only IPC service for the future Cyralyx UI (mission §19).
// Binds to 127.0.0.1 only; no auth needed locally, but refuses non-loopback.
const http = require('http');
const paths = require('./paths');
const compat = require('./compatibility');
const tasks = require('./tasks');
const registry = require('./providers/registry');
const permissions = require('./permissions');
const events = require('./events');

const DEFAULT_PORT = 38765; // arbitrary high port

function json(res, code, obj) {
  res.writeHead(code, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(obj));
}

function systemStatus() {
  return {
    compatibility: compat.report(),
    providers: registry.list().map((p) => ({ name: p, status: registry.configuredStatus(p) })),
    tasks: { count: tasks.list().length },
    permissions: permissions.effectiveMode,
    events: events.recent(10),
    workspace: paths.workspace(),
  };
}

function handle(req, res) {
  // Guard: only accept loopback connections (127.0.0.1 / ::1)
  const addr = req.socket.remoteAddress || '';
  if (!addr.includes('127.0.0.1') && addr !== '::1' && addr !== '::ffff:127.0.0.1') {
    json(res, 403, { error: 'forbidden: non-loopback' });
    return;
  }
  const url = new URL(req.url, 'http://localhost');
  const pathName = url.pathname;

  try {
    if (req.method === 'GET' && pathName === '/api/status') return json(res, 200, systemStatus());
    if (req.method === 'GET' && pathName === '/api/compatibility') return json(res, 200, compat.report());
    if (req.method === 'GET' && pathName === '/api/providers') return json(res, 200, registry.list().map((p) => ({ name: p, status: registry.configuredStatus(p) })));
    if (req.method === 'GET' && pathName === '/api/tasks') return json(res, 200, tasks.list());
    if (req.method === 'POST' && pathName === '/api/tasks') {
      let body = '';
      req.on('data', (d) => { body += d; });
      req.on('end', () => {
        try {
          const { title } = JSON.parse(body || '{}');
          if (!title) return json(res, 400, { error: 'title required' });
          const t = tasks.add({ title });
          json(res, 201, t);
        } catch (e) { json(res, 400, { error: e.message }); }
      });
      return;
    }
    if (req.method === 'GET' && pathName === '/api/events') return json(res, 200, events.recent());
    if (req.method === 'GET' && pathName === '/api/health') {
      return json(res, 200, { status: 'ok', version: '0.2.0', bind: '127.0.0.1:' + DEFAULT_PORT });
    }
    json(res, 404, { error: 'not found', path: pathName });
  } catch (e) {
    json(res, 500, { error: e.message });
  }
}

function start(port = DEFAULT_PORT, { host = '127.0.0.1' } = {}) {
  return new Promise((resolve, reject) => {
    const server = http.createServer(handle);
    server.on('error', reject);
    server.listen(port, host, () => {
      // eslint-disable-next-line no-console
      console.log(`AgentStack API listening on http://${host}:${port} (localhost only)`);
      resolve(server);
    });
  });
}

module.exports = { start, DEFAULT_PORT, systemStatus };
