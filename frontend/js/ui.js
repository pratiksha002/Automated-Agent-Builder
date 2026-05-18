/* ─── Toast ───────────────────────────────────────────────────────── */
let _tc = null;
function tc() {
  if (!_tc) {
    _tc = document.createElement('div');
    _tc.id = 'toast-container';
    document.body.appendChild(_tc);
  }
  return _tc;
}
export function toast(msg, type = 'info', ms = 3500) {
  const icons = { error: '✕', success: '✓', info: 'i' };
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.innerHTML = `<span style="font-family:var(--font-mono);font-size:12px;flex-shrink:0">${icons[type]||'i'}</span><span>${msg}</span>`;
  tc().appendChild(el);
  setTimeout(() => { el.classList.add('out'); el.addEventListener('animationend', () => el.remove(), { once: true }); }, ms);
}

/* ─── Confirm dialog ──────────────────────────────────────────────── */
export function confirmDialog(title, body, confirmLabel = 'Delete', danger = true) {
  return new Promise(resolve => {
    const ov = document.createElement('div');
    ov.className = 'confirm-overlay';
    ov.innerHTML = `
      <div class="confirm-box">
        <h3>${title}</h3>
        <p>${body}</p>
        <div class="confirm-actions">
          <button class="btn btn-ghost" id="_cc">Cancel</button>
          <button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" id="_co" style="${danger ? 'border:1px solid var(--danger)' : ''}">${confirmLabel}</button>
        </div>
      </div>`;
    document.body.appendChild(ov);
    ov.querySelector('#_cc').onclick = () => { ov.remove(); resolve(false); };
    ov.querySelector('#_co').onclick = () => { ov.remove(); resolve(true); };
    ov.addEventListener('click', e => { if (e.target === ov) { ov.remove(); resolve(false); } });
  });
}

/* ─── Time helpers ────────────────────────────────────────────────── */
export function relativeTime(d) {
  const diff = Date.now() - new Date(d).getTime();
  const m = Math.floor(diff / 60000), h = Math.floor(diff / 3600000), dd = Math.floor(diff / 86400000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  if (h < 24) return `${h}h ago`;
  if (dd < 7) return `${dd}d ago`;
  return new Date(d).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
export function formatTime(d) {
  return new Date(d).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

/* ─── Scroll animation (IntersectionObserver) ────────────────────── */
export function observeFadeIn(selector = '[data-fade]') {
  const els = document.querySelectorAll(selector);
  if (!els.length) return;
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); io.unobserve(e.target); } });
  }, { threshold: 0.1 });
  els.forEach(el => { el.style.opacity = '0'; el.style.transform = 'translateY(24px)'; el.style.transition = 'opacity 0.55s var(--ease), transform 0.55s var(--ease)'; io.observe(el); });
  // add visible style once
  if (!document.getElementById('_fade-style')) {
    const s = document.createElement('style'); s.id = '_fade-style';
    s.textContent = '[data-fade].visible { opacity: 1 !important; transform: none !important; }';
    document.head.appendChild(s);
  }
}