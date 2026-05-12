import { api } from './api.js';

if (!sessionStorage.getItem('token')) {
    window.location.href = '/index.html';
}

// ─── State ────────────────────────────────────────────────────────────────────
let activeConversationId = null;
let activeAgentId = sessionStorage.getItem('active_agent_id');
let activeAgentName = sessionStorage.getItem('active_agent_name');
let isSending = false;

// ─── DOM ──────────────────────────────────────────────────────────────────────
const sidebarList = document.getElementById('sidebar-list');
const messagesEl = document.getElementById('messages');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const chatAgentName = document.getElementById('chat-agent-name');
const newChatBtn = document.getElementById('new-chat-btn');
const logoutBtn = document.getElementById('logout-btn');
const chatEmptyEl = document.getElementById('chat-empty');
const chatAreaContent = document.getElementById('chat-area-content');

logoutBtn?.addEventListener('click', () => {
    sessionStorage.clear();
    window.location.href = '/index.html';
});

// ─── Set agent name in header ─────────────────────────────────────────────────
if (chatAgentName && activeAgentName) {
    chatAgentName.textContent = activeAgentName;
}

// ─── Render a single message bubble ──────────────────────────────────────────
function renderMessage(role, content) {
    const wrapper = document.createElement('div');
    wrapper.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'U' : 'AI';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = content;

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    messagesEl.appendChild(wrapper);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ─── Typing indicator ─────────────────────────────────────────────────────────
function showTyping() {
    const wrapper = document.createElement('div');
    wrapper.className = 'message assistant';
    wrapper.id = 'typing-indicator';
    wrapper.innerHTML = `
    <div class="message-avatar">AI</div>
    <div class="message-bubble">
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
    messagesEl.appendChild(wrapper);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function hideTyping() {
    document.getElementById('typing-indicator')?.remove();
}

// ─── Load conversation history ────────────────────────────────────────────────
async function loadConversation(conversationId) {
    activeConversationId = conversationId;
    messagesEl.innerHTML = '';

    // Mark active in sidebar
    document.querySelectorAll('.sidebar-item').forEach(el => {
        el.classList.toggle('active', el.dataset.id === conversationId);
    });

    try {
        const conv = await api.conversations.get(conversationId);
        const messages = conv.messages || [];

        if (chatEmptyEl) chatEmptyEl.style.display = 'none';
        if (chatAreaContent) chatAreaContent.style.display = 'flex';

        messages.forEach(m => {
            if (m.role !== 'system') renderMessage(m.role, m.content);
        });

        chatInput.focus();
    } catch (err) {
        messagesEl.innerHTML = `<p style="color:var(--danger);font-size:13px;">${err.message}</p>`;
    }
}

// ─── Load sidebar conversation list ──────────────────────────────────────────
async function loadSidebar() {
    try {
        const conversations = await api.conversations.list();

        // Filter to conversations with this agent
        const filtered = activeAgentId
            ? conversations.filter(c => c.agent_id === activeAgentId)
            : conversations;

        sidebarList.innerHTML = '';

        if (filtered.length === 0) {
            sidebarList.innerHTML = '<p class="sidebar-empty">No conversations yet.</p>';
            return;
        }

        filtered.forEach(conv => {
            const item = document.createElement('div');
            item.className = 'sidebar-item';
            item.dataset.id = conv.id;
            item.innerHTML = `
        <div class="sidebar-item-title">${conv.title || 'New conversation'}</div>
        <div class="sidebar-item-meta">${new Date(conv.updated_at).toLocaleDateString()}</div>
      `;
            item.addEventListener('click', () => loadConversation(conv.id));
            sidebarList.appendChild(item);
        });

        // Auto-load most recent
        if (filtered.length > 0 && !activeConversationId) {
            loadConversation(filtered[0].id);
        }
    } catch (err) {
        sidebarList.innerHTML = `<p class="sidebar-empty">${err.message}</p>`;
    }
}

// ─── New conversation ─────────────────────────────────────────────────────────
newChatBtn?.addEventListener('click', async () => {
    if (!activeAgentId) {
        alert('No agent selected. Go back to the dashboard and click Chat on an agent.');
        return;
    }
    try {
        const conv = await api.conversations.create(activeAgentId);
        activeConversationId = conv.id;
        messagesEl.innerHTML = '';
        if (chatEmptyEl) chatEmptyEl.style.display = 'none';
        if (chatAreaContent) chatAreaContent.style.display = 'flex';
        await loadSidebar();
        loadConversation(conv.id);
    } catch (err) {
        alert(err.message);
    }
});

// ─── Send message ─────────────────────────────────────────────────────────────
async function sendMessage() {
    if (isSending) return;
    const content = chatInput.value.trim();
    if (!content) return;

    if (!activeConversationId) {
        // Auto-create a conversation if none is active
        if (!activeAgentId) {
            alert('No agent selected.');
            return;
        }
        try {
            const conv = await api.conversations.create(activeAgentId);
            activeConversationId = conv.id;
            await loadSidebar();
        } catch (err) {
            alert(err.message);
            return;
        }
    }

    isSending = true;
    sendBtn.disabled = true;
    chatInput.value = '';
    chatInput.style.height = 'auto';

    if (chatEmptyEl) chatEmptyEl.style.display = 'none';
    if (chatAreaContent) chatAreaContent.style.display = 'flex';

    renderMessage('user', content);
    showTyping();

    try {
        const response = await api.messages.send(activeConversationId, content);
        hideTyping();
        renderMessage('assistant', response.content);
        // Refresh sidebar to update title
        await loadSidebar();
    } catch (err) {
        hideTyping();
        renderMessage('assistant', `Error: ${err.message}`);
    } finally {
        isSending = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

sendBtn?.addEventListener('click', sendMessage);

chatInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Auto-resize textarea
chatInput?.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 140) + 'px';
});

// ─── Init ─────────────────────────────────────────────────────────────────────
loadSidebar();