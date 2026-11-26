import React, { useState, useEffect, useCallback } from 'react';
import { Key, Copy, Check, Trash2, Plus, Loader2, Code2, Bot } from 'lucide-react';
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
  const [copied, setCopied] = useState(null);
  const [revealedKeys, setRevealedKeys] = useState({});

  const loadAgents = useCallback(async () => {
    if (!selectedId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const list = await apiService.getAgents(selectedId);
      setAgents(list);
      if (list.length > 0) setAgentId((prev) => prev || list[0].id);
    } catch (err) {
      setError(apiError(err, 'Could not load chatbots.'));
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  const loadKeys = useCallback(async () => {
    if (!selectedId || !agentId) {
      setKeys([]);
      return;
    }
    try {
      const list = await apiService.getApiKeys(selectedId, agentId);
      setKeys(list || []);

      // Auto-reveal all keys so they are permanently visible across page refreshes
      for (const k of list || []) {
        try {
          const data = await apiService.revealApiKey(selectedId, agentId, k.id);
          const full = data.api_key || data.key || '';
          if (full) {
            setRevealedKeys((prev) => ({ ...prev, [k.id]: full }));
          }
        } catch (_) {}
      }
    } catch (err) {
      setError(apiError(err, 'Could not load API keys.'));
    }
  }, [selectedId, agentId]);

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  useEffect(() => {
    loadKeys();
  }, [loadKeys]);

  const copy = async (text, id) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // fallback
    }
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const createKey = async (e) => {
    e.preventDefault();
    if (!keyName.trim()) {
      setError('Give the API key a name first.');
      return;
    }
    setCreating(true);
    setError(null);
    try {
      const created = await apiService.createApiKey(selectedId, agentId, {
        name: keyName.trim(),
      });
      const raw = created.api_key || created.key;
      if (raw && created.id) {
        setRevealedKeys((prev) => ({ ...prev, [created.id]: raw }));
      }
      setKeyName('');
      await loadKeys();
    } catch (err) {
      setError(apiError(err, 'Could not create API key.'));
    } finally {
      setCreating(false);
    }
  };

  const deleteKey = async (key) => {
    if (
      !window.confirm(
        `Delete API key "${key.name || key.prefix}"? The website widget using this key will stop working.`
      )
    )
      return;
    try {
      await apiService.deleteApiKey(selectedId, agentId, key.id);
      setRevealedKeys((prev) => {
        const next = { ...prev };
        delete next[key.id];
        return next;
      });
      loadKeys();
    } catch (err) {
      setError(apiError(err, 'Could not delete API key.'));
    }
  };

  if (loading) return <Spinner label="Loading integrations..." />;
  if (!selectedId)
    return (
      <EmptyState
        icon={Code2}
        title="No project selected"
        text="Select a project to manage integrations."
      />
    );
  if (agents.length === 0)
    return (
      <EmptyState
        icon={Bot}
        title="No chatbots created yet"
        text="Create a chatbot first, then come back here to get its website widget and API key."
      />
    );

  const selectedAgent = agents.find((a) => String(a.id) === String(agentId));
  const serverUrl =
    typeof window !== 'undefined' && window.location.origin
      ? window.location.origin
      : API_BASE_URL || 'http://localhost:8000';

  // Find active key string to automatically populate in the script snippet
  const activeKeyStr =
    (keys[0] && revealedKeys[keys[0].id]) ||
    (keys[0] && keys[0].prefix ? `${keys[0].prefix}...` : 'YOUR_API_KEY');

  const widgetSnippet = `<script src="${serverUrl}/widget.js" data-agent-key="${activeKeyStr}" data-api-url="${serverUrl}"></script>`;

  const curlExample = `curl -X POST ${serverUrl}/api/public/chat \\
  -H "Content-Type: application/json" \\
  -H "X-Agent-Key: ${activeKeyStr}" \\
  -d '{"message": "Hello, what are your opening hours?"}'`;

  const pythonExample = `import requests

response = requests.post(
    "${serverUrl}/api/public/chat",
    headers={"X-Agent-Key": "${activeKeyStr}"},
    json={"message": "What are your opening hours?"},
    timeout=60,
)
response.raise_for_status()
data = response.json()
print(data["response"])
print("Conversation ID:", data["conversation_id"])`;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 tracking-tight">
          Website Widget & API Integration
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Generate API keys and embed code. Paste the widget script on any website to deploy your chatbot.
        </p>
      </div>

      <ErrorBox message={error} onRetry={loadAgents} />

      {/* Select Chatbot */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs">
        <label className={labelCls}>Select Chatbot</label>
        <select
          className={inputCls + ' max-w-md'}
          value={agentId}
          onChange={(e) => setAgentId(e.target.value)}
        >
          {agents.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name} ({a.model || 'qwen2.5:7b'})
            </option>
          ))}
        </select>
        {selectedAgent && (
          <p className="text-xs text-teal-700 font-medium mt-2">
            Selected bot: <strong>{selectedAgent.name}</strong> — answers strictly from its own
            uploaded knowledge documents.
          </p>
        )}
      </div>

      {/* API Keys Section */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-6 shadow-xs">
        <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
          <Key className="w-4 h-4 text-teal-600" /> API Keys (Permanent)
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Keys stay saved permanently in the database until you explicitly delete them.
        </p>

        {/* Create Key Form */}
        <form onSubmit={createKey} className="flex gap-2 mt-4">
          <input
            className={inputCls}
            value={keyName}
            onChange={(e) => setKeyName(e.target.value)}
            placeholder="Key name, for example: Production Website Widget"
          />
          <button type="submit" disabled={creating} className={btnPrimary + ' shrink-0'}>
            {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}{' '}
            Create Key
          </button>
        </form>

        {/* Keys List */}
        {keys.length === 0 ? (
          <p className="text-xs text-slate-400 mt-4 py-2">
            No API keys created yet for this chatbot. Create one above to get your embed script.
          </p>
        ) : (
          <div className="divide-y divide-slate-100 mt-4">
            {keys.map((k) => {
              const fullKey = revealedKeys[k.id] || k.prefix || 'sk-live-...';
              return (
                <div key={k.id} className="py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-slate-800">{k.name || 'API Key'}</p>
                    <code className="inline-block mt-1 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-teal-800 font-mono break-all select-all">
                      {fullKey}
                    </code>
                    <span className="block text-[11px] text-slate-400 mt-0.5">
                      Created: {k.created_at ? new Date(k.created_at).toLocaleDateString() : 'Active'}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => copy(fullKey, `key-${k.id}`)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold rounded-lg border border-slate-200 transition-colors"
                      title="Copy Key"
                    >
                      {copied === `key-${k.id}` ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                      <span>{copied === `key-${k.id}` ? 'Copied' : 'Copy'}</span>
                    </button>
                    <button
                      onClick={() => deleteKey(k)}
                      title="Delete key"
                      className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Website Widget Snippet */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-6 shadow-xs">
        <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
          <Code2 className="w-4 h-4 text-teal-600" /> Embed Chatbot on Your Website
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Paste this single tag right before the closing <code>&lt;/body&gt;</code> tag of your website (WordPress, Shopify, React, HTML).
        </p>

        <div className="relative mt-3">
          <pre className="bg-slate-900 text-slate-100 text-xs sm:text-sm rounded-xl p-4 overflow-x-auto whitespace-pre-wrap break-all leading-relaxed font-mono">
            {widgetSnippet}
          </pre>
          <button
            onClick={() => copy(widgetSnippet, 'widget')}
            className="absolute top-3 right-3 flex items-center gap-1.5 bg-white/10 hover:bg-white/20 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
          >
            {copied === 'widget' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied === 'widget' ? 'Copied' : 'Copy Code'}</span>
          </button>
        </div>
      </div>

      {/* REST API Examples */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-6 shadow-xs space-y-4">
        <h2 className="text-base font-semibold text-slate-800">Direct REST API Access</h2>
        <p className="text-xs text-slate-500">
          Call the chatbot from your own backend, mobile app, or Python script.
        </p>

        {/* cURL */}
        <div>
          <p className="text-xs font-semibold text-slate-700 mb-1">cURL Example</p>
          <div className="relative">
            <pre className="bg-slate-900 text-slate-100 text-xs rounded-xl p-4 overflow-x-auto whitespace-pre-wrap break-all font-mono">
              {curlExample}
            </pre>
            <button
              onClick={() => copy(curlExample, 'curl')}
              className="absolute top-3 right-3 flex items-center gap-1 bg-white/10 hover:bg-white/20 text-white text-xs font-medium px-2.5 py-1 rounded-lg"
            >
              {copied === 'curl' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied === 'curl' ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
        </div>

        {/* Python */}
        <div>
          <p className="text-xs font-semibold text-slate-700 mb-1">Python Example</p>
          <div className="relative">
            <pre className="bg-slate-900 text-slate-100 text-xs rounded-xl p-4 overflow-x-auto whitespace-pre-wrap break-all font-mono">
              {pythonExample}
            </pre>
            <button
              onClick={() => copy(pythonExample, 'python')}
              className="absolute top-3 right-3 flex items-center gap-1 bg-white/10 hover:bg-white/20 text-white text-xs font-medium px-2.5 py-1 rounded-lg"
            >
              {copied === 'python' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied === 'python' ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
