import axios from 'axios';

const rawBase = import.meta.env.VITE_API_BASE_URL || '';
export const API_BASE_URL = (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && (!rawBase || rawBase.includes('localhost')))
  ? ''
  : (rawBase || 'http://localhost:8000');
export const TOKEN_KEY = 'rag_access_token';
export const WORKSPACE_KEY = 'rag_workspace_id';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 180000,
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



export const apiService = {
  // Legacy health and stats
  getHealth: async () => (await apiClient.get('/api/health')).data,
  // Chat models actually pulled on the self-hosted Ollama server.
  getOllamaModels: async () => (await apiClient.get('/api/ollama/models')).data,
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
  // Auth
  signup: async (payload) => (await apiClient.post('/api/auth/signup', payload)).data,
  login: async (payload) => (await apiClient.post('/api/auth/login', payload)).data,
  getMe: async () => (await apiClient.get('/api/auth/me')).data,

  // Workspaces
  getWorkspaces: async () => normalizeList((await apiClient.get('/api/workspaces')).data, ['workspaces']),
  createWorkspace: async (payload) => (await apiClient.post('/api/workspaces', payload)).data,
  deleteWorkspace: async (id) => (await apiClient.delete(`/api/workspaces/${id}`)).data,
  getWorkspace: async (id) => (await apiClient.get(`/api/workspaces/${id}`)).data,

  // Agents
  getAgents: async (ws) => normalizeList((await apiClient.get(`/api/workspaces/${ws}/agents`)).data, ['agents']),
  createAgent: async (ws, payload) => (await apiClient.post(`/api/workspaces/${ws}/agents`, payload)).data,
  updateAgent: async (ws, id, payload) => (await apiClient.patch(`/api/workspaces/${ws}/agents/${id}`, payload)).data,
  deleteAgent: async (ws, id) => (await apiClient.delete(`/api/workspaces/${ws}/agents/${id}`)).data,
  toggleAgentActive: async (ws, id) => (await apiClient.post(`/api/workspaces/${ws}/agents/${id}/toggle-active`)).data,
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
  addAgentDocumentUrl: async (ws, agentId, url, type) => (await apiClient.post(`/api/workspaces/${ws}/agents/${agentId}/documents/url`, { url, type: type || 'url' })).data,
  deleteAgentDocument: async (ws, agentId, docId) => (await apiClient.delete(`/api/workspaces/${ws}/agents/${agentId}/documents/${docId}`)).data,

  // Agent chat and conversations
  chatWithAgent: async (ws, agentId, payload) => (await apiClient.post(`/api/workspaces/${ws}/agents/${agentId}/chat`, payload)).data,
  getConversations: async (ws) => normalizeList((await apiClient.get(`/api/workspaces/${ws}/conversations`)).data, ['conversations']),
  getConversation: async (ws, id) => (await apiClient.get(`/api/workspaces/${ws}/conversations/${id}`)).data,
  deleteConversation: async (ws, id) => (await apiClient.delete(`/api/workspaces/${ws}/conversations/${id}`)).data,

  // API keys
  getApiKeys: async (ws, agentId) => normalizeList((await apiClient.get(`/api/workspaces/${ws}/agents/${agentId}/api-keys`)).data, ['api_keys', 'keys']),
  createApiKey: async (ws, agentId, payload) => (await apiClient.post(`/api/workspaces/${ws}/agents/${agentId}/api-keys`, payload)).data,
  revealApiKey: async (ws, agentId, keyId) => (await apiClient.get(`/api/workspaces/${ws}/agents/${agentId}/api-keys/${keyId}/reveal`)).data,
  deleteApiKey: async (ws, agentId, keyId) => (await apiClient.delete(`/api/workspaces/${ws}/agents/${agentId}/api-keys/${keyId}`)).data,
};

export default apiService;
export { apiClient };
