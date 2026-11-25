import React from 'react';
import { Menu, Activity } from 'lucide-react';

export default function Navbar({ onToggleSidebar, title, isOnline }) {
  return (
    <header className="h-16 bg-white border-b border-slate-200 sticky top-0 z-30 flex items-center justify-between px-4 sm:px-8">
      <div className="flex items-center space-x-4">
        <button onClick={onToggleSidebar} className="p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 md:hidden" aria-label="Toggle Navigation">
          <Menu className="w-5 h-5" />
        </button>
        <h1 className="text-lg font-semibold text-slate-800 tracking-tight truncate">{title}</h1>
      </div>
      <div className="flex items-center space-x-4">
        <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium border ${isOnline ? 'bg-emerald-50 text-emerald-700 border-emerald-200/80' : 'bg-rose-50 text-rose-700 border-rose-200/80'}`}>
          <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
          <span className="hidden sm:inline">{isOnline ? 'Backend Connected' : 'Backend Offline'}</span>
          <Activity className="w-3.5 h-3.5 sm:hidden" />
        </div>
      </div>
    </header>
  );
}
