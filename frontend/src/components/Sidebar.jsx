import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Bot, MessageSquare, Files, History, BarChart3,
  CreditCard, Plug, ShieldCheck, Settings, Sparkles, X, LogOut, FlaskConical,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import WorkspaceSwitcher from './WorkspaceSwitcher';

const navItems = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Agents', path: '/agents', icon: Bot },
  { name: 'Playground', path: '/agents', icon: FlaskConical },
  { name: 'Conversations', path: '/conversations', icon: History },
  { name: 'Analytics', path: '/analytics', icon: BarChart3 },
  { name: 'Billing', path: '/billing', icon: CreditCard },
  { name: 'Integrations', path: '/integrations', icon: Plug },
  { name: 'Documents', path: '/documents', icon: Files },
  { name: 'AI Agent Chat', path: '/chat', icon: MessageSquare },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export default function Sidebar({ isOpen, onClose }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user?.is_super_admin || user?.role === 'admin' || user?.is_admin;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 bg-slate-900/40 z-40 md:hidden" onClick={onClose} />
      )}
      <aside className={`fixed top-0 left-0 z-50 h-full w-64 bg-[#0F2A3D] flex flex-col justify-between transition-transform duration-300 md:translate-x-0 ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
        <div className="overflow-y-auto">
          <div className="h-16 flex items-center justify-between px-6 border-b border-white/25">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-xl bg-teal-700 flex items-center justify-center text-white shadow-sm">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <span className="font-bold text-white tracking-tight text-base block leading-tight">RAG Agent</span>
                <span className="text-[11px] font-medium text-white/60">SaaS Platform</span>
              </div>
            </div>
            <button onClick={onClose} className="p-1 rounded-lg text-white/60 hover:text-white hover:bg-white/10 md:hidden">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="p-4">
            <WorkspaceSwitcher />
          </div>

          <nav className="px-4 pb-4 space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.name + item.path}
                  to={item.path}
                  end={item.path === '/'}
                  onClick={() => onClose && onClose()}
                  className={({ isActive }) => `flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${isActive ? 'bg-white text-[#0F2A3D] font-semibold shadow-sm' : 'text-white/75 hover:text-white hover:bg-white/10'}`}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  <span>{item.name}</span>
                </NavLink>
              );
            })}
            {isAdmin && (
              <NavLink
                to="/admin"
                onClick={() => onClose && onClose()}
                className={({ isActive }) => `flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${isActive ? 'bg-white text-[#0F2A3D] font-semibold shadow-sm' : 'text-white/75 hover:text-white hover:bg-white/10'}`}
              >
                <ShieldCheck className="w-5 h-5 flex-shrink-0" />
                <span>Admin</span>
              </NavLink>
            )}
          </nav>
        </div>

        <div className="p-4 border-t border-white/25 space-y-3">
          <div className="flex items-center gap-3 px-1">
            <div className="w-9 h-9 rounded-full bg-white text-[#0F2A3D] flex items-center justify-center font-bold text-sm shrink-0">
              {(user?.name || user?.email || 'U').charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-white truncate">{user?.name || 'Account'}</p>
              <p className="text-xs text-white/60 truncate">{user?.email || ''}</p>
            </div>
            <button onClick={handleLogout} title="Log out" className="p-2 rounded-lg text-white/60 hover:text-white hover:bg-white/10">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
          <div className="bg-white/10 rounded-xl p-3 border border-white/25">
            <div className="flex items-center space-x-2 text-xs font-semibold text-white mb-1">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Separate knowledge base per workspace</span>
            </div>
            <p className="text-[11px] text-white/60 leading-relaxed">
              Each workspace has its own agents, documents and vector store. Data never crosses workspaces.
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
