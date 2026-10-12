import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import type { Token } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

class ApiClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        if (this.accessToken && config.headers) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.clearToken();
          if (typeof window !== 'undefined') {
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );

    // Load token from localStorage on init
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('access_token');
      if (stored) {
        this.accessToken = stored;
      }
    }
  }

  setToken(token: string) {
    this.accessToken = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', token);
    }
  }

  clearToken() {
    this.accessToken = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
    }
  }

  getToken(): string | null {
    return this.accessToken;
  }

  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  // Auth
  async login(username: string, password: string): Promise<Token> {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    const response = await this.client.post<Token>('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    this.setToken(response.data.access_token);
    return response.data;
  }

  async register(data: { email: string; password: string; full_name?: string; role: string }): Promise<Token> {
    const response = await this.client.post<Token>('/auth/register', data);
    this.setToken(response.data.access_token);
    return response.data;
  }

  async getMe() {
    const response = await this.client.get('/auth/me');
    return response.data;
  }

  logout() {
    this.clearToken();
  }

  // Incidents
  async listIncidents(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    severity?: string;
  }) {
    const response = await this.client.get('/incidents', { params });
    return response.data;
  }

  async getIncident(id: number) {
    const response = await this.client.get(`/incidents/${id}`);
    return response.data;
  }

  async createIncident(data: { title: string; description: string; raw_data?: string }) {
    const response = await this.client.post('/incidents', data);
    return response.data;
  }

  async updateIncident(id: number, data: Partial<{ title: string; description: string; status: string; severity: string }>) {
    const response = await this.client.patch(`/incidents/${id}`, data);
    return response.data;
  }

  async deleteIncident(id: number) {
    await this.client.delete(`/incidents/${id}`);
  }

  // Triage
  async triageIncident(incidentId: number, useLlm = true) {
    const response = await this.client.post(`/incidents/${incidentId}/triage`, {
      incident_id: incidentId,
      use_llm: useLlm,
    });
    return response.data;
  }

  // Blast radius
  async analyzeBlastRadius(incidentId: number, services?: string[], useLlm = true) {
    const response = await this.client.post(`/incidents/${incidentId}/blast`, {
      incident_id: incidentId,
      services,
      use_llm: useLlm,
    });
    return response.data;
  }

  // Comms
  async generateComms(incidentId: number, channel: string, phase: string, useLlm = true) {
    const response = await this.client.post(`/incidents/${incidentId}/comms`, {
      incident_id: incidentId,
      channel,
      phase,
      use_llm: useLlm,
    });
    return response.data;
  }

  // Postmortem
  async generatePostmortem(incidentId: number, useLlm = true) {
    const response = await this.client.post(`/incidents/${incidentId}/postmortem`, {
      incident_id: incidentId,
      use_llm: useLlm,
    });
    return response.data;
  }

  // Health
  async healthCheck() {
    const response = await this.client.get('/health');
    return response.data;
  }

  async getLLMProviders() {
    const response = await this.client.get('/llm/providers');
    return response.data;
  }
}

export const api = new ApiClient();