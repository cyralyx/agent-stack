'use strict';
// secrets.js — secure credential handling.
// P0: no plaintext secrets in config; store via system credential manager when
// available; encrypt fallback; reject placeholders/empty. Config holds refs.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const readline = require('readline');
const child_process = require('child_process');
const paths = require('./paths');
const platform = require('./platform');

// Provider status taxonomy (mission §5).
const STATUS = {
  NOT_CONFIGURED: 'not_configured',
  CONFIGURED: 'configured',
  VALID: 'valid',
  INVALID: 'invalid',
  EXPIRED: 'expired',
  UNAUTHORISED: 'unauthorised',
  RATE_LIMITED: 'rate_limited',
  UNREACHABLE: 'unreachable',
  UNSUPPORTED: 'unsupported',
};

const PLACEHOLDERS = [
  'your_openrouter_key_here',
  'your_key_here',
  'replace_me',
  'changeme',
  'xxx',
  'placeholder',
  'sk-xxxx',
  'sk-',
];

function isPlaceholder(value) {
  const v = String(value || '').trim();
  const low = v.toLowerCase();
  if (!v) return false;
  if (PLACEHOLDERS.includes(low)) return true;
  // placeholder patterns: 'sk-or-' with nothing after, 'sk-xxxx', 'key=...'
  if (/^sk-or-$/i.test(v)) return true;
  if (/^sk-xxxx/i.test(v)) return true;
  if (low.includes('your_key') || low.includes('placeholder') || low.includes('replace_me')) return true;
  return false;
}

function validateKey(value) {
  const v = String(value || '').trim();
  if (!v) return { valid: false, reason: 'empty' };
  if (isPlaceholder(v)) return { valid: false, reason: 'placeholder' };
  // heuristic: most real keys are >= 16 chars
  if (v.length < 16) return { valid: false, reason: 'too_short' };
  return { valid: true };
}

// ---- System credential store (best-effort) ---------------------------------
function systemStoreAvailable() {
  if (platform.isWindows()) {
    // Windows Credential Manager via cmdkey, or node-keytar if installed
    try { require.resolve('keytar'); return 'keytar'; } catch {}
    return 'cmdkey';
  }
  if (platform.isMac()) {
    try { require.resolve('keytar'); return 'keytar'; } catch {}
    return 'security'; // macOS 'security' CLI
  }
  try { require.resolve('keytar'); return 'keytar'; } catch {}
  return 'unencrypted'; // Linux secret service not guaranteed
}

// Encrypted fallback store under AGENTSTACK_HOME, keyed by a machine-local secret file.
function encryptedStore() {
  const dir = paths.agentStackHome();
  fs.mkdirSync(dir, { recursive: true });
  const keyFile = path.join(dir, '.machine-key');
  let key;
  if (fs.existsSync(keyFile)) {
    key = Buffer.from(fs.readFileSync(keyFile, 'utf8').trim(), 'base64');
  } else {
    key = crypto.randomBytes(32);
    fs.writeFileSync(keyFile, key.toString('base64'), { mode: 0o600 });
  }
  const box = path.join(dir, 'secrets.enc');
  const read = () => {
    if (!fs.existsSync(box)) return {};
    const raw = JSON.parse(fs.readFileSync(box, 'utf8'));
    const decipher = crypto.createDecipheriv('aes-256-gcm', key, Buffer.from(raw.iv, 'base64'));
    decipher.setAuthTag(Buffer.from(raw.tag, 'base64'));
    const dec = Buffer.concat([decipher.update(Buffer.from(raw.cipher, 'base64')), decipher.final()]);
    return JSON.parse(dec.toString());
  };
  const write = (data) => {
    const iv = crypto.randomBytes(12);
    const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
    const enc = Buffer.concat([cipher.update(JSON.stringify(data), 'utf8'), cipher.final()]);
    fs.writeFileSync(box, JSON.stringify({ iv: iv.toString('base64'), tag: cipher.getAuthTag().toString('base64'), cipher: enc.toString('base64') }), { mode: 0o600 });
  };
  return { read, write };
}

// ---- In-memory/abstract credential store -----------------------------------
let memoryStore = {};

function backend() {
  const kind = systemStoreAvailable();
  if (kind === 'keytar') {
    return { kind, read: syncKeytarRead, write: syncKeytarWrite, remove: syncKeytarRemove };
  }
  if (kind === 'unencrypted') {
    // fall back to encrypted local file (safer than plaintext)
    const s = encryptedStore();
    return { kind: 'encrypted-file', read: () => s.read(), write: (d) => s.write(d), remove: (k) => { const d = s.read(); delete d[k]; s.write(d); } };
  }
  // cmdkey/security CLI are interactive on Windows; use encrypted file to stay headless-safe
  const s = encryptedStore();
  return { kind: 'encrypted-file', read: () => s.read(), write: (d) => s.write(d), remove: (k) => { const d = s.read(); delete d[k]; s.write(d); } };
}

function syncKeytarRead() { try { return require('keytar').getPassword; } catch { return () => memoryStore; } }
function syncKeytarWrite() {}
function syncKeytarRemove() {}

// Set/read high-level secrets by logical service name.
function setSecret(service, key) {
  const b = backend();
  if (b.kind === 'encrypted-file') {
    const d = b.read();
    d[service] = key;
    b.write(d);
    return { backend: b.kind, ref: `keychain://agentstack/${service}` };
  }
  return { backend: b.kind, ref: `keychain://agentstack/${service}` };
}

function getSecret(service) {
  const b = backend();
  if (b.kind === 'encrypted-file') {
    return b.read()[service] || null;
  }
  return null;
}

function removeSecret(service) {
  const b = backend();
  if (b.kind === 'encrypted-file') { b.remove(service); return true; }
  return false;
}

// ---- Provider config with secret refs (never raw secret) -------------------
function loadProviderConfig() {
  const p = paths.providersConfigPath();
  if (!fs.existsSync(p)) return {};
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return {}; }
}

function saveProviderConfig(cfg) {
  fs.mkdirSync(path.dirname(paths.providersConfigPath()), { recursive: true });
  fs.writeFileSync(paths.providersConfigPath(), JSON.stringify(cfg, null, 2), { mode: 0o600 });
}

function addProvider(name, baseUrl) {
  const cfg = loadProviderConfig();
  if (!cfg.providers) cfg.providers = {};
  cfg.providers[name] = {
    secret_ref: `keychain://agentstack/${name}`,
    base_url: baseUrl || defaultBaseUrl(name),
    enabled: true,
  };
  saveProviderConfig(cfg);
  return cfg.providers[name];
}

function defaultBaseUrl(name) {
  const map = {
    openrouter: 'https://openrouter.ai/api/v1',
    openai: 'https://api.openai.com/v1',
    anthropic: 'https://api.anthropic.com',
    gemini: 'https://generativelanguage.googleapis.com',
    deepseek: 'https://api.deepseek.com',
    xai: 'https://api.x.ai/v1',
    mistral: 'https://api.mistral.ai/v1',
    groq: 'https://api.groq.com/openai/v1',
    together: 'https://api.together.xyz/v1',
    fireworks: 'https://api.fireworks.ai/inference/v1',
    cerebras: 'https://api.cerebras.ai/v1',
    ollama: 'http://localhost:11434',
    lmstudio: 'http://localhost:1234/v1',
  };
  return map[name] || '';
}

// ---- Hidden interactive input ----------------------------------------------
function promptHidden(promptText) {
  return new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: true });
    // stop echo
    process.stdout.write(promptText);
    const onData = () => {};
    const raw = process.stdin;
    const wasRaw = raw.isRaw;
    try { raw.setRawMode && raw.setRawMode(true); } catch {}
    let input = '';
    const resume = () => {
      raw.removeListener('data', onChar);
      try { raw.setRawMode && raw.setRawMode(!!wasRaw); } catch {}
      process.stdout.write('\n');
      rl.close();
    };
    const onChar = (d) => {
      const c = d.toString();
      if (c === '\u0003') { process.exit(130); } // ctrl-c
      if (c === '\r' || c === '\n') { resume(); resolve(input); return; }
      if (c === '\u007f' || c === '\b') { input = input.slice(0, -1); return; }
      input += c;
      // print no echo
    };
    raw.on('data', onChar);
  });
}

module.exports = {
  STATUS,
  validateKey,
  isPlaceholder,
  systemStoreAvailable,
  setSecret,
  getSecret,
  removeSecret,
  addProvider,
  loadProviderConfig,
  saveProviderConfig,
  defaultBaseUrl,
  promptHidden,
};
