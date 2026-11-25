import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Bot, Plus, History, Files, Loader2 } from 'lucide-react';
import apiService, { apiError } from '../services/api';
import { useWorkspace } from '../context/WorkspaceContext';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import { Spinner, ErrorBox, EmptyState } from '../components/ui';

export default function Playground() {
  const { agentId } = useParams();
  const { selectedId } = useWorkspace();
  const [agent, setAgent] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const endRef = useRef(null);

  const greeting = () => ({
    role: 'assistant',
    content: agent?.greeting || `Hello! I am ${agent?.name || 'your AI agent'}. Ask me anything about the uploaded knowledge base.`,
    timestamp: new Date().toISOString(),
    sources: [],
  });

  const load = useCallback(async () => {
    if (!selectedId || !agentId) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      const [agentData, convs] = await Promise.allSettled([
        apiService.getAgent(selectedId, agentId),
        apiService.getConversations(selectedId),
      ]);
      if (agentData.status === 'fulfilled') setAgent(agentData.value.agent || agentData.value);
      if (convs.status === 'fulfilled') {
        const list = convs.value.filter((c) => !c.agent_id || String(c.agent_id) === String(agentId));
        setConversations(list);
      }
    } catch (err) {
      setError(apiError(err, 'Could not load playground. The backend agent endpoints may not be ready yet.'));
    } finally { setLoading(false); }
  }, [selectedId, agentId]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (agent && messages.length === 0) setMessages([greeting()]); }, [agent]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, sending]);

  const startNew = () => { setConversationId(null); setMessages([greeting()]); setError(null); };

  const openConversation = async (conv) => {
    setConversationId(conv.id);
    try {
      const data = await apiService.getConversation(selectedId, conv.id);
      const list = data.messages || data.conversation?.messages || [];
      setMessages(list.length > 0 ? list : [greeting()]);
    } catch (err) {
      setError(apiError(err, 'Could not load this conversation.'));
    }
  };

  const send = async (text) => {
    setError(null);
    const userMsg = { role: 'user', content: text, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);
    try {
      const data = await apiService.chatWithAgent(selectedId, agentId, { message: text, conversation_id: conversationId });
      if (data.conversation_id) setConversationId(data.conversation_id);
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: data.response || data.answer || 'No response returned.',
        sources: data.sources || [],
        timestamp: new Date().toISOString(),
      }]);
      load();
    } catch (err) {
      setError(apiError(err, 'Failed to get a response from the agent.'));
      setMessages((prev) => [...prev, { role: 'assistant', content: `Failed to get a response: ${apiError(err)}`, timestamp: new Date().toISOString() }]);
    } finally { setSending(false); }
  };

  if (loading) return <Spinner label="Loading playground..." />;
  if (!selectedId) return <EmptyState icon={Bot} title="No workspace selected" text="Select a workspace from the sidebar to test an agent." />;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center"><Bot className="w-5 h-5" /></div>
          <div>
            <h2 className="text-xl font-extrabold text-slate-900">{agent?.name || 'Agent playground'}</h2>
            <p className="text-xs text-slate-500">{agent?.provider || ''} {agent?.model ? `/ ${agent.model}` : ''} {agent?.language ? ` / ${agent.language}` : ''}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Link to={`/agents/${agentId}/knowledge`} className="inline-flex items-center gap-2 bg-white border border-slate-200 text-slate-700 font-semibold px-3.5 py-2 rounded-xl text-sm"><Files className="w-4 h-4" /> Knowledge</Link>
          <button onClick={startNew} className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-3.5 py-2 rounded-xl text-sm"><Plus className="w-4 h-4" /> New conversation</button>
        </div>
      </div>

      <ErrorBox message={error} onRetry={load} />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5 items-start">
        <div className="bg-white rounded-2xl border border-slate-200 p-4 lg:col-span-1">
          <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-2 mb-3"><History className="w-4 h-4 text-indigo-600" /> Conversations</h3>
          {conversations.length === 0 ? (
            <p className="text-xs text-slate-500">No conversations yet. Send a message to start the first one.</p>
          ) : (
            <div className="space-y-1.5 max-h-[420px] overflow-y-auto">
              {conversations.map((c) => (
                <button
                  key={c.id}
                  onClick={() => openConversation(c)}
                  className={`w-full text-left px-3 py-2.5 rounded-xl text-sm transition-colors ${String(conversationId) === String(c.id) ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'text-slate-600 hover:bg-slate-50'}`}
                >
                  <span className="block truncate">{c.title || c.first_message || `Conversation ${String(c.id).slice(0, 8)}`}</span>
                  <span className="block text-[11px] text-slate-400 mt-0.5">{c.message_count ?? c.messages?.length ?? ''} {c.created_at ? new Date(c.created_at).toLocaleDateString() : ''}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[calc(100vh-15rem)] min-h-[480px] lg:col-span-3">
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
            {messages.map((m, i) => <ChatMessage key={i} message={m} />)}
            {sending && (
              <div className="flex items-center gap-2 text-xs text-slate-500 py-2">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-600" /> Searching knowledge base and synthesizing...
              </div>
            )}
            <div ref={endRef} />
          </div>
          <ChatInput onSendMessage={send} isLoading={sending} />
        </div>
      </div>
    </div>
  );
}
