import { api } from './api.js';

// Redirect if already logged in
if (sessionStorage.getItem('token')) {
    window.location.href = '/dashboard.html';
}

const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const showRegister = document.getElementById('show-register');
const showLogin = document.getElementById('show-login');
const loginError = document.getElementById('login-error');
const registerError = document.getElementById('register-error');

// ─── Toggle between login and register ───────────────────────────────────────
showRegister?.addEventListener('click', () => {
    loginForm.style.display = 'none';
    registerForm.style.display = 'flex';
});

showLogin?.addEventListener('click', () => {
    registerForm.style.display = 'none';
    loginForm.style.display = 'flex';
});

// ─── Login ────────────────────────────────────────────────────────────────────
loginForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    loginError.textContent = '';

    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const btn = loginForm.querySelector('button[type=submit]');

    btn.disabled = true;
    btn.textContent = 'Signing in...';

    try {
        const { access_token } = await api.auth.login(email, password);
        sessionStorage.setItem('token', access_token);
        window.location.href = '/dashboard.html';
    } catch (err) {
        loginError.textContent = err.message;
        btn.disabled = false;
        btn.textContent = 'Sign in';
    }
});

// ─── Register ─────────────────────────────────────────────────────────────────
registerForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    registerError.textContent = '';

    const full_name = document.getElementById('register-name').value.trim();
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    const btn = registerForm.querySelector('button[type=submit]');

    btn.disabled = true;
    btn.textContent = 'Creating account...';

    try {
        await api.auth.register(email, password, full_name);
        // Auto-login after register
        const { access_token } = await api.auth.login(email, password);
        sessionStorage.setItem('token', access_token);
        window.location.href = '/dashboard.html';
    } catch (err) {
        registerError.textContent = err.message;
        btn.disabled = false;
        btn.textContent = 'Create account';
    }
});