import React, { useState, useEffect } from 'react';
import { Files, RefreshCw, AlertCircle, Search } from 'lucide-react';
import FileUpload from '../components/FileUpload';
import DocumentCard from '../components/DocumentCard';
import apiService from '../services/api';

export default function Documents() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getDocuments();
      setDocuments(data || []);
    } catch (err) {
      setError('Failed to fetch documents. Verify that the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleUploadSuccess = async (file, onProgress) => {
    const response = await apiService.uploadDocument(file, onProgress);
    await fetchDocuments();
    return response;
  };

  const handleDelete = async (documentId) => {
    if (!window.confirm('Are you sure you want to delete this document from the vector store?')) {
      return;
    }

    try {
      setDeletingId(documentId);
      await apiService.deleteDocument(documentId);
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete document.');
    } finally {
      setDeletingId(null);
    }
  };

  const filteredDocuments = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
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
            Upload, manage, and inspect documents vectorized into ChromaDB for RAG context.
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

      {/* File Upload Zone */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200/90 shadow-xs">
        <FileUpload onUploadSuccess={handleUploadSuccess} />
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

