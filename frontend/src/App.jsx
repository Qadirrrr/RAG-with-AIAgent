import React, { useState, useEffect } from 'react';
import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { Bot, MessageSquare, Files } from 'lucide-react';
import Chat from './pages/Chat';
import Documents from './pages/Documents';
import apiService from './services/api';

export default function App() {
  const [isOnline, setIsOnline] = useState(false);
  const [modelInfo, setModelInfo] = useState('');

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await apiService.getHealth();
        setIsOnline(data?.status === 'healthy');
        if (data?.model) {
          setModelInfo(`${data.model}`);
        }
      } catch {
        setIsOnline(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#F7F9FB] flex flex-col">
      {/* Top Navbar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-teal-600 text-white flex items-center justify-center shadow-xs">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-800 text-base">RAG AI Agent</span>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${
                    isOnline ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      isOnline ? 'bg-emerald-500' : 'bg-rose-500'
                    }`}
                  />
                  {isOnline ? (modelInfo ? `${modelInfo}` : 'Online') : 'Ollama Offline'}
                </span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `inline-flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-semibold transition-all ${
                  isActive
                    ? 'bg-white text-teal-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`
              }
            >
              <MessageSquare className="w-4 h-4" />
              <span>Chat</span>
            </NavLink>
            <NavLink
              to="/documents"
              className={({ isActive }) =>
                `inline-flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-semibold transition-all ${
                  isActive
                    ? 'bg-white text-teal-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`
              }
            >
              <Files className="w-4 h-4" />
              <span>Documents</span>
            </NavLink>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-4 sm:p-6">
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
