import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Documents from './pages/Documents';
import Chat from './pages/Chat';
import Settings from './pages/Settings';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Landing from './pages/Landing';
import Agents from './pages/Agents';
import Playground from './pages/Playground';
import Knowledge from './pages/Knowledge';
import Conversations from './pages/Conversations';
import Analytics from './pages/Analytics';
import Billing from './pages/Billing';
import Integrations from './pages/Integrations';
import Admin from './pages/Admin';
import apiService from './services/api';
import { AuthProvider, useAuth } from './context/AuthContext';
import { WorkspaceProvider } from './context/WorkspaceContext';
import { Spinner } from './components/ui';

const routeTitles = {
  '/': 'Dashboard',
  '/agents': 'AI Agents',
  '/conversations': 'Conversations',
  '/analytics': 'Analytics',
  '/billing': 'Billing and Plans',
  '/integrations': 'Integrations',
  '/admin': 'Super-admin',
  '/documents': 'Knowledge Documents',
  '/chat': 'AI Agent Chat',
  '/settings': 'System Settings',
};

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="min-h-screen bg-[#F7F9FB]"><Spinner label="Checking your session..." /></div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
}

function PublicOnly({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="min-h-screen bg-[#F7F9FB]"><Spinner label="Checking your session..." /></div>;
  if (isAuthenticated) return <Navigate to="/" replace />;
  return children;
}

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
            <Route path="/" element={<Dashboard />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/agents/:agentId/playground" element={<Playground />} />
            <Route path="/agents/:agentId/knowledge" element={<Knowledge />} />
            <Route path="/conversations" element={<Conversations />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/billing" element={<Billing />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/admin" element={<Admin />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/chat" element={<Chat />} />
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
        <Routes>
          <Route path="/landing" element={<Landing />} />
          <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
          <Route path="/signup" element={<PublicOnly><Signup /></PublicOnly>} />
          <Route path="/*" element={<ProtectedRoute><Shell /></ProtectedRoute>} />
        </Routes>
      </WorkspaceProvider>
    </AuthProvider>
  );
}
