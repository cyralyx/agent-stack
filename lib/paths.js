'use strict';
// paths.js — platform-aware configuration/state/data directory resolution.
// P0: stop hard-coding 'AppData/Local/hermes' and 'Documents/Obsidian Vault'.
const path = require('path');
const os = require('os');
const fs = require('fs');
const platform = require('./platform');

// Root of this repo (lib/..).
const REPO_ROOT = path.resolve(__dirname, '..');

// Detect hermest home per-platform.
function hermesHome() {
  if (process.env.HERMES_HOME) return process.env.HERMES_HOME;
  if (platform.isWindows()) {
    return path.join(os.homedir(), 'AppData', 'Local', 'hermes');
  }
  if (platform.isMac()) {
    return path.join(os.homedir(), 'Library', 'Application Support', 'Hermes');
  }
  // Linux
  return path.join(os.homedir(), '.config', 'hermes');
}

// AgentStack's own state directory (not Hermes').
function agentStackHome() {
  if (process.env.AGENTSTACK_HOME) return process.env.AGENTSTACK_HOME;
  if (platform.isWindows()) {
    return path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local'), 'Cyralyx', 'AgentStack');
  }
  if (platform.isMac()) {
    return path.join(os.homedir(), 'Library', 'Application Support', 'AgentStack');
  }
  // Linux: XDG_CONFIG_HOME or ~/.config
  const xdg = process.env.XDG_CONFIG_HOME || path.join(os.homedir(), '.config');
  return path.join(xdg, 'agentstack');
}

function dataHome() { return path.join(agentStackHome(), 'data'); }
function configHome() { return path.join(agentStackHome(), 'config'); }
function cacheHome() { return path.join(agentStackHome(), 'cache'); }
function dbPath() { return path.join(dataHome(), 'agentstack.db'); }
function tasksDbPath() { return path.join(dataHome(), 'tasks.db'); }
function permissionsPath() { return path.join(configHome(), 'permissions.json'); }
function providersConfigPath() { return path.join(configHome(), 'providers.json'); }
function configFilePath() { return path.join(configHome(), 'agentstack.json'); }

// Vault / workspace: allow override, otherwise a reasonable default per platform.
function defaultWorkspace() {
  if (process.env.STACK_VAULT) return process.env.STACK_VAULT;
  if (platform.isWindows()) {
    return path.join(os.homedir(), 'Documents', 'Obsidian Vault');
  }
  return path.join(os.homedir(), 'Documents', 'Obsidian Vault');
}

// First-run workspace selection: find an existing vault or mark missing.
function workspace(overrides) {
  const chosen = (overrides && overrides.vault) || defaultWorkspace();
  return {
    path: chosen,
    exists: fs.existsSync(chosen),
    isObsidian: fs.existsSync(path.join(chosen, '.obsidian')) || fs.existsSync(path.join(chosen, 'AGENTS.md')),
  };
}

// Ensure all state dirs exist; returns the base.
function ensureDirs() {
  for (const d of [agentStackHome(), dataHome(), configHome(), cacheHome()]) {
    fs.mkdirSync(d, { recursive: true });
  }
  return agentStackHome();
}

module.exports = {
  REPO_ROOT,
  hermesHome,
  agentStackHome,
  dataHome,
  configHome,
  cacheHome,
  dbPath,
  tasksDbPath,
  permissionsPath,
  providersConfigPath,
  configFilePath,
  defaultWorkspace,
  workspace,
  ensureDirs,
};
