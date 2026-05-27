import { api } from './api.js';
import { toast } from './ui.js';

if (!sessionStorage.getItem('token')) {
  window.location.href = '/login.html';
}

document.getElementById('logout-btn')?.addEventListener('click', () => {
  sessionStorage.clear(); window.location.href = '/index.html';
});
document.getElementById('back-btn')?.addEventListener('click', () => {
  window.location.href = '/dashboard.html';
});

const TOOLS = [
  { name: 'web_search',    label: 'Web Search'    },
  { name: 'calculator',    label: 'Calculator'    },
  { name: 'code_executor', label: 'Code Executor' },
];

// ── Render tools grid ─────────────────────────────────────────────
const toolsGrid = document.getElementById('tools-grid');
TOOLS.forEach(t => {
  const lbl = document.createElement('label');
  lbl.className = 'tool-lbl';
  lbl.innerHTML = `<input type="checkbox" value="${t.name}"> ${t.label}`;
  const cb = lbl.querySelector('input');
  cb.addEventListener('change', () => lbl.classList.toggle('checked', cb.checked));
  toolsGrid?.appendChild(lbl);
});

// ── Prompt counter ────────────────────────────────────────────────
const promptEl = document.getElementById('agent-prompt');
const countEl  = document.getElementById('prompt-count');
promptEl?.addEventListener('input', () => {
  if (countEl) countEl.textContent = promptEl.value.length + ' chars';
});

// ── Get selected model from dropdown ─────────────────────────────

function getSelectedModel() {
  const select = document.getElementById('model-select');
  if (!select || !select.value) return null;
  const option = select.options[select.selectedIndex];
  const provider = option.getAttribute('data-provider');
  if (!provider) return null;
  return {
    id:       select.value,
    provider: provider,
  };
}
// ── Resolve model UUID ────────────────────────────────────────────
async function resolveModelUUID(selected) {
  try {
    const models = await fetch('http://localhost:8001/api/v1/models').then(r => r.json());
    if (Array.isArray(models)) {
      for (const m of models) {
        if (selected.provider === 'groq'   && m.groq_model_id   === selected.id) return m.id;
        if (selected.provider === 'ollama' && m.ollama_model_id === selected.id) return m.id;
      }
    }
  } catch (_) {}

  try {
    const token  = sessionStorage.getItem('token');
    const agents = await fetch('http://localhost:8001/api/v1/agents', {
      headers: { 'Authorization': `Bearer ${token}` }
    }).then(r => r.json());

    if (Array.isArray(agents)) {
      for (const a of agents) {
        if (!a.is_platform_agent) continue;
        const n = (a.name || '').toLowerCase();
        let gid = null;
        if (n.includes('llama') && n.includes('70'))     gid = 'llama-3.3-70b-versatile';
        else if (n.includes('llama') && n.includes('8')) gid = 'llama-3.1-8b-instant';
        else if (n.includes('mixtral'))                  gid = 'mixtral-8x7b-32768';
        else if (n.includes('gemma'))                    gid = 'gemma2-9b-it';
        if (gid === selected.id) return a.model_id;
      }
    }
  } catch (_) {}

  return null;
}

// ── Submit ────────────────────────────────────────────────────────
document.getElementById('create-form')?.addEventListener('submit', async e => {
  e.preventDefault();
  const errEl = document.getElementById('form-error');
  const btn   = e.target.querySelector('button[type=submit]');
  errEl.textContent = '';

  const name          = document.getElementById('agent-name').value.trim();
  const description   = document.getElementById('agent-desc').value.trim();
  const system_prompt = promptEl?.value.trim();
  const selected      = getSelectedModel();
  const tools         = Array.from(
    toolsGrid?.querySelectorAll('input:checked') || []
  ).map(cb => ({ tool_name: cb.value, tool_config: {} }));

  if (!name || !system_prompt) {
    errEl.textContent = 'Name and system prompt are required.';
    return;
  }
  if (!selected) {
    errEl.textContent = 'Please select a model.';
    return;
  }

  btn.disabled = true; btn.textContent = 'Creating…';

  const model_id = await resolveModelUUID(selected);
  if (!model_id) {
    errEl.textContent = 'Could not resolve model. Make sure the backend is running and try again.';
    btn.disabled = false; btn.textContent = 'Create Agent';
    return;
  }

  try {
    await api.agents.create({ name, description, system_prompt, model_id, tools });
    toast(`"${name}" created!`, 'success');
    setTimeout(() => window.location.href = '/dashboard.html', 700);
  } catch (err) {
    errEl.textContent = err.message;
    btn.disabled = false; btn.textContent = 'Create Agent';
  }
});