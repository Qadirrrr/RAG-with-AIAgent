import React, { useState, useEffect, useCallback } from 'react';
import { Files, Upload, Trash2, RefreshCw, AlertCircle, CheckCircle, FileText, Search } from 'lucide-react';
import apiService, { apiError } from '../services/api';

export default function Documents() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchDocs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const list = await apiService.getDocuments();
      setDocuments(list);
    } catch (err) {
      setError(apiError(err, 'Failed to fetch documents.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadProgress(0);
    setError(null);
    setSuccess(null);

    try {
      const res = await apiService.uploadDocument(file, (evt) => {
        if (evt.total) {
          setUploadProgress(Math.round((evt.loaded * 100) / evt.total));
        }
      });
      setSuccess(`"${file.name}" uploaded and indexed successfully (${res.chunks} chunks).`);
      e.target.value = '';
      await fetchDocs();
    } catch (err) {
      setError(apiError(err, 'Failed to upload document.'));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId, filename) => {
    if (!window.confirm(`Delete "${filename}"? Its chunks will be removed from vector memory.`)) {
      return;
    }
    setDeletingId(docId);
    setError(null);
    setSuccess(null);
    try {
      await apiService.deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
      setSuccess(`"${filename}" deleted successfully.`);
    } catch (err) {
      setError(apiError(err, 'Failed to delete document.'));
    } finally {
      setDeletingId(null);
    }
  };

  const filtered = documents.filter((d) =>
    (d.filename || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">Knowledge Documents</h1>
          <p className="text-sm text-slate-500 mt-1">
            Upload PDFs, text, or docs. The AI answers strictly from these files.
          </p>
        </div>
        <button
          onClick={fetchDocs}
          disabled={loading}
          className="inline-flex items-center gap-2 bg-white hover:bg-slate-50 text-slate-700 font-medium px-4 py-2 rounded-xl text-sm border border-slate-200 transition-colors shadow-xs disabled:opacity-50 self-start sm:self-auto"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-teal-600' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-center space-x-3 text-rose-800 text-sm">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center space-x-3 text-emerald-800 text-sm">
          <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* Upload Box */}
      <div className="bg-white rounded-2xl p-6 border-2 border-dashed border-slate-200 hover:border-teal-500 transition-colors text-center shadow-xs">
        <label className="cursor-pointer block">
          <input
            type="file"
            onChange={handleFileUpload}
            disabled={uploading}
            accept=".pdf,.txt,.docx,.csv,.md"
            className="hidden"
          />
          <div className="w-12 h-12 rounded-2xl bg-teal-50 text-teal-600 flex items-center justify-center mx-auto mb-3">
            <Upload className={`w-6 h-6 ${uploading ? 'animate-bounce' : ''}`} />
          </div>
          <p className="text-sm font-semibold text-slate-800">
            {uploading ? 'Uploading and indexing document...' : 'Click or drop files to upload'}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Supported formats: PDF, DOCX, TXT, CSV, Markdown
          </p>
        </label>

        {uploading && (
          <div className="mt-4 max-w-xs mx-auto">
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div
                className="bg-teal-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress || 30}%` }}
              />
            </div>
            <p className="text-xs text-slate-500 mt-1">Processing into vector store...</p>
          </div>
        )}
      </div>

      {/* Document List Header & Search */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-slate-800 flex items-center gap-2">
            <Files className="w-5 h-5 text-teal-600" />
            <span>Indexed Documents ({documents.length})</span>
          </h2>
          {documents.length > 0 && (
            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-white rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600"
              />
            </div>
          )}
        </div>

        {/* Document items */}
        {loading ? (
          <div className="text-center py-10 text-sm text-slate-500">Loading documents...</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 px-4 bg-white rounded-2xl border border-slate-200">
            <FileText className="w-10 h-10 mx-auto text-slate-300 mb-2" />
            <p className="text-sm font-semibold text-slate-700">No documents found</p>
            <p className="text-xs text-slate-400 mt-1">Upload a PDF or document above to get started.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-2.5">
            {filtered.map((doc) => (
              <div
                key={doc.id}
                className="bg-white rounded-xl p-4 border border-slate-200/90 shadow-xs flex items-center justify-between gap-4 hover:border-slate-300 transition-colors"
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-800 truncate">{doc.filename}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700">
                        {doc.status || 'processed'}
                      </span>
                      <span className="text-xs text-slate-400">
                        {doc.chunks} chunks indexed
                      </span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => handleDelete(doc.id, doc.filename)}
                  disabled={deletingId === doc.id}
                  className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors shrink-0 disabled:opacity-40"
                  title="Delete document"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
