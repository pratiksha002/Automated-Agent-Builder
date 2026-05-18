import { api } from './api.js';

if (sessionStorage.getItem('token')) window.location.href = '/dashboard.html';

const loginPanel    = document.getElementById('login-panel');
const registerPanel = document.getElementById('register-panel');

document.getElementById('show-register')?.addEventListener('click', () => {
  loginPanel.classList.add('panel-hidden');
  registerPanel.classList.remove('panel-hidden');
});
document.getElementById('show-login')?.addEventListener('click', () => {
  registerPanel.classList.add('panel-hidden');
  loginPanel.classList.remove('panel-hidden');
});

document.getElementById('login-form')?.addEventListener('submit', async e => {
  e.preventDefault();
  const errEl = document.getElementById('login-error');
  const btn   = e.target.querySelector('button[type=submit]');
  errEl.textContent = '';
  btn.disabled = true; btn.textContent = 'Signing in…';
  try {
    const { access_token } = await api.auth.login(
      document.getElementById('login-email').value.trim(),
      document.getElementById('login-password').value,
    );
    sessionStorage.setItem('token', access_token);
    window.location.href = '/dashboard.html';
  } catch (err) {
    errEl.textContent = err.message;
    btn.disabled = false; btn.textContent = 'Sign in';
  }
});

document.getElementById('register-form')?.addEventListener('submit', async e => {
  e.preventDefault();
  const errEl = document.getElementById('register-error');
  const btn   = e.target.querySelector('button[type=submit]');
  errEl.textContent = '';
  btn.disabled = true; btn.textContent = 'Creating account…';
  try {
    const email    = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;
    const full_name = document.getElementById('reg-name').value.trim();
    await api.auth.register(email, password, full_name);
    const { access_token } = await api.auth.login(email, password);
    sessionStorage.setItem('token', access_token);
    window.location.href = '/dashboard.html';
  } catch (err) {
    errEl.textContent = err.message;
    btn.disabled = false; btn.textContent = 'Create account';
  }
});