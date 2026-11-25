import React, { useState, useEffect, useCallback } from 'react';
import { History, MessageSquare, Bot } from 'lucide-react';
import apiService, { apiError } from '../services/api';
import { useWorkspace } from '../context/WorkspaceContext';
import ChatMessage from '../components/ChatMessage';
import { Spinner, ErrorBox, EmptyState } from '../components/ui';

export default function Conversations() {
  const { selectedId } = useWorkspace();
  const [list, setList] = useState([]);
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!selectedId) { setLoading(false); setList([]); return; }
    setLoading(true);
    setError(null);
    try { setList(await apiService.getConversations(selectedId)); }
    catch (err) { setError(apiError(err, 'Could not load conversations.')); }
    finally { setLoading(false); }
  }, [selectedId]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setSelected(null); setMessages([]); }, [selectedId]);

  const open = async (conv) => {
    setSelected(conv);
    setLoadingDetail(true);
    try {
      const data = await apiService.getConversation(selectedId, conv.id);
      setMessages(data.messages || data.conversation?.messages || conv.messages || []);
    } catch (err) {
      setError(apiError(err, 'Could not load this conversation.'));
      setMessages([]);
    } finally { setLoadingDetail(false); }
  };

  if (loading) return <Spinner label="Loading conversations..." />;
  if (!selectedId) return <EmptyState icon={History} title="No workspace selected" text="Select a workspace from the sidebar to view conversations." />;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-extrabold text-slate-900">Conversations</h2>
        <p className="text-sm text-slate-500 mt-1">Every chat your agents have with visitors, in one place.</p>
      </div>
      <ErrorBox message={error} onRetry={load} />
      {list.length === 0 ? (
        <EmptyState icon={MessageSquare} title="No conversations yet" text="Conversations appear here once someone chats with one of your agents in the playground, widget or API." />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-start">
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden lg:col-span-1">
            <ul className="divide-y divide-slate-100 max-h-[560px] overflow-y-auto">
              {list.map((c) => (
                <li key={c.id}>
                  <button onClick={() => open(c)} className={`w-full text-left px-5 py-4 hover:bg-slate-50 ${String(selected?.id) === String(c.id) ? 'bg-teal-50' : ''}`}>
                    <p className="text-sm font-semibold text-slate-800 truncate">{c.title || c.first_message || `Conversation ${String(c.id).slice(0, 8)}`}</p>
                    <p className="text-xs text-slate-500 mt-1 flex items-center gap-3">
                      <span className="flex items-center gap-1"><Bot className="w-3.5 h-3.5" /> {c.agent_name || c.agent_id || 'Agent'}</span>
                      <span>{c.message_count ?? c.messages?.length ?? 0} messages</span>
                      <span>{c.created_at ? new Date(c.created_at).toLocaleDateString() : ''}</span>
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-white rounded-2xl border border-slate-200 p-6 lg:col-span-2 min-h-[300px]">
            {!selected ? (
              <p className="text-sm text-slate-500 text-center py-16">Select a conversation to view its full message history.</p>
            ) : loadingDetail ? (
              <Spinner label="Loading messages..." />
            ) : messages.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-16">No messages in this conversation.</p>
            ) : (
              <div className="space-y-2">
                <h3 className="font-semibold text-slate-800 mb-4">{selected.title || 'Conversation'}</h3>
                {messages.map((m, i) => <ChatMessage key={i} message={m} />)}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
