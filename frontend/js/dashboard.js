import { api } from './api.js';

if (!sessionStorage.getItem('token')) {
    window.location.href = '/index.html';
}

const platformGrid = document.getElementById('platform-agents');
const userGrid = document.getElementById('user-agents');
const userNameEl = document.getElementById('user-name');
const logoutBtn = document.getElementById('logout-btn');

// ─── Logout ───────────────────────────────────────────────────────────────────
logoutBtn?.addEventListener('click', () => {
    sessionStorage.clear();
    window.location.href = '/index.html';
});

// ─── Load user info ───────────────────────────────────────────────────────────
async function loadUser() {
    try {
        const user = await api.auth.me();
        if (userNameEl) userNameEl.textContent = user.full_name;
    } catch (_) { }
}

// ─── Render agent card ────────────────────────────────────────────────────────
function renderCard(agent) {
    const card = document.createElement('div');
    card.className = 'agent-card';
    card.innerHTML = `
    <div class="agent-card-header">
      <span class="agent-card-name">${agent.name}</span>
      <span class="tag ${agent.is_platform_agent ? 'tag-platform' : 'tag-user'}">
        ${agent.is_platform_agent ? 'Platform' : 'Mine'}
      </span>
    </div>
    <p class="agent-card-desc">${agent.description || 'No description provided.'}</p>
    <div class="agent-card-footer">
      <span class="agent-card-model">${agent.model_id}</span>
      <div class="agent-card-actions">
        <button class="chat-btn" title="Chat">💬 Chat</button>
        ${!agent.is_platform_agent ? `<button class="delete-btn" title="Delete">✕</button>` : ''}
      </div>
    </div>
  `;

    // Chat button
    card.querySelector('.chat-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        sessionStorage.setItem('active_agent_id', agent.id);
        sessionStorage.setItem('active_agent_name', agent.name);
        window.location.href = '/chat.html';
    });

    // Delete button (user agents only)
    card.querySelector('.delete-btn')?.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (!confirm(`Delete "${agent.name}"?`)) return;
        try {
            await api.agents.delete(agent.id);
            card.remove();
        } catch (err) {
            alert(err.message);
        }
    });

    return card;
}

// ─── Load agents ──────────────────────────────────────────────────────────────
async function loadAgents() {
    try {
        const agents = await api.agents.list();

        const platform = agents.filter(a => a.is_platform_agent);
        const mine = agents.filter(a => !a.is_platform_agent);

        platformGrid.innerHTML = '';
        userGrid.innerHTML = '';

        if (platform.length === 0) {
            platformGrid.innerHTML = '<p class="empty-state">No platform agents found.</p>';
        } else {
            platform.forEach(a => platformGrid.appendChild(renderCard(a)));
        }

        if (mine.length === 0) {
            userGrid.innerHTML = '<p class="empty-state">You haven\'t created any agents yet.</p>';
        } else {
            mine.forEach(a => userGrid.appendChild(renderCard(a)));
        }
    } catch (err) {
        platformGrid.innerHTML = `<p class="empty-state">${err.message}</p>`;
    }
}

loadUser();
loadAgents();