import React, { useState, useEffect } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Documents from './pages/Documents';
import Chat from './pages/Chat';
import Settings from './pages/Settings';
import apiService from './services/api';

const routeTitles = {
  '/': 'Enterprise RAG Dashboard',
  '/documents': 'Knowledge Documents',
  '/chat': 'AI Agent Chat',
  '/settings': 'System Settings',
};

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isOnline, setIsOnline] = useState(false);
  const location = useLocation();

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 15000); // Check every 15s
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      const data = await apiService.getHealth();
      setIsOnline(data?.status === 'healthy');
    } catch {
      setIsOnline(false);
    }
  };

  const currentTitle = routeTitles[location.pathname] || 'RAG AI Agent';

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar Navigation */}
      <Sidebar 
        isOpen={sidebarOpen} 
        onClose={() => setSidebarOpen(false)} 
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col md:pl-64 min-w-0">
        {/* Top Navbar */}
        <Navbar 
          title={currentTitle}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          isOnline={isOnline}
        />

        {/* Page Content Container */}
        <main className="flex-1 p-4 sm:p-8 max-w-7xl w-full mx-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

