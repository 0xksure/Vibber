import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = useAuthStore.getState().refreshToken;
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refreshToken,
        });

        const { accessToken } = response.data;
        useAuthStore.getState().updateTokens({ accessToken });

        originalRequest.headers.Authorization = `Bearer ${accessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        useAuthStore.getState().logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: (email, password) =>
    api.post('/auth/login', { email, password }),

  register: (data) =>
    api.post('/auth/register', data),

  logout: () =>
    api.post('/auth/logout'),

  me: () =>
    api.get('/auth/me'),
};

// Agents API
export const agentsApi = {
  list: () =>
    api.get('/agents'),

  get: (id) =>
    api.get(`/agents/${id}`),

  create: (data) =>
    api.post('/agents', data),

  update: (id, data) =>
    api.put(`/agents/${id}`, data),

  delete: (id) =>
    api.delete(`/agents/${id}`),

  train: (id) =>
    api.post(`/agents/${id}/train`),

  getStatus: (id) =>
    api.get(`/agents/${id}/status`),

  updateSettings: (id, settings) =>
    api.put(`/agents/${id}/settings`, settings),
};

// Integrations API
export const integrationsApi = {
  list: () =>
    api.get('/integrations'),

  connect: (provider, agentId) =>
    api.get(`/integrations/${provider}/connect?agent_id=${agentId}`),

  disconnect: (id) =>
    api.delete(`/integrations/${id}`),

  getStatus: (id) =>
    api.get(`/integrations/${id}/status`),
};

// Interactions API
export const interactionsApi = {
  list: (params) =>
    api.get('/interactions', { params }),

  get: (id) =>
    api.get(`/interactions/${id}`),

  feedback: (id, data) =>
    api.post(`/interactions/${id}/feedback`, data),
};

// Escalations API
export const escalationsApi = {
  list: (agentId) =>
    api.get('/escalations', { params: { agent_id: agentId } }),

  get: (id) =>
    api.get(`/escalations/${id}`),

  resolve: (id, data) =>
    api.post(`/escalations/${id}/resolve`, data),

  approve: (id) =>
    api.post(`/escalations/${id}/approve`),

  reject: (id, data) =>
    api.post(`/escalations/${id}/reject`, data),
};

// Analytics API
export const analyticsApi = {
  overview: (agentId) =>
    api.get('/analytics/overview', { params: { agent_id: agentId } }),

  trends: (agentId, days = 30) =>
    api.get('/analytics/trends', { params: { agent_id: agentId, days } }),

  performance: (agentId) =>
    api.get('/analytics/performance', { params: { agent_id: agentId } }),
};

export default api;
