import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Bot, Plus, MessageSquare, Files, Trash2, ChevronRight } from 'lucide-react';
import apiService, { apiError } from '../services/api';
import { useWorkspace } from '../context/WorkspaceContext';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import { Spinner, ErrorBox, EmptyState } from '../components/ui';

export default function Playground() {
  const { agentId } = useParams();
  const { selectedId } = useWorkspace();

  const [agent, setAgent]               = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId]  = useState(null);   // currently open conversation
  const [messages, setMessages]          = useState([]);
  const [loading, setLoading]            = useState(true);
  const [sending, setSending]            = useState(false);
  const [error, setError]                = useState(null);
  const endRef = useRef(null);

  // ─── helpers ────────────────────────────────────────────────────────────────

  const makeGreeting = (a) => ({
    role: 'assistant',
    content: a?.greeting || `Hello! I am ${a?.name || 'your assistant'}. How can I help you today?`,
    timestamp: new Date().toISOString(),
  });

  const convLabel = (c) =>
    c.title || c.first_message || `Conversation ${String(c.id).slice(0, 8)}`;

  // ─── load agent + conversations ─────────────────────────────────────────────

  const loadConversations = useCallback(async (currentAgent) => {
    if (!selectedId) return;
    try {
      const raw = await apiService.getConversations(selectedId);
      // Keep only conversations belonging to this agent
      const list = raw.filter(
        (c) => !c.agent_id || String(c.agent_id) === String(agentId)
      );
      // Sort newest first
      list.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
      setConversations(list);
    } catch (_) {
      // Silently ignore – conversations panel is non-critical
    }
  }, [selectedId, agentId]);

  const load = useCallback(async () => {
    if (!selectedId || !agentId) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      const agentData = await apiService.getAgent(selectedId, agentId);
      const a = agentData.agent || agentData;
      setAgent(a);
      setMessages([makeGreeting(a)]);
      await loadConversations(a);
    } catch (err) {
      setError(apiError(err, 'Could not load playground.'));
    } finally {
      setLoading(false);
    }
  }, [selectedId, agentId, loadConversations]);

  useEffect(() => { load(); }, [load]);

  // Reset when agent changes
  useEffect(() => {
    setMessages([]);
    setActiveConvId(null);
    setConversations([]);
  }, [selectedId, agentId]);

  // Auto-scroll
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, sending]);

  // ─── actions ────────────────────────────────────────────────────────────────

  const startNew = () => {
    setActiveConvId(null);
    setMessages(agent ? [makeGreeting(agent)] : []);
    setError(null);
  };

  const openConversation = async (conv) => {
    if (String(activeConvId) === String(conv.id)) return; // already open
    setError(null);
    setActiveConvId(conv.id);
    try {
      const data = await apiService.getConversation(selectedId, conv.id);
      const list = data.messages || data.conversation?.messages || [];
      setMessages(list.length > 0 ? list : [makeGreeting(agent)]);
    } catch (err) {
      setError(apiError(err, 'Could not load this conversation.'));
    }
  };

  const removeConversation = async (e, conv) => {
    e.stopPropagation();
    if (!window.confirm('Delete this conversation?')) return;
    try {
      await apiService.deleteConversation(selectedId, conv.id);
      setConversations((prev) => prev.filter((c) => String(c.id) !== String(conv.id)));
      if (String(activeConvId) === String(conv.id)) startNew();
    } catch (err) {
      setError(apiError(err, 'Could not delete conversation.'));
    }
  };

  const send = async (text) => {
    setError(null);
    const userMsg = { role: 'user', content: text, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);
    try {
      const data = await apiService.chatWithAgent(selectedId, agentId, {
        message: text,
        conversation_id: activeConvId,
      });

      // Set / update conversation id from response
      if (data.conversation_id) {
        setActiveConvId(data.conversation_id);
      }

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response || data.answer || 'No response returned.',
          sources: data.sources || [],
          timestamp: new Date().toISOString(),
        },
      ]);

      // Refresh conversation list so the new conversation appears in sidebar
      await loadConversations(agent);
    } catch (err) {
      const isTimeout =
        err.code === 'ECONNABORTED' || (err.message || '').toLowerCase().includes('timeout');
      const friendlyMsg = isTimeout
        ? 'The assistant is taking longer than expected. Please try again in a moment.'
        : apiError(err, 'Something went wrong. Please try again.');
      setError(friendlyMsg);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: friendlyMsg, timestamp: new Date().toISOString() },
      ]);
    } finally {
      setSending(false);
    }
  };

  // ─── render ─────────────────────────────────────────────────────────────────

  if (loading) return <Spinner label="Loading playground..." />;
  if (!selectedId)
    return (
      <EmptyState
        icon={Bot}
        title="No project selected"
        text="Select a project from the sidebar to test a chatbot."
      />
    );

  const isNewChat = !activeConvId;

  return (
    <div className="flex flex-col gap-4 h-full">

      {/* ── Header ── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-extrabold text-slate-900">
              {agent?.name || 'Agent Playground'}
            </h2>
            <p className="text-xs text-slate-500">
              {[agent?.provider, agent?.model && `/ ${agent.model}`, agent?.language && `/ ${agent.language}`]
                .filter(Boolean)
                .join(' ')}
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          <Link
            to={`/agents/${agentId}/knowledge`}
            className="inline-flex items-center gap-2 bg-white border border-slate-200 text-slate-700 font-semibold px-3.5 py-2 rounded-xl text-sm hover:bg-slate-50 transition-colors"
          >
            <Files className="w-4 h-4" /> Knowledge
          </Link>
          <button
            onClick={startNew}
            className="inline-flex items-center gap-2 bg-teal-700 hover:bg-teal-800 text-white font-semibold px-3.5 py-2 rounded-xl text-sm transition-colors"
          >
            <Plus className="w-4 h-4" /> New conversation
          </button>
        </div>
      </div>

      <ErrorBox message={error} onRetry={load} />

      {/* ── Main layout ── */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5 items-start flex-1 min-h-0">

        {/* ── Sidebar: Conversations ── */}
        <div className="bg-white rounded-2xl border border-slate-200 p-4 lg:col-span-1 flex flex-col gap-3">
          <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-teal-600" />
            Conversations
          </h3>

          {/* "New chat" row — always visible */}
          <button
            onClick={startNew}
            className={`w-full flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
              isNewChat
                ? 'bg-teal-50 text-teal-700 border border-teal-200'
                : 'text-slate-500 hover:bg-slate-50 border border-transparent'
            }`}
          >
            <Plus className="w-4 h-4 shrink-0" />
            <span className="truncate">New chat</span>
            {isNewChat && <ChevronRight className="w-3.5 h-3.5 ml-auto shrink-0 text-teal-600" />}
          </button>

          {/* Past conversations */}
          {conversations.length === 0 ? (
            <p className="text-xs text-slate-400 text-center py-4">
              No previous conversations yet.
            </p>
          ) : (
            <div className="space-y-1 max-h-[55vh] overflow-y-auto pr-0.5">
              {conversations.map((c) => {
                const isActive = String(activeConvId) === String(c.id);
                return (
                  <div
                    key={c.id}
                    className={`group flex items-start rounded-xl transition-colors ${
                      isActive ? 'bg-teal-50 border border-teal-200' : 'hover:bg-slate-50 border border-transparent'
                    }`}
                  >
                    <button
                      onClick={() => openConversation(c)}
                      className={`flex-1 min-w-0 text-left px-3 py-2.5 text-sm ${
                        isActive ? 'text-teal-700 font-semibold' : 'text-slate-600'
                      }`}
                    >
                      <span className="block truncate">{convLabel(c)}</span>
                      <span className="block text-[11px] text-slate-400 mt-0.5">
                        {c.message_count != null ? `${c.message_count} msg${c.message_count !== 1 ? 's' : ''}` : ''}
                        {c.created_at
                          ? `  ·  ${new Date(c.created_at).toLocaleDateString()}`
                          : ''}
                      </span>
                    </button>

                    {/* Delete button — only on hover */}
                    <button
                      onClick={(e) => removeConversation(e, c)}
                      title="Delete conversation"
                      aria-label="Delete conversation"
                      className="shrink-0 mt-2 mr-2 p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ── Chat panel ── */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[calc(100vh-15rem)] min-h-[480px] lg:col-span-3">

          {/* Chat header strip */}
          <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-2 bg-slate-50/60">
            <MessageSquare className="w-4 h-4 text-teal-600" />
            <span className="text-sm font-semibold text-slate-700">
              {isNewChat
                ? 'New conversation'
                : convLabel(conversations.find((c) => String(c.id) === String(activeConvId)) || {})}
            </span>
            {!isNewChat && (
              <span className="ml-auto text-xs text-slate-400">
                {conversations.find((c) => String(c.id) === String(activeConvId))?.message_count ?? ''} messages
              </span>
            )}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
            {messages.map((m, i) => (
              <ChatMessage key={i} message={m} />
            ))}

            {/* Typing indicator */}
            {sending && (
              <div className="flex justify-start py-2" aria-label="Loading">
                <div className="bg-slate-50 border border-slate-200/80 rounded-2xl px-4 py-3 flex items-center space-x-1.5">
                  <div className="w-2 h-2 rounded-full bg-teal-500 animate-bounce" />
                  <div className="w-2 h-2 rounded-full bg-teal-500 animate-bounce [animation-delay:-.3s]" />
                  <div className="w-2 h-2 rounded-full bg-teal-500 animate-bounce [animation-delay:-.5s]" />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Input */}
          <ChatInput onSendMessage={send} isLoading={sending} />
        </div>
      </div>
    </div>
  );
}
