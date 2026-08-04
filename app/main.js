'use strict';
// AgentStack desktop app — main process.
// Merges Hermes (brain) + OpenClaw (hands) + Obsidian (memory) plus providers,
// councils, permissions, tasks, security, and cost into one polished GUI.
// All backend work is delegated to the lib/ modules in this repo.

const { app, BrowserWindow, ipcMain, shell } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const HOME = os.homedir();
const HERMES_HOME = process.env.HERMES_HOME || path.join(HOME, 'AppData', 'Local', 'hermes');
const VAULT = process.env.STACK_VAULT || path.join(HOME, 'Documents', 'Obsidian Vault');

// Resolve repo root. In a packaged app (electron-packager -> resources/app) the
// lib/council/modules/etc. folders are copied into __dirname. In dev they live
// one level up from app/.
const hasLibLocal = fs.existsSync(path.join(__dirname, 'lib'));
const REPO = hasLibLocal ? __dirname : path.join(__dirname, '..');

// Load the real backend. Wrap so missing/corrupt modules never crash the shell.
function loadLib(name) {
  try { return require(path.join(REPO, 'lib', name)); } catch (e) { return null; }
}
const paths = loadLib('paths');
const tasks = loadLib('tasks');
const secrets = loadLib('secrets');
const perms = loadLib('permissions');
const compat = loadLib('compatibility');
const security = loadLib('security');
const events = loadLib('events');
const registry = loadLib(path.join('providers', 'registry'));

let mainWindow = null;

// ------------------------------------------------------------ detection ----
function detectHermes() {
  const cands = [
    path.join(HERMES_HOME, 'hermes-agent', 'venv', 'Scripts', 'hermes.exe'),
    path.join(HERMES_HOME, 'venv', 'Scripts', 'hermes.exe'),
    path.join(HERMES_HOME, 'hermes-agent', 'venv', 'bin', 'hermes'),
  ];
  for (const c of cands) if (fs.existsSync(c)) return c;
  try {
    const r = require('child_process').spawnSync(process.platform === 'win32' ? 'where' : 'which', ['hermes'], { encoding: 'utf8' });
    if (r.status === 0 && r.stdout.trim()) return r.stdout.trim().split('\n')[0];
  } catch {}
  return null;
}

function detectOpenClaw() {
  const cands = [
    path.join(process.env.APPDATA || path.join(HOME, 'AppData', 'Roaming'), 'npm', 'node_modules', 'openclaw', 'openclaw.mjs'),
    path.join(HOME, 'AppData', 'Roaming', 'npm', 'node_modules', 'openclaw', 'openclaw.mjs'),
    path.join(HOME, '.npm-global', 'lib', 'node_modules', 'openclaw', 'openclaw.mjs'),
  ];
  for (const c of cands) if (fs.existsSync(c)) return c;
  try {
    const r = require('child_process').spawnSync(process.platform === 'win32' ? 'where' : 'which', ['openclaw'], { encoding: 'utf8' });
    if (r.status === 0 && r.stdout.trim()) return r.stdout.trim().split('\n')[0];
  } catch {}
  return null;
}

function detectVault() {
  return fs.existsSync(path.join(VAULT, 'AGENTS.md')) || fs.existsSync(VAULT) ? VAULT : null;
}

function getProviderStatus() {
  if (!secrets) return { provider: 'unknown', hasKey: false, detail: 'secrets module unavailable' };
  const cfg = secrets.loadProviderConfig();
  const list = (registry && registry.list) ? registry.list() : [];
  const configured = list.filter((p) => registry.configuredStatus(p) !== 'not_configured');
  return {
    provider: configured[0] || null,
    count: configured.length,
    configured,
    detail: (cfg && cfg.providers ? Object.keys(cfg.providers) : []).join(', ') || 'none configured',
  };
}

function systemStatus() {
  const compatReport = compat && compat.report ? compat.report() : null;
  const incompat = compatReport ? compatReport.checks.filter((c) => c.compatible === false).map((c) => c.component) : [];
  const asked = events && events.recent && events.recent(8) || [];
  return {
    hermes: detectHermes(),
    openclaw: detectOpenClaw(),
    vault: detectVault(),
    provider: getProviderStatus(),
    compat: compatReport ? { overall: compatReport.overall, checks: compatReport.checks } : null,
    incompat,
    hermesHome: HERMES_HOME,
    events: asked,
  };
}

// --------------------------------------------------------------- exec ----
function runAsync(cmd, args, opts = {}) {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, { encoding: 'utf8', ...opts });
    let out = '', err = '';
    const to = setTimeout(() => { try { child.kill(); } catch {} }, opts.timeout || 180000);
    child.stdout.on('data', (d) => { out += d; });
    child.stderr.on('data', (d) => { err += d; });
    child.on('close', (code) => { clearTimeout(to); resolve({ code, out, err }); });
    child.on('error', (e) => { clearTimeout(to); resolve({ code: -1, out, err: String(e) }); });
  });
}

function ensureHermesEnvLoaded(env = {}) {
  // Load OPENROUTER_API_KEY from HERMES_HOME/.env if present so child hermes
  // calls can authenticate.
  if (env.OPENROUTER_API_KEY) return env;
  try {
    const envf = path.join(HERMES_HOME, '.env');
    if (fs.existsSync(envf)) {
      for (const line of fs.readFileSync(envf, 'utf8').split('\n')) {
        const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.+)\s*$/);
        if (m && m[1] === 'OPENROUTER_API_KEY' && m[2] && !/your_|xxx|replace/i.test(m[2])) {
          env.OPENROUTER_API_KEY = m[2].trim();
        }
      }
    }
  } catch {}
  return env;
}

function runHermesChat(prompt, model) {
  const bin = detectHermes();
  if (!bin) return Promise.resolve({ code: 1, out: '', err: 'Hermes not found' });
  const args = ['chat', '-Q', '-q', prompt, '--provider', 'openrouter', '--model', model || 'openai/gpt-4o-mini', '--source', 'agentstack-app'];
  const env = ensureHermesEnvLoaded({ ...process.env });
  return runAsync(bin, args, { timeout: 240000, env });
}

// ------------------------------------------------------------- IPC ----
ipcMain.handle('system:status', () => systemStatus());
ipcMain.handle('system:open', (_e, target) => {
  const st = systemStatus();
  if (target === 'vault' && st.vault) shell.openPath(st.vault);
  if (target === 'hermesHome' && st.hermesHome) shell.openPath(st.hermesHome);
  return true;
});
ipcMain.handle('system:openExternal', (_e, url) => { shell.openExternal(url); return true; });

ipcMain.handle('app:ask', async (_e, prompt, model) => {
  if (!prompt) return { ok: false, ok2: false, out: '', hint: 'no prompt' };
  if (events) events.emit('agent.started', { agent: 'hermes', source: 'app' });
  const r = await runHermesChat(prompt, model);
  const ok = r.code === 0;
  if (events) events.emit(ok ? 'task.completed' : 'task.failed', { agent: 'hermes', ok });
  return { ok, out: r.out, err: r.err };
});

ipcMain.handle('app:council', async (_e, prompt) => {
  if (!prompt) return { ok: false, out: '', err: 'no prompt' };
  const py = path.join(REPO, 'council', 'council_v2.py');
  if (!fs.existsSync(py)) return { ok: false, out: '', err: 'council not found in package' };
  const pyCmd = process.platform === 'win32' ? 'python' : 'python3';
  const r = await runAsync(pyCmd, [py, prompt, '--cheap-chairman', '--domain', 'general'], { timeout: 240000, env: ensureHermesEnvLoaded({ ...process.env }) });
  return { ok: r.code === 0, out: r.out, err: r.err };
});

// ---- tasks (real durable store) ----
ipcMain.handle('tasks:list', () => {
  if (!tasks) return { ok: false, data: 'tasks module unavailable' };
  try { return { ok: true, data: tasks.list() }; } catch (e) { return { ok: false, err: String(e) }; }
});
ipcMain.handle('tasks:add', (_e, title, extra) => {
  if (!tasks) return { ok: false, data: 'tasks module unavailable' };
  try {
    const t = tasks.add({ title, description: (extra && extra.description) || '', tags: (extra && extra.tags) || [] });
    return { ok: true, data: t };
  } catch (e) { return { ok: false, err: String(e) }; }
});
ipcMain.handle('tasks:complete', (_e, id) => {
  if (!tasks) return { ok: false, data: 'unavailable' };
  try { const t = tasks.complete(id); return { ok: !!t, data: t }; } catch (e) { return { ok: false, err: String(e) }; }
});
ipcMain.handle('tasks:reopen', (_e, id) => {
  if (!tasks) return { ok: false, data: 'unavailable' };
  try { const t = tasks.reopen(id); return { ok: !!t, data: t }; } catch (e) { return { ok: false, err: String(e) }; }
});
ipcMain.handle('tasks:remove', (_e, id) => {
  if (!tasks) return { ok: false, data: 'unavailable' };
  try { const ok = tasks.remove(id); return { ok, data: id }; } catch (e) { return { ok: false, err: String(e) }; }
});
ipcMain.handle('tasks:export', () => {
  if (!tasks) return { ok: false, data: 'unavailable' };
  try { const md = tasks.exportMarkdown ? tasks.exportMarkdown() : String(tasks.toMarkdown ? tasks.toMarkdown(tasks.list()) : ''); return { ok: true, data: md }; } catch (e) { return { ok: false, err: String(e) }; }
});

// ---- notes (write to vault) ----
ipcMain.handle('notes:add', (_e, text) => {
  if (!text) return { ok: false, data: 'no text' };
  const noteDir = path.join(VAULT, 'Agent Hub', 'Inbox');
  try { fs.mkdirSync(noteDir, { recursive: true }); } catch {}
  const stamp = new Date().toISOString().slice(0, 10);
  const file = path.join(noteDir, `quick-note-${Date.now()}.md`);
  try { fs.writeFileSync(file, `# Quick note · ${stamp}\n\n${text}\n`); return { ok: true, data: file }; } catch (e) { return { ok: false, err: String(e) }; }
});

// ---- providers ----
ipcMain.handle('providers:list', () => {
  if (!registry || !registry.list) return { ok: false, data: 'providers module unavailable' };
  try {
    const list = registry.list();
    return { ok: true, data: list.map((p) => ({ name: p, configured: registry.configuredStatus(p) !== 'not_configured' })) };
  } catch (e) { return { ok: false, err: String(e) }; }
});
ipcMain.handle('providers:status', () => {
  try { return { ok: true, data: getProviderStatus() }; } catch (e) { return { ok: false, err: String(e) }; }
});

// ---- permissions ----
ipcMain.handle('perms:list', () => {
  if (!perms) return { ok: false, data: 'permissions module unavailable' };
  try {
    const policy = perms.loadPolicy();
    return { ok: true, data: policy.policy || policy || {} };
  } catch (e) { return { ok: false, err: String(e) }; }
});
ipcMain.handle('perms:audit', () => {
  if (!perms) return { ok: false, data: [] };
  try { return { ok: true, data: perms.audit() }; } catch (e) { return { ok: false, err: String(e) }; }
});

// ---- security ----
ipcMain.handle('security:scan', async () => {
  if (!security) return { ok: false, data: 'security module unavailable' };
  try {
    return await Promise.resolve(security.full(REPO));
  } catch (e) { return { ok: false, err: String(e) }; }
});

// ---- cost ----
ipcMain.handle('cost:report', (_e, days) => {
  const bin = path.join(REPO, 'council', 'cost_ledger.py');
  if (!fs.existsSync(bin)) return { ok: false, data: 'cost ledger not in package' };
  const pyCmd = process.platform === 'win32' ? 'python' : 'python3';
  return runAsync(pyCmd, [bin, 'report', '--days', String(days || 7)], { timeout: 60000 }).then((r) => ({ ok: r.code === 0, out: r.out, err: r.err }));
});

// ---- events ----
ipcMain.handle('events:recent', () => {
  if (!events) return { ok: true, data: [] };
  try { return { ok: true, data: events.recent(30) }; } catch (e) { return { ok: false, data: [] }; }
});

// ------------------------------------------------------------- window ----
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 780,
    minWidth: 920,
    minHeight: 640,
    title: 'AgentStack',
    backgroundColor: '#0b1020',
    icon: path.join(__dirname, 'logo.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.setMenuBarVisibility(false);
  mainWindow.loadFile(path.join(__dirname, 'index.html'));
  mainWindow.on('closed', () => { mainWindow = null; });
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
