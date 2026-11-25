import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Bot, Plus, FlaskConical, Files, MessageSquare, Pencil, Trash2, Loader2 } from 'lucide-react';
import apiService, { apiError } from '../services/api';
import { useWorkspace } from '../context/WorkspaceContext';
import { Spinner, ErrorBox, EmptyState, Modal, inputCls, labelCls, btnPrimary, btnSecondary } from '../components/ui';

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'ur', label: 'Urdu' },
  { value: 'es', label: 'Spanish' },
  { value: 'ar', label: 'Arabic' },
];

const TOOL_OPTIONS = [
  { value: 'knowledge_search', label: 'Knowledge search', hint: 'Search this chatbot\'s uploaded documents and websites.' },
  { value: 'list_documents', label: 'List documents', hint: 'See which documents are in the knowledge base.' },
  { value: 'calculator', label: 'Calculator', hint: 'Do simple arithmetic.' },
  { value: 'current_datetime', label: 'Date and time', hint: 'Answer questions about the current date and time.' },
];
const ALL_TOOLS = TOOL_OPTIONS.map((t) => t.value);

const emptyForm = { name: '', description: '', instructions: '', language: 'en', provider: 'ollama', model: 'qwen2.5:7b', temperature: 0.7, greeting: '', mode: 'rag', show_citations: false, tools: [...ALL_TOOLS], widget_title: '', widget_welcome_message: 'Hello! How can I help you?', widget_color: '#0F766E', widget_position: 'right', widget_icon: 'chat', widget_icon_url: '' };

export default function Agents() {
  const { selectedId, workspaces, createWorkspace } = useWorkspace();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const openedFromDashboard = useRef(false);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);
  const [creatingWs, setCreatingWs] = useState(false);
  // Models actually pulled on the Ollama server, loaded when the form
  // opens. Null until loaded; the select falls back to the default.
  const [pulledModels, setPulledModels] = useState(null);

  const loadModels = useCallback(async () => {
    try {
      const data = await apiService.getOllamaModels();
      const list = Array.isArray(data?.models) ? data.models : [];
      setPulledModels(list.length ? list : [data?.default || 'qwen2.5:7b']);
    } catch {
      setPulledModels(['qwen2.5:7b']);
    }
  }, []);

  useEffect(() => { if (showModal) loadModels(); }, [showModal, loadModels]);

  const load = useCallback(async () => {
    if (!selectedId) { setLoading(false); setAgents([]); return; }
    setLoading(true);
    setError(null);
    try {
      const list = await apiService.getAgents(selectedId);
      setAgents(list);
    } catch (err) {
      setError(apiError(err, 'Could not load chatbots.'));
    } finally { setLoading(false); }
  }, [selectedId]);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => { setEditing(null); setForm(emptyForm); setFormError(null); setShowModal(true); };

  // Dashboard "New Chatbot" button links here with ?new=1: open the create form once, then clear the param.
  useEffect(() => {
    if (searchParams.get('new') === '1' && selectedId && !openedFromDashboard.current) {
      openedFromDashboard.current = true;
      openCreate();
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, selectedId, setSearchParams]);
  const openEdit = (agent) => {
    setEditing(agent);
    setForm({
      name: agent.name || '',
      description: agent.description || '',
      instructions: agent.instructions || '',
      language: agent.language || 'en',
      provider: 'ollama',
      model: agent.model || 'qwen2.5:7b',
      temperature: agent.temperature ?? 0.7,
      greeting: agent.greeting || '',
      mode: agent.mode || 'rag',
      show_citations: Boolean(agent.show_citations),
      tools: agent.tools_enabled ? agent.tools_enabled.split(',').map((s) => s.trim()).filter((s) => ALL_TOOLS.includes(s)) : [...ALL_TOOLS],
      widget_title: agent.widget_title || '',
      widget_welcome_message: agent.widget_welcome_message || 'Hello! How can I help you?',
      widget_color: /^#[0-9a-fA-F]{6}$/.test(agent.widget_color || '') ? agent.widget_color : '#0F766E',
      widget_position: agent.widget_position === 'left' ? 'left' : 'right',
      widget_icon: ['chat', 'robot', 'custom'].includes(agent.widget_icon) ? agent.widget_icon : 'chat',
      widget_icon_url: agent.widget_icon_url || '',
    });
    setFormError(null);
    setShowModal(true);
  };

  const toggleActive = async (agent) => {
    try {
      const updated = await apiService.toggleAgentActive(selectedId, agent.id);
      setAgents((prev) => prev.map((a) => (a.id === agent.id ? { ...a, is_active: updated.is_active } : a)));
    } catch (err) {
      setError(apiError(err, 'Could not change chatbot status.'));
    }
  };

  const save = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) { setFormError('Chatbot name is required.'); return; }
    setSaving(true);
    setFormError(null);
    try {
      const payload = { ...form, tools_enabled: (form.tools || []).join(',') };
      delete payload.tools;
      if (editing) await apiService.updateAgent(selectedId, editing.id, payload);
      else await apiService.createAgent(selectedId, payload);
      setShowModal(false);
      load();
    } catch (err) {
      setFormError(apiError(err, 'Could not save chatbot.'));
    } finally { setSaving(false); }
  };

  const remove = async (agent) => {
    if (!window.confirm(`Delete chatbot "${agent.name}"? This cannot be undone.`)) return;
    try { await apiService.deleteAgent(selectedId, agent.id); load(); }
    catch (err) { setError(apiError(err, 'Could not delete chatbot.')); }
  };

  const createFirstWorkspace = async () => {
    setCreatingWs(true);
    try { await createWorkspace('My Project'); } catch { setError('Could not create project.'); }
    finally { setCreatingWs(false); }
  };

  if (!selectedId && !loading) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-extrabold text-slate-900">Chatbots</h2>
        <EmptyState
          icon={Bot}
          title="No project yet"
          text="Create a project first, then add chatbots to it. Each project keeps its own chatbots and knowledge base."
          action={<button onClick={createFirstWorkspace} disabled={creatingWs} className={btnPrimary}>{creatingWs ? 'Creating...' : 'Create my project'}</button>}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-extrabold text-slate-900">Chatbots</h2>
          <p className="text-sm text-slate-500 mt-1">Create and manage chatbots for this project. Each chatbot answers only from its own project knowledge.</p>
        </div>
        <button onClick={openCreate} className={btnPrimary}><Plus className="w-4 h-4" /> Create chatbot</button>
      </div>

      <ErrorBox message={error} onRetry={load} />
      {loading ? <Spinner label="Loading chatbots..." /> : agents.length === 0 ? (
        <EmptyState icon={Bot} title="No chatbots yet" text="Create your first chatbot, add documents to its knowledge base, then test it in the playground." action={<button onClick={openCreate} className={btnPrimary}><Plus className="w-4 h-4" /> Create chatbot</button>} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {agents.map((agent) => (
            <div key={agent.id} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col">
              <div className="flex items-start justify-between gap-2">
                <div className="w-11 h-11 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center"><Bot className="w-5 h-5" /></div>
                <div className="flex items-center gap-1">
                  <span className={`text-[11px] font-semibold px-2 py-1 rounded-full ${agent.is_active === false ? 'bg-slate-100 text-slate-500' : 'bg-emerald-50 text-emerald-700'}`}>
                    {agent.is_active === false ? 'Inactive' : 'Active'}
                  </span>
                  <button onClick={() => openEdit(agent)} title="Edit chatbot" className="p-2 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100"><Pencil className="w-4 h-4" /></button>
                  <button onClick={() => remove(agent)} title="Delete chatbot" className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
              <h3 className="font-semibold text-slate-900 mt-4">{agent.name}</h3>
              <p className="text-xs text-slate-500 mt-1 line-clamp-2 min-h-[2rem]">{agent.description || agent.instructions || 'No description set.'}</p>
              <div className="flex flex-wrap gap-2 mt-4">
                <span className="text-[11px] font-semibold bg-teal-50 text-teal-700 px-2 py-1 rounded-full">ollama / {agent.model || 'qwen2.5:7b'}</span>
                <span className="text-[11px] font-semibold bg-slate-100 text-slate-600 px-2 py-1 rounded-full">{agent.language || 'en'}</span>
                <span className="text-[11px] font-semibold bg-slate-100 text-slate-600 px-2 py-1 rounded-full">{agent.mode === 'agent' ? 'RAG + Agent' : 'Strict RAG'}</span>
              </div>
              <button onClick={() => toggleActive(agent)} className="mt-4 text-xs font-semibold text-teal-700 hover:text-teal-800 text-left">
                {agent.is_active === false ? 'Activate chatbot' : 'Deactivate chatbot'}
              </button>
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
        <Modal title={editing ? 'Edit chatbot' : 'Create chatbot'} onClose={() => setShowModal(false)} wide>
          <form onSubmit={save} className="space-y-4">
            <div>
              <label className={labelCls}>Chatbot name</label>
              <input className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Support Assistant" />
            </div>
            <div>
              <label className={labelCls}>Description</label>
              <input className={inputCls} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Answers customer questions about our plans and pricing." />
            </div>
            <div>
              <label className={labelCls}>Instructions</label>
              <textarea className={inputCls + ' min-h-[110px]'} value={form.instructions} onChange={(e) => setForm({ ...form, instructions: e.target.value })} placeholder="You are a helpful support chatbot. Answer only from the uploaded knowledge." />
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
                <select className={inputCls} value="ollama" disabled>
                  <option value="ollama">Ollama (self-hosted)</option>
                </select>
                <p className="text-xs text-slate-500 mt-1">Runs on your own server. No API key needed.</p>
              </div>
              <div>
                <label className={labelCls}>Mode</label>
                <select className={inputCls} value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value })}>
                  <option value="rag">Strict RAG</option>
                  <option value="agent">RAG + Agent</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Model</label>
                {(() => {
                  const options = pulledModels && pulledModels.length ? pulledModels : ['qwen2.5:7b'];
                  const storedNotOnServer = form.model && !options.includes(form.model);
                  return (
                    <>
                      <select className={inputCls} value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })}>
                        {storedNotOnServer && <option value={form.model}>{form.model} (not on server)</option>}
                        {options.map((m) => <option key={m} value={m}>{m}</option>)}
                      </select>
                      {storedNotOnServer
                        ? <p className="text-xs text-amber-600 mt-1">This model is not pulled on the server. Chats will use the default model until it is pulled.</p>
                        : <p className="text-xs text-slate-500 mt-1">Only models pulled on your Ollama server are listed.</p>}
                    </>
                  );
                })()}
              </div>
              <div>
                <label className={labelCls}>Temperature: {form.temperature}</label>
                <input type="range" min="0" max="1" step="0.1" className="w-full accent-teal-700" value={form.temperature} onChange={(e) => setForm({ ...form, temperature: parseFloat(e.target.value) })} />
              </div>
            </div>
            <div>
              <label className={labelCls}>Greeting message</label>
              <input className={inputCls} value={form.greeting} onChange={(e) => setForm({ ...form, greeting: e.target.value })} placeholder="Hello! How can I help you today?" />
            </div>
            <div className="border-t border-slate-100 pt-4 space-y-4">
              <div>
                <h4 className="text-sm font-semibold text-slate-800">Website widget</h4>
                <p className="text-xs text-slate-500 mt-0.5">How the chat widget looks on your website. Changes apply to the embedded widget automatically.</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Widget title</label>
                  <input className={inputCls} value={form.widget_title} onChange={(e) => setForm({ ...form, widget_title: e.target.value })} placeholder={form.name || 'Chatbot name'} />
                  <p className="text-xs text-slate-500 mt-1">Leave empty to show the chatbot name.</p>
                </div>
                <div>
                  <label className={labelCls}>Widget color</label>
                  <div className="flex items-center gap-2">
                    <input type="color" className="w-11 h-10 shrink-0 p-0.5 bg-white border border-slate-300 rounded-lg cursor-pointer" value={form.widget_color} onChange={(e) => setForm({ ...form, widget_color: e.target.value })} />
                    <input className={inputCls} value={form.widget_color} onChange={(e) => setForm({ ...form, widget_color: e.target.value })} placeholder="#0F766E" />
                  </div>
                </div>
                <div>
                  <label className={labelCls}>Position</label>
                  <select className={inputCls} value={form.widget_position} onChange={(e) => setForm({ ...form, widget_position: e.target.value })}>
                    <option value="right">Bottom right</option>
                    <option value="left">Bottom left</option>
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Icon</label>
                  <select className={inputCls} value={form.widget_icon} onChange={(e) => setForm({ ...form, widget_icon: e.target.value })}>
                    <option value="chat">Chat bubble</option>
                    <option value="robot">Robot</option>
                    <option value="custom">Custom image</option>
                  </select>
                </div>
              </div>
              {form.widget_icon === 'custom' && (
                <div>
                  <label className={labelCls}>Icon image URL</label>
                  <input className={inputCls} value={form.widget_icon_url} onChange={(e) => setForm({ ...form, widget_icon_url: e.target.value })} placeholder="https://yourwebsite.com/logo.png" />
                  <p className="text-xs text-slate-500 mt-1">A square image works best. If empty, the chat bubble icon is used.</p>
                </div>
              )}
              <div>
                <label className={labelCls}>Welcome message</label>
                <input className={inputCls} value={form.widget_welcome_message} onChange={(e) => setForm({ ...form, widget_welcome_message: e.target.value })} placeholder="Hello! How can I help you?" />
                <p className="text-xs text-slate-500 mt-1">The first message a visitor sees when they open the widget.</p>
              </div>
              <div>
                <label className={labelCls}>Preview</label>
                <div className="relative h-52 rounded-xl border border-slate-200 bg-slate-50 overflow-hidden">
                  <div className={`absolute bottom-16 w-60 max-w-[75%] rounded-2xl bg-white border border-slate-200 shadow-lg overflow-hidden ${form.widget_position === 'left' ? 'left-4' : 'right-4'}`}>
                    <div className="px-4 py-3 text-white text-sm font-semibold truncate" style={{ background: form.widget_color }}>
                      {form.widget_title || form.name || 'Chatbot name'}
                    </div>
                    <div className="p-3">
                      <div className="inline-block max-w-full bg-slate-100 text-slate-700 text-xs leading-relaxed px-3 py-2 rounded-xl">
                        {form.widget_welcome_message || 'Hello! How can I help you?'}
                      </div>
                    </div>
                  </div>
                  <div className={`absolute bottom-4 w-12 h-12 rounded-full shadow-lg flex items-center justify-center overflow-hidden ${form.widget_position === 'left' ? 'left-4' : 'right-4'}`} style={{ background: form.widget_color }}>
                    {form.widget_icon === 'custom' && form.widget_icon_url ? (
                      <img src={form.widget_icon_url} alt="" className="w-full h-full object-cover" />
                    ) : form.widget_icon === 'robot' ? (
                      <Bot className="w-6 h-6 text-white" />
                    ) : (
                      <MessageSquare className="w-6 h-6 text-white" />
                    )}
                  </div>
                </div>
              </div>
            </div>
            {form.mode === 'agent' && (
              <div>
                <label className={labelCls}>Agent tools</label>
                <p className="text-xs text-slate-500 mb-2">Choose which tools this chatbot may use. All tools are read-only and can only access this chatbot's own project data.</p>
                <div className="space-y-2">
                  {TOOL_OPTIONS.map((t) => (
                    <label key={t.value} className="flex items-start gap-2.5 text-sm text-slate-700 cursor-pointer">
                      <input
                        type="checkbox"
                        className="w-4 h-4 mt-0.5 accent-teal-700"
                        checked={(form.tools || []).includes(t.value)}
                        onChange={(e) => setForm({ ...form, tools: e.target.checked ? [...(form.tools || []), t.value] : (form.tools || []).filter((x) => x !== t.value) })}
                      />
                      <span>{t.label} <span className="block text-xs text-slate-500">{t.hint}</span></span>
                    </label>
                  ))}
                </div>
              </div>
            )}
            <label className="flex items-center gap-2.5 text-sm text-slate-700 cursor-pointer">
              <input type="checkbox" className="w-4 h-4 accent-teal-700" checked={form.show_citations} onChange={(e) => setForm({ ...form, show_citations: e.target.checked })} />
              Show source names under answers (citations)
            </label>
            {formError && <p className="text-sm text-rose-600">{formError}</p>}
            <div className="flex gap-2 justify-end">
              <button type="button" onClick={() => setShowModal(false)} className={btnSecondary}>Cancel</button>
              <button type="submit" disabled={saving} className={btnPrimary}>{saving ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</> : editing ? 'Save changes' : 'Create chatbot'}</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
