#!/usr/bin/env node
/**
 * AgentStack — one clean system.
 * Merges Hermes (brain) + OpenClaw (hands) + Obsidian (memory) into a single
 * CLI, OpenClaw-style: install once, drop in a token, done.
 *
 *   agentstack install --token sk-or-...   first-run setup (pre-ready)
 *   agentstack doctor                       check everything is healthy
 *   agentstack status                       system overview
 *   agentstack ask "question"               route by intent (brain/hands)
 *   agentstack council "question"           cheap council (opt-in)
 *   agentstack note "text"                  append to the shared vault
 *   agentstack todo add|list|done <task>    shared task queue in the vault
 *   agentstack cost report                  cost-per-verified-success ledger
 *   agentstack skills                       list bundled skills
 *   agentstack audit                        security audit
 *   agentstack telegram on|off|status       manage the Telegram gateway
 *
 * The whole system is one app: `agentstack` (alias `stack`).
 */
'use strict';

const { execFileSync, spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '..');
const HOME = os.homedir();
const HERMES_HOME = process.env.HERMES_HOME || path.join(HOME, 'AppData', 'Local', 'hermes');
const VAULT = process.env.STACK_VAULT || path.join(HOME, 'Documents', 'Obsidian Vault');
const BIN_DIR = path.join(HOME, 'bin');

const C = { reset: '\x1b[0m', cyan: '\x1b[36m', green: '\x1b[32m', yellow: '\x1b[33m', red: '\x1b[31m' };
const info = (m) => console.log(`${C.cyan}==>${C.reset} ${m}`);
const ok = (m) => console.log(`  ${C.green}✓${C.reset} ${m}`);
const warn = (m) => console.log(`  ${C.yellow}!${C.reset} ${m}`);
const err = (m) => console.log(`  ${C.red}x${C.reset} ${m}`);

function run(cmd, args, opts = {}) {
  // On Windows, run without shell (spawnSync) so paths with spaces survive.
  const r = spawnSync(cmd, args, { encoding: 'utf8', shell: false, ...opts });
  if (r.error) throw r.error;
  return { status: r.status, out: (r.stdout || '').trim(), err: (r.stderr || '').trim() };
}

function bash(script, opts = {}) {
  const shell = process.platform === 'win32' ? 'bash' : 'bash';
  return run(shell, ['-c', script], opts);
}

// ---------------------------------------------------------------- commands --
const cmds = {
  // ---- install: first-run, pre-ready ---------------------------------------
  install(args) {
    const tokenArg = args.find((a) => a === '--token') ? args[args.indexOf('--token') + 1] : '';
    info('AgentStack — one clean system install');
    info('1/8 Hermes (brain)');
    const h = detectHermes();
    if (h) ok(`Hermes detected (${h})`);
    else { warn('Hermes not found'); }

    info('2/8 OpenClaw (hands)');
    const oc = detectOpenClaw();
    if (oc) ok(`OpenClaw detected (${oc})`);
    else { warn('OpenClaw not found — npm i -g openclaw'); }

    info('3/8 Obsidian vault (memory)');
    if (fs.existsSync(VAULT)) ok(`Vault at ${VAULT}`);
    else {
      fs.mkdirSync(VAULT, { recursive: true });
      if (!fs.existsSync(path.join(VAULT, 'AGENTS.md'))) fs.writeFileSync(path.join(VAULT, 'AGENTS.md'), '# AgentStack shared brain\n');
      ok(`Vault scaffolded at ${VAULT}`);
    }

    info('4/8 Hermes config');
    fs.mkdirSync(HERMES_HOME, { recursive: true });
    const cfg = path.join(HERMES_HOME, 'config.yaml');
    if (!fs.existsSync(cfg)) {
      fs.copyFileSync(path.join(REPO_ROOT, 'config', 'hermes.config.yaml'), cfg);
      ok('wrote config.yaml from template');
    } else ok('config.yaml exists — preserved');

    info('5/8 Hermes .env (secrets)');
    const envf = path.join(HERMES_HOME, '.env');
    if (fs.existsSync(envf)) {
      ok('.env exists — preserved');
      if (tokenArg && !fs.readFileSync(envf, 'utf8').includes('OPENROUTER_API_KEY=')) {
        fs.appendFileSync(envf, `\nOPENROUTER_API_KEY=${tokenArg}\n`);
        ok('added OPENROUTER_API_KEY');
      }
    } else {
      const content = `# AgentStack .env — your secrets live here (never committed)\nOPENROUTER_API_KEY=${tokenArg || 'your_openrouter_key_here'}\nTELEGRAM_BOT_TOKEN=\n`;
      fs.writeFileSync(envf, content);
      ok(tokenArg ? 'wrote .env with your OpenRouter token' : 'wrote .env template');
    }

    info('6/8 Linking stack + bridges into PATH');
    fs.mkdirSync(BIN_DIR, { recursive: true });
    for (const name of ['stack', 'stack.cmd', 'hermes-to-openclaw', 'hermes-worker', 'vault-note']) {
      const src = path.join(REPO_ROOT, 'bin', name);
      if (!fs.existsSync(src)) continue;
      try { fs.chmodSync(src, 0o755); } catch {}
      const link = path.join(BIN_DIR, name);
      try { fs.unlinkSync(link); } catch {}
      try {
        fs.symlinkSync(src, link, 'junction');
      } catch {
        // junction failed — copy instead (works everywhere, no admin)
        try { fs.copyFileSync(src, link); } catch {}
      }
    }
    ok(`linked to ${BIN_DIR}`);

    info('7/8 AgentStack skills -> Hermes');
    const sk = path.join(HERMES_HOME, 'skills');
    fs.mkdirSync(sk, { recursive: true });
    let n = 0;
    for (const dir of ['learning', 'terminal']) {
      const srcDir = path.join(REPO_ROOT, 'skills', dir);
      if (!fs.existsSync(srcDir)) continue;
      for (const entry of fs.readdirSync(srcDir)) {
        const target = path.join(sk, entry);
        if (!fs.existsSync(target)) {
          try { fs.symlinkSync(path.join(srcDir, entry), target, 'junction'); }
          catch { try { fs.cpSync(path.join(srcDir, entry), target, { recursive: true }); } catch {} }
        }
        n++;
      }
    }
    ok(`installed ${n} skills`);

    info('8/8 Hooks');
    const hk = path.join(HERMES_HOME, 'hooks');
    fs.mkdirSync(hk, { recursive: true });
    const hookSrc = path.join(REPO_ROOT, 'hooks', 'openclaw-wife-reviewer');
    if (fs.existsSync(hookSrc)) {
      try { fs.chmodSync(hookSrc, 0o755); } catch {}
      const target = path.join(hk, 'openclaw-wife-reviewer');
      if (!fs.existsSync(target)) fs.symlinkSync(hookSrc, target, 'junction');
      ok('hooks deployed');
    }

    console.log();
    info('=== AgentStack install complete ===');
    ok('Run:  agentstack status   to verify');
    if (tokenArg) ok('OpenRouter token dropped in. Add TELEGRAM_BOT_TOKEN to .env, then: agentstack telegram on');
    else warn('No token given — set OPENROUTER_API_KEY in ' + envf);
    return 0;
  },

  // ---- doctor: full health check -------------------------------------------
  doctor() {
    info('AgentStack doctor');
    let allOk = true;
    const h = detectHermes();
    if (h) ok(`Hermes (brain): ${h}`); else { err('Hermes not found'); allOk = false; }
    const oc = detectOpenClaw();
    if (oc) ok(`OpenClaw (hands): ${oc}`); else { err('OpenClaw not found'); allOk = false; }
    if (fs.existsSync(VAULT)) ok(`Vault (memory): ${VAULT}`); else { warn(`Vault missing: ${VAULT}`); }
    const envf = path.join(HERMES_HOME, '.env');
    if (fs.existsSync(envf)) {
      const env = fs.readFileSync(envf, 'utf8');
      ok(env.includes('OPENROUTER_API_KEY=') ? '.env: OPENROUTER_API_KEY set' : '.env: missing OPENROUTER_API_KEY');
    } else { warn('.env missing'); }

    const cfg = path.join(HERMES_HOME, 'config.yaml');
    if (fs.existsSync(cfg)) ok('config.yaml present'); else warn('config.yaml missing');

    const sk = path.join(HERMES_HOME, 'skills');
    if (fs.existsSync(sk)) {
      const count = fs.readdirSync(sk).filter((e) => !e.startsWith('.')).length;
      ok(`skills: ${count} installed`);
    } else warn('no skills installed');

    if (h && fs.existsSync(path.join(HERMES_HOME, 'hooks'))) ok('hooks deployed');
    console.log();
    ok(allOk ? 'Verdict: stack healthy' : 'Verdict: fix the x items above, then re-run agentstack doctor');
    return allOk ? 0 : 1;
  },

  // ---- status: overview -----------------------------------------------------
  status() {
    const h = detectHermes();
    const oc = detectOpenClaw();
    console.log(`${C.cyan}═══ AgentStack ═══${C.reset}`);
    console.log(`  ${h ? C.green + '✓' + C.reset : C.red + 'x' + C.reset} brain   (Hermes):   ${h || 'not found'}`);
    console.log(`  ${oc ? C.green + '✓' + C.reset : C.red + 'x' + C.reset} hands   (OpenClaw): ${oc || 'not found'}`);
    console.log(`  ${fs.existsSync(VAULT) ? C.green + '✓' + C.reset : C.red + 'x' + C.reset} memory  (vault):    ${VAULT}`);
    const envf = path.join(HERMES_HOME, '.env');
    const tokenSet = fs.existsSync(envf) && fs.readFileSync(envf, 'utf8').includes('OPENROUTER_API_KEY=') && !fs.readFileSync(envf, 'utf8').includes('your_openrouter');
    console.log(`  ${tokenSet ? C.green + '✓' + C.reset : C.yellow + '!' + C.reset} token   (OpenRouter): ${tokenSet ? 'set' : 'not set'}`);
    return 0;
  },

  // ---- ask: route by intent (brain or hands) --------------------------------
  ask(args) {
    const q = args.join(' ');
    if (!q) { err('Usage: agentstack ask "question"'); return 2; }
    const envf = path.join(HERMES_HOME, '.env');
    const hasToken = fs.existsSync(envf) && fs.readFileSync(envf, 'utf8').includes('OPENROUTER_API_KEY=');
    if (!hasToken) { err('No OPENROUTER_API_KEY. Run: agentstack install --token sk-or-...'); return 1; }
    // simple intent routing: hands for "do X", brain otherwise
    const doVerbs = /^(create|make|build|write|fix|install|run|start|stop|deploy|scan|gather|list|remove|delete|organize|sort|merge|push|commit|test)\b/i;
    const toHands = doVerbs.test(q) && !!detectOpenClaw();
    info(toHands ? 'routing to OpenClaw (hands)...' : 'routing to Hermes (brain)...');
    const b = toHands ? 'bridges/hermes-to-openclaw' : 'bridges/hermes-worker';
    const bridge = path.join(REPO_ROOT, b);
    // Convert to POSIX path for bash (MSYS) — critical on Windows with spaces.
    let posix = bridge;
    try {
      if (process.platform === 'win32') {
        const cyg = spawnSync('cygpath', ['-u', bridge], { encoding: 'utf8' });
        if (cyg.status === 0 && cyg.stdout.trim()) posix = cyg.stdout.trim();
      }
    } catch {}
    const r = run('bash', [posix, q], { timeout: 120000 });
    console.log(r.out || r.err || '(no output)');
    return r.status ?? 0;
  },

  // ---- council --------------------------------------------------------------
  council(args) {
    const py = path.join(REPO_ROOT, 'council', 'council_v2.py');
    if (!fs.existsSync(py)) { err('council not found'); return 1; }
    const pyCmd = process.platform === 'win32' ? 'python' : 'python3';
    // spawnSync with args array handles spaces correctly (no shell mangling)
    const r = spawnSync(pyCmd, [py, ...args], { encoding: 'utf8', timeout: 120000 });
    if (r.error) { err(`council failed: ${r.error.message}`); return 1; }
    console.log((r.stdout || r.stderr || '').trim());
    return r.status ?? 0;
  },

  // ---- note: append to shared vault -----------------------------------------
  note(args) {
    const text = args.join(' ');
    if (!text) { err('Usage: agentstack note "text"'); return 2; }
    const noteDir = path.join(VAULT, 'Agent Hub', 'Daily Notes');
    fs.mkdirSync(noteDir, { recursive: true });
    const file = path.join(noteDir, `${new Date().toISOString().slice(0, 10)}.md`);
    fs.appendFileSync(file, `\n- ${new Date().toLocaleString()} — ${text}\n`);
    ok(`note appended to ${file}`);
    return 0;
  },

  // ---- todo: shared task queue in vault -------------------------------------
  todo(args) {
    const [action, ...rest] = args;
    const tasks = path.join(VAULT, 'Agent Hub', 'Tasks.md');
    fs.mkdirSync(path.dirname(tasks), { recursive: true });
    if (!fs.existsSync(tasks)) fs.writeFileSync(tasks, '# Tasks\n\n');
    let lines = fs.readFileSync(tasks, 'utf8').split('\n');
    switch (action) {
      case 'add': {
        const t = rest.join(' ');
        if (!t) { err('Usage: agentstack todo add "task"'); return 2; }
        const id = lines.filter((l) => /^\d+\.\s*\[ \]/.test(l)).length + 1;
        lines.push(`- [ ] ${id}. ${t}`);
        fs.writeFileSync(tasks, lines.join('\n'));
        ok(`task ${id} added`);
        return 0;
      }
      case 'list': {
        const open = lines.filter((l) => /^\d+\.\s*\[ \]/.test(l) || /- \[ \]/.test(l));
        console.log(open.length ? open.join('\n') : 'No open tasks');
        return 0;
      }
      case 'done': {
        const n = parseInt(rest[0], 10);
        if (!n) { err('Usage: agentstack todo done <id>'); return 2; }
        let hit = 0;
        lines = lines.map((l) => {
          const m = l.match(/^-\s*\[\s*\]\s*(\d+)\.\s*/);
          if (m && parseInt(m[1], 10) === n) { hit = 1; return l.replace('[ ]', '[x]'); }
          return l;
        });
        fs.writeFileSync(tasks, lines.join('\n'));
        hit ? ok(`task ${n} done`) : warn(`no task ${n}`);
        return hit ? 0 : 1;
      }
      default: err('Usage: agentstack todo add|list|done'); return 2;
    }
  },

  // ---- cost report ----------------------------------------------------------
  cost(args) {
    const py = path.join(REPO_ROOT, 'council', 'cost_ledger.py');
    if (!fs.existsSync(py)) { err('cost ledger not found'); return 1; }
    const pyCmd = process.platform === 'win32' ? 'python' : 'python3';
    const r = run(pyCmd, [py, ...args], { timeout: 30000 });
    console.log(r.out || r.err);
    return r.status ?? 0;
  },

  // ---- skills: list bundled -------------------------------------------------
  skills() {
    info('AgentStack bundled skills');
    let n = 0;
    for (const dir of ['learning', 'terminal', 'ecosystem']) {
      const srcDir = path.join(REPO_ROOT, 'skills', dir);
      if (!fs.existsSync(srcDir)) continue;
      for (const entry of fs.readdirSync(srcDir)) {
        const skmd = path.join(srcDir, entry, 'SKILL.md');
        if (!fs.existsSync(skmd)) continue;
        const desc = fs.readFileSync(skmd, 'utf8').split('\n').find((l) => l.startsWith('description:'))?.replace('description:', '').trim().slice(0, 70) || '';
        console.log(`  ${C.green}✓${C.reset} ${entry} — ${desc}`);
        n++;
      }
    }
    console.log(`  (${n} skills)`);
    return 0;
  },

  // ---- audit ----------------------------------------------------------------
  audit() {
    info('AgentStack security audit');
    const r = bash(`cd "${REPO_ROOT}" && git grep -lnE "sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|OPENROUTER_API_KEY=.+" 2>/dev/null || true`);
    const hits = (r.out || '').split('\n').filter((l) => l && !l.includes('hermes.env.example') && !l.includes('bin/'));
    if (hits.length) { err(`secrets found: ${hits.join(', ')}`); return 1; }
    ok('no secret values in tracked files');
    ok('guardrails: Budget $10/mo + PromptInjection (verify in OpenRouter dashboard)');
    const sk = path.join(HERMES_HOME, 'skills');
    ok(fs.existsSync(sk) ? `skills installed: ${fs.readdirSync(sk).length}` : 'skills: none installed');
    return 0;
  },

  // ---- telegram -------------------------------------------------------------
  telegram(args) {
    const [action] = args;
    if (!action) { err('Usage: agentstack telegram on|off|status'); return 2; }
    const hermes = detectHermes();
    if (!hermes) { err('Hermes not found'); return 1; }
    const r = run('hermes', ['gateway', action === 'status' ? 'status' : (action === 'on' ? 'start' : 'stop')], { timeout: 60000 });
    console.log(r.out || r.err || `telegram ${action}`);
    return r.status ?? 0;
  },

  // ---- help -----------------------------------------------------------------
  help() {
    console.log(`AgentStack — one clean system (Hermes brain + OpenClaw hands + Obsidian memory)

Usage: agentstack <command> [args]

  install [--token sk-or-...]   first-run setup — pre-ready, drop-in token
  doctor                         health check for the whole system
  status                         system overview
  ask "question"                 route by intent (brain or hands)
  council "question"             cheap council (opt-in, --cheap-chairman for routine)
  note "text"                    append to shared vault
  todo add|list|done <task>      shared task queue in the vault
  cost report|log|credits        cost-per-verified-success ledger
  skills                         list bundled skills
  audit                          security audit
  telegram on|off|status         manage the Telegram gateway
  help                           this message

Alias: stack  (same binary)
`);
    return 0;
  },
};

// ---------------------------------------------------------------- helpers --
function detectHermes() {
  const candidates = [
    path.join(HERMES_HOME, 'hermes-agent', 'venv', 'Scripts', 'hermes.exe'),
    path.join(HERMES_HOME, 'venv', 'Scripts', 'hermes.exe'),
  ];
  for (const c of candidates) if (fs.existsSync(c)) return c;
  try { const r = run(process.platform === 'win32' ? 'where' : 'which', ['hermes']); if (r.status === 0 && r.out) return r.out.split('\n')[0]; } catch {}
  return null;
}

function detectOpenClaw() {
  const candidates = [
    path.join(process.env.APPDATA || '', 'npm', 'node_modules', 'openclaw', 'openclaw.mjs'),
    path.join(HOME, 'AppData', 'Roaming', 'npm', 'node_modules', 'openclaw', 'openclaw.mjs'),
    path.join(HOME, '.npm-global', 'lib', 'node_modules', 'openclaw', 'openclaw.mjs'),
  ];
  for (const c of candidates) if (fs.existsSync(c)) return c;
  try { const r = run(process.platform === 'win32' ? 'where' : 'which', ['openclaw']); if (r.status === 0 && r.out) return r.out.split('\n')[0]; } catch {}
  return null;
}

// ---------------------------------------------------------------- dispatch --
const [cmd, ...rest] = process.argv.slice(2);
if (!cmd || cmd === 'help' || cmd === '-h' || cmd === '--help') {
  cmds.help();
  process.exit(0);
}
if (cmds[cmd]) {
  process.exit(cmds[cmd](rest));
}
console.error(`Unknown command: ${cmd}`);
cmds.help();
process.exit(2);
