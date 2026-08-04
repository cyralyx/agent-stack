'use strict';
// events.js — structured event emission (mission §19).
// Produces a documented event stream for the future Cyralyx UI.
const fs = require('fs');
const path = require('path');
const paths = require('./paths');

const EVENT_TYPES = [
  'task.created',
  'task.routed',
  'permission.requested',
  'agent.started',
  'tool.invoked',
  'output.received',
  'validation.started',
  'task.completed',
  'task.failed',
  'memory.written',
  'provider.error',
  'budget.warning',
];

let _sink = null;

function sink() {
  if (_sink) return _sink;
  fs.mkdirSync(path.join(paths.dataHome(), 'events'), { recursive: true });
  _sink = path.join(paths.dataHome(), 'events', 'events.ndjson');
  return _sink;
}

function emit(type, data = {}, opts = {}) {
  if (!EVENT_TYPES.includes(type)) throw new Error(`Unknown event type: ${type}`);
  const event = {
    ts: (opts.ts || new Date()).toISOString(),
    type,
    ...data,
  };
  // Events are persisted by default so the stream is observable by the UI/API.
  const persist = opts.persist !== false;
  if (persist) {
    try { fs.appendFileSync(sink(), JSON.stringify(event) + '\n'); } catch {}
  }
  notify(event);
  if (opts.handler) opts.handler(event);
  return event;
}

// In-memory subscriber list (for API/UI).
const subscribers = [];
function subscribe(fn) { subscribers.push(fn); return () => { const i = subscribers.indexOf(fn); if (i >= 0) subscribers.splice(i, 1); }; }
function notify(event) { for (const fn of subscribers) { try { fn(event); } catch {} } }

function recent(limit = 50) {
  const file = sink();
  if (!fs.existsSync(file)) return [];
  const lines = fs.readFileSync(file, 'utf8').split('\n').filter(Boolean);
  return lines.slice(-limit).map((l) => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
}

module.exports = { EVENT_TYPES, emit, subscribe, notify, recent, sink };
