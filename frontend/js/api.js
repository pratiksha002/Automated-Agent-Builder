const BASE_URL = 'http://localhost:8001';

function getToken() {
    return sessionStorage.getItem('token');
}

function authHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`,
    };
}

async function request(method, path, body = null, auth = true) {
    const headers = auth ? authHeaders() : { 'Content-Type': 'application/json' };
    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);

    const res = await fetch(`${BASE_URL}${path}`, options);

    if (res.status === 401) {
        sessionStorage.clear();
        window.location.href = '/index.html';
        return;
    }

    const data = res.status !== 204 ? await res.json() : null;

    if (!res.ok) {
        const msg = data?.detail || 'Something went wrong';
        throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }

    return data;
}

// ─── Auth ────────────────────────────────────────────────────────────────────
export const api = {
    auth: {
        register: (email, password, full_name) =>
            request('POST', '/api/v1/auth/register', { email, password, full_name }, false),

        login: (email, password) =>
            request('POST', '/api/v1/auth/login', { email, password }, false),

        me: () =>
            request('GET', '/api/v1/auth/me'),
    },

    // ─── Agents ──────────────────────────────────────────────────────────────
    agents: {
        list: () =>
            request('GET', '/api/v1/agents'),

        get: (id) =>
            request('GET', `/api/v1/agents/${id}`),

        create: (data) =>
            request('POST', '/api/v1/agents', data),

        update: (id, data) =>
            request('PATCH', `/api/v1/agents/${id}`, data),

        delete: (id) =>
            request('DELETE', `/api/v1/agents/${id}`),
    },

    // ─── Conversations ────────────────────────────────────────────────────────
    conversations: {
        list: () =>
            request('GET', '/api/v1/conversations'),

        get: (id) =>
            request('GET', `/api/v1/conversations/${id}`),

        create: (agent_id) =>
            request('POST', '/api/v1/conversations', { agent_id }),

        delete: (id) =>
            request('DELETE', `/api/v1/conversations/${id}`),
    },

    // ─── Messages ─────────────────────────────────────────────────────────────
    messages: {
        send: (conversation_id, content) =>
            request('POST', `/api/v1/conversations/${conversation_id}/messages`, { content }),
    },
};