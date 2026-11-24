import React from 'react';
import { FileText, Trash2, Calendar, HardDrive, Layers, CheckCircle2, Clock, AlertTriangle } from 'lucide-react';

export default function DocumentCard({ document, onDelete, isDeleting }) {
  const formatBytes = (bytes, decimals = 1) => {
    if (!+bytes) return '0 B';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getBadgeStyle = (type) => {
    switch (type?.toUpperCase()) {
      case 'PDF':
        return 'bg-red-50 text-red-600 border-red-200';
      case 'DOCX':
      case 'DOC':
        return 'bg-blue-50 text-blue-600 border-blue-200';
      case 'TXT':
      case 'MD':
        return 'bg-emerald-50 text-emerald-600 border-emerald-200';
      default:
        return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between">
      <div>
        {/* Top Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center space-x-3">
            <span className={`px-2.5 py-1 rounded-lg text-xs font-bold uppercase tracking-wider border ${getBadgeStyle(document.file_type)}`}>
              {document.file_type || 'FILE'}
            </span>
            <span className={`
              inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[11px] font-medium
              ${document.status === 'processed' ? 'bg-emerald-50 text-emerald-700' : ''}
              ${document.status === 'processing' ? 'bg-amber-50 text-amber-700 animate-pulse' : ''}
              ${document.status === 'failed' ? 'bg-rose-50 text-rose-700' : ''}
            `}>
              {document.status === 'processed' && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
              {document.status === 'processing' && <Clock className="w-3 h-3 text-amber-600" />}
              {document.status === 'failed' && <AlertTriangle className="w-3 h-3 text-rose-600" />}
              <span className="capitalize">{document.status}</span>
            </span>
          </div>

          <button
            onClick={() => onDelete(document.id)}
            disabled={isDeleting}
            title="Delete Document"
            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>

        {/* Filename */}
        <h3 className="font-semibold text-slate-800 text-sm mb-1.5 truncate" title={document.filename}>
          {document.filename}
        </h3>

        {/* Error message if failed */}
        {document.status === 'failed' && document.error_message && (
          <p className="text-[11px] text-rose-600 bg-rose-50 p-2 rounded-lg mb-3">
            {document.error_message}
          </p>
        )}
      </div>

      {/* Metadata Footprint */}
      <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center space-x-1.5" title="File Size">
          <HardDrive className="w-3.5 h-3.5 text-slate-400" />
          <span>{formatBytes(document.file_size)}</span>
        </div>

        <div className="flex items-center space-x-1.5" title="Chunks indexed in Chroma">
          <Layers className="w-3.5 h-3.5 text-indigo-500" />
          <span className="font-medium text-slate-700">{document.chunks_count || 0} chunks</span>
        </div>

        <div className="flex items-center space-x-1.5" title="Uploaded At">
          <Calendar className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-[11px]">{new Date(document.upload_date).toLocaleDateString()}</span>
        </div>
      </div>
    </div>
  );
}

