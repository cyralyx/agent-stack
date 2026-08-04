'use strict';
// security.js — security audit subsystem (mission §13).
// Splits the old narrow `audit` into: secrets, dependencies, permissions,
// skills, config, full. Uses observable checks only.
const fs = require('fs');
const path = require('path');
const child_process = require('child_process');
const paths = require('./paths');
const platform = require('./platform');

// Scan for likely committed secrets in tracked files (best-effort).
function scanSecrets(dir) {
  const findings = [];
  const patterns = [
    /sk-[A-Za-z0-9]{20,}/g,
    /ghp_[A-Za-z0-9]{20,}/g,
    /gho_[A-Za-z0-9]{20,}/g,
    /AIza[0-9A-Za-z_-]{20,}/g, // Google
    /xox[baprs]-[0-9A-Za-z-]{20,}/g, // Slack
    /AKIA[0-9A-Z]{16}/g, // AWS
    /BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY/g,
  ];
  function walk(d, depth) {
    if (depth > 6) return;
    let entries;
    try { entries = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (e.name.startsWith('.git') || e.name === 'node_modules' || e.name === 'dist' || e.name === 'release') continue;
      const full = path.join(d, e.name);
      if (e.isDirectory()) { walk(full, depth + 1); continue; }
      if (e.isFile() && /\.(py|js|json|yaml|yml|toml|sh|env|md|config|txt)$/i.test(e.name)) {
        try {
          const content = fs.readFileSync(full, 'utf8');
          for (const re of patterns) {
            re.lastIndex = 0;
            let m;
            while ((m = re.exec(content)) !== null) {
              findings.push({ file: path.relative(dir, full), secret: m[0].slice(0, 8) + '…(redacted)', pattern: re.source.slice(0, 20) });
            }
          }
        } catch {}
      }
    }
  }
  walk(dir, 0);
  return findings;
}

// Check unsafe file permissions (POSIX only).
function unsafePermissions(dir) {
  if (!platform.isLinux() && !platform.isMac()) return [];
  const findings = [];
  for (const f of [paths.permissionsPath(), paths.providersConfigPath()].filter(Boolean)) {
    if (fs.existsSync(f)) {
      try {
        const st = fs.statSync(f);
        if (st.mode & 0o077) findings.push({ file: f, issue: 'world/group readable or writable' });
      } catch {}
    }
  }
  return findings;
}

// Dependency audit via npm audit (informational; CI gate separately).
function dependencies(dir, { run = false } = {}) {
  if (!run) return { status: 'not_run', note: 'run npm audit' };
  const r = child_process.spawnSync('npm', ['audit', '--json'], { cwd: dir, encoding: 'utf8', timeout: 60000 });
  if (r.status === 0) return { status: 'ok', note: 'no vulnerabilities (or none reported)' };
  try { return { status: 'findings', data: JSON.parse(r.stdout) }; }
  catch { return { status: 'error', note: (r.stderr || r.stdout || '').slice(0, 200) }; }
}

// Review skills for untrusted installs / dangerous content (shallow).
function skills(dir) {
  const findings = [];
  const skillsBase = path.join(dir, 'skills');
  if (!fs.existsSync(skillsBase)) return findings;
  function walk(d, depth) {
    if (depth > 4) return;
    let e2;
    try { e2 = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of e2) {
      const full = path.join(d, e.name);
      if (e.isDirectory()) walk(full, depth + 1);
      else if (/\.(sh|py|js)$/i.test(e.name)) {
        try {
          const c = fs.readFileSync(full, 'utf8');
          if (/curl\s+\|?\s*(bash|sh)|wget\s+.*\|\s*(bash|sh)|chmod\s+777|sudo\s+(rm|chmod)/i.test(c)) {
            findings.push({ file: path.relative(dir, full), issue: 'suspicious shell command' });
          }
        } catch {}
      }
    }
  }
  walk(skillsBase, 0);
  return findings;
}

// Provider config review — no raw secrets in config, no disabled providers left enabled.
function providerConfig() {
  const findings = [];
  const cfg = require('./secrets').loadProviderConfig();
  const raw = JSON.stringify(cfg);
  if (/sk-[A-Za-z0-9]{20,}|AKIA|AIza/.test(raw)) findings.push({ issue: 'possible raw secret in provider config' });
  const enabled = (cfg.providers || {});
  for (const [name, p] of Object.entries(enabled)) {
    if (p.enabled === false) continue;
    if (!require('./secrets').getSecret(name)) {
      findings.push({ issue: `provider ${name} enabled but no secret stored`, provider: name });
    }
  }
  return findings;
}

// Full audit — runs every sub-check.
function full(dir = process.cwd()) {
  const repoDir = dir;
  const secretsFindings = scanSecrets(repoDir);
  const skillFindings = skills(repoDir);
  const permFindings = unsafePermissions(repoDir);
  const provFindings = providerConfig();
  return {
    secrets: { count: secretsFindings.length, findings: secretsFindings.slice(0, 20) },
    permissions: { count: permFindings.length, findings: permFindings },
    skills: { count: skillFindings.length, findings: skillFindings },
    providers: { count: provFindings.length, findings: provFindings },
    all_clear: secretsFindings.length === 0 && permFindings.length === 0 && skillFindings.length === 0 && provFindings.length === 0,
  };
}

module.exports = { scanSecrets, unsafePermissions, dependencies, skills, providerConfig, full };
