const BASE = 'http://localhost:8001';
const token = () => sessionStorage.getItem('token');
const authH = () => ({ 'Content-Type': 'application/json', 'Authorization': `Bearer ${token()}` });

async function req(method, path, body = null, auth = true) {
  const opts = { method, headers: auth ? authH() : { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${BASE}${path}`, opts);
  if (res.status === 401) { sessionStorage.clear(); window.location.href = '/index.html'; return; }
  const data = res.status !== 204 ? await res.json() : null;
  if (!res.ok) {
    const msg = data?.detail || 'Something went wrong';
    throw new Error(typeof msg === 'string' ? msg : msg.map?.(e => e.msg || e).join(', ') || JSON.stringify(msg));
  }
  return data;
}

export const api = {
  auth: {
    register: (email, password, full_name) => req('POST', '/api/v1/auth/register', { email, password, full_name }, false),
    login:    (email, password)            => req('POST', '/api/v1/auth/login',    { email, password }, false),
    me:       ()                           => req('GET',  '/api/v1/auth/me'),
  },
  models: {
    list: () => req('GET', '/api/v1/models', null, false),
  },
  agents: {
    list:   ()         => req('GET',    '/api/v1/agents'),
    get:    id         => req('GET',    `/api/v1/agents/${id}`),
    create: data       => req('POST',   '/api/v1/agents', data),
    update: (id, data) => req('PATCH',  `/api/v1/agents/${id}`, data),
    delete: id         => req('DELETE', `/api/v1/agents/${id}`),
  },
  conversations: {
    list:   ()    => req('GET',    '/api/v1/conversations'),
    get:    id    => req('GET',    `/api/v1/conversations/${id}`),
    create: agentId => req('POST', '/api/v1/conversations', { agent_id: agentId }),
    delete: id    => req('DELETE', `/api/v1/conversations/${id}`),
  },
  messages: {
    send: (cid, content) => req('POST', `/api/v1/conversations/${cid}/messages`, { content }),
  },
};

// Provider switch
export const providerApi = {
  switch: (conversationId, provider) =>
    req('POST', `/api/v1/conversations/${conversationId}/switch-provider`, { provider }),
};