import { createContext, useCallback, useContext, useEffect, useMemo, useState, ReactNode } from 'react';
import { api, fetchMe, TOKEN_KEY, EMAIL_KEY, PERMISSIONS_KEY } from '../api/client';
import type { LoginResponse } from '../types';

interface AuthContextValue {
  token: string | null;
  email: string | null;
  permissions: string[];
  isAuthenticated: boolean;
  hasPermission: (p: string) => boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function readStoredPermissions(): string[] {
  try {
    const raw = localStorage.getItem(PERMISSIONS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === 'string') : [];
  } catch {
    return [];
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [email, setEmail] = useState<string | null>(() => localStorage.getItem(EMAIL_KEY));
  const [permissions, setPermissions] = useState<string[]>(() => readStoredPermissions());

  const applyMe = useCallback((perms: string[], emailValue: string) => {
    setPermissions(perms);
    setEmail(emailValue);
    localStorage.setItem(EMAIL_KEY, emailValue);
    localStorage.setItem(PERMISSIONS_KEY, JSON.stringify(perms));
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_KEY);
    localStorage.removeItem(PERMISSIONS_KEY);
    setToken(null);
    setEmail(null);
    setPermissions([]);
  }, []);

  const login = useCallback(
    async (emailArg: string, password: string) => {
      const { data } = await api.post<LoginResponse>('/auth/admin/login', {
        email: emailArg,
        password,
      });
      localStorage.setItem(TOKEN_KEY, data.access_token);
      setToken(data.access_token);
      try {
        const me = await fetchMe();
        applyMe(me.role?.permissions ?? [], me.email ?? emailArg);
      } catch {
        // Fall back to email only; permissions stay empty.
        applyMe([], emailArg);
      }
    },
    [applyMe],
  );

  // On mount (or when token changes via storage), refresh permissions from /auth/me.
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetchMe()
      .then((me) => {
        if (cancelled) return;
        applyMe(me.role?.permissions ?? [], me.email ?? email ?? '');
      })
      .catch((err) => {
        if (cancelled) return;
        // 401 is already handled by axios interceptor (redirects to /login and clears token).
        // For other errors, keep cached permissions.
        if (err?.response?.status === 401) {
          logout();
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const hasPermission = useCallback(
    (p: string) => permissions.includes(p),
    [permissions],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      email,
      permissions,
      isAuthenticated: Boolean(token),
      hasPermission,
      login,
      logout,
    }),
    [token, email, permissions, hasPermission, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
