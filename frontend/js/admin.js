const BASE_URL = 'https://automated-agent-builder.onrender.com';

function getAdminToken() {
  return sessionStorage.getItem('admin_token');
}

function adminHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getAdminToken()}`,
  };
}

async function adminRequest(method, path, body = null, auth = true) {
  const headers = auth ? adminHeaders() : { 'Content-Type': 'application/json' };
  const options = { method, headers };
  if (body) options.body = JSON.stringify(body);

  const res = await fetch(`${BASE_URL}${path}`, options);

  if (res.status === 401) {
    sessionStorage.removeItem('admin_token');
    window.location.href = '/admin-login.html';
    return;
  }

  const data = res.status !== 204 ? await res.json() : null;
  if (!res.ok) throw new Error(data?.detail || 'Request failed');
  return data;
}

// ─── State ────────────────────────────────────────────────────────────────────
let allUsers = [];
let usageChart = null;

// ─── DOM ──────────────────────────────────────────────────────────────────────
const statsBar = document.getElementById('stats-bar');
const userGrid = document.getElementById('user-grid');
const flagsBody = document.getElementById('flags-body');
const drawerOverlay = document.getElementById('drawer-overlay');
const drawer = document.getElementById('user-drawer');
const drawerContent = document.getElementById('drawer-content');
const logoutBtn = document.getElementById('logout-btn');
const userSearch = document.getElementById('user-search');

// ─── Redirect if not logged in ────────────────────────────────────────────────
if (!getAdminToken()) {
  window.location.href = '/admin-login.html';
}

// ─── Logout ───────────────────────────────────────────────────────────────────
logoutBtn?.addEventListener('click', () => {
  sessionStorage.removeItem('admin_token');
  window.location.href = '/admin-login.html';
});

// ─── Load global stats ────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const s = await adminRequest('GET', '/api/v1/admin/dashboard');
    statsBar.innerHTML = `
      <div class="stat-card">
        <div class="stat-label">Total Users</div>
        <div class="stat-value accent">${s.total_users}</div>
        <div class="stat-sub">${s.active_users_today} active today</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Banned Users</div>
        <div class="stat-value ${s.banned_users > 0 ? 'danger' : ''}">${s.banned_users}</div>
        <div class="stat-sub">&nbsp;</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Agents</div>
        <div class="stat-value">${s.total_agents}</div>
        <div class="stat-sub">${s.user_agents} user / ${s.platform_agents} platform</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Messages</div>
        <div class="stat-value">${s.total_messages}</div>
        <div class="stat-sub">${s.messages_24h} last 24h</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Unreviewed Flags</div>
        <div class="stat-value ${s.unreviewed_flags > 0 ? 'danger' : 'success'}">${s.unreviewed_flags}</div>
        <div class="stat-sub">${s.total_flags} total</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Most Used Agent</div>
        <div class="stat-value" style="font-size:17px;margin-top:4px;">${s.most_used_agent || 'N/A'}</div>
        <div class="stat-sub">${s.most_used_agent_count} uses</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Groq vs Ollama</div>
        <div class="stat-value accent" style="font-size:22px;">${s.groq_usage_pct}%</div>
        <div class="stat-sub">Groq · ${s.ollama_usage_pct}% Ollama</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Avg Response</div>
        <div class="stat-value">${s.avg_response_ms}</div>
        <div class="stat-sub">milliseconds</div>
      </div>
    `;
  } catch (err) {
    statsBar.innerHTML = `<p style="color:var(--danger);font-family:var(--font-mono);font-size:13px;">${err.message}</p>`;
  }
}

// ─── Load users ───────────────────────────────────────────────────────────────
async function loadUsers() {
  try {
    allUsers = await adminRequest('GET', '/api/v1/admin/users');
    renderUsers(allUsers);
  } catch (err) {
    userGrid.innerHTML = `<p style="color:var(--danger);font-family:var(--font-mono);font-size:13px;">${err.message}</p>`;
  }
}

function renderUsers(users) {
  userGrid.innerHTML = '';
  if (users.length === 0) {
    userGrid.innerHTML = '<p style="color:var(--text-3);font-family:var(--font-mono);font-size:13px;">No users found.</p>';
    return;
  }
  users.forEach(u => {
    const card = document.createElement('div');
    card.className = `user-card${u.is_banned ? ' banned' : ''}`;
    card.innerHTML = `
      <div class="user-card-header">
        <div class="user-avatar">${u.full_name[0].toUpperCase()}</div>
        <div class="user-name">${u.full_name}</div>
        ${u.is_banned
        ? '<span class="tag" style="background:var(--danger-bg);color:var(--danger);border:1px solid rgba(240,92,92,0.3);font-size:9px;">BANNED</span>'
        : ''}
      </div>
      <div class="user-email">${u.email}</div>
      <div class="user-meta">
        <span>Joined ${new Date(u.created_at).toLocaleDateString()}</span>
        <span>${u.is_active ? 'Active' : 'Inactive'}</span>
      </div>
    `;
    card.addEventListener('click', () => openUserDrawer(u));
    userGrid.appendChild(card);
  });
}

// ─── Search ───────────────────────────────────────────────────────────────────
userSearch?.addEventListener('input', () => {
  const q = userSearch.value.toLowerCase();
  renderUsers(allUsers.filter(u =>
    u.full_name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
  ));
});

// ─── User Drawer ──────────────────────────────────────────────────────────────
async function openUserDrawer(user) {
  drawerContent.innerHTML = `
    <div style="display:grid;place-items:center;height:200px;color:var(--text-3);font-family:var(--font-mono);font-size:13px;">
      Loading...
    </div>`;
  drawerOverlay.classList.add('open');
  drawer.classList.add('open');

  try {
    const detail = await adminRequest('GET', `/api/v1/admin/users/${user.id}`);
    const s = detail.stats;
    const u = detail.user;

    drawerContent.innerHTML = `
      <div class="drawer-header">
        <div>
          <div class="drawer-title">${u.full_name}</div>
          <div class="drawer-subtitle">${u.email}</div>
        </div>
        <button class="drawer-close" id="close-drawer">✕</button>
      </div>

      <div class="drawer-stats">
        <div class="drawer-stat">
          <div class="stat-label">Messages Sent</div>
          <div class="stat-value accent">${s.total_messages}</div>
        </div>
        <div class="drawer-stat">
          <div class="stat-label">Agents Created</div>
          <div class="stat-value">${s.total_agents}</div>
        </div>
        <div class="drawer-stat">
          <div class="stat-label">Conversations</div>
          <div class="stat-value">${s.total_conversations}</div>
        </div>
        <div class="drawer-stat">
          <div class="stat-label">Flags Raised</div>
          <div class="stat-value ${s.total_flags > 0 ? 'danger' : ''}">${s.total_flags}</div>
        </div>
        <div class="drawer-stat">
          <div class="stat-label">Avg Response</div>
          <div class="stat-value">${s.avg_response_ms}<span style="font-size:13px;color:var(--text-3)">ms</span></div>
        </div>
        <div class="drawer-stat">
          <div class="stat-label">Top Agent</div>
          <div style="font-size:14px;font-weight:600;color:var(--text);margin-top:6px;font-family:var(--font-body);">${s.most_used_agent || 'N/A'}</div>
        </div>
      </div>

      <div class="drawer-actions">
        ${u.is_banned
        ? `<button class="btn btn-outline btn-sm" id="unban-btn">Unban User</button>`
        : `<button class="btn btn-danger btn-sm" id="ban-btn">Ban User</button>`
      }
      </div>

      <div class="chart-section-title">Messages — Last 30 Days</div>
      <div class="chart-container">
        <canvas id="usage-chart"></canvas>
      </div>

      ${s.recent_flags.length > 0 ? `
        <div class="chart-section-title" style="margin-top:8px;">Recent Flags</div>
        <table class="flags-table">
          <thead><tr><th>Type</th><th>Reason</th><th>Date</th></tr></thead>
          <tbody>
            ${s.recent_flags.map(f => `
              <tr>
                <td><span class="flag-type ${f.flag_type}">${f.flag_type}</span></td>
                <td style="color:var(--text-3);font-size:12px;">${f.flag_reason || '—'}</td>
                <td style="font-family:var(--font-mono);font-size:11px;color:var(--text-3);">${new Date(f.created_at).toLocaleDateString()}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      ` : ''}
    `;

    document.getElementById('close-drawer')?.addEventListener('click', closeDrawer);

    document.getElementById('ban-btn')?.addEventListener('click', async () => {
      if (!confirm(`Ban ${u.full_name}? They will not be able to log in.`)) return;
      await adminRequest('POST', `/api/v1/admin/users/${u.id}/ban`);
      closeDrawer();
      loadUsers();
    });

    document.getElementById('unban-btn')?.addEventListener('click', async () => {
      await adminRequest('POST', `/api/v1/admin/users/${u.id}/unban`);
      closeDrawer();
      loadUsers();
    });

    renderUsageChart(s.daily_usage);

  } catch (err) {
    drawerContent.innerHTML = `<p style="color:var(--danger);font-family:var(--font-mono);font-size:13px;padding:20px;">${err.message}</p>`;
  }
}

function closeDrawer() {
  drawer.classList.remove('open');
  drawerOverlay.classList.remove('open');
  if (usageChart) { usageChart.destroy(); usageChart = null; }
}

drawerOverlay?.addEventListener('click', closeDrawer);

// ─── Usage Chart ──────────────────────────────────────────────────────────────
function renderUsageChart(dailyUsage) {
  const ctx = document.getElementById('usage-chart');
  if (!ctx || !window.Chart) return;
  if (usageChart) usageChart.destroy();

  usageChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: dailyUsage.map(d => d.date),
      datasets: [{
        label: 'Messages',
        data: dailyUsage.map(d => d.count),
        borderColor: '#7c6df0',
        backgroundColor: 'rgba(124,109,240,0.08)',
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: '#9d91f5',
        fill: true,
        tension: 0.4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          ticks: { color: '#606078', font: { family: 'JetBrains Mono', size: 10 } },
          grid: { color: '#252530' },
        },
        y: {
          ticks: { color: '#606078', font: { family: 'JetBrains Mono', size: 10 } },
          grid: { color: '#252530' },
          beginAtZero: true,
        },
      },
    },
  });
}

// ─── Load Flags ───────────────────────────────────────────────────────────────
async function loadFlags() {
  try {
    const flags = await adminRequest('GET', '/api/v1/admin/flags?reviewed=false');
    flagsBody.innerHTML = '';

    if (flags.length === 0) {
      flagsBody.innerHTML = `
        <tr>
          <td colspan="5" style="color:var(--text-3);font-family:var(--font-mono);font-size:13px;padding:20px 14px;">
            No unreviewed flags.
          </td>
        </tr>`;
      return;
    }

    flags.forEach(f => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><span class="flag-type ${f.flag_type}">${f.flag_type}</span></td>
        <td style="font-size:12px;color:var(--text-3);">${f.flag_reason || '—'}</td>
        <td style="font-family:var(--font-mono);font-size:11px;color:var(--text-3);">${f.user_id.slice(0, 8)}...</td>
        <td style="font-family:var(--font-mono);font-size:11px;color:var(--text-3);">${new Date(f.created_at).toLocaleDateString()}</td>
        <td><button class="review-btn" data-id="${f.id}">Review</button></td>
      `;
      tr.querySelector('.review-btn').addEventListener('click', async (e) => {
        const btn = e.target;
        btn.disabled = true;
        btn.textContent = 'Done';
        try {
          await adminRequest('PATCH', `/api/v1/admin/flags/${f.id}/review`);
          tr.style.opacity = '0.35';
        } catch (err) {
          btn.disabled = false;
          btn.textContent = 'Review';
        }
      });
      flagsBody.appendChild(tr);
    });
  } catch (err) {
    flagsBody.innerHTML = `
      <tr>
        <td colspan="5" style="color:var(--danger);font-family:var(--font-mono);font-size:13px;padding:14px;">
          ${err.message}
        </td>
      </tr>`;
  }
}

// ─── Init ─────────────────────────────────────────────────────────────────────
loadStats();
loadUsers();
loadFlags();