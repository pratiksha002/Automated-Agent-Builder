import { api, providerApi } from './api.js';
import { toast, confirmDialog, relativeTime, formatTime } from './ui.js';

if (!sessionStorage.getItem('token')) window.location.href = '/index.html';

// ── State ─────────────────────────────────────────────────────────────────
let activeCid    = null;
let isSending    = false;
let allConvs     = [];
const agentId    = sessionStorage.getItem('active_agent_id');
const agentName  = sessionStorage.getItem('active_agent_name') || 'Agent';
const agentModel = sessionStorage.getItem('active_agent_model') || '';

// ── DOM ───────────────────────────────────────────────────────────────────
const sidebarList   = document.getElementById('sidebar-list');
const searchInput   = document.getElementById('sidebar-search');
const msgWrap       = document.getElementById('messages');
const chatInput     = document.getElementById('chat-input');
const sendBtn       = document.getElementById('send-btn');
const charCountEl   = document.getElementById('char-count');
const welcomeEl     = document.getElementById('chat-welcome');
const chatContentEl = document.getElementById('chat-content');
const newBtn        = document.getElementById('new-chat-btn');
const headerName    = document.getElementById('chat-agent-name');
const headerSub     = document.getElementById('chat-agent-sub');
const startersEl    = document.getElementById('starters');

// Provider UI
const providerBadge  = document.getElementById('provider-badge');
const providerLabel  = document.getElementById('provider-label');
const switchBtn      = document.getElementById('switch-provider-btn');
const fallbackBanner = document.getElementById('fallback-banner');
const fallbackClose  = document.getElementById('fallback-banner-close');

let currentProvider = 'groq';

// ── Init header ───────────────────────────────────────────────────────────
if (headerName) headerName.textContent = agentName;
if (headerSub)  headerSub.textContent  = agentModel;

document.getElementById('logout-btn')?.addEventListener('click', () => {
  sessionStorage.clear(); window.location.href = '/index.html';
});

// ── Provider UI helpers ───────────────────────────────────────────────────
function updateProviderUI(provider) {
  currentProvider = provider;
  const isGroq = provider === 'groq';
  if (providerBadge) providerBadge.className = `provider-badge ${provider}`;
  if (providerLabel) providerLabel.textContent = isGroq ? 'Groq' : 'Ollama';
  if (switchBtn) {
    switchBtn.textContent = isGroq ? 'Switch to Ollama' : 'Switch to Groq';
    switchBtn.title = isGroq
      ? 'Switch to local Ollama inference (no rate limits)'
      : 'Switch back to Groq cloud inference';
  }
}

fallbackClose?.addEventListener('click', () => {
  fallbackBanner?.classList.remove('show');
});

switchBtn?.addEventListener('click', async () => {
  if (!activeCid) { toast('Start a conversation first.', 'info'); return; }
  const target = currentProvider === 'groq' ? 'ollama' : 'groq';
  switchBtn.disabled = true;
  try {
    const result = await providerApi.switch(activeCid, target);
    updateProviderUI(result.provider);
    toast(result.message, 'success', 4000);
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    switchBtn.disabled = false;
  }
});

// ── Greeting & agent-aware starters ──────────────────────────────────────
const hour = new Date().getHours();
const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

function getStarters(name) {
  const n = (name || '').toLowerCase();
  if (n.includes('support') || n.includes('help'))
    return [
      'I have an issue I need help with.',
      'Can you walk me through troubleshooting steps?',
      'What kinds of problems can you solve?',
      'How do I escalate an unresolved issue?',
    ];
  if (n.includes('code') || n.includes('dev') || n.includes('engineer'))
    return [
      'Review this code snippet for me.',
      'What is the best way to structure a REST API?',
      'Explain the difference between async and sync in Python.',
      'Help me debug a function that returns unexpected output.',
    ];
  if (n.includes('research') || n.includes('data') || n.includes('analyst'))
    return [
      'Summarise the key findings from a topic for me.',
      'What are the most important papers on transformer models?',
      'Help me structure a research methodology.',
      'Compare and contrast two approaches to a problem.',
    ];
  if (n.includes('write') || n.includes('content') || n.includes('copy'))
    return [
      'Write a short LinkedIn post about AI productivity.',
      'Give me five headline ideas for a product launch.',
      'Rewrite this paragraph to be more concise.',
      'What makes a compelling product description?',
    ];
  if (n.includes('tutor') || n.includes('teach') || n.includes('learn'))
    return [
      'Explain this concept as if I\'m a beginner.',
      'Give me a practice problem to test my understanding.',
      'What are the most important fundamentals to master first?',
      'Create a short study plan for me.',
    ];
  return [
    'What can you help me with today?',
    'Give me a quick overview of your capabilities.',
    'Help me think through a complex problem.',
    'What is the best way to get started?',
  ];
}

if (startersEl) {
  getStarters(agentName).forEach(s => {
    const btn = document.createElement('button');
    btn.className = 'starter'; btn.textContent = s;
    btn.addEventListener('click', () => {
      chatInput.value = s;
      chatInput.dispatchEvent(new Event('input'));
      sendMessage();
    });
    startersEl.appendChild(btn);
  });
}

// Inject greeting
const greetingEl = document.getElementById('chat-greeting');
if (greetingEl) {
  greetingEl.innerHTML = `
    <span style="color:var(--text-3);font-size:13px;font-family:var(--font-mono)">${greeting}</span>
    <h2 style="font-family:var(--font-display);font-size:24px;font-weight:800;letter-spacing:-0.03em;margin:6px 0 8px">
      I'm <span style="color:var(--violet-2)">${agentName}</span>
    </h2>
    <p style="font-size:14px;color:var(--text-2);max-width:360px;line-height:1.6">
      Ready to help. Pick a suggestion below or type your own question to get started.
    </p>`;
}

// ── Markdown (CDN) ────────────────────────────────────────────────────────
let markedReady = false;
const ms = document.createElement('script');
ms.src = 'https://cdn.jsdelivr.net/npm/marked@9/marked.min.js';
ms.onload = () => { window.marked.setOptions({ breaks: true, gfm: true }); markedReady = true; };
document.head.appendChild(ms);

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function renderMd(text) {
  if (!markedReady || !window.marked) return escHtml(text).replace(/\n/g,'<br>');
  let html = window.marked.parse(text);
  html = html.replace(
    /<pre><code(?: class="language-(\w+)")?>([\s\S]*?)<\/code><\/pre>/g,
    (_, lang, code) => `
      <pre>
        <div class="code-header">
          <span>${lang || 'code'}</span>
          <button class="code-copy" data-code="${encodeURIComponent(code)}">Copy</button>
        </div>
        <code${lang ? ` class="language-${lang}"` : ''}>${code}</code>
      </pre>`
  );
  return html;
}

function attachCodeCopy(el) {
  el.querySelectorAll('.code-copy').forEach(btn => {
    btn.addEventListener('click', () => {
      navigator.clipboard.writeText(decodeURIComponent(btn.dataset.code || '')).then(() => {
        btn.textContent = 'Copied!'; btn.classList.add('done');
        setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('done'); }, 2000);
      });
    });
  });
}

// ── Render message bubble ─────────────────────────────────────────────────
function renderMessage(role, content, ts = null, messageId = null) {
  const wrap = document.createElement('div');
  wrap.className = `msg ${role}`;
  const timeStr = ts ? formatTime(ts) : formatTime(new Date().toISOString());
  const initials = role === 'user' ? 'You' : 'AI';
  const html = role === 'assistant' ? renderMd(content) : `<p>${escHtml(content)}</p>`;

  wrap.innerHTML = `
    <div class="msg-avatar">${initials}</div>
    <div class="msg-content">
      <div class="msg-bubble">${html}</div>
      <div class="msg-actions">
        <span class="msg-time">${timeStr}</span>
        <button class="msg-act copy-btn" title="Copy message">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            style="width:11px;height:11px">
            <rect x="9" y="9" width="13" height="13" rx="2"/>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
          Copy
        </button>
      </div>
    </div>`;

  wrap.querySelector('.copy-btn').addEventListener('click', () => {
    navigator.clipboard.writeText(content).then(() => {
      const btn = wrap.querySelector('.copy-btn');
      btn.textContent = 'Copied'; btn.classList.add('done');
      setTimeout(() => {
        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy`;
        btn.classList.remove('done');
      }, 2000);
    });
  });

  attachCodeCopy(wrap);
  msgWrap.appendChild(wrap);
  msgWrap.scrollTop = msgWrap.scrollHeight;
  return wrap;
}

// ── Stream text word-by-word ──────────────────────────────────────────────
async function streamInto(bubble, fullText) {
  const words = fullText.split(' ');
  let acc = '';
  bubble.classList.add('streaming-cursor');
  for (let i = 0; i < words.length; i++) {
    acc += (i ? ' ' : '') + words[i];
    bubble.innerHTML = markedReady && window.marked
      ? window.marked.parse(acc)
      : escHtml(acc).replace(/\n/g, '<br>');
    msgWrap.scrollTop = msgWrap.scrollHeight;
    await new Promise(r => setTimeout(r, words[i].length > 7 ? 20 : 13));
  }
  bubble.classList.remove('streaming-cursor');
  bubble.innerHTML = renderMd(fullText);
  attachCodeCopy(bubble);
  msgWrap.scrollTop = msgWrap.scrollHeight;
}

// ── Typing indicator ──────────────────────────────────────────────────────
function showTyping() {
  const el = document.createElement('div');
  el.className = 'msg assistant'; el.id = 'typing';
  el.innerHTML = `
    <div class="msg-avatar">AI</div>
    <div class="msg-content"><div class="msg-bubble">
      <div class="typing">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div></div>`;
  msgWrap.appendChild(el);
  msgWrap.scrollTop = msgWrap.scrollHeight;
}
function hideTyping() { document.getElementById('typing')?.remove(); }

// ── Load conversation ─────────────────────────────────────────────────────
async function loadConv(id) {
  activeCid = id;
  msgWrap.innerHTML = '';
  document.querySelectorAll('.s-item').forEach(el =>
    el.classList.toggle('active', el.dataset.id === id));
  if (welcomeEl)     welcomeEl.style.display     = 'none';
  if (chatContentEl) chatContentEl.style.display = 'flex';
  if (fallbackBanner) fallbackBanner.classList.remove('show');
  try {
    const conv = await api.conversations.get(id);
    // Sync provider badge to what was saved for this conversation
    if (conv.current_provider) updateProviderUI(conv.current_provider);
    (conv.messages || [])
      .filter(m => m.role !== 'system')
      .forEach(m => renderMessage(m.role, m.content, m.created_at, m.id));
    chatInput.focus();
  } catch (err) { toast(err.message, 'error'); }
}

// ── Sidebar ───────────────────────────────────────────────────────────────
function renderSidebar(convs) {
  sidebarList.innerHTML = '';
  if (!convs.length) {
    sidebarList.innerHTML = '<p class="sidebar-empty">No conversations yet.<br>Click + New to start one.</p>';
    return;
  }
  convs.forEach(c => {
    const el = document.createElement('div');
    el.className = 's-item' + (c.id === activeCid ? ' active' : '');
    el.dataset.id = c.id;
    el.innerHTML = `
      <div class="s-item-indicator"></div>
      <div class="s-item-body">
        <div class="s-item-title">${escHtml(c.title || 'New conversation')}</div>
        <div class="s-item-meta">${relativeTime(c.updated_at)}</div>
      </div>
      <button class="s-item-del" title="Delete conversation">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
          style="width:11px;height:11px;pointer-events:none">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>`;

    el.addEventListener('click', e => {
      if (e.target.closest('.s-item-del')) return;
      loadConv(c.id);
    });

    el.querySelector('.s-item-del').addEventListener('click', async e => {
      e.stopPropagation();
      const ok = await confirmDialog(
        'Delete conversation',
        'This conversation and all its messages will be permanently deleted.'
      );
      if (!ok) return;
      try {
        await api.conversations.delete(c.id);
        allConvs = allConvs.filter(x => x.id !== c.id);
        if (activeCid === c.id) {
          activeCid = null; msgWrap.innerHTML = '';
          if (welcomeEl)     welcomeEl.style.display     = 'flex';
          if (chatContentEl) chatContentEl.style.display = 'none';
          if (fallbackBanner) fallbackBanner.classList.remove('show');
          updateProviderUI('groq');
        }
        renderSidebar(filtered());
        toast('Conversation deleted', 'success');
      } catch (err) { toast(err.message, 'error'); }
    });

    sidebarList.appendChild(el);
  });
}

function filtered() {
  const q = (searchInput?.value || '').trim().toLowerCase();
  const base = agentId
    ? allConvs.filter(c => c.agent_id === agentId)
    : allConvs;
  return q ? base.filter(c => (c.title || '').toLowerCase().includes(q)) : base;
}

async function loadSidebar(autoFirst = false) {
  try {
    allConvs = await api.conversations.list();
    renderSidebar(filtered());
    if (autoFirst && !activeCid && filtered().length) {
      loadConv(filtered()[0].id);
    }
  } catch (err) {
    sidebarList.innerHTML = `<p class="sidebar-empty">${escHtml(err.message)}</p>`;
  }
}

searchInput?.addEventListener('input', () => renderSidebar(filtered()));

// ── New chat ──────────────────────────────────────────────────────────────
newBtn?.addEventListener('click', async () => {
  if (!agentId) { toast('No agent selected. Return to the dashboard.', 'error'); return; }
  try {
    const c = await api.conversations.create(agentId);
    activeCid = c.id;
    msgWrap.innerHTML = '';
    if (welcomeEl)     welcomeEl.style.display     = 'flex';
    if (chatContentEl) chatContentEl.style.display = 'none';
    if (fallbackBanner) fallbackBanner.classList.remove('show');
    if (c.current_provider) updateProviderUI(c.current_provider);
    await loadSidebar();
    chatInput.focus();
  } catch (err) { toast(err.message, 'error'); }
});

// ── Send message ──────────────────────────────────────────────────────────
async function sendMessage() {
  if (isSending) return;
  const content = chatInput.value.trim();
  if (!content) return;

  if (!activeCid) {
    if (!agentId) { toast('No agent selected.', 'error'); return; }
    try {
      const c = await api.conversations.create(agentId);
      activeCid = c.id;
      if (c.current_provider) updateProviderUI(c.current_provider);
      await loadSidebar();
    } catch (err) { toast(err.message, 'error'); return; }
  }

  isSending = true; sendBtn.disabled = true;
  if (welcomeEl)     welcomeEl.style.display     = 'none';
  if (chatContentEl) chatContentEl.style.display = 'flex';
  chatInput.value = ''; chatInput.style.height = 'auto';
  if (charCountEl) charCountEl.textContent = '0';

  renderMessage('user', content);
  showTyping();

  try {
    const res = await api.messages.send(activeCid, content);
    hideTyping();

    // Update provider badge
    if (res.provider) updateProviderUI(res.provider);

    // Show fallback banner if Groq was rate-limited and Ollama took over
    if (res.was_fallback && fallbackBanner) {
      fallbackBanner.classList.add('show');
    }

    // Build assistant wrapper
    const wrap = document.createElement('div');
    wrap.className = 'msg assistant';
    const now = new Date().toISOString();
    wrap.innerHTML = `
      <div class="msg-avatar">AI</div>
      <div class="msg-content">
        <div class="msg-bubble"></div>
        <div class="msg-actions">
          <span class="msg-time">${formatTime(now)}</span>
          <button class="msg-act copy-btn" title="Copy message">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              style="width:11px;height:11px">
              <rect x="9" y="9" width="13" height="13" rx="2"/>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
            Copy
          </button>
        </div>
      </div>`;

    wrap.querySelector('.copy-btn').addEventListener('click', () => {
      navigator.clipboard.writeText(res.content).then(() => {
        const btn = wrap.querySelector('.copy-btn');
        btn.textContent = 'Copied'; btn.classList.add('done');
        setTimeout(() => {
          btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy`;
          btn.classList.remove('done');
        }, 2000);
      });
    });

    msgWrap.appendChild(wrap);
    await streamInto(wrap.querySelector('.msg-bubble'), res.content);
    await loadSidebar();

  } catch (err) {
    hideTyping();
    renderMessage('assistant', `Something went wrong: ${err.message}`);
    toast(err.message, 'error');
  } finally {
    isSending = false; sendBtn.disabled = false; chatInput.focus();
  }
}

sendBtn?.addEventListener('click', sendMessage);
chatInput?.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
chatInput?.addEventListener('input', () => {
  chatInput.style.height = 'auto';
  chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + 'px';
  const l = chatInput.value.length;
  if (charCountEl) {
    charCountEl.textContent = l;
    charCountEl.className = 'char-count' + (l > 1800 ? ' warn' : '');
  }
});

// ── Init ──────────────────────────────────────────────────────────────────
loadSidebar(true);