import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { FileText, Link2, Trash2, FlaskConical, Loader2 } from 'lucide-react';
import apiService, { apiError } from '../services/api';
import { useWorkspace } from '../context/WorkspaceContext';
import FileUpload from '../components/FileUpload';
import { Spinner, ErrorBox, EmptyState, inputCls, labelCls, btnPrimary } from '../components/ui';

export default function Knowledge() {
  const { agentId } = useParams();
  const { selectedId } = useWorkspace();
  const [agent, setAgent] = useState(null);
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [url, setUrl] = useState('');
  const [addingUrl, setAddingUrl] = useState(false);
  const [urlError, setUrlError] = useState(null);

  const load = useCallback(async () => {
    if (!selectedId || !agentId) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      const [agentData, docList] = await Promise.allSettled([
        apiService.getAgent(selectedId, agentId),
        apiService.getAgentDocuments(selectedId, agentId),
      ]);
      if (agentData.status === 'fulfilled') setAgent(agentData.value.agent || agentData.value);
      if (docList.status === 'fulfilled') setDocs(docList.value);
      else setError(apiError(docList.reason, 'Could not load documents.'));
    } catch (err) {
      setError(apiError(err, 'Could not load knowledge base.'));
    } finally { setLoading(false); }
  }, [selectedId, agentId]);

  useEffect(() => { load(); }, [load]);

  const handleUpload = async (file, onProgress) => {
    const result = await apiService.uploadAgentDocument(selectedId, agentId, file, onProgress);
    load();
    return result;
  };

  const addUrl = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;
    try { new URL(url.trim()); } catch { setUrlError('Please enter a valid URL, for example https://example.com/docs'); return; }
    setAddingUrl(true);
    setUrlError(null);
    try {
      await apiService.addAgentDocumentUrl(selectedId, agentId, url.trim());
      setUrl('');
      load();
    } catch (err) {
      setUrlError(apiError(err, 'Could not add this URL.'));
    } finally { setAddingUrl(false); }
  };

  const remove = async (doc) => {
    if (!window.confirm(`Delete "${doc.filename || doc.name || doc.title}" from this agent?`)) return;
    try { await apiService.deleteAgentDocument(selectedId, agentId, doc.id); load(); }
    catch (err) { setError(apiError(err, 'Could not delete document.')); }
  };

  if (loading) return <Spinner label="Loading knowledge base..." />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-extrabold text-slate-900">Knowledge base</h2>
          <p className="text-sm text-slate-500 mt-1">{agent?.name ? `Documents for ${agent.name}` : 'Documents for this agent'}: files are extracted, chunked, embedded and stored for retrieval.</p>
        </div>
        <Link to={`/agents/${agentId}/playground`} className={btnPrimary}><FlaskConical className="w-4 h-4" /> Test in playground</Link>
      </div>

      <ErrorBox message={error} onRetry={load} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white rounded-2xl border border-slate-200 p-6">
          <h3 className="font-semibold text-slate-800 mb-4">Upload a document</h3>
          <FileUpload onUploadSuccess={handleUpload} />
          <p className="text-xs text-slate-400 mt-3">PDF, DOCX and TXT files up to 25 MB. Uploaded files belong only to this agent and workspace.</p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200 p-6">
          <h3 className="font-semibold text-slate-800 mb-4">Add a website URL</h3>
          <form onSubmit={addUrl} className="space-y-3">
            <div>
              <label className={labelCls}>Website URL</label>
              <div className="flex gap-2">
                <input className={inputCls} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.com/help" />
                <button type="submit" disabled={addingUrl} className={btnPrimary + ' shrink-0'}>
                  {addingUrl ? <Loader2 className="w-4 h-4 animate-spin" /> : <Link2 className="w-4 h-4" />} Add
                </button>
              </div>
            </div>
            {urlError && <p className="text-sm text-rose-600">{urlError}</p>}
            <p className="text-xs text-slate-500">The page content is fetched, chunked and added to this agent knowledge base.</p>
          </form>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">Documents ({docs.length})</h3>
        </div>
        {docs.length === 0 ? (
          <div className="p-6"><EmptyState icon={FileText} title="No documents yet" text="Upload a file or add a website URL above. Your agent can only answer from the knowledge you add here." /></div>
        ) : (
          <ul className="divide-y divide-slate-100">
            {docs.map((doc) => (
              <li key={doc.id} className="px-6 py-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center shrink-0"><FileText className="w-5 h-5" /></div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-800 truncate">{doc.filename || doc.name || doc.title || doc.url || 'Document'}</p>
                  <p className="text-xs text-slate-500">
                    {doc.status ? `${doc.status} ` : ''}{doc.chunks_count ?? doc.chunk_count ? ` / ${doc.chunks_count ?? doc.chunk_count} chunks` : ''}{doc.created_at ? ` / ${new Date(doc.created_at).toLocaleDateString()}` : ''}
                  </p>
                  {doc.url && <p className="text-xs text-teal-600 truncate">{doc.url}</p>}
                </div>
                <span className={`hidden sm:inline text-xs font-semibold px-2.5 py-1 rounded-full ${doc.status === 'processed' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                  {doc.status || 'ready'}
                </span>
                <button onClick={() => remove(doc)} title="Delete document" className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50"><Trash2 className="w-4 h-4" /></button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
