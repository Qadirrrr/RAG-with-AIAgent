import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import apiService, { WORKSPACE_KEY } from '../services/api';

const WorkspaceContext = createContext(null);

export function WorkspaceProvider({ children }) {
  const [workspaces, setWorkspaces] = useState([]);
  const [selectedId, setSelectedId] = useState(() => localStorage.getItem(WORKSPACE_KEY) || 'default');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let list = await apiService.getWorkspaces();
      if (!list || list.length === 0) {
        // Automatically create a default workspace
        try {
          const created = await apiService.createWorkspace({ name: 'Default' });
          const newWs = created.workspace || created;
          if (newWs?.id) list = [newWs];
        } catch (_) {}
      }
      setWorkspaces(list || []);
      if (list && list.length > 0) {
        const id = list[0].id;
        setSelectedId(id);
        localStorage.setItem(WORKSPACE_KEY, id);
      }
      return list || [];
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Could not load workspaces.');
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

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

  const deleteWorkspace = async (id) => {
    await apiService.deleteWorkspace(id);
    await load();
  };

  return (
    <WorkspaceContext.Provider
      value={{
        workspaces,
        selectedId,
        loading,
        error,
        load,
        selectWorkspace,
        createWorkspace,
        deleteWorkspace,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error('useWorkspace must be used inside WorkspaceProvider');
  return ctx;
}
