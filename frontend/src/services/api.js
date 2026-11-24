import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60 seconds for RAG agent calls
});

export const apiService = {
  // Health
  getHealth: async () => {
    const response = await apiClient.get('/api/health');
    return response.data;
  },

  // Stats
  getStats: async () => {
    const response = await apiClient.get('/api/stats');
    return response.data;
  },

  // Documents
  getDocuments: async () => {
    const response = await apiClient.get('/api/documents');
    return response.data;
  },

  uploadDocument: async (file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post('/api/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
    });
    return response.data;
  },

  deleteDocument: async (documentId) => {
    const response = await apiClient.delete(`/api/documents/${documentId}`);
    return response.data;
  },

  // Chat with AI Agent
  sendMessage: async (message, history = []) => {
    const response = await apiClient.post('/api/chat', {
      message,
      history,
    });
    return response.data;
  },
};

export default apiService;

