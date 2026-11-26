import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import apiService, { TOKEN_KEY, setUnauthorizedHandler } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem('rag_workspace_id');
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => logout());
    if (!token) { setLoading(false); return; }
    apiService.getMe()
      .then((data) => setUser(data.user || data))
      .catch(() => logout())
      .finally(() => setLoading(false));
  }, [token, logout]);

  const saveAuth = (data) => {
    const t = data.access_token || data.token;
    if (t) { localStorage.setItem(TOKEN_KEY, t); setToken(t); }
    if (data.user) setUser(data.user);
    return data;
  };

  const login = async (email, password) => saveAuth(await apiService.login({ email, password }));
  const signup = async (name, email, password) => saveAuth(await apiService.signup({ name, email, password }));

  return (
    <AuthContext.Provider value={{ user, token, loading, isAuthenticated: !!token, login, signup, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
