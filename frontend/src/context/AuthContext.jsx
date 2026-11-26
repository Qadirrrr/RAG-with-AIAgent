import React, { createContext, useContext, useState } from 'react';

const AuthContext = createContext(null);

const DEFAULT_USER = {
  id: 'default-admin',
  name: 'Admin',
  email: 'admin@ragagent.local',
  is_active: true,
  is_super_admin: true,
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(DEFAULT_USER);
  const [token, setToken] = useState('single-user-token');

  const logout = () => {};
  const login = async () => DEFAULT_USER;
  const signup = async () => DEFAULT_USER;

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading: false,
        isAuthenticated: true,
        login,
        signup,
        logout,
        setUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
