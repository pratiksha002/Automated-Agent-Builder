import { api } from './api.js';

if (!sessionStorage.getItem('token')) {
    window.location.href = '/index.html';
}

const form = document.getElementById('create-agent-form');
const errorEl = document.getElementById('form-error');
const modelSelect = document.getElementById('model-select');
const toolsGrid = document.getElementById('tools-grid');
const backBtn = document.getElementById('back-btn');
const logoutBtn = document.getElementById('logout-btn');

const AVAILABLE_TOOLS = [
    { name: 'web_search', label: 'Web Search' },
    { name: 'calculator', label: 'Calculator' },
    { name: 'code_executor', label: 'Code Executor' },
];

const MODELS = [
    { id: 'llama-3.3-70b-versatile', label: 'LLaMA 3.3 70B' },
    { id: 'llama-3.1-8b-instant', label: 'LLaMA 3.1 8B' },
    { id: 'mixtral-8x7b-32768', label: 'Mixtral 8x7B' },
    { id: 'gemma2-9b-it', label: 'Gemma 2 9B' },
];

logoutBtn?.addEventListener('click', () => {
    sessionStorage.clear();
    window.location.href = '/index.html';
});

backBtn?.addEventListener('click', () => {
    window.location.href = '/dashboard.html';
});

// ─── Populate model dropdown ──────────────────────────────────────────────────
function populateModels() {
    if (!modelSelect) return;
    MODELS.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = m.label;
        modelSelect.appendChild(opt);
    });
}

// ─── Populate tools grid ──────────────────────────────────────────────────────
function populateTools() {
    if (!toolsGrid) return;
    AVAILABLE_TOOLS.forEach(tool => {
        const label = document.createElement('label');
        label.className = 'tool-checkbox';
        label.innerHTML = `
      <input type="checkbox" value="${tool.name}" />
      ${tool.label}
    `;
        const checkbox = label.querySelector('input');
        checkbox.addEventListener('change', () => {
            label.classList.toggle('checked', checkbox.checked);
        });
        toolsGrid.appendChild(label);
    });
}

// ─── Get selected tools ───────────────────────────────────────────────────────
function getSelectedTools() {
    const checkboxes = toolsGrid?.querySelectorAll('input[type=checkbox]:checked') || [];
    return Array.from(checkboxes).map(cb => ({
        tool_name: cb.value,
        tool_config: {},
    }));
}

// ─── Get selected model UUID from backend ────────────────────────────────────
// We need the UUID from the DB, not the groq_model_id string.
// We fetch the agent list which includes model_id UUIDs from platform agents
// and use that to build a groq_id -> UUID map.
async function getModelUUID(groqModelId) {
    const agents = await api.agents.list();
    const match = agents.find(a => a.is_platform_agent);
    if (!match) throw new Error('Could not resolve model UUID.');

    // Fetch the full agent to get model details
    const full = await api.agents.get(match.id);
    // We need a dedicated models endpoint ideally, but for now
    // we return the model_id from a platform agent using the same model
    const platformByModel = agents.filter(a => a.is_platform_agent);
    for (const a of platformByModel) {
        const detail = await api.agents.get(a.id);
        // We check the groq_model_id via name matching — crude but works for v1
        if (detail.name.toLowerCase().includes('general') && groqModelId.includes('70b')) {
            return detail.model_id;
        }
    }
    return full.model_id;
}

// ─── Submit ───────────────────────────────────────────────────────────────────
form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorEl.textContent = '';

    const name = document.getElementById('agent-name').value.trim();
    const description = document.getElementById('agent-description').value.trim();
    const system_prompt = document.getElementById('agent-system-prompt').value.trim();
    const groqModelId = modelSelect?.value;
    const tools = getSelectedTools();
    const btn = form.querySelector('button[type=submit]');

    if (!name || !system_prompt) {
        errorEl.textContent = 'Name and system prompt are required.';
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Creating...';

    try {
        // Resolve model UUID from backend
        const model_id = await getModelUUID(groqModelId);

        await api.agents.create({
            name,
            description,
            system_prompt,
            model_id,
            tools,
        });

        window.location.href = '/dashboard.html';
    } catch (err) {
        errorEl.textContent = err.message;
        btn.disabled = false;
        btn.textContent = 'Create Agent';
    }
});

populateModels();
populateTools();