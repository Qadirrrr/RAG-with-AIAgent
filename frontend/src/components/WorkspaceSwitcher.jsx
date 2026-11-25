import React, { useState } from 'react';
import { Building2, Plus, Check, ChevronDown } from 'lucide-react';
import { useWorkspace } from '../context/WorkspaceContext';
import { Modal, inputCls, labelCls, btnPrimary } from './ui';

export default function WorkspaceSwitcher() {
  const { workspaces, selected, selectWorkspace, createWorkspace, loading } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const create = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await createWorkspace(name.trim());
      setName('');
      setShowCreate(false);
      setOpen(false);
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Could not create workspace.');
    } finally { setSaving(false); }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-left"
      >
        <span className="w-8 h-8 rounded-lg bg-teal-700 text-white flex items-center justify-center shrink-0">
          <Building2 className="w-4 h-4" />
        </span>
        <span className="flex-1 min-w-0">
          <span className="block text-xs text-slate-400 font-medium">Workspace</span>
          <span className="block text-[13px] font-semibold text-slate-800 truncate">
            {selected ? selected.name : loading ? 'Loading...' : 'No workspace yet'}
          </span>
        </span>
        <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />
      </button>

      {open && (
        <div className="absolute left-0 right-0 mt-2 bg-white border border-slate-200 rounded-xl shadow-lg z-50 overflow-hidden">
          {workspaces.map((w) => (
            <button
              key={w.id}
              onClick={() => { selectWorkspace(w.id); setOpen(false); }}
              className="w-full flex items-center gap-2 px-4 py-2.5 text-[13px] text-left hover:bg-slate-50"
            >
              <span className="flex-1 truncate text-slate-700">{w.name}</span>
              {String(selected?.id) === String(w.id) && <Check className="w-4 h-4 text-teal-600" />}
            </button>
          ))}
          <button
            onClick={() => { setShowCreate(true); setOpen(false); }}
            className="w-full flex items-center gap-2 px-4 py-2.5 text-[13px] font-semibold text-teal-600 hover:bg-teal-50 border-t border-slate-100"
          >
            <Plus className="w-4 h-4" /> New workspace
          </button>
        </div>
      )}

      {showCreate && (
        <Modal title="Create workspace" onClose={() => setShowCreate(false)}>
          <form onSubmit={create} className="space-y-4">
            <div>
              <label className={labelCls}>Workspace name</label>
              <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="My company" autoFocus />
            </div>
            {error && <p className="text-sm text-rose-600">{error}</p>}
            <button type="submit" disabled={saving} className={btnPrimary + ' w-full'}>
              {saving ? 'Creating...' : 'Create workspace'}
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}
