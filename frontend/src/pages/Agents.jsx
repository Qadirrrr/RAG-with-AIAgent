import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Bot, Plus, Files, MessageSquare, Pencil, Trash2, Loader2, Plug, CheckCircle2 } from 'lucide-react';
import apiService, { apiError } from '../services/api';
import { useWorkspace } from '../context/WorkspaceContext';
import { Spinner, ErrorBox, EmptyState, Modal, inputCls, labelCls, btnPrimary, btnSecondary } from '../components/ui';

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'ur', label: 'Urdu' },
  { value: 'es', label: 'Spanish' },
  { value: 'ar', label: 'Arabic' },
];

const ALL_TOOLS = ['knowledge_search', 'list_documents', 'calculator', 'current_datetime'];

const emptyForm = {
  name: '',
  description: '',
  instructions: '',
  language: 'en',
  provider: 'ollama',
  model: 'qwen2.5:7b',
  temperature: 0.2,
  greeting: 'Hello! How can I help you today?',
  mode: 'rag',
  show_citations: false,
  tools: [...ALL_TOOLS],
  widget_title: '',
  widget_welcome_message: 'Hello! How can I help you?',
  widget_color: '#0F766E',
  widget_position: 'right',
  widget_icon: 'chat',
  widget_icon_url: '',
};

export default function Agents() {
  const { selectedId, createWorkspace } = useWorkspace();
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

  useEffect(() => {
    if (showModal) loadModels();
  }, [showModal, loadModels]);

  const load = useCallback(async () => {
    if (!selectedId) {
      setLoading(false);
      setAgents([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const list = await apiService.getAgents(selectedId);
      setAgents(list);
    } catch (err) {
      setError(apiError(err, 'Could not load chatbots.'));
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setFormError(null);
    setShowModal(true);
  };

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
      temperature: agent.temperature ?? 0.2,
      greeting: agent.greeting || 'Hello! How can I help you today?',
      mode: agent.mode || 'rag',
      show_citations: Boolean(agent.show_citations),
      tools: agent.tools_enabled
        ? agent.tools_enabled.split(',').map((s) => s.trim())
        : [...ALL_TOOLS],
      widget_title: agent.widget_title || '',
      widget_welcome_message: agent.widget_welcome_message || 'Hello! How can I help you?',
      widget_color: /^#[0-9a-fA-F]{6}$/.test(agent.widget_color || '')
        ? agent.widget_color
        : '#0F766E',
      widget_position: agent.widget_position === 'left' ? 'left' : 'right',
      widget_icon: 'chat',
      widget_icon_url: '',
    });
    setFormError(null);
    setShowModal(true);
  };

  const toggleActive = async (agent) => {
    try {
      const updated = await apiService.toggleAgentActive(selectedId, agent.id);
      setAgents((prev) =>
        prev.map((a) => (a.id === agent.id ? { ...a, is_active: updated.is_active } : a))
      );
    } catch (err) {
      setError(apiError(err, 'Could not change chatbot status.'));
    }
  };

  const save = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) {
      setFormError('Chatbot name is required.');
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      const payload = {
        ...form,
        tools_enabled: (form.tools || ALL_TOOLS).join(','),
      };
      delete payload.tools;
      if (editing) await apiService.updateAgent(selectedId, editing.id, payload);
      else await apiService.createAgent(selectedId, payload);
      setShowModal(false);
      load();
    } catch (err) {
      setFormError(apiError(err, 'Could not save chatbot.'));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (agent) => {
    if (!window.confirm(`Delete chatbot "${agent.name}"? This cannot be undone.`)) return;
    try {
      await apiService.deleteAgent(selectedId, agent.id);
      load();
    } catch (err) {
      setError(apiError(err, 'Could not delete chatbot.'));
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">AI Chatbots</h1>
          <p className="text-sm text-slate-500 mt-1">
            Create and configure custom chatbots. Each chatbot answers strictly from its uploaded knowledge.
          </p>
        </div>
        <button onClick={openCreate} className={btnPrimary}>
          <Plus className="w-4 h-4" /> Create Chatbot
        </button>
      </div>

      <ErrorBox message={error} onRetry={load} />

      {loading ? (
        <Spinner label="Loading chatbots..." />
      ) : agents.length === 0 ? (
        <EmptyState
          icon={Bot}
          title="No chatbots created yet"
          text="Create your first chatbot, upload documents to its knowledge base, and integrate it with your website."
          action={
            <button onClick={openCreate} className={btnPrimary}>
              <Plus className="w-4 h-4" /> Create Chatbot
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors"
            >
              <div>
                {/* Header row */}
                <div className="flex items-start justify-between gap-2">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold"
                    style={{ background: agent.widget_color || '#0F766E' }}
                  >
                    <Bot className="w-5 h-5" />
                  </div>
                  <div className="flex items-center gap-1">
                    <span
                      className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                        agent.is_active === false
                          ? 'bg-slate-100 text-slate-500'
                          : 'bg-emerald-50 text-emerald-700'
                      }`}
                    >
                      {agent.is_active === false ? 'Inactive' : 'Active'}
                    </span>
                    <button
                      onClick={() => openEdit(agent)}
                      title="Edit chatbot"
                      className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => remove(agent)}
                      title="Delete chatbot"
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Name & greeting */}
                <h3 className="font-bold text-slate-900 mt-3 text-base truncate">{agent.name}</h3>
                <p className="text-xs text-slate-500 mt-1 line-clamp-2 min-h-[2rem]">
                  {agent.instructions || agent.greeting || 'Ready to assist.'}
                </p>

                {/* Badges */}
                <div className="flex flex-wrap gap-1.5 mt-3">
                  <span className="text-[11px] font-medium bg-teal-50 text-teal-700 px-2 py-0.5 rounded-md">
                    {agent.model || 'qwen2.5:7b'}
                  </span>
                  <span className="text-[11px] font-medium bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md">
                    {agent.language === 'ur' ? 'Urdu' : 'English'}
                  </span>
                  <span className="text-[11px] font-medium bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md">
                    {agent.mode === 'agent' ? 'RAG + Agent' : 'Strict RAG'}
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-5 pt-4 border-t border-slate-100 space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <Link
                    to={`/agents/${agent.id}/knowledge`}
                    className="inline-flex items-center justify-center gap-1.5 bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium px-3 py-2 rounded-xl text-xs border border-slate-200 transition-colors"
                  >
                    <Files className="w-3.5 h-3.5 text-teal-600" />
                    <span>Knowledge</span>
                  </Link>
                  <Link
                    to={`/agents/${agent.id}/playground`}
                    className="inline-flex items-center justify-center gap-1.5 bg-teal-700 hover:bg-teal-800 text-white font-medium px-3 py-2 rounded-xl text-xs transition-colors shadow-xs"
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span>Test Chat</span>
                  </Link>
                </div>
                <Link
                  to="/integrations"
                  className="w-full inline-flex items-center justify-center gap-1.5 text-teal-700 hover:text-teal-800 text-xs font-semibold py-1 transition-colors"
                >
                  <Plug className="w-3.5 h-3.5" />
                  <span>Get API Key & Embed Script</span>
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Streamlined Create / Edit Modal — Only Important Fields */}
      {showModal && (
        <Modal
          title={editing ? 'Edit Chatbot' : 'Create New Chatbot'}
          onClose={() => setShowModal(false)}
          wide
        >
          <form onSubmit={save} className="space-y-5">
            {/* 1. Chatbot Name */}
            <div>
              <label className={labelCls}>Chatbot Name *</label>
              <input
                className={inputCls}
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. Customer Support AI"
                required
              />
            </div>

            {/* 2. Instructions */}
            <div>
              <label className={labelCls}>Instructions (How it should behave)</label>
              <textarea
                className={inputCls + ' min-h-[90px]'}
                value={form.instructions}
                onChange={(e) => setForm({ ...form, instructions: e.target.value })}
                placeholder="e.g. You are a professional assistant. Answer questions directly using only the uploaded knowledge."
              />
            </div>

            {/* 3. Settings Grid: Model, Mode, Language */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className={labelCls}>Language</label>
                <select
                  className={inputCls}
                  value={form.language}
                  onChange={(e) => setForm({ ...form, language: e.target.value })}
                >
                  {LANGUAGES.map((l) => (
                    <option key={l.value} value={l.value}>
                      {l.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelCls}>Model</label>
                {(() => {
                  const options =
                    pulledModels && pulledModels.length ? pulledModels : ['qwen2.5:7b'];
                  return (
                    <select
                      className={inputCls}
                      value={form.model}
                      onChange={(e) => setForm({ ...form, model: e.target.value })}
                    >
                      {options.map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>
                  );
                })()}
              </div>
              <div>
                <label className={labelCls}>Mode</label>
                <select
                  className={inputCls}
                  value={form.mode}
                  onChange={(e) => setForm({ ...form, mode: e.target.value })}
                >
                  <option value="rag">Strict RAG (Fast)</option>
                  <option value="agent">RAG + Agent</option>
                </select>
              </div>
            </div>

            {/* 4. Initial Greeting */}
            <div>
              <label className={labelCls}>Initial Greeting Message</label>
              <input
                className={inputCls}
                value={form.greeting}
                onChange={(e) => setForm({ ...form, greeting: e.target.value })}
                placeholder="Hello! How can I help you today?"
              />
            </div>

            {/* 5. Website Widget & Header Customization */}
            <div className="border-t border-slate-100 pt-4 space-y-4">
              <div>
                <h4 className="text-sm font-bold text-slate-800">
                  Website Widget & Header Appearance
                </h4>
                <p className="text-xs text-slate-500">
                  How the chatbot header and widget will appear when embedded on your website.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Header Title</label>
                  <input
                    className={inputCls}
                    value={form.widget_title}
                    onChange={(e) => setForm({ ...form, widget_title: e.target.value })}
                    placeholder={form.name || 'Chat with Assistant'}
                  />
                </div>
                <div>
                  <label className={labelCls}>Header Color</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      className="w-10 h-10 p-0.5 bg-white border border-slate-300 rounded-lg cursor-pointer shrink-0"
                      value={form.widget_color}
                      onChange={(e) => setForm({ ...form, widget_color: e.target.value })}
                    />
                    <input
                      className={inputCls}
                      value={form.widget_color}
                      onChange={(e) => setForm({ ...form, widget_color: e.target.value })}
                      placeholder="#0F766E"
                    />
                  </div>
                </div>
              </div>

              {/* Live Preview */}
              <div>
                <label className={labelCls}>Widget Header Preview</label>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div
                    className="rounded-t-xl px-4 py-3 text-white text-sm font-bold flex items-center justify-between"
                    style={{ background: form.widget_color || '#0F766E' }}
                  >
                    <span>{form.widget_title || form.name || 'AI Assistant'}</span>
                    <Bot className="w-4 h-4 opacity-80" />
                  </div>
                  <div className="bg-white p-3 rounded-b-xl border-x border-b border-slate-200 text-xs text-slate-600">
                    {form.greeting || 'Hello! How can I help you today?'}
                  </div>
                </div>
              </div>
            </div>

            {formError && <p className="text-sm text-rose-600 font-medium">{formError}</p>}

            {/* Modal Buttons */}
            <div className="flex gap-2 justify-end pt-2">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className={btnSecondary}
              >
                Cancel
              </button>
              <button type="submit" disabled={saving} className={btnPrimary}>
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Saving...
                  </>
                ) : editing ? (
                  'Save Changes'
                ) : (
                  'Create Chatbot'
                )}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
