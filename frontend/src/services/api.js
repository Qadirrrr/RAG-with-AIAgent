import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 180000,
});

export function apiError(err, fallback = 'Request failed. Please try again.') {
  return err?.response?.data?.detail || err?.response?.data?.message || err?.message || fallback;
}

export const apiService = {
  // Health check
  getHealth: async () => (await apiClient.get('/api/health')).data,

  // Direct chat
  sendMessage: async (message, history = []) => {
    const res = await apiClient.post('/api/chat', { message, history });
    return res.data;
  },

  // Documents
  getDocuments: async () => {
    const res = await apiClient.get('/api/documents');
    return Array.isArray(res.data) ? res.data : [];
  },

  uploadDocument: async (file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/api/documents', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress,
    });
    return res.data;
  },

  deleteDocument: async (documentId) => {
    const res = await apiClient.delete(`/api/documents/${documentId}`);
    return res.data;
  },
};

export default apiService;
export { apiClient };
