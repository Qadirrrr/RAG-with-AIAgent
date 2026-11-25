import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Files, RefreshCw, AlertCircle, Search } from 'lucide-react';
import DocumentCard from '../components/DocumentCard';
import apiService, { apiError } from '../services/api';
import { useWorkspace } from '../context/WorkspaceContext';

export default function Documents() {
  const { selectedId } = useWorkspace();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchDocuments = useCallback(async () => {
    if (!selectedId) { setDocuments([]); setLoading(false); return; }
    try {
      setLoading(true);
      setError(null);
      setDocuments([]);
      const docs = await apiService.getWorkspaceDocuments(selectedId);
      setDocuments(docs || []);
    } catch (err) {
      setError(apiError(err, 'Failed to fetch documents. Verify that the backend server is running.'));
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  useEffect(() => { fetchDocuments(); }, [fetchDocuments]);

  const handleDelete = async (documentId) => {
    const doc = documents.find((d) => d.id === documentId);
    if (!doc?.agent_id) return;
    if (!window.confirm('Are you sure you want to delete this document?')) {
      return;
    }
    try {
      setDeletingId(documentId);
      await apiService.deleteAgentDocument(selectedId, doc.agent_id, documentId);
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
    } catch (err) {
      alert(apiError(err, 'Failed to delete document.'));
    } finally {
      setDeletingId(null);
    }
  };

  const filteredDocuments = documents.filter((doc) =>
    (doc.filename || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-800 tracking-tight">
            Knowledge Documents
          </h2>
          <p className="text-slate-500 text-sm mt-1">
            All documents in this workspace, across its agents.
          </p>
        </div>

        <button
          onClick={fetchDocuments}
          disabled={loading}
          className="inline-flex items-center space-x-2 bg-white hover:bg-slate-50 text-slate-700 font-medium px-4 py-2 rounded-xl text-sm border border-slate-200 transition-colors shadow-xs disabled:opacity-50 self-start sm:self-auto"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-teal-600' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Upload happens per agent, so files always belong to one workspace and one agent */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/90 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <p className="text-sm text-slate-600">Documents belong to an agent in this workspace. Add files or website URLs from an agent knowledge base.</p>
        <Link to="/agents" className="inline-flex items-center justify-center bg-teal-700 hover:bg-teal-800 text-white font-semibold px-4 py-2 rounded-xl text-sm shrink-0">Go to Agents</Link>
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-center space-x-3 text-rose-800 text-sm">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Document List Section */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h3 className="text-base font-semibold text-slate-800 flex items-center space-x-2">
            <Files className="w-5 h-5 text-teal-600" />
            <span>Uploaded Files ({documents.length})</span>
          </h3>

          {/* Search box */}
          {documents.length > 0 && (
            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-white border border-slate-200 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-600/20/20 focus:border-teal-500"
              />
            </div>
          )}
        </div>

        {loading && documents.length === 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3].map((n) => (
              <div key={n} className="bg-white rounded-2xl border border-slate-200 p-6 h-40 animate-pulse flex flex-col justify-between">
                <div className="h-4 bg-slate-100 rounded w-1/3" />
                <div className="h-3 bg-slate-100 rounded w-2/3" />
                <div className="h-4 bg-slate-100 rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : filteredDocuments.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredDocuments.map((doc) => (
              <DocumentCard
                key={doc.id}
                document={doc}
                onDelete={handleDelete}
                isDeleting={deletingId === doc.id}
              />
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200/90 p-12 text-center text-slate-400">
            <Files className="w-12 h-12 mx-auto text-slate-300 mb-3" />
            <p className="text-base font-semibold text-slate-700">No documents found</p>
            <p className="text-xs text-slate-500 mt-1">
              {searchQuery ? 'No documents match your search query.' : 'Upload a PDF, DOCX, or TXT file above to get started.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

