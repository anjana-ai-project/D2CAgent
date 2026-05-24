const BASE_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000';

const api = {
  health: async () => {
    const res = await fetch(`${BASE_URL}/health`);
    return res.json();
  },

  getAgents: async () => {
    const res = await fetch(`${BASE_URL}/agents`);
    return res.json();
  },

  getAgent: async (agentId) => {
    const res = await fetch(`${BASE_URL}/agents/${agentId}`);
    return res.json();
  },

  createAgent: async (agent) => {
    const res = await fetch(`${BASE_URL}/agents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(agent)
    });
    return res.json();
  },

  updateAgent: async (agentId, update) => {
    const res = await fetch(`${BASE_URL}/agents/${agentId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(update)
    });
    return res.json();
  },

  deleteAgent: async (agentId) => {
    const res = await fetch(`${BASE_URL}/agents/${agentId}`, {
      method: 'DELETE'
    });
    return res.json();
  },

  getWorkflows: async () => {
    const res = await fetch(`${BASE_URL}/workflows`);
    return res.json();
  },

  getLogs: async (limit = 50) => {
    const res = await fetch(
      `${BASE_URL}/monitoring/logs?limit=${limit}`);
    return res.json();
  },

  getConversations: async (limit = 50) => {
    const res = await fetch(
      `${BASE_URL}/monitoring/conversations?limit=${limit}`);
    return res.json();
  },

  getFlags: async () => {
    const res = await fetch(`${BASE_URL}/monitoring/flags`);
    return res.json();
  },

  resolveFlag: async (flagId) => {
    const res = await fetch(
      `${BASE_URL}/monitoring/flags/${flagId}/resolve`,
      { method: 'PUT' }
    );
    return res.json();
  },

  getRuns: async (limit = 20) => {
    const res = await fetch(
      `${BASE_URL}/monitoring/runs?limit=${limit}`);
    return res.json();
  },

  getProducts: async () => {
    const res = await fetch(`${BASE_URL}/products`);
    return res.json();
  },

  connectMonitor: (onMessage) => {
    const ws = new WebSocket(`${WS_URL}/ws/monitor`);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error('WS parse error:', e);
      }
    };
    ws.onerror = (e) => console.error('WS error:', e);
    ws.onclose = () => console.log('WS disconnected');
    return ws;
  }
};

export default api;