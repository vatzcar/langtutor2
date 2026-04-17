import axios, { AxiosError } from 'axios';
import type { AdminMe } from '../types';

export const TOKEN_KEY = 'admin_token';
export const EMAIL_KEY = 'admin_email';
export const PERMISSIONS_KEY = 'admin_permissions';

export const api = axios.create({
  baseURL: 'http://localhost:8001/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(EMAIL_KEY);
      localStorage.removeItem(PERMISSIONS_KEY);
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

export function extractErrorMessage(err: unknown, fallback = 'Request failed'): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { detail?: string | { msg?: string }[] } | undefined;
    if (typeof data?.detail === 'string') return data.detail;
    if (Array.isArray(data?.detail) && data.detail[0]?.msg) return data.detail[0].msg;
    return err.message || fallback;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

export async function fetchMe(): Promise<AdminMe> {
  const { data } = await api.get<AdminMe>('/auth/me');
  return data;
}
