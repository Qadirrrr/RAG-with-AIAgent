import React, { useState } from 'react';
import { Building2, Plus, Check, ChevronDown, Trash2 } from 'lucide-react';
import { useWorkspace } from '../context/WorkspaceContext';
import { Modal, inputCls, labelCls, btnPrimary } from './ui';

export default function WorkspaceSwitcher() {
  const { workspaces, selected, selectWorkspace, createWorkspace, deleteWorkspace, loading } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  const remove = async (w) => {
    if (!window.confirm(`Delete project '${w.name}'? Its chatbots, documents and chats will also be deleted. This cannot be undone.`)) return;
    setDeleteError(null);
    try {
      await deleteWorkspace(w.id);
      setOpen(false);
    } catch (err) {
      setDeleteError(err?.response?.data?.detail || err.message || 'Could not delete project.');
    }
  };

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
      setError(err?.response?.data?.detail || err.message || 'Could not create project.');
    } finally { setSaving(false); }
  };

  return (
    <div className="relative">
      <button
        onClick={() => { setDeleteError(null); setOpen(!open); }}
        className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl border border-white/25 bg-white/10 hover:bg-white/15 text-left"
      >
        <span className="w-8 h-8 rounded-lg bg-teal-700 text-white flex items-center justify-center shrink-0">
          <Building2 className="w-4 h-4" />
        </span>
        <span className="flex-1 min-w-0">
          <span className="block text-[11px] text-white/60 font-medium">Project</span>
          <span className="block text-[13px] font-semibold text-white truncate">
            {selected ? selected.name : loading ? 'Loading...' : 'No project yet'}
          </span>
        </span>
        <ChevronDown className="w-4 h-4 text-white/60 shrink-0" />
      </button>

      {open && (
        <div className="absolute left-0 right-0 mt-2 bg-[#14344D] border border-white/15 rounded-xl shadow-lg z-50 overflow-hidden">
          {workspaces.map((w) => (
            <div key={w.id} className="group flex items-center hover:bg-white/10">
              <button
                onClick={() => { selectWorkspace(w.id); setOpen(false); }}
                className="flex-1 min-w-0 flex items-center gap-2 pl-4 pr-1 py-2.5 text-[13px] text-left"
              >
                <span className="flex-1 truncate text-white/85">{w.name}</span>
                {String(selected?.id) === String(w.id) && <Check className="w-4 h-4 text-teal-400 shrink-0" />}
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); remove(w); }}
                title={`Delete project ${w.name}`}
                className="p-2 mr-1.5 rounded-lg text-white/50 hover:text-red-300 hover:bg-white/10 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 shrink-0"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
          <button
            onClick={() => { setShowCreate(true); setOpen(false); }}
            className="w-full flex items-center gap-2 px-4 py-2.5 text-[13px] font-semibold text-teal-300 hover:bg-white/10 border-t border-white/10"
          >
            <Plus className="w-4 h-4" /> New project
          </button>
        </div>
      )}

      {deleteError && (
        <p className="mt-2 px-1 text-xs text-red-300">{deleteError}</p>
      )}

      {showCreate && (
        <Modal title="Create project" onClose={() => setShowCreate(false)}>
          <form onSubmit={create} className="space-y-4">
            <div>
              <label className={labelCls}>Project name</label>
              <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="My company" autoFocus />
            </div>
            {error && <p className="text-sm text-rose-600">{error}</p>}
            <button type="submit" disabled={saving} className={btnPrimary + ' w-full'}>
              {saving ? 'Creating...' : 'Create project'}
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}
