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

// AgentStack lib modules
const paths = require(path.join(REPO_ROOT, 'lib', 'paths'));
const platform = require(path.join(REPO_ROOT, 'lib', 'platform'));
const secrets = require(path.join(REPO_ROOT, 'lib', 'secrets'));
const tasks = require(path.join(REPO_ROOT, 'lib', 'tasks'));
const permissions = require(path.join(REPO_ROOT, 'lib', 'permissions'));
const compat = require(path.join(REPO_ROOT, 'lib', 'compatibility'));
const registry = require(path.join(REPO_ROOT, 'lib', 'providers', 'registry'));
const routing = require(path.join(REPO_ROOT, 'lib', 'routing'));
const security = require(path.join(REPO_ROOT, 'lib', 'security'));
const events = require(path.join(REPO_ROOT, 'lib', 'events'));
const api = require(path.join(REPO_ROOT, 'lib', 'api'));

const HERMES_HOME = paths.hermesHome();
const VAULT = process.env.STACK_VAULT || paths.defaultWorkspace();
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
    if (tokenArg) {
      // P0: CLI secrets are insecure (shell history, process list). Deprecated.
      warn('WARNING: --token on the command line is DEPRECATED and insecure.');
      warn('The token may appear in shell history, process listings, and logs.');
      warn('Recommended: run `agentstack provider add openrouter` for hidden input.');
      warn('The --token flag will be removed in v0.3.0.');
    }
    info('AgentStack — compatibility & orchestration layer install');
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

  // ---- doctor: full health check (supports --json) ---------------------------
  doctor(args) {
    const wantJson = (args || []).includes('--json');
    const checks = [];
    const add = (id, status, severity, message, repairable, suggested) => checks.push({ id, status, severity, message, repairable, suggested_action: suggested });

    const h = detectHermes();
    const oc = detectOpenClaw();
    if (h) add('component.hermes', 'pass', 'high', `Hermes detected (${h})`, false, null);
    else add('component.hermes', 'fail', 'high', 'Hermes not found', true, 'install Hermes');
    if (oc) add('component.openclaw', 'pass', 'high', `OpenClaw detected (${oc})`, false, null);
    else add('component.openclaw', 'fail', 'high', 'OpenClaw not found', true, 'npm i -g openclaw');
    if (fs.existsSync(VAULT)) add('component.vault', 'pass', 'medium', `Vault at ${VAULT}`, false, null);
    else add('component.vault', 'warn', 'medium', `Vault missing: ${VAULT}`, true, 'create the workspace or set STACK_VAULT');

    const envf = path.join(HERMES_HOME, '.env');
    const hasKey = fs.existsSync(envf) && fs.readFileSync(envf, 'utf8').includes('OPENROUTER_API_KEY=') && !fs.readFileSync(envf, 'utf8').includes('OPENROUTER_API_KEY=your_');
    if (hasKey) add('provider.auth', 'pass', 'high', 'provider key present in .env', false, null);
    else add('provider.auth', 'fail', 'high', 'no provider key configured', true, 'agentstack provider add openrouter');

    const cfg = path.join(HERMES_HOME, 'config.yaml');
    if (fs.existsSync(cfg)) add('config.present', 'pass', 'low', 'config.yaml present', false, null);
    else add('config.present', 'warn', 'medium', 'config.yaml missing', true, 'run agentstack setup');

    const sk = path.join(HERMES_HOME, 'skills');
    const skillCount = fs.existsSync(sk) ? fs.readdirSync(sk).filter((e) => !e.startsWith('.')).length : 0;
    if (fs.existsSync(sk)) add('config.skills', 'pass', 'low', `skills: ${skillCount} installed`, false, null);
    else add('config.skills', 'warn', 'low', 'no skills installed', true, 'install the skills bundle');

    const incompatible = [];
    for (const c of compat.report().checks) {
      if (c.compatible === false) incompatible.push(c.component);
    }
    if (incompatible.length) add('compatibility', 'fail', 'high', `incompatible: ${incompatible.join(', ')}`, true, 'check agentstack compatibility');
    else add('compatibility', 'pass', 'medium', 'compatibility checks pass', false, null);

    const failed = checks.filter((c) => c.status === 'fail');
    const warned = checks.filter((c) => c.status === 'warn');
    const overall = failed.length ? 'unsafe' : (warned.length ? 'degraded' : 'healthy');

    if (wantJson) {
      console.log(JSON.stringify({ status: overall, summary: { pass: checks.length - failed.length - warned.length, warn: warned.length, fail: failed.length }, checks }, null, 2));
      return failed.length ? 1 : 0;
    }

    info(`AgentStack doctor — ${overall.toUpperCase()}`);
    for (const c of checks) {
      const mark = c.status === 'pass' ? '✓' : (c.status === 'warn' ? '!' : 'x');
      const col = c.status === 'pass' ? C.green : (c.status === 'warn' ? C.yellow : C.red);
      console.log(`  ${col}${mark}${C.reset} ${c.message}`);
      if (c.suggested_action) console.log(`      → ${c.suggested_action}`);
    }
    console.log();
    ok(overall === 'healthy' ? 'Verdict: healthy' : (overall === 'degraded' ? `${C.yellow}Verdict: degraded${C.reset}` : `${C.red}Verdict: fix the issues above${C.reset}`));
    return failed.length ? 1 : 0;
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
    // parse flags: --agent hermes|openclaw, --explain-route (stripped from the question)
    let agent = null;
    let explain = false;
    const qParts = [];
    for (let i = 0; i < args.length; i++) {
      if (args[i] === '--agent') { agent = args[i + 1]; i++; }
      else if (args[i] === '--explain-route') { explain = true; }
      else qParts.push(args[i]);
    }
    const q = qParts.join(' ');
    if (!q) { err('Usage: agentstack ask [--agent hermes|openclaw] [--explain-route] "question"'); return 2; }
    const envf = path.join(HERMES_HOME, '.env');
    const hasToken = fs.existsSync(envf) && fs.readFileSync(envf, 'utf8').includes('OPENROUTER_API_KEY=');
    if (!hasToken) {
      err('No provider key configured. Run: agentstack provider add openrouter (or set OPENROUTER_API_KEY in .env)');
      return 1;
    }
    // P1: layered routing
    const route = routing.route(q, { agent });
    if (explain) {
      console.log(JSON.stringify({ selected_target: route.selected_target, reason: route.reason, confidence: route.confidence, alternatives: route.alternatives, required_permissions: route.required_permissions }, null, 2));
    }
    const toHands = route.selected_target === 'openclaw' && !!detectOpenClaw();
    info(toHands ? `routing to OpenClaw (hands): ${route.reason}` : `routing to Hermes (brain): ${route.reason}`);
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

  // ---- security --------------------------------------------------------------
  security(args) {
    const [sub] = args;
    if (!sub || sub === 'full') {
      const r = security.full(REPO_ROOT);
      info('Security audit (full)');
      console.log(`  secrets: ${r.secrets.count} (${r.secrets.findings.length ? 'see below' : 'none'})`);
      for (const f of r.secrets.findings) console.log(`    - ${f.file}: ${f.secret}`);
      console.log(`  permissions: ${r.permissions.count}`);
      for (const f of r.permissions.findings) console.log(`    - ${f.file}: ${f.issue}`);
      console.log(`  skills: ${r.skills.count}`);
      for (const f of r.skills.findings) console.log(`    - ${f.file}: ${f.issue}`);
      console.log(`  providers: ${r.providers.count}`);
      for (const f of r.providers.findings) console.log(`    - ${f.issue}`);
      ok(r.all_clear ? 'all clear' : 'findings above (review before trusting claims)');
      return r.all_clear ? 0 : 1;
    }
    if (sub === 'secrets') {
      const f = security.scanSecrets(REPO_ROOT);
      info(`Security secrets: ${f.length} finding(s)`);
      for (const s of f) console.log(`  - ${s.file}: ${s.secret}`);
      return f.length ? 1 : 0;
    }
    if (sub === 'permissions') {
      const a = permissions.audit();
      console.log(JSON.stringify({ defaults: a.defaults, entries: a.entries }, null, 2));
      return 0;
    }
    if (sub === 'skills') {
      const f = security.skills(REPO_ROOT);
      info(`Security skills: ${f.length} finding(s)`);
      for (const s of f) console.log(`  - ${s.file}: ${s.issue}`);
      return f.length ? 1 : 0;
    }
    if (sub === 'config') {
      const f = security.providerConfig();
      info(`Security config: ${f.length} finding(s)`);
      for (const s of f) console.log(`  - ${s.issue}`);
      return f.length ? 1 : 0;
    }
    if (sub === 'dependencies') {
      info('Security dependencies');
      const r = security.dependencies(REPO_ROOT, { run: true });
      console.log(`  ${r.status}: ${r.note || JSON.stringify(r.data && r.data.metadata) || ''}`);
      return r.status === 'ok' || r.status === 'not_run' ? 0 : 1;
    }
    err('Usage: agentstack security secrets|dependencies|permissions|skills|config|full');
    return 2;
  },

  // ---- api (localhost IPC for Cyralyx UI) ------------------------------------
  api(args) {
    const [sub] = args;
    if (sub === 'serve') {
      const port = parseInt(args[1] || '', 10) || 38765;
      info(`Starting AgentStack API on 127.0.0.1:${port} (localhost only)`);
      api.start(port).catch((e) => { err(`api failed to start: ${e.message}`); process.exit(1); });
      return 0; // keeps serving until killed
    }
    err('Usage: agentstack api serve [port]');
    return 2;
  },

  // ---- audit (kept; delegates to security) ------------------------------------
  audit() {
    return this.security(['full']);
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

  // ---- provider --------------------------------------------------------------
  provider(args) {
    const [sub, name] = args;
    if (!sub) { err('Usage: agentstack provider list|add|test|remove|disable <provider>'); return 2; }
    if (sub === 'list') {
      info('Providers');
      const cfg = secrets.loadProviderConfig();
      for (const p of registry.list()) {
        const status = registry.configuredStatus(p);
        const mark = status === 'valid' ? '✓' : (status === 'not_configured' ? '·' : '!');
        const extra = (cfg.providers && cfg.providers[p] && cfg.providers[p].enabled === false) ? ' (disabled)' : '';
        console.log(`  ${mark} ${p} — ${status}${extra}`);
      }
      return 0;
    }
    if (!name) { err('Usage: agentstack provider ' + sub + ' <provider>'); return 2; }
    if (sub === 'add') {
      // secure hidden input
      warn('Enter the API key for ' + name + ' (input hidden):');
      return secrets.promptHidden('API key: ').then(async (key) => {
        const v = secrets.validateKey(key);
        if (!v.valid) { err(`Invalid key: ${v.reason}`); return 1; }
        secrets.setSecret(name, key);
        const cfgEntry = secrets.addProvider(name);
        info(`Provider ${name} configured (secret_ref=${cfgEntry.secret_ref})`);
        // connection test
        info('Testing connection…');
        try {
          const adapter = registry.getAdapter(name);
          const result = await adapter.test();
          console.log(`  ${result.status === 'valid' ? '✓' : '!'} ${result.message}`);
          if (result.status === 'valid') {
            const cfg = secrets.loadProviderConfig();
            if (!cfg.providers) cfg.providers = {};
            cfg.providers[name].status = 'valid';
            secrets.saveProviderConfig(cfg);
          }
          return result.status === 'valid' ? 0 : 1;
        } catch (e) {
          err(`test failed: ${e.message}`);
          return 1;
        }
      });
    }
    if (sub === 'test') {
      return (async () => {
        try {
          const adapter = registry.getAdapter(name);
          const result = await adapter.test();
          console.log(`  ${result.status === 'valid' ? '✓' : '!'} ${name}: ${result.message}`);
          const cfg = secrets.loadProviderConfig();
          if (cfg.providers && cfg.providers[name]) {
            cfg.providers[name].status = result.status;
            secrets.saveProviderConfig(cfg);
          }
          return result.status === 'valid' ? 0 : 1;
        } catch (e) {
          err(`${name} test failed: ${e.message}`);
          return 1;
        }
      })();
    }
    if (sub === 'remove') {
      secrets.removeSecret(name);
      const cfg = secrets.loadProviderConfig();
      if (cfg.providers && cfg.providers[name]) delete cfg.providers[name];
      secrets.saveProviderConfig(cfg);
      ok(`Provider ${name} removed (secret + config)`);
      return 0;
    }
    if (sub === 'disable') {
      const cfg = secrets.loadProviderConfig();
      if (!cfg.providers) cfg.providers = {};
      if (!cfg.providers[name]) cfg.providers[name] = { enabled: true };
      cfg.providers[name].enabled = false;
      secrets.saveProviderConfig(cfg);
      ok(`Provider ${name} disabled`);
      return 0;
    }
    err('Usage: agentstack provider list|add|test|remove|disable <provider>');
    return 2;
  },

  // ---- secrets --------------------------------------------------------------
  secrets(args) {
    const [sub] = args;
    if (sub === 'doctor') {
      const backend = secrets.systemStoreAvailable();
      info('Secrets doctor');
      console.log(`  Credential backend: ${backend}`);
      const cfg = secrets.loadProviderConfig();
      const names = registry.list();
      for (const n of names) {
        const hasKey = !!secrets.getSecret(n);
        const status = registry.configuredStatus(n);
        console.log(`  ${hasKey ? '✓' : '·'} ${n}: ${status}${hasKey ? ' (key stored, not validated)' : ''}`);
      }
      return 0;
    }
    err('Usage: agentstack secrets doctor');
    return 2;
  },

  // ---- task (structured storage) ----------------------------------------------
  task(args) {
    const [sub, ...rest] = args;
    if (!sub) { err('Usage: agentstack task add|list|show|complete|reopen|remove|export|sync'); return 2; }
    if (sub === 'add') {
      const title = rest.join(' ');
      if (!title) { err('Usage: agentstack task add "title"'); return 2; }
      const t = tasks.add({ title });
      ok(`task ${t.display} added (id=${t.id})`);
      return 0;
    }
    if (sub === 'list') {
      const list = tasks.list();
      if (!list.length) { console.log('No tasks'); return 0; }
      for (const t of list) {
        console.log(`  ${t.status === 'completed' ? '[x]' : '[ ]'} ${t.display}. ${t.title}  (${t.status})`);
      }
      return 0;
    }
    if (sub === 'show') {
      const id = rest[0];
      const t = tasks.getById(id);
      if (!t) { err('task not found'); return 1; }
      console.log(JSON.stringify(t, null, 2));
      return 0;
    }
    if (sub === 'complete') {
      const t = tasks.complete(rest[0]);
      if (!t) { err('task not found'); return 1; }
      ok(`task ${rest[0]} completed`);
      return 0;
    }
    if (sub === 'reopen') {
      const t = tasks.reopen(rest[0]);
      if (!t) { err('task not found'); return 1; }
      ok(`task ${rest[0]} reopened`);
      return 0;
    }
    if (sub === 'remove') {
      const ok2 = tasks.remove(rest[0]);
      if (!ok2) { err('task not found'); return 1; }
      ok(`task ${rest[0]} removed`);
      return 0;
    }
    if (sub === 'export') {
      const f = tasks.exportMarkdown(rest[0]);
      ok(`tasks exported to ${f}`);
      return 0;
    }
    if (sub === 'sync') {
      const f = tasks.exportMarkdown();
      ok(`Markdown view synced: ${f}`);
      return 0;
    }
    if (sub === 'migrate') {
      const r = tasks.migrateFromLegacy(rest[0]);
      console.log(`Migration: imported=${r.imported} duplicates=${r.duplicates} backedUp=${r.backedUp || 'none'}`);
      return r.imported >= 0 ? 0 : 1;
    }
    err('Usage: agentstack task add|list|show|complete|reopen|remove|export|sync|migrate');
    return 2;
  },

  // ---- permissions --------------------------------------------------------------
  permissions(args) {
    const [sub, cat, mode] = args;
    if (!sub) { err('Usage: agentstack permissions list|set|reset|audit'); return 2; }
    if (sub === 'list') {
      info('Permission categories');
      for (const c of permissions.CATEGORIES) {
        console.log(`  ${c} -> ${permissions.effectiveMode(c)}`);
      }
      return 0;
    }
    if (sub === 'set') {
      if (!cat || !mode) { err('Usage: agentstack permissions set <category> <mode>'); return 2; }
      try { const r = permissions.set(cat, mode); ok(`${r.category} -> ${r.mode} (${r.scope})`); return 0; }
      catch (e) { err(e.message); return 1; }
    }
    if (sub === 'reset') { permissions.reset(); ok('permissions reset to defaults'); return 0; }
    if (sub === 'audit') {
      const a = permissions.audit();
      console.log(JSON.stringify({ defaults: a.defaults, entries: a.entries, recent_log: a.log.slice(-10) }, null, 2));
      return 0;
    }
    err('Usage: agentstack permissions list|set|reset|audit');
    return 2;
  },

  // ---- compatibility --------------------------------------------------------------
  compatibility(args) {
    const [sub] = args;
    const r = compat.report();
    if (sub === 'check' || sub === 'report' || !sub) {
      info('Compatibility report');
      for (const c of r.checks) {
        const mark = c.compatible === true ? '✓' : (c.compatible === null ? '?' : 'x');
        console.log(`  ${mark} ${c.component}: ${c.version || 'unknown'}${c.message ? ' (' + c.message + ')' : ''}`);
      }
      return r.checks.every((c) => c.compatible !== false) ? 0 : 1;
    }
    err('Usage: agentstack compatibility [check|report]');
    return 2;
  },

  // ---- help -----------------------------------------------------------------
  help() {
    console.log(`AgentStack — compatibility & orchestration layer (Hermes + OpenClaw + Obsidian + providers + councils)

Usage: agentstack <command> [args]

  install [--token sk-or-...]   setup (--token DEPRECATED: use provider add)
  provider list|add|test|remove|disable <name>
  secrets doctor                 inspect credential storage + provider status
  doctor                         health check for the whole system
  status                         system overview
  compatibility [check|report]   version compatibility registry
  task add|list|show|complete|reopen|remove|export|sync|migrate
  permissions list|set|reset|audit
  ask "question"                 route by intent (brain or hands)
  council "question"             cheap council (opt-in, --cheap-chairman for routine)
  note "text"                    append to shared vault
  todo add|list|done <task>      compatibility alias for task
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
  const code = cmds[cmd](rest);
  // api serve starts a long-running server: don't call process.exit immediately.
  if (!(cmd === 'api' && rest[0] === 'serve')) {
    process.exit(typeof code === 'number' ? code : 0);
  }
} else {
  console.error(`Unknown command: ${cmd}`);
  cmds.help();
  process.exit(2);
}
