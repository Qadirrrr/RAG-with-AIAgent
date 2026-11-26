import React from 'react';
import { NavLink } from 'react-router-dom';
import { Bot, Files, Plug, Settings, X } from 'lucide-react';

const navItems = [
  { name: 'Chatbots', path: '/agents', icon: Bot },
  { name: 'Integrations & API Script', path: '/integrations', icon: Plug },
  { name: 'Knowledge Documents', path: '/documents', icon: Files },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export default function Sidebar({ isOpen, onClose }) {
  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 bg-slate-900/40 z-40 md:hidden" onClick={onClose} />
      )}
      <aside
        className={`fixed top-0 left-0 z-50 h-full w-64 bg-[#0F2A3D] flex flex-col justify-between transition-transform duration-300 md:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="overflow-y-auto">
          {/* Brand Header */}
          <div className="h-16 flex items-center justify-between px-6 border-b border-white/20">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-xl bg-teal-600 flex items-center justify-center text-white shadow-sm">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <span className="font-bold text-white tracking-tight text-[15px] block leading-tight">
                  RAG AI Agent
                </span>
                <span className="text-[11px] font-medium text-teal-400">
                  Self-Hosted AI
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-lg text-white/60 hover:text-white hover:bg-white/10 md:hidden"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.name + item.path}
                  to={item.path}
                  end={item.path === '/'}
                  onClick={() => onClose && onClose()}
                  className={({ isActive }) =>
                    `flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-[13px] font-medium transition-all ${
                      isActive
                        ? 'bg-teal-700 text-white font-semibold shadow-sm'
                        : 'text-white/75 hover:text-white hover:bg-white/10'
                    }`
                  }
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  <span>{item.name}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Footer info */}
        <div className="p-4 border-t border-white/20 text-center">
          <p className="text-[11px] text-white/50">RAG AI Agent Platform</p>
        </div>
      </aside>
    </>
  );
}
