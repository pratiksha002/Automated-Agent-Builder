import { api } from './api.js';
import { toast } from './ui.js';

if (!sessionStorage.getItem('token')) window.location.href = '/index.html';

document.getElementById('logout-btn')?.addEventListener('click', () => { sessionStorage.clear(); window.location.href = '/index.html'; });
document.getElementById('back-btn')?.addEventListener('click', () => window.location.href = '/dashboard.html');

const MODELS = [
  { id: 'llama-3.3-70b-versatile', name: 'LLaMA 3.3',  detail: '70B · Best quality' },
  { id: 'llama-3.1-8b-instant',    name: 'LLaMA 3.1',  detail: '8B · Fastest'        },
  { id: 'mixtral-8x7b-32768',      name: 'Mixtral',    detail: '8×7B · 32k context'  },
  { id: 'gemma2-9b-it',            name: 'Gemma 2',    detail: '9B · Efficient'       },
];
const TOOLS = [
  { name: 'web_search',    label: 'Web Search'    },
  { name: 'calculator',    label: 'Calculator'    },
  { name: 'code_executor', label: 'Code Executor' },
];

// Populate models
const modelGrid = document.getElementById('model-grid');
MODELS.forEach((m, i) => {
  const div = document.createElement('div');
  div.className = 'model-opt';
  div.innerHTML = `
    <input type="radio" name="model" id="m-${m.id}" value="${m.id}" ${i === 0 ? 'checked' : ''}>
    <label class="model-lbl" for="m-${m.id}">
      <span class="model-name">${m.name}</span>
      <span class="model-detail">${m.detail}</span>
    </label>`;
  modelGrid?.appendChild(div);
});

// Populate tools
const toolsGrid = document.getElementById('tools-grid');
TOOLS.forEach(t => {
  const lbl = document.createElement('label');
  lbl.className = 'tool-lbl';
  lbl.innerHTML = `<input type="checkbox" value="${t.name}"> ${t.label}`;
  const cb = lbl.querySelector('input');
  cb.addEventListener('change', () => lbl.classList.toggle('checked', cb.checked));
  toolsGrid?.appendChild(lbl);
});

// Prompt counter
const promptEl = document.getElementById('agent-prompt');
const countEl  = document.getElementById('prompt-count');
promptEl?.addEventListener('input', () => { if (countEl) countEl.textContent = promptEl.value.length + ' chars'; });

// We need a real model UUID to send to the backend.
// Fetch the platform agents to build a groq_model_id → UUID map.
let modelUuidMap = {};
async function buildModelMap() {
  try {
    const agents = await api.agents.list();
    const platform = agents.filter(a => a.is_platform_agent);
    for (const a of platform) {
      const det = await api.agents.get(a.id);
      // We don't have groq_model_id from AgentRead, but we can infer it
      // from the agent name which the seed sets deterministically.
      const n = (det.name || '').toLowerCase();
      let groqId = null;
      if (n.includes('llama') && n.includes('70')) groqId = 'llama-3.3-70b-versatile';
      else if (n.includes('llama') && n.includes('8'))  groqId = 'llama-3.1-8b-instant';
      else if (n.includes('mixtral'))                   groqId = 'mixtral-8x7b-32768';
      else if (n.includes('gemma'))                     groqId = 'gemma2-9b-it';
      if (groqId) modelUuidMap[groqId] = det.model_id;
    }
  } catch (_) {}
}
buildModelMap();

document.getElementById('create-form')?.addEventListener('submit', async e => {
  e.preventDefault();
  const errEl = document.getElementById('form-error');
  const btn   = e.target.querySelector('button[type=submit]');
  errEl.textContent = '';

  const name        = document.getElementById('agent-name').value.trim();
  const description = document.getElementById('agent-desc').value.trim();
  const system_prompt = promptEl?.value.trim();
  const groqId      = document.querySelector('input[name="model"]:checked')?.value || MODELS[0].id;
  const tools       = Array.from(toolsGrid?.querySelectorAll('input:checked') || []).map(cb => ({ tool_name: cb.value, tool_config: {} }));

  if (!name || !system_prompt) { errEl.textContent = 'Name and system prompt are required.'; return; }

  const model_id = modelUuidMap[groqId];
  if (!model_id) { errEl.textContent = 'Model not resolved yet — try again in a moment.'; return; }

  btn.disabled = true; btn.textContent = 'Creating…';
  try {
    await api.agents.create({ name, description, system_prompt, model_id, tools });
    toast(`"${name}" created!`, 'success');
    setTimeout(() => window.location.href = '/dashboard.html', 700);
  } catch (err) {
    errEl.textContent = err.message;
    btn.disabled = false; btn.textContent = 'Create Agent';
  }
});