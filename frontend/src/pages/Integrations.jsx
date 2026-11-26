import React, { useState, useEffect, useCallback } from 'react';
import { Plug, Key, Copy, Check, Trash2, Plus, Loader2 } from 'lucide-react';
import apiService, { apiError, API_BASE_URL } from '../services/api';
import { useWorkspace } from '../context/WorkspaceContext';
import { Spinner, ErrorBox, EmptyState, inputCls, labelCls, btnPrimary } from '../components/ui';

export default function Integrations() {
  const { selectedId } = useWorkspace();
  const [agents, setAgents] = useState([]);
  const [agentId, setAgentId] = useState('');
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [keyName, setKeyName] = useState('');
  const [creating, setCreating] = useState(false);
  const [newKey, setNewKey] = useState(null);
  const [copied, setCopied] = useState(null);

  const loadAgents = useCallback(async () => {
    if (!selectedId) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      const list = await apiService.getAgents(selectedId);
      setAgents(list);
      if (list.length > 0) setAgentId((prev) => prev || list[0].id);
    } catch (err) {
      setError(apiError(err, 'Could not load chatbots.'));
    } finally { setLoading(false); }
  }, [selectedId]);

  const loadKeys = useCallback(async () => {
    if (!selectedId || !agentId) { setKeys([]); return; }
    try { setKeys(await apiService.getApiKeys(selectedId, agentId)); }
    catch (err) { setError(apiError(err, 'Could not load API keys.')); }
  }, [selectedId, agentId]);

  useEffect(() => { loadAgents(); }, [loadAgents]);
  useEffect(() => { loadKeys(); }, [loadKeys]);

  const copy = async (text, id) => {
    try { await navigator.clipboard.writeText(text); } catch { /* clipboard unavailable */ }
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const createKey = async (e) => {
    e.preventDefault();
    if (!keyName.trim()) { setError('Give the API key a name first.'); return; }
    setCreating(true);
    setError(null);
    setNewKey(null);
    try {
      const created = await apiService.createApiKey(selectedId, agentId, { name: keyName.trim() });
      if (created.key) setNewKey(created.key);
      setKeyName('');
      loadKeys();
    } catch (err) {
      setError(apiError(err, 'Could not create API key.'));
    } finally { setCreating(false); }
  };

  const deleteKey = async (key) => {
    if (!window.confirm(`Revoke API key "${key.name || key.prefix}"? Existing integrations using it will stop working.`)) return;
    try { await apiService.deleteApiKey(selectedId, agentId, key.id); loadKeys(); }
    catch (err) { setError(apiError(err, 'Could not delete API key.')); }
  };

  if (loading) return <Spinner label="Loading integrations..." />;
  if (!selectedId) return <EmptyState icon={Plug} title="No workspace selected" text="Select a workspace from the sidebar to manage integrations." />;
  if (agents.length === 0) return <EmptyState icon={Plug} title="No chatbots yet" text="Create a chatbot first, then come back here to get its website widget and API key." />;

  const selectedAgent = agents.find((a) => String(a.id) === String(agentId));
  const widgetSnippet = `<script src="${API_BASE_URL}/widget.js" data-agent-key="YOUR_API_KEY" data-api-url="${API_BASE_URL}"></script>`;
  const curlExample = `curl -X POST ${API_BASE_URL}/api/public/chat \\\n  -H "Content-Type: application/json" \\\n  -H "X-Agent-Key: YOUR_API_KEY" \\\n  -d '{"message": "Hello, what are your opening hours?"}'`;
  const pythonExample = `import requests

response = requests.post(
    "${API_BASE_URL}/api/public/chat",
    headers={"X-Agent-Key": "YOUR_API_KEY"},
    json={"message": "What are your opening hours?"},
    timeout=60,
)
response.raise_for_status()
data = response.json()
print(data["response"])
print("Conversation ID:", data["conversation_id"])`;
  const responseExample = `{
  "conversation_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "response": "We are open Monday to Saturday, 9 AM to 6 PM.",
  "sources": [],
  "agent_steps": []
}`;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-extrabold text-slate-900">Add to your website</h2>
        <p className="text-sm text-slate-500 mt-1">Pick a chatbot, create its API key, and paste the widget code on your website. The chatbot answers only from that chatbot's own documents and website data, never from another chatbot or project.</p>
      </div>
      <ErrorBox message={error} onRetry={loadAgents} />

      <div className="bg-white rounded-2xl border border-slate-200 p-6">
        <label className={labelCls}>Chatbot</label>
        <select className={inputCls + ' max-w-md'} value={agentId} onChange={(e) => setAgentId(e.target.value)}>
          {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        {selectedAgent && <p className="text-xs text-slate-500 mt-2">{selectedAgent.provider || ''} {selectedAgent.model ? `/ ${selectedAgent.model}` : ''}</p>}
        {selectedAgent && <p className="text-xs text-teal-700 mt-1">This chatbot answers only from its own documents. Add or change its data on its Knowledge page.</p>}
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-800">Website widget</h3>
        <p className="text-sm text-slate-500 mt-1">Paste this one line before the closing <code className="bg-slate-100 px-1 rounded">&lt;/body&gt;</code> tag on any website. Create an API key below first, then replace YOUR_API_KEY.</p>
        <div className="relative mt-4">
          <pre className="bg-slate-900 text-slate-100 text-xs sm:text-sm rounded-xl p-4 overflow-x-auto whitespace-pre-wrap break-all">{widgetSnippet}</pre>
          <button onClick={() => copy(widgetSnippet, 'widget')} className="absolute top-3 right-3 flex items-center gap-1.5 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold px-3 py-1.5 rounded-lg">
            {copied === 'widget' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />} {copied === 'widget' ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-800">REST API</h3>
        <p className="text-sm text-slate-500 mt-1">Anyone can ask this chatbot a question from their own code. Send a POST request to <code className="bg-slate-100 px-1 rounded">POST {API_BASE_URL}/api/public/chat</code> with your API key in the <code className="bg-slate-100 px-1 rounded">X-Agent-Key</code> header and a JSON body with a <code className="bg-slate-100 px-1 rounded">message</code> field. That is all: your API key is linked to this one chatbot, so no agent ID is needed, and the answer comes only from this chatbot's own documents. To continue the same conversation, send the <code className="bg-slate-100 px-1 rounded">conversation_id</code> from the first response with your next message.</p>

        <p className="text-sm font-semibold text-slate-700 mt-5">Python example</p>
        <div className="relative mt-2">
          <pre className="bg-slate-900 text-slate-100 text-xs sm:text-sm rounded-xl p-4 overflow-x-auto whitespace-pre-wrap break-all">{pythonExample}</pre>
          <button onClick={() => copy(pythonExample, 'python')} className="absolute top-3 right-3 flex items-center gap-1.5 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold px-3 py-1.5 rounded-lg">
            {copied === 'python' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />} {copied === 'python' ? 'Copied' : 'Copy'}
          </button>
        </div>

        <p className="text-sm font-semibold text-slate-700 mt-5">curl example</p>
        <div className="relative mt-2">
          <pre className="bg-slate-900 text-slate-100 text-xs sm:text-sm rounded-xl p-4 overflow-x-auto whitespace-pre-wrap break-all">{curlExample}</pre>
          <button onClick={() => copy(curlExample, 'curl')} className="absolute top-3 right-3 flex items-center gap-1.5 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold px-3 py-1.5 rounded-lg">
            {copied === 'curl' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />} {copied === 'curl' ? 'Copied' : 'Copy'}
          </button>
        </div>

        <p className="text-sm font-semibold text-slate-700 mt-5">Response</p>
        <pre className="bg-slate-900 text-slate-100 text-xs sm:text-sm rounded-xl p-4 overflow-x-auto whitespace-pre-wrap break-all mt-2">{responseExample}</pre>
        <p className="text-sm text-slate-500 mt-2">The answer text is in the <code className="bg-slate-100 px-1 rounded">response</code> field. <code className="bg-slate-100 px-1 rounded">sources</code> lists the documents used when citations are switched on for this chatbot, otherwise it is empty.</p>

        <p className="text-sm font-semibold text-slate-700 mt-5">Errors</p>
        <ul className="text-sm text-slate-500 mt-2 space-y-1.5 list-disc list-inside">
          <li><code className="bg-slate-100 px-1 rounded">401</code> The API key is missing or invalid, or an <code className="bg-slate-100 px-1 rounded">agent_id</code> was sent that does not belong to this key.</li>
          <li><code className="bg-slate-100 px-1 rounded">403</code> This chatbot is deactivated. Activate it on the Chatbots page to use the API.</li>
          <li><code className="bg-slate-100 px-1 rounded">422</code> The request body is invalid, for example the <code className="bg-slate-100 px-1 rounded">message</code> field is missing.</li>
        </ul>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-800 flex items-center gap-2"><Key className="w-4 h-4 text-teal-600" /> API keys</h3>
        <p className="text-sm text-slate-500 mt-1">Keys are shown in full only once, right after creation. Store them safely.</p>
        {newKey && (
          <div className="mt-4 p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
            <p className="text-xs font-semibold text-emerald-800 mb-2">Your new API key (copy it now, it will not be shown again):</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-white border border-emerald-200 rounded-lg px-3 py-2 text-sm break-all">{newKey}</code>
              <button onClick={() => copy(newKey, 'newkey')} className={btnPrimary + ' !px-3 !py-2 text-xs'}>{copied === 'newkey' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />} {copied === 'newkey' ? 'Copied' : 'Copy'}</button>
            </div>
          </div>
        )}
        <form onSubmit={createKey} className="flex gap-2 mt-4">
          <input className={inputCls} value={keyName} onChange={(e) => setKeyName(e.target.value)} placeholder="Key name, for example Website widget" />
          <button type="submit" disabled={creating} className={btnPrimary + ' shrink-0'}>{creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} Create key</button>
        </form>
        {keys.length === 0 ? (
          <p className="text-sm text-slate-500 mt-4">No API keys yet for this chatbot.</p>
        ) : (
          <ul className="divide-y divide-slate-100 mt-4">
            {keys.map((k) => (
              <li key={k.id} className="py-3 flex items-center gap-3">
                <Key className="w-4 h-4 text-slate-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-800 truncate">{k.name || 'API key'}</p>
                  <p className="text-xs text-slate-500 font-mono">{k.prefix || k.key_prefix || ''}... {k.created_at ? ` / ${new Date(k.created_at).toLocaleDateString()}` : ''}</p>
                </div>
                <button onClick={() => deleteKey(k)} title="Revoke key" className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50"><Trash2 className="w-4 h-4" /></button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
