import { api } from './api.js';
import { toast, confirmDialog } from './ui.js';

if (!sessionStorage.getItem('token')) window.location.href = '/index.html';

const platformGrid = document.getElementById('platform-agents');
const userGrid     = document.getElementById('user-agents');
const userNameEl   = document.getElementById('user-name');

document.getElementById('logout-btn')?.addEventListener('click', () => {
  sessionStorage.clear(); window.location.href = '/index.html';
});

// Model display names — keyed by the groq_model_id string (never UUIDs)
const MODEL_NAMES = {
  'llama-3.3-70b-versatile': 'LLaMA 3.3 · 70B',
  'llama-3.1-8b-instant':    'LLaMA 3.1 · 8B',
  'mixtral-8x7b-32768':      'Mixtral · 8×7B',
  'gemma2-9b-it':            'Gemma 2 · 9B',
};

// We need the model name from the model detail. Since AgentListItem only returns
// model_id (a UUID), we fetch all models once and build a lookup map.
let modelMap = {}; // uuid → display name

async function loadModelMap() {
  // Platform agents always have is_platform_agent=true; we fetch one detail to
  // get the Model relationship. However the backend /agents list returns model_id UUID.
  // We build the map by fetching full detail of each platform agent (cheap, few calls).
  // This avoids showing raw UUIDs anywhere on the UI.
  try {
    const agents = await api.agents.list();
    const platform = agents.filter(a => a.is_platform_agent);
    await Promise.all(platform.map(async a => {
      if (!modelMap[a.model_id]) {
        const detail = await api.agents.get(a.id);
        // AgentRead has model_id UUID — we still need the groq string.
        // Since the seed is deterministic, map by checking the detail name.
        // Fallback: just mark as known so we don't re-fetch.
        modelMap[a.model_id] = resolveName(detail);
      }
    }));
  } catch (_) {}
}

function resolveName(agentDetail) {
  // Try to infer from agent name as fallback
  const n = (agentDetail.name || '').toLowerCase();
  if (n.includes('llama') && n.includes('70')) return 'LLaMA 3.3 · 70B';
  if (n.includes('llama') && n.includes('8'))  return 'LLaMA 3.1 · 8B';
  if (n.includes('mixtral'))                   return 'Mixtral · 8×7B';
  if (n.includes('gemma'))                     return 'Gemma 2 · 9B';
  return 'Language Model';
}

function skeletons(grid, n = 3) {
  grid.innerHTML = Array(n).fill('<div class="skeleton skeleton-card"></div>').join('');
}

function svgIcon(type) {
  const icons = {
    cpu:    '<polyline points="9 3 9 21"/><polyline points="15 3 15 21"/><polyline points="3 9 21 9"/><polyline points="3 15 21 15"/>',
    chat:   '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    trash:  '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    bot:    '<rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/>',
    plus:   '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  };
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="width:14px;height:14px">${icons[type]||''}</svg>`;
}

function renderCard(agent) {
  const card = document.createElement('div');
  card.className = 'agent-card';
  const modelName   = modelMap[agent.model_id] || 'Language Model';
  const platformTag = agent.is_platform_agent ? 'Platform' : 'Custom';
  const tagClass    = agent.is_platform_agent ? 'tag-platform' : 'tag-user';

  // Footer: Chat button + 3-dot menu (custom agents only)
  const menuBtn = !agent.is_platform_agent
    ? '<button class="card-menu-btn" title="More options" aria-label="More options">'
      + '<span></span><span></span><span></span>'
      + '</button>'
      + '<div class="card-dropdown">'
      + '<button class="card-dropdown-item fb-item">Feedback &amp; Improve</button>'
      + '<button class="card-dropdown-item del-item danger">Delete agent</button>'
      + '</div>'
    : '';

  card.innerHTML =
    '<div class="agent-card-top">'
    + '<div class="agent-card-name">' + agent.name + '</div>'
    + '<span class="tag ' + tagClass + '">' + platformTag + '</span>'
    + '</div>'
    + '<p class="agent-card-desc">' + (agent.description || 'No description provided.') + '</p>'
    + '<div class="agent-card-footer">'
    + '<span class="agent-card-meta">' + modelName + '</span>'
    + '<div class="agent-card-actions">'
    + '<button class="btn btn-sm btn-primary chat-btn">Chat</button>'
    + '<div class="card-menu-wrap">' + menuBtn + '</div>'
    + '</div>'
    + '</div>';

  // Chat
  card.querySelector('.chat-btn').addEventListener('click', e => {
    e.stopPropagation();
    sessionStorage.setItem('active_agent_id',    agent.id);
    sessionStorage.setItem('active_agent_name',  agent.name);
    sessionStorage.setItem('active_agent_model', modelName);
    window.location.href = '/chat.html';
  });

  // 3-dot toggle
  const menuWrap  = card.querySelector('.card-menu-wrap');
  const menuBtnEl = card.querySelector('.card-menu-btn');
  const dropdown  = card.querySelector('.card-dropdown');

  if (menuBtnEl && dropdown) {
    menuBtnEl.addEventListener('click', e => {
      e.stopPropagation();
      const isOpen = dropdown.classList.contains('open');
      // Close all other open dropdowns
      document.querySelectorAll('.card-dropdown.open').forEach(d => d.classList.remove('open'));
      if (!isOpen) dropdown.classList.add('open');
    });
  }

  // Feedback
  card.querySelector('.fb-item')?.addEventListener('click', e => {
    e.stopPropagation();
    window.location.href = '/feedback.html?agent=' + agent.id + '&name=' + encodeURIComponent(agent.name);
  });

  // Delete
  card.querySelector('.del-item')?.addEventListener('click', async e => {
    e.stopPropagation();
    if (dropdown) dropdown.classList.remove('open');
    const ok = await confirmDialog('Delete agent', '"' + agent.name + '" will be permanently deleted. This cannot be undone.');
    if (!ok) return;
    try {
      await api.agents.delete(agent.id);
      card.style.transition = 'opacity 200ms, transform 200ms';
      card.style.opacity = '0';
      card.style.transform = 'scale(0.96)';
      setTimeout(() => card.remove(), 220);
      toast('"' + agent.name + '" deleted', 'success');
    } catch (err) { toast(err.message, 'error'); }
  });

  return card;
}


async function loadAgents() {
  skeletons(platformGrid, 3); skeletons(userGrid, 2);
  try {
    await loadModelMap();
    const agents   = await api.agents.list();
    const platform = agents.filter(a =>  a.is_platform_agent);
    const mine     = agents.filter(a => !a.is_platform_agent);

    platformGrid.innerHTML = '';
    userGrid.innerHTML     = '';

    if (!platform.length) {
      platformGrid.innerHTML = `<div class="empty-state">
        <svg viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/></svg>
        <div class="empty-state-title">No platform agents yet</div>
        <p>Check back soon.</p></div>`;
    } else { platform.forEach(a => platformGrid.appendChild(renderCard(a))); }

    if (!mine.length) {
      userGrid.innerHTML = `<div class="empty-state">
        <svg viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        <div class="empty-state-title">No custom agents yet</div>
        <p>Click <strong>New Agent</strong> above to create your first one.</p></div>`;
    } else { mine.forEach(a => userGrid.appendChild(renderCard(a))); }
  } catch (err) { toast(err.message, 'error'); }
}

async function loadUser() {
  try { const u = await api.auth.me(); if (userNameEl) userNameEl.textContent = u.full_name; } catch (_) {}
}

loadUser(); loadAgents();

// Close any open dropdown when clicking outside a card
document.addEventListener('click', () => {
  document.querySelectorAll('.card-dropdown.open').forEach(d => d.classList.remove('open'));
});