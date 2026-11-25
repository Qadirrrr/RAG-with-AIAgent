import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const TOKEN_KEY = 'rag_access_token';
export const WORKSPACE_KEY = 'rag_workspace_id';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000,
});

apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let onUnauthorized = null;
export function setUnauthorizedHandler(fn) { onUnauthorized = fn; }

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401 && onUnauthorized) onUnauthorized();
    return Promise.reject(err);
  }
);

export function normalizeList(data, keys = []) {
  if (Array.isArray(data)) return data;
  if (data && typeof data === 'object') {
    for (const k of keys) if (Array.isArray(data[k])) return data[k];
    if (Array.isArray(data.items)) return data.items;
    if (Array.isArray(data.results)) return data.results;
  }
  return [];
}

export function apiError(err, fallback = 'Request failed. Please try again.') {
  return err?.response?.data?.detail || err?.response?.data?.message || err?.message || fallback;
}

export const FALLBACK_PLANS = [
  { id: 'free', name: 'Free', price: 0, currency: 'USD', interval: 'month', agents_limit: 1, messages_limit: 100, documents_limit: 10, features: ['1 AI agent', '100 messages per month', '10 documents', 'Community support'] },
  { id: 'starter', name: 'Starter', price: 19, currency: 'USD', interval: 'month', agents_limit: 3, messages_limit: 1000, documents_limit: 50, features: ['3 AI agents', '1,000 messages per month', '50 documents', 'Website widget', 'Email support'] },
  { id: 'pro', name: 'Pro', price: 49, currency: 'USD', interval: 'month', agents_limit: 10, messages_limit: 10000, documents_limit: 200, features: ['10 AI agents', '10,000 messages per month', '200 documents', 'REST API access', 'Analytics', 'Priority support'] },
  { id: 'scale', name: 'Scale', price: 99, currency: 'USD', interval: 'month', agents_limit: 50, messages_limit: 50000, documents_limit: 1000, features: ['50 AI agents', '50,000 messages per month', '1,000 documents', 'REST API access', 'Advanced analytics', 'Dedicated support'] },
];

export const MODEL_OPTIONS = {
  gemini: ['gemini-3.5-flash-lite'],
  openai: ['gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo'],
};

export const apiService = {
  // Legacy health and stats
  getHealth: async () => (await apiClient.get('/api/health')).data,
  getStats: async () => (await apiClient.get('/api/stats')).data,
  getDocuments: async () => (await apiClient.get('/api/documents')).data,
  uploadDocument: async (file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/api/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress,
    });
    return res.data;
  },
  deleteDocument: async (documentId) => (await apiClient.delete(`/api/documents/${documentId}`)).data,
  sendMessage: async (message, history = []) => (await apiClient.post('/api/chat', { message, history })).data,

  // Auth
  signup: async (payload) => (await apiClient.post('/api/auth/signup', payload)).data,
  login: async (payload) => (await apiClient.post('/api/auth/login', payload)).data,
  getMe: async () => (await apiClient.get('/api/auth/me')).data,

  // Workspaces
  getWorkspaces: async () => normalizeList((await apiClient.get('/api/workspaces')).data, ['workspaces']),
  createWorkspace: async (payload) => (await apiClient.post('/api/workspaces', payload)).data,
  getWorkspace: async (id) => (await apiClient.get(`/api/workspaces/${id}`)).data,

  // Agents
  getAgents: async (ws) => normalizeList((await apiClient.get(`/api/workspaces/${ws}/agents`)).data, ['agents']),
  createAgent: async (ws, payload) => (await apiClient.post(`/api/workspaces/${ws}/agents`, payload)).data,
  updateAgent: async (ws, id, payload) => (await apiClient.patch(`/api/workspaces/${ws}/agents/${id}`, payload)).data,
  deleteAgent: async (ws, id) => (await apiClient.delete(`/api/workspaces/${ws}/agents/${id}`)).data,
  getAgent: async (ws, id) => (await apiClient.get(`/api/workspaces/${ws}/agents/${id}`)).data,

  // Agent documents and knowledge
  getAgentDocuments: async (ws, agentId) => normalizeList((await apiClient.get(`/api/workspaces/${ws}/agents/${agentId}/documents`)).data, ['documents']),
  uploadAgentDocument: async (ws, agentId, file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post(`/api/workspaces/${ws}/agents/${agentId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress,
    });
    return res.data;
  },
  addAgentDocumentUrl: async (ws, agentId, url) => (await apiClient.post(`/api/workspaces/${ws}/agents/${agentId}/documents/url`, { url })).data,
  deleteAgentDocument: async (ws, agentId, docId) => (await apiClient.delete(`/api/workspaces/${ws}/agents/${agentId}/documents/${docId}`)).data,

  // Agent chat and conversations
  chatWithAgent: async (ws, agentId, payload) => (await apiClient.post(`/api/workspaces/${ws}/agents/${agentId}/chat`, payload)).data,
  getConversations: async (ws) => normalizeList((await apiClient.get(`/api/workspaces/${ws}/conversations`)).data, ['conversations']),
  getConversation: async (ws, id) => (await apiClient.get(`/api/workspaces/${ws}/conversations/${id}`)).data,

  // Analytics
  getAnalytics: async (ws) => (await apiClient.get(`/api/workspaces/${ws}/analytics`)).data,

  // API keys
  getApiKeys: async (ws, agentId) => normalizeList((await apiClient.get(`/api/workspaces/${ws}/agents/${agentId}/api-keys`)).data, ['api_keys', 'keys']),
  createApiKey: async (ws, agentId, payload) => (await apiClient.post(`/api/workspaces/${ws}/agents/${agentId}/api-keys`, payload)).data,
  deleteApiKey: async (ws, agentId, keyId) => (await apiClient.delete(`/api/workspaces/${ws}/agents/${agentId}/api-keys/${keyId}`)).data,

  // Plans and billing
  getPlans: async () => {
    try {
      return normalizeList((await apiClient.get('/api/plans')).data, ['plans']);
    } catch {
      return FALLBACK_PLANS;
    }
  },
  changeSubscription: async (ws, plan) => (await apiClient.post(`/api/workspaces/${ws}/subscription`, { plan })).data,

  // Admin
  getAdminOverview: async () => (await apiClient.get('/api/admin/overview')).data,
  getAdminUsers: async () => normalizeList((await apiClient.get('/api/admin/users')).data, ['users']),
};

export default apiService;
export { apiClient };
