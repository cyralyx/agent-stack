'use strict';
// renderer.js — UI logic. Talks only to window.agentstack (contextBridge).

const $ = (sel) => document.querySelector(sel);
const api = window.agentstack;

// ---------------------------------------------------------- nav ----
const navItems = document.querySelectorAll('.nav-item');
const views = document.querySelectorAll('.view');
function showView(name) {
  navItems.forEach((n) => n.classList.toggle('active', n.dataset.view === name));
  views.forEach((v) => v.classList.toggle('active', v.id === `view-${name}`));
  if (name === 'tasks') loadTasks();
  if (name === 'providers') loadProviders();
  if (name === 'cost') showCost();
}
navItems.forEach((n) => n.addEventListener('click', () => showView(n.dataset.view)));

// ---------------------------------------------------------- home ----
async function loadStatus() {
  const chip = $('#healthChip');
  const grid = $('#statusGrid');
  const st = await api.status();
  if (!st) { chip.textContent = 'offline'; chip.className = 'health-chip bad'; return; }

  let ok = true;
  const cards = [];
  cards.push(card('Hermes · brain', st.hermes ? val(st.hermes) : '—', st.hermes ? 'ok' : 'bad', 'Brain / orchestrator'));
  cards.push(card('OpenClaw · hands', st.openclaw ? val(st.openclaw) : '—', st.openclaw ? 'ok' : 'bad', 'Executor / worker'));
  cards.push(card('Vault · memory', st.vault ? val(st.vault) : '—', st.vault ? 'ok' : 'bad', 'Markdown workspace'));
  cards.push(card('Provider', st.provider && st.provider.provider ? st.provider.provider : 'not configured', st.provider && st.provider.count > 0 ? 'ok' : 'bad', st.provider ? st.provider.detail : ''));
  if (st.compat && st.compat.checks && st.compat.checks.length) {
    const fails = st.compat.checks.filter((c) => c.compatible === false).length;
    cards.push(card('Compatibility', fails === 0 ? 'all pass' : `${fails} issue${fails > 1 ? 's' : ''}`, fails === 0 ? 'ok' : 'bad', ['node', 'python', 'hermes', 'openclaw', 'os', 'bridge_protocol'].join(', ')));
  }
  grid.innerHTML = cards.join('');

  const bad = st.incompat && st.incompat.length ? `issues: ${st.incompat.join(', ')}` : '';
  ok = !!(st.hermes && st.openclaw && st.vault && !(st.incompat && st.incompat.length));
  chip.textContent = ok ? '✓ Stack healthy' : (bad || 'needs attention');
  chip.className = 'health-chip ' + (ok ? 'ok' : 'bad');

  loadEvents();
}
function card(title, value, state, sub) {
  const tag = state === 'ok' ? '<span class="tag ok">ready</span>' : '<span class="tag bad">missing</span>';
  return `<div class="card"><h3>${title}</h3><div class="value">${value}</div><div class="sub">${sub}</div>${tag}</div>`;
}
function val(p) {
  const s = String(p);
  const parts = s.split(/[\\/]/);
  return parts[parts.length - 1] || s;
}

async function loadEvents() {
  const el = $('#eventsList');
  const r = await api.events.recent();
  const evts = (r && r.ok && r.data) || [];
  el.innerHTML = evts.length
    ? evts.map((e) => `<div class="evt"><span class="t">${e.type || ''}</span><span class="msg">${(e.data && e.data.agent) || ''} ${e.data && e.data.ok === false ? 'failed' : e.data && e.data.title ? '· ' + e.data.title : ''}</span></div>`).join('')
    : '<div class="evt">No activity yet.</div>';
}

// ---------------------------------------------------------- ask ----
$('#askBtn').addEventListener('click', async () => {
  const prompt = $('#askInput').value.trim();
  if (!prompt) return;
  const out = $('#askOutput');
  out.hidden = false; out.className = 'output'; out.textContent = 'Thinking…';
  $('#askBtn').disabled = true;
  const r = await api.ask(prompt, $('#askModel').value.trim());
  $('#askBtn').disabled = false;
  const text = (r && (r.out || r.err)) || 'no response';
  out.textContent = text.trim();
  out.className = 'output ' + (r && r.ok ? 'ok' : 'err');
});
$('#askInput').addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) $('#askBtn').click(); });

// ---------------------------------------------------------- council ----
$('#councilBtn').addEventListener('click', async () => {
  const prompt = $('#councilInput').value.trim();
  if (!prompt) return;
  const out = $('#councilOutput');
  out.hidden = false; out.className = 'output'; out.textContent = 'Running council…';
  $('#councilBtn').disabled = true;
  const r = await api.council(prompt);
  $('#councilBtn').disabled = false;
  const text = (r && (r.out || r.err)) || 'no response';
  out.textContent = text.trim();
  out.className = 'output ' + (r && r.ok ? 'ok' : 'err');
});

// ---------------------------------------------------------- tasks ----
async function loadTasks() {
  const r = await api.tasks.list();
  const tasks = (r && r.ok && r.data) || [];
  const open = tasks.filter((t) => t.status === 'open');
  $('#taskBadge').textContent = open.length;
  const ul = $('#taskList');
  if (!tasks.length) { ul.innerHTML = '<li style="color:var(--muted)">No tasks yet.</li>'; return; }
  ul.innerHTML = tasks.map((t) => `
    <li data-id="${t.id}">
      <button class="check ${t.status === 'completed' ? 'done' : ''}" data-action="toggle">${t.status === 'completed' ? '✓' : ''}</button>
      <span class="title ${t.status === 'completed' ? 'done-t' : ''}">${esc(t.title)}</span>
      <button class="del" data-action="del" title="delete">✕</button>
    </li>`).join('');
}
$('#taskList').addEventListener('click', async (e) => {
  const li = e.target.closest('li');
  if (!li) return;
  const id = li.dataset.id;
  const act = e.target.dataset.action;
  if (act === 'toggle') {
    const t = (await api.tasks.list()).data.find((x) => x.id === id);
    if (t && t.status === 'completed') await api.tasks.reopen(id); else await api.tasks.complete(id);
  } else if (act === 'del') {
    await api.tasks.remove(id);
  }
  loadTasks();
});
$('#taskAddBtn').addEventListener('click', async () => {
  const v = $('#taskInput').value.trim();
  if (!v) return;
  await api.tasks.add(v);
  $('#taskInput').value = '';
  loadTasks();
});
$('#taskInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('#taskAddBtn').click(); });
$('#taskExportBtn').addEventListener('click', async () => {
  const r = await api.tasks.export();
  const out = $('#noteOutput');
  out.hidden = false; out.className = 'output ok'; out.textContent = (r && r.data) || '';
  showView('notes');
});

// ---------------------------------------------------------- notes ----
$('#noteBtn').addEventListener('click', async () => {
  const text = $('#noteInput').value.trim();
  if (!text) return;
  const out = $('#noteOutput');
  out.hidden = false; out.textContent = 'Saving…';
  const r = await api.notes.add(text);
  out.className = 'output ' + (r && r.ok ? 'ok' : 'err');
  out.textContent = r && r.ok ? `✓ Saved to ${r.data}` : ((r && r.err) || 'error');
  $('#noteInput').value = '';
});

// ---------------------------------------------------------- providers ----
async function loadProviders() {
  const el = $('#providerList');
  const r = await api.providers.list();
  const list = (r && r.ok && r.data) || [];
  if (!list.length) { el.innerHTML = '<div class="evt">No providers yet. Run `agentstack provider add` in a terminal.</div>'; return; }
  el.innerHTML = list.map((p) => `
    <div class="provider-row">
      <span class="name">${esc(p.name)}</span>
      <span class="pill ${p.configured ? 'connected' : 'not'}">${p.configured ? 'connected' : 'not configured'}</span>
    </div>`).join('');
}

// ---------------------------------------------------------- security ----
$('#secScanBtn').addEventListener('click', async () => {
  const out = $('#secOutput');
  out.hidden = false; out.className = 'output'; out.textContent = 'Scanning…';
  const r = await api.security.scan();
  const s = (r && r.ok && r.data) || null;
  if (!s) { out.className = 'output err'; out.textContent = (r && r.err) || 'scan failed'; return; }
  const lines = [
    `Secrets: ${s.secrets}`,
    `Permissions: ${s.permissions}`,
    `Skills: ${s.skills}`,
    `Providers: ${s.providers}`,
    `Dependencies: ${s.dependencies}`,
    s.clean ? '✓ All clear' : '! Review findings',
  ];
  out.className = 'output ' + (s.clean ? 'ok' : 'err');
  out.textContent = lines.join('\n');
});

// ---------------------------------------------------------- cost ----
async function showCost() {
  const days = $('#costDays').value || '7';
  const out = $('#costOutput');
  out.hidden = false; out.className = 'output'; out.textContent = 'Loading…';
  const r = await api.cost.report(days);
  out.textContent = (r && (r.out || r.err)) || 'no data';
  out.className = 'output ' + (r && r.ok ? 'ok' : 'err');
}
$('#costBtn').addEventListener('click', showCost);

// ---------------------------------------------------------- helpers ----
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// ---------------------------------------------------------- boot ----
loadStatus();
setInterval(loadStatus, 15000);
