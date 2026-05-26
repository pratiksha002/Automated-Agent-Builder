import { api } from './api.js';
import { toast } from './ui.js';

// Guard — if no token, redirect to login not index
if (!sessionStorage.getItem('token')) {
  window.location.href = '/login.html';
}

document.getElementById('logout-btn')?.addEventListener('click', () => {
  sessionStorage.clear(); window.location.href = '/index.html';
});
document.getElementById('back-btn')?.addEventListener('click', () => {
  window.location.href = '/dashboard.html';
});

// ── Model definitions ─────────────────────────────────────────────
const GROQ_MODELS = [
  { id: 'llama-3.3-70b-versatile', name: 'LLaMA 3.3',  detail: '70B · Best quality',  provider: 'groq'   },
  { id: 'llama-3.1-8b-instant',    name: 'LLaMA 3.1',  detail: '8B · Fastest',         provider: 'groq'   },
  { id: 'mixtral-8x7b-32768',      name: 'Mixtral',    detail: '8×7B · 32k context',   provider: 'groq'   },
  { id: 'gemma2-9b-it',            name: 'Gemma 2',    detail: '9B · Efficient',        provider: 'groq'   },
];
const OLLAMA_MODELS = [
  { id: 'llama3.2',    name: 'LLaMA 3.2',  detail: 'Local · No rate limits', provider: 'ollama' },
  { id: 'llama3.1:8b', name: 'LLaMA 3.1',  detail: 'Local · 8B · Fast',      provider: 'ollama' },
  { id: 'mistral',     name: 'Mistral 7B', detail: 'Local · 7B · Balanced',  provider: 'ollama' },
  { id: 'phi3:mini',   name: 'Phi-3 Mini', detail: 'Local · Lightweight',    provider: 'ollama' },
];
const TOOLS = [
  { name: 'web_search',    label: 'Web Search'    },
  { name: 'calculator',    label: 'Calculator'    },
  { name: 'code_executor', label: 'Code Executor' },
];

// ── Render model grid ─────────────────────────────────────────────
const modelGrid = document.getElementById('model-grid');

function renderModels() {
  if (!modelGrid) return;

  const groqLabel = document.createElement('div');
  groqLabel.className = 'model-section-label';
  groqLabel.textContent = 'Groq — Cloud (fast, requires API key)';
  modelGrid.appendChild(groqLabel);

  GROQ_MODELS.forEach((m, i) => {
    const div = document.createElement('div');
    div.className = 'model-opt';
    div.innerHTML = `
      <input type="radio" name="model" id="m-${m.id}"
        value="${m.id}" data-provider="${m.provider}" ${i === 0 ? 'checked' : ''}>
      <label class="model-lbl" for="m-${m.id}">
        <span class="model-name">${m.name}</span>
        <span class="model-detail">${m.detail}</span>
      </label>`;
    modelGrid.appendChild(div);
  });

  const ollamaLabel = document.createElement('div');
  ollamaLabel.className = 'model-section-label';
  ollamaLabel.style.marginTop = '16px';
  ollamaLabel.textContent = 'Ollama — Local (no rate limits, requires Ollama installed)';
  modelGrid.appendChild(ollamaLabel);

  OLLAMA_MODELS.forEach(m => {
    const div = document.createElement('div');
    div.className = 'model-opt';
    div.innerHTML = `
      <input type="radio" name="model" id="m-${m.id}"
        value="${m.id}" data-provider="${m.provider}">
      <label class="model-lbl ollama-lbl" for="m-${m.id}"
        style="border-color:rgba(74,222,128,0.15);">
        <span class="model-name">${m.name}</span>
        <span class="model-detail" style="color:#4ade80;">${m.detail}</span>
      </label>`;
    const radio = div.querySelector('input');
    radio.addEventListener('change', () => {
      if (radio.checked) {
        div.querySelector('.model-lbl').style.borderColor = 'rgba(74,222,128,0.5)';
        div.querySelector('.model-lbl').style.background  = 'rgba(74,222,128,0.06)';
      }
    });
    modelGrid.appendChild(div);
  });
}

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

// ── Get selected model ────────────────────────────────────────────
function getSelectedModel() {
  const radio = document.querySelector('input[name="model"]:checked');
  if (!radio) return null;
  return { id: radio.value, provider: radio.dataset.provider };
}

// ── Resolve model UUID at submit time (not on page load) ──────────
// This is the key fix: we only call the API when the user clicks
// Create, not on page load. This prevents any redirect on arrival.
async function resolveModelUUID(selected) {
  // Try the public models endpoint first
  try {
    const models = await fetch('http://localhost:8001/api/v1/models').then(r => r.json());
    if (Array.isArray(models)) {
      for (const m of models) {
        if (selected.provider === 'groq'   && m.groq_model_id   === selected.id) return m.id;
        if (selected.provider === 'ollama' && m.ollama_model_id === selected.id) return m.id;
      }
    }
  } catch (_) {}

  // Fallback: infer from platform agents
  try {
    const token   = sessionStorage.getItem('token');
    const agents  = await fetch('http://localhost:8001/api/v1/agents', {
      headers: { 'Authorization': `Bearer ${token}` }
    }).then(r => r.json());

    if (Array.isArray(agents)) {
      for (const a of agents) {
        if (!a.is_platform_agent) continue;
        const n = (a.name || '').toLowerCase();
        let gid = null;
        if (n.includes('llama') && n.includes('70'))    gid = 'llama-3.3-70b-versatile';
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

  // Resolve UUID only at submit time
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

// ── Init — ONLY render UI, no API calls ───────────────────────────
renderModels();