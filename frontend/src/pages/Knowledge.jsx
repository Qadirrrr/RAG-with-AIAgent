import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { FileText, Trash2, FlaskConical } from 'lucide-react';
import apiService, { apiError } from '../services/api';
import { useWorkspace } from '../context/WorkspaceContext';
import FileUpload from '../components/FileUpload';
import { Spinner, ErrorBox, EmptyState, btnPrimary } from '../components/ui';

export default function Knowledge() {
  const { agentId } = useParams();
  const { selectedId } = useWorkspace();
  const [agent, setAgent] = useState(null);
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!selectedId || !agentId) {
      setLoading(false);
      return;
    }
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
    } finally {
      setLoading(false);
    }
  }, [selectedId, agentId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleUpload = async (file, onProgress) => {
    const result = await apiService.uploadAgentDocument(selectedId, agentId, file, onProgress);
    load();
    return result;
  };

  const remove = async (doc) => {
    if (!window.confirm(`Delete "${doc.filename || doc.name || doc.title}" from this chatbot?`))
      return;
    try {
      await apiService.deleteAgentDocument(selectedId, agentId, doc.id);
      load();
    } catch (err) {
      setError(apiError(err, 'Could not delete document.'));
    }
  };

  if (loading) return <Spinner label="Loading knowledge base..." />;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 tracking-tight">
            Knowledge Base
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            {agent?.name ? `Documents for ${agent.name}` : 'Chatbot Knowledge'}: files are
            extracted, chunked, and stored in vector memory for retrieval.
          </p>
        </div>
        <Link to={`/agents/${agentId}/playground`} className={btnPrimary}>
          <FlaskConical className="w-4 h-4" /> Test in Playground
        </Link>
      </div>

      <ErrorBox message={error} onRetry={load} />

      {/* Upload Document Box */}
      <div className="bg-white rounded-2xl border border-slate-200/90 p-6 shadow-xs">
        <h3 className="font-semibold text-slate-800 mb-3 text-base">Upload Documents</h3>
        <FileUpload onUploadSuccess={handleUpload} />
        <p className="text-xs text-slate-500 mt-3">
          Supported files: <strong>PDF, DOCX, TXT, MD, CSV</strong> up to 25 MB. The chatbot
          answers only from these files.
        </p>
      </div>

      {/* Document List */}
      <div className="bg-white rounded-2xl border border-slate-200/90 overflow-hidden shadow-xs">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800 text-sm">
            Uploaded Documents ({docs.length})
          </h3>
        </div>
        {docs.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={FileText}
              title="No documents yet"
              text="Upload a PDF or document above. Your chatbot answers strictly from the files you upload here."
            />
          </div>
        ) : (
          <ul className="divide-y divide-slate-100">
            {docs.map((doc) => (
              <li key={doc.id} className="px-6 py-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-800 truncate">
                    {doc.filename || doc.name || doc.title || 'Document'}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {doc.chunks_count ?? doc.chunk_count
                      ? `${doc.chunks_count ?? doc.chunk_count} chunks indexed`
                      : 'Indexed'}{' '}
                    {doc.created_at ? ` · ${new Date(doc.created_at).toLocaleDateString()}` : ''}
                  </p>
                </div>
                <span
                  className={`hidden sm:inline text-xs font-semibold px-2.5 py-1 rounded-full ${
                    doc.status === 'processed'
                      ? 'bg-emerald-50 text-emerald-700'
                      : 'bg-amber-50 text-amber-700'
                  }`}
                >
                  {doc.status || 'ready'}
                </span>
                <button
                  onClick={() => remove(doc)}
                  title="Delete document"
                  className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
