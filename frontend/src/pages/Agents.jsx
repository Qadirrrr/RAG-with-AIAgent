import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bot, Plus, FlaskConical, Files, MessageSquare, Pencil, Trash2, Loader2 } from 'lucide-react';
import apiService, { apiError, MODEL_OPTIONS } from '../services/api';
import { useWorkspace } from '../context/WorkspaceContext';
import { Spinner, ErrorBox, EmptyState, Modal, inputCls, labelCls, btnPrimary, btnSecondary } from '../components/ui';

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'ur', label: 'Urdu' },
  { value: 'es', label: 'Spanish' },
  { value: 'ar', label: 'Arabic' },
];

const emptyForm = { name: '', instructions: '', language: 'en', provider: 'gemini', model: 'gemini-1.5-flash', temperature: 0.7, greeting: '' };

export default function Agents() {
  const { selectedId, workspaces, createWorkspace } = useWorkspace();
  const navigate = useNavigate();
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);
  const [creatingWs, setCreatingWs] = useState(false);

  const load = useCallback(async () => {
    if (!selectedId) { setLoading(false); setAgents([]); return; }
    setLoading(true);
    setError(null);
    try {
      const list = await apiService.getAgents(selectedId);
      setAgents(list);
    } catch (err) {
      setError(apiError(err, 'Could not load agents. The backend agent endpoints may not be ready yet.'));
    } finally { setLoading(false); }
  }, [selectedId]);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => { setEditing(null); setForm(emptyForm); setFormError(null); setShowModal(true); };
  const openEdit = (agent) => {
    setEditing(agent);
    setForm({
      name: agent.name || '',
      instructions: agent.instructions || '',
      language: agent.language || 'en',
      provider: agent.provider || 'gemini',
      model: agent.model || MODEL_OPTIONS[agent.provider || 'gemini'][0],
      temperature: agent.temperature ?? 0.7,
      greeting: agent.greeting || '',
    });
    setFormError(null);
    setShowModal(true);
  };

  const save = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) { setFormError('Agent name is required.'); return; }
    setSaving(true);
    setFormError(null);
    try {
      if (editing) await apiService.updateAgent(selectedId, editing.id, form);
      else await apiService.createAgent(selectedId, form);
      setShowModal(false);
      load();
    } catch (err) {
      setFormError(apiError(err, 'Could not save agent.'));
    } finally { setSaving(false); }
  };

  const remove = async (agent) => {
    if (!window.confirm(`Delete agent "${agent.name}"? This cannot be undone.`)) return;
    try { await apiService.deleteAgent(selectedId, agent.id); load(); }
    catch (err) { setError(apiError(err, 'Could not delete agent.')); }
  };

  const createFirstWorkspace = async () => {
    setCreatingWs(true);
    try { await createWorkspace('My Workspace'); } catch { setError('Could not create workspace.'); }
    finally { setCreatingWs(false); }
  };

  if (!selectedId && !loading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-extrabold text-slate-900">Agents</h2>
        <EmptyState
          icon={Bot}
          title="No workspace yet"
          text="Create a workspace first, then add AI agents to it. Each workspace keeps its own agents and knowledge base."
          action={<button onClick={createFirstWorkspace} disabled={creatingWs} className={btnPrimary}>{creatingWs ? 'Creating...' : 'Create my workspace'}</button>}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-extrabold text-slate-900">Agents</h2>
          <p className="text-sm text-slate-500 mt-1">Create and manage AI agents for this workspace.</p>
        </div>
        <button onClick={openCreate} className={btnPrimary}><Plus className="w-4 h-4" /> Create agent</button>
      </div>

      <ErrorBox message={error} onRetry={load} />
      {loading ? <Spinner label="Loading agents..." /> : agents.length === 0 ? (
        <EmptyState icon={Bot} title="No agents yet" text="Create your first agent, add documents to its knowledge base, then test it in the playground." action={<button onClick={openCreate} className={btnPrimary}><Plus className="w-4 h-4" /> Create agent</button>} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {agents.map((agent) => (
            <div key={agent.id} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col">
              <div className="flex items-start justify-between gap-2">
                <div className="w-11 h-11 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center"><Bot className="w-5 h-5" /></div>
                <div className="flex gap-1">
                  <button onClick={() => openEdit(agent)} title="Edit agent" className="p-2 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100"><Pencil className="w-4 h-4" /></button>
                  <button onClick={() => remove(agent)} title="Delete agent" className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
              <h3 className="font-semibold text-slate-900 mt-4">{agent.name}</h3>
              <p className="text-xs text-slate-500 mt-1 line-clamp-2 min-h-[2rem]">{agent.instructions || 'No instructions set.'}</p>
              <div className="flex flex-wrap gap-2 mt-4">
                <span className="text-[11px] font-semibold bg-indigo-50 text-indigo-700 px-2 py-1 rounded-full">{agent.provider || 'gemini'} / {agent.model || 'default'}</span>
                <span className="text-[11px] font-semibold bg-slate-100 text-slate-600 px-2 py-1 rounded-full">{agent.language || 'en'}</span>
              </div>
              <div className="flex items-center gap-4 mt-4 text-xs text-slate-500">
                <span className="flex items-center gap-1"><Files className="w-3.5 h-3.5" /> {agent.documents_count ?? agent.document_count ?? 0} docs</span>
                <span className="flex items-center gap-1"><MessageSquare className="w-3.5 h-3.5" /> {agent.messages_count ?? agent.message_count ?? 0} messages</span>
              </div>
              <div className="flex gap-2 mt-5 pt-4 border-t border-slate-100">
                <button onClick={() => navigate(`/agents/${agent.id}/playground`)} className={btnPrimary + ' flex-1 !px-3 !py-2 text-xs'}><FlaskConical className="w-4 h-4" /> Playground</button>
                <Link to={`/agents/${agent.id}/knowledge`} className={btnSecondary + ' flex-1 !px-3 !py-2 text-xs'}><Files className="w-4 h-4" /> Knowledge</Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <Modal title={editing ? 'Edit agent' : 'Create agent'} onClose={() => setShowModal(false)} wide>
          <form onSubmit={save} className="space-y-4">
            <div>
              <label className={labelCls}>Agent name</label>
              <input className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Support Assistant" />
            </div>
            <div>
              <label className={labelCls}>Instructions</label>
              <textarea className={inputCls + ' min-h-[110px]'} value={form.instructions} onChange={(e) => setForm({ ...form, instructions: e.target.value })} placeholder="You are a helpful support agent. Answer only from the uploaded documents and cite your sources." />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className={labelCls}>Language</label>
                <select className={inputCls} value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
                  {LANGUAGES.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>Provider</label>
                <select className={inputCls} value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value, model: MODEL_OPTIONS[e.target.value][0] })}>
                  <option value="gemini">Google Gemini</option>
                  <option value="openai">OpenAI</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Model</label>
                <select className={inputCls} value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })}>
                  {MODEL_OPTIONS[form.provider].map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>Temperature: {form.temperature}</label>
                <input type="range" min="0" max="1" step="0.1" className="w-full accent-indigo-600" value={form.temperature} onChange={(e) => setForm({ ...form, temperature: parseFloat(e.target.value) })} />
              </div>
            </div>
            <div>
              <label className={labelCls}>Greeting message</label>
              <input className={inputCls} value={form.greeting} onChange={(e) => setForm({ ...form, greeting: e.target.value })} placeholder="Hello! How can I help you today?" />
            </div>
            {formError && <p className="text-sm text-rose-600">{formError}</p>}
            <div className="flex gap-2 justify-end">
              <button type="button" onClick={() => setShowModal(false)} className={btnSecondary}>Cancel</button>
              <button type="submit" disabled={saving} className={btnPrimary}>{saving ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</> : editing ? 'Save changes' : 'Create agent'}</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
