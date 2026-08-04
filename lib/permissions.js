'use strict';
// permissions.js — permission gates for execution agents (P1).
// Default deny/ask. Decisions are logged.
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const paths = require('./paths');

const CATEGORIES = [
  'files.read',
  'files.write',
  'process.execute',
  'network.access',
  'browser.control',
  'secrets.read',
  'git.write',
  'system.admin',
  'messaging.send',
  'vault.write',
];

const MODES = ['deny', 'ask', 'allow_once', 'allow_session', 'allow_project', 'allow_permanent'];

let _policy = null;

function loadPolicy() {
  if (_policy) return _policy;
  const file = paths.permissionsPath();
  fs.mkdirSync(path.dirname(file), { recursive: true });
  if (!fs.existsSync(file)) {
    // default: deny-ask for everything except safe reads
    _policy = { version: 1, defaults: {}, entries: {}, log: [] };
    for (const c of CATEGORIES) {
      _policy.defaults[c] = (c === 'files.read' || c === 'vault.write') ? 'allow_project' : 'ask';
    }
    savePolicy();
    return _policy;
  }
  try {
    _policy = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (!_policy.defaults) { _policy.defaults = {}; for (const c of CATEGORIES) _policy.defaults[c] = 'ask'; }
    if (!_policy.entries) _policy.entries = {};
    if (!_policy.log) _policy.log = [];
    return _policy;
  } catch {
    _policy = { version: 1, defaults: {}, entries: {}, log: [] };
    savePolicy();
    return _policy;
  }
}

function savePolicy() {
  fs.mkdirSync(path.dirname(paths.permissionsPath()), { recursive: true });
  fs.writeFileSync(paths.permissionsPath(), JSON.stringify(_policy, null, 2), { mode: 0o600 });
}

function logDecision(entry) {
  _policy.log.push({ ts: new Date().toISOString(), ...entry });
  if (_policy.log.length > 500) _policy.log = _policy.log.slice(-500);
  savePolicy();
}

// Effective mode for a category + optional agent/project.
function effectiveMode(category, { agent = null, project = null } = {}) {
  const p = loadPolicy();
  if (agent && p.entries[agent] && p.entries[agent][category]) return p.entries[agent][category];
  if (project && p.entries[`project:${project}`] && p.entries[`project:${project}`][category]) return p.entries[`project:${project}`][category];
  return p.defaults[category] || 'ask';
}

function set(category, mode, { agent = null, project = null } = {}) {
  if (!CATEGORIES.includes(category)) throw new Error(`Unknown permission category: ${category}`);
  if (!MODES.includes(mode)) throw new Error(`Unknown mode: ${mode}`);
  const p = loadPolicy();
  const key = agent ? agent : (project ? `project:${project}` : 'default');
  if (key === 'default') { p.defaults[category] = mode; }
  else {
    if (!p.entries[key]) p.entries[key] = {};
    if (mode === 'deny') p.entries[key][category] = 'deny';
    else p.entries[key][category] = mode;
  }
  savePolicy();
  return { category, mode, scope: key };
}

function reset() {
  _policy = null;
  const file = paths.permissionsPath();
  if (fs.existsSync(file)) fs.unlinkSync(file);
  loadPolicy();
  return true;
}

function audit() {
  const p = loadPolicy();
  return {
    defaults: p.defaults,
    entries: p.entries,
    log: p.log,
  };
}

// Evaluate a proposed action against policy. Returns { allowed, mode, reason }.
function evaluate({ category, agent = null, project = null, action = '' }) {
  const mode = effectiveMode(category, { agent, project });
  logDecision({ category, agent, project, action, mode, outcome: mode === 'deny' ? 'denied' : (mode === 'ask' ? 'asked' : 'allowed') });
  if (mode === 'deny') return { allowed: false, mode, reason: `denied by policy (${category})` };
  if (mode === 'allow_once' || mode === 'allow_session' || mode === 'allow_project' || mode === 'allow_permanent') {
    return { allowed: true, mode, reason: `allowed by policy (${category}: ${mode})` };
  }
  // ask
  return { allowed: null, mode, reason: 'requires approval' };
}

// Interactive prompt for approval of a dangerous action.
function promptApproval(spec) {
  return new Promise((resolve) => {
    console.log('\n=== AgentStack permission request ===');
    console.log(`Target agent:  ${spec.agent || '(default)'}`);
    console.log(`Proposed:      ${spec.action || ''}`);
    console.log(`Command:       ${spec.command || ''}`);
    console.log(`Working dir:   ${spec.cwd || ''}`);
    console.log(`Files:         ${(spec.files || []).join(', ') || 'none'}`);
    console.log(`Network:       ${(spec.destinations || []).join(', ') || 'none'}`);
    console.log(`Rollback:      ${spec.rollback || 'none'}`);
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question(`Allow ${spec.category}? (y=once/N=deny/a=allow-project-forever) `, (ans) => {
      rl.close();
      const a = ans.trim().toLowerCase();
      if (a === 'y') { logDecision({ ...spec, outcome: 'allow_once' }); resolve({ allowed: true, mode: 'allow_once' }); }
      else if (a === 'a') { set(spec.category, 'allow_project', { agent: spec.agent, project: spec.project }); logDecision({ ...spec, outcome: 'allow_project' }); resolve({ allowed: true, mode: 'allow_project' }); }
      else { logDecision({ ...spec, outcome: 'denied' }); resolve({ allowed: false, mode: 'deny' }); }
    });
  });
}

module.exports = { CATEGORIES, MODES, loadPolicy, effectiveMode, set, reset, audit, evaluate, promptApproval };
