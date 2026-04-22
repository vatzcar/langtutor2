import axios, { AxiosError } from 'axios';
import type { AdminMe } from '../types';

export const TOKEN_KEY = 'admin_token';
export const EMAIL_KEY = 'admin_email';
export const PERMISSIONS_KEY = 'admin_permissions';

// Backend API URL.
//   - Default points at the TensorDock dev server.
//   - Override locally by creating admin/.env.local with:
//       VITE_API_BASE_URL=http://localhost:8001/api/v1
//   - For a production build, set VITE_API_BASE_URL at build time.
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://38.224.253.71:8001/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
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

/**
 * Resolve a backend-relative path (e.g. `/uploads/languages/abc.png`) into a
 * fully-qualified URL pointing at the API host. Passes through absolute URLs
 * untouched.
 *
 * The backend stores uploaded asset paths as origin-relative strings. Rendered
 * as `<img src={x}>` in the admin SPA, they'd resolve against the admin's
 * origin (e.g. Vite dev server on :5173) instead of the backend host.
 */
export function assetUrl(path: string | null | undefined): string {
  if (!path) return '';
  if (/^https?:\/\//i.test(path)) return path;
  // API_BASE_URL is `<origin>/api/v1`; strip the `/api/v1` suffix to get origin.
  const origin = API_BASE_URL.replace(/\/api\/v1\/?$/, '');
  return path.startsWith('/') ? `${origin}${path}` : `${origin}/${path}`;
}
