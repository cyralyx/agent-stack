'use strict';
// AgentStack desktop app — main process.
// Merges Hermes (brain) + OpenClaw (hands) + Obsidian (memory) into one clean
// GUI. Hard-gated: the app will NOT run unless all three are present.

const { app, BrowserWindow, ipcMain, shell } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const HOME = os.homedir();
const HERMES_HOME = process.env.HERMES_HOME || path.join(HOME, 'AppData', 'Local', 'hermes');
const VAULT = process.env.STACK_VAULT || path.join(HOME, 'Documents', 'Obsidian Vault');

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

function getTokenStatus() {
  const envf = path.join(HERMES_HOME, '.env');
  if (!fs.existsSync(envf)) return { set: false, file: null };
  const content = fs.readFileSync(envf, 'utf8');
  const has = content.includes('OPENROUTER_API_KEY=') && !content.includes('OPENROUTER_API_KEY=your_') && !content.includes('OPENROUTER_API_KEY=\n');
  return { set: has, file: envf };
}

function systemStatus() {
  return {
    hermes: detectHermes(),
    openclaw: detectOpenClaw(),
    vault: detectVault(),
    token: getTokenStatus(),
    hermesHome: HERMES_HOME,
  };
}

// --------------------------------------------------------------- exec ----
function runAsync(cmd, args, opts = {}) {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, { encoding: 'utf8', ...opts });
    let out = '', err = '';
    const to = setTimeout(() => { try { child.kill(); } catch {} }, opts.timeout || 120000);
    child.stdout.on('data', (d) => { out += d; });
    child.stderr.on('data', (d) => { err += d; });
    child.on('close', (code) => { clearTimeout(to); resolve({ code, out, err }); });
    child.on('error', (e) => { clearTimeout(to); resolve({ code: -1, out, err: String(e) }); });
  });
}

function runHermesChat(prompt, model) {
  const bin = detectHermes();
  if (!bin) return Promise.resolve({ code: 1, out: '', err: 'Hermes not found' });
  const args = ['chat', '-Q', '-q', prompt, '--provider', 'openrouter', '--model', model || 'openai/gpt-4o-mini', '--source', 'agentstack-app'];
  return runAsync(bin, args, { timeout: 180000 });
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
ipcMain.handle('app:ask', async (_e, prompt) => {
  const r = await runHermesChat(prompt);
  return { ok: r.code === 0, out: r.out, err: r.err };
});
ipcMain.handle('app:council', async (_e, prompt) => {
  const repo = path.join(__dirname, '..');
  const py = path.join(repo, 'council', 'council_v2.py');
  if (!fs.existsSync(py)) return { ok: false, out: '', err: 'council not found' };
  const pyCmd = process.platform === 'win32' ? 'python' : 'python3';
  const r = await runAsync(pyCmd, [py, prompt, '--cheap-chairman'], { timeout: 180000 });
  return { ok: r.code === 0, out: r.out, err: r.err };
});
ipcMain.handle('app:todo', async (_e, action, arg) => {
  const tasksFile = path.join(VAULT, 'Agent Hub', 'Tasks.md');
  try { fs.mkdirSync(path.dirname(tasksFile), { recursive: true }); } catch {}
  if (!fs.existsSync(tasksFile)) fs.writeFileSync(tasksFile, '# Tasks\n\n');
  let lines = fs.readFileSync(tasksFile, 'utf8').split('\n');
  if (action === 'list') {
    const open = lines.filter((l) => /^-\s*\[\s*\]/.test(l));
    return { ok: true, data: open.join('\n') || 'No open tasks' };
  }
  if (action === 'add') {
    const id = lines.filter((l) => /^-\s*\[\s*\]\s*\d+\./.test(l)).length + 1;
    lines.push(`- [ ] ${id}. ${arg}`);
    fs.writeFileSync(tasksFile, lines.join('\n'));
    return { ok: true, data: `task ${id} added` };
  }
  if (action === 'done') {
    const n = parseInt(arg, 10);
    let hit = 0;
    lines = lines.map((l) => {
      const m = l.match(/^-\s*\[\s*\]\s*(\d+)\./);
      if (m && parseInt(m[1], 10) === n) { hit = 1; return l.replace('[ ]', '[x]'); }
      return l;
    });
    fs.writeFileSync(tasksFile, lines.join('\n'));
    return { ok: hit === 1, data: hit ? `task ${n} done` : `no task ${n}` };
  }
  return { ok: false, data: 'unknown action' };
});

// ------------------------------------------------------------- window ----
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 740,
    minWidth: 860,
    minHeight: 600,
    title: 'AgentStack',
    backgroundColor: '#0f172a',
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
