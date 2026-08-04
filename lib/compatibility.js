'use strict';
// compatibility.js — compatibility registry + checks (P0).
// Track minimum/tested versions of Hermes, OpenClaw, Node, Python, OS, providers.
const fs = require('fs');
const path = require('path');
const child_process = require('child_process');
const platform = require('./platform');
const paths = require('./paths');

// Must match the config/agentstack.compatibility.yaml intent.
const REGISTRY = {
  hermes: { minimum: '0.18.0', tested: ['0.18.0'] },
  openclaw: { minimum: '1.0.0', tested: ['1.0.0'] },
  agentstack: { bridge_protocol: '1.0' },
  node: { minimum: '20.0.0' },
  python: { minimum: '3.9.0' },
};

function versionAtLeast(actual, min) {
  if (!actual) return false;
  const norm = (v) => v.split(/[.-]/).map((n) => parseInt(n, 10) || 0);
  const a = norm(String(actual).replace(/^v/, ''));
  const m = norm(min);
  for (let i = 0; i < Math.max(a.length, m.length); i++) {
    const av = a[i] || 0, mv = m[i] || 0;
    if (av < mv) return false;
    if (av > mv) return true;
  }
  return true;
}

function checkNode() {
  const v = (process.version || '').replace(/^v/, '');
  return { component: 'node', version: v, compatible: versionAtLeast(v, REGISTRY.node.minimum) };
}

function checkPython() {
  const py = platform.resolvePython();
  if (!py) return { component: 'python', version: null, compatible: false, message: 'python not found' };
  try {
    const r = child_process.spawnSync(py, ['--version'], { encoding: 'utf8', timeout: 5000 });
    const m = (r.stdout || r.stderr || '').match(/(\d+\.\d+\.\d+)/);
    const v = m ? m[1] : null;
    return { component: 'python', version: v, compatible: v ? versionAtLeast(v, REGISTRY.python.minimum) : false };
  } catch (e) {
    return { component: 'python', version: null, compatible: false, message: e.message };
  }
}

function checkHermes() {
  // detect hermes executable
  const home = paths.hermesHome();
  const cands = [
    path.join(home, 'hermes-agent', 'venv', 'Scripts', 'hermes.exe'),
    path.join(home, 'venv', 'Scripts', 'hermes.exe'),
    path.join(home, 'hermes-agent', 'venv', 'bin', 'hermes'),
  ];
  const bin = cands.find((c) => fs.existsSync(c)) || platform.resolveCommand('hermes');
  if (!bin) return { component: 'hermes', version: null, compatible: false, message: 'hermes not found' };
  try {
    const r = child_process.spawnSync(bin, ['--version'], { encoding: 'utf8', timeout: 5000 });
    const m = (r.stdout || r.stderr || '').match(/(\d+\.\d+\.\d+)/);
    const v = m ? m[1] : null;
    return { component: 'hermes', version: v || 'unknown', compatible: v ? versionAtLeast(v, REGISTRY.hermes.minimum) : null, path: bin };
  } catch (e) {
    return { component: 'hermes', version: null, compatible: null, message: e.message, path: bin };
  }
}

function checkOpenClaw() {
  const bin = platform.resolveCommand('openclaw');
  const home = paths.agentStackHome();
  const cands = [
    path.join(process.env.APPDATA || '', 'npm', 'node_modules', 'openclaw', 'openclaw.mjs'),
    path.join(require('os').homedir(), 'AppData', 'Roaming', 'npm', 'node_modules', 'openclaw', 'openclaw.mjs'),
  ];
  const found = bin || cands.find((c) => fs.existsSync(c));
  if (!found) return { component: 'openclaw', version: null, compatible: false, message: 'openclaw not found' };
  return { component: 'openclaw', version: 'unknown', compatible: null, path: found, message: 'version not resolvable offline' };
}

function report() {
  return {
    registry: REGISTRY,
    checks: [
      checkNode(),
      checkPython(),
      checkHermes(),
      checkOpenClaw(),
      { component: 'os', version: `${platform.PLATFORM}`, compatible: true },
      { component: 'bridge_protocol', version: REGISTRY.agentstack.bridge_protocol, compatible: true },
    ],
  };
}

module.exports = { REGISTRY, versionAtLeast, checkNode, checkPython, checkHermes, checkOpenClaw, report };
