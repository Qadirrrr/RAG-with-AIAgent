import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import apiService, { WORKSPACE_KEY } from '../services/api';
import { useAuth } from './AuthContext';

const WorkspaceContext = createContext(null);

export function WorkspaceProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [workspaces, setWorkspaces] = useState([]);
  const [selectedId, setSelectedId] = useState(() => localStorage.getItem(WORKSPACE_KEY));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!isAuthenticated) return [];
    setLoading(true);
    setError(null);
    try {
      const list = await apiService.getWorkspaces();
      setWorkspaces(list);
      if (list.length > 0) {
        const saved = localStorage.getItem(WORKSPACE_KEY);
        const valid = list.find((w) => String(w.id) === String(saved));
        const chosen = valid ? valid.id : list[0].id;
        setSelectedId(chosen);
        localStorage.setItem(WORKSPACE_KEY, chosen);
      } else {
        setSelectedId(null);
        localStorage.removeItem(WORKSPACE_KEY);
      }
      return list;
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Could not load workspaces.');
      return [];
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => { load(); }, [load]);

  const selectWorkspace = (id) => {
    setSelectedId(id);
    if (id) localStorage.setItem(WORKSPACE_KEY, id);
    else localStorage.removeItem(WORKSPACE_KEY);
  };

  const createWorkspace = async (name) => {
    const created = await apiService.createWorkspace({ name });
    const ws = created.workspace || created;
    await load();
    if (ws?.id) selectWorkspace(ws.id);
    return ws;
  };

  const selected = workspaces.find((w) => String(w.id) === String(selectedId)) || null;

  return (
    <WorkspaceContext.Provider value={{ workspaces, selected, selectedId, loading, error, load, selectWorkspace, createWorkspace }}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error('useWorkspace must be used inside WorkspaceProvider');
  return ctx;
}
