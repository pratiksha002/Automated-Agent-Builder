// ── Toast notification utility ────────────────────────────────────────────────
// Usage: import { toast } from './toast.js'
//        toast('Message sent!', 'success')
//        toast('Something went wrong', 'error')

function getContainer() {
  let c = document.getElementById('toast-container');
  if (!c) {
    c = document.createElement('div');
    c.id = 'toast-container';
    document.body.appendChild(c);
  }
  return c;
}

export function toast(message, type = 'info', duration = 3500) {
  const container = getContainer();
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;

  const icons = { error: '✕', success: '✓', info: 'ℹ' };
  el.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span>${message}</span>`;

  container.appendChild(el);

  const dismiss = () => {
    el.classList.add('toast-out');
    el.addEventListener('animationend', () => el.remove(), { once: true });
  };

  el.addEventListener('click', dismiss);
  setTimeout(dismiss, duration);
}