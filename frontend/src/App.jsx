import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import Agents from './pages/Agents';
import Playground from './pages/Playground';
import Knowledge from './pages/Knowledge';
import Integrations from './pages/Integrations';
import Documents from './pages/Documents';
import Settings from './pages/Settings';
import apiService from './services/api';
import { AuthProvider } from './context/AuthContext';
import { WorkspaceProvider } from './context/WorkspaceContext';

const routeTitles = {
  '/': 'AI Chatbots',
  '/agents': 'AI Chatbots',
  '/integrations': 'Integrations & API Script',
  '/documents': 'Knowledge Documents',
  '/settings': 'System Settings',
};

function Shell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isOnline, setIsOnline] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await apiService.getHealth();
        setIsOnline(data?.status === 'healthy');
      } catch { setIsOnline(false); }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const title = routeTitles[location.pathname] || (location.pathname.startsWith('/agents/') && location.pathname.includes('/playground') ? 'Agent Playground' : location.pathname.includes('/knowledge') ? 'Knowledge Base' : 'RAG AI Agent');

  return (
    <div className="min-h-screen bg-[#F7F9FB] flex">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 flex flex-col md:pl-64 min-w-0">
        <Navbar title={title} onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} isOnline={isOnline} />
        <main className="flex-1 p-4 sm:p-8 max-w-7xl w-full mx-auto">
          <Routes>
            <Route path="/" element={<Agents />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/agents/:agentId/playground" element={<Playground />} />
            <Route path="/agents/:agentId/knowledge" element={<Knowledge />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <WorkspaceProvider>
        <Shell />
      </WorkspaceProvider>
    </AuthProvider>
  );
}
