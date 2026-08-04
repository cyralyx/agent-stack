'use strict';
// platform.js — central platform detection + tool resolution.
// P0: stop hard-coding 'python', bash availability, npm global locations.
const os = require('os');
const child_process = require('child_process');

const PLATFORM = os.platform(); // 'win32' | 'darwin' | 'linux' | ...

function isWindows() { return PLATFORM === 'win32'; }
function isMac() { return PLATFORM === 'darwin'; }
function isLinux() { return PLATFORM === 'linux'; }

// Resolve a command allowing .exe/.cmd/.bat on Windows, plain on POSIX.
function resolveCommand(name) {
  const candidates = isWindows()
    ? [name, `${name}.exe`, `${name}.cmd`, `${name}.bat`, `${name}.ps1`]
    : [name];
  for (const c of candidates) {
    try {
      const r = child_process.spawnSync(
        isWindows() ? 'where' : 'which', [c],
        { encoding: 'utf8', shell: false }
      );
      if (r.status === 0 && r.stdout && r.stdout.trim()) {
        return r.stdout.trim().split(/\r?\n/)[0];
      }
    } catch { /* continue */ }
  }
  return null;
}

// Resolve the Python interpreter: prefer python3 on POSIX, python on Windows,
// but fall back gracefully. Never assume the bare name works.
function resolvePython() {
  const order = isWindows()
    ? ['py', 'python', 'python3']
    : ['python3', 'python'];
  for (const c of order) {
    const resolved = resolveCommand(c);
    if (resolved) {
      try {
        const r = child_process.spawnSync(c, ['--version'], { encoding: 'utf8', shell: false, timeout: 5000 });
        if (r.status === 0) return resolveCommand(c);
      } catch { /* try next */ }
    }
  }
  return null;
}

// Resolve Node/npm.
function resolveNode() { return resolveCommand('node'); }
function resolveNpm() { return resolveCommand('npm'); }

// Resolve the system package manager for a platform (informational).
function packageManager() {
  if (isWindows()) return 'npm';
  if (isMac()) return 'npm'; // or brew
  return 'npm'; // or apt/apk
}

module.exports = {
  PLATFORM,
  isWindows,
  isMac,
  isLinux,
  resolveCommand,
  resolvePython,
  resolveNode,
  resolveNpm,
  packageManager,
};
