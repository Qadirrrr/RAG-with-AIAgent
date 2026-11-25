import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  FileText, 
  CheckCircle2, 
  HelpCircle, 
  Layers, 
  ArrowRight, 
  Upload, 
  MessageSquare, 
  Activity, 
  Clock, 
  AlertCircle 
} from 'lucide-react';
import StatCard from '../components/StatCard';
import apiService from '../services/api';
import { useWorkspace } from '../context/WorkspaceContext';

const EMPTY_STATS = {
  total_documents: 0,
  processed_documents: 0,
  total_chunks: 0,
  total_questions_asked: 0,
  recent_activity: [],
};

export default function Dashboard() {
  const { selectedId } = useWorkspace();
  const [stats, setStats] = useState(EMPTY_STATS);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, [selectedId]);

  const fetchDashboardData = async () => {
    if (!selectedId) {
      setStats(EMPTY_STATS);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setStats(EMPTY_STATS);
      const [statsData, healthData] = await Promise.allSettled([
        apiService.getWorkspaceStats(selectedId),
        apiService.getHealth()
      ]);

      if (statsData.status === 'fulfilled') {
        setStats({ ...EMPTY_STATS, ...statsData.value });
      }
      if (healthData.status === 'fulfilled') {
        setHealth(healthData.value);
      }
      setError(null);
    } catch (err) {
      setError('Could not load dashboard metrics. Check if backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const formatActivityTime = (isoString) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Welcome Banner */}
      <div className="bg-[#0F2A3D] rounded-2xl p-6 sm:p-8 text-white shadow-sm">
        <div className="max-w-2xl">
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-white/10 text-white mb-3">
            RAG Knowledge System Active
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            Intelligent Document Agent
          </h2>
          <p className="mt-2 text-slate-300 text-sm sm:text-base leading-relaxed">
            Upload your documents and website pages, then ask questions and get direct, professional answers.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              to="/documents"
              className="inline-flex items-center space-x-2 bg-white text-[#0F2A3D] hover:bg-slate-100 font-semibold px-4 py-2.5 rounded-xl text-sm transition-colors shadow-sm"
            >
              <Upload className="w-4 h-4" />
              <span>Upload Documents</span>
            </Link>
            <Link
              to="/chat"
              className="inline-flex items-center space-x-2 bg-teal-700 hover:bg-teal-800 text-white font-semibold px-4 py-2.5 rounded-xl text-sm transition-colors shadow-sm"
            >
              <MessageSquare className="w-4 h-4" />
              <span>Start Chatbot Chat</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Error alert if backend unreachable */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-center space-x-3 text-rose-800 text-sm">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Stat Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          title="Total Documents"
          value={stats.total_documents}
          icon={FileText}
          description="PDF, DOCX, and TXT files"
          color="teal"
        />
        <StatCard
          title="Processed Documents"
          value={stats.processed_documents}
          icon={CheckCircle2}
          description="Ready in this project"
          color="emerald"
        />
        <StatCard
          title="Questions Asked"
          value={stats.total_questions_asked}
          icon={HelpCircle}
          description="Questions answered"
          color="blue"
        />
        <StatCard
          title="Total Chunks"
          value={stats.total_chunks}
          icon={Layers}
          description="Knowledge segments"
          color="amber"
        />
      </div>

      {/* Two Column Section: Quick Actions & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: System Status & Guide */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200/90 p-6 shadow-xs">
            <h3 className="text-base font-semibold text-slate-800 mb-4 flex items-center space-x-2">
              <Activity className="w-5 h-5 text-teal-600" />
              <span>System Status</span>
            </h3>

            <div className="space-y-3.5 text-sm">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <span className="text-slate-500">Vector Store</span>
                <span className="font-medium text-slate-800 flex items-center space-x-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span>ChromaDB Persistent</span>
                </span>
              </div>

              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <span className="text-slate-500">AI Provider</span>
                <span className="font-mono text-xs font-semibold text-teal-600 bg-teal-50 px-2 py-0.5 rounded uppercase">
                  {health?.provider === 'gemini' ? 'Google Gemini' : health?.provider === 'openai' ? 'OpenAI' : 'None'}
                </span>
              </div>

              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <span className="text-slate-500">AI Model</span>
                <span className="font-mono text-xs font-semibold text-teal-600 bg-teal-50 px-2 py-0.5 rounded">
                  {health?.model || 'gemini-3.5-flash-lite'}
                </span>
              </div>

              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <span className="text-slate-500">Embeddings</span>
                <span className="font-mono text-xs font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                  {health?.embedding_model || 'models/text-embedding-004'}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-slate-500">API Key</span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                  health?.api_configured ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                }`}>
                  {health?.api_configured ? 'Configured' : 'Missing in .env'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Recent Activity */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-2xl border border-slate-200/90 p-6 shadow-xs h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-5">
                <h3 className="text-base font-semibold text-slate-800 flex items-center space-x-2">
                  <Clock className="w-5 h-5 text-teal-600" />
                  <span>Recent Activity</span>
                </h3>
                <Link to="/documents" className="text-xs font-semibold text-teal-600 hover:text-teal-700 flex items-center space-x-1">
                  <span>View all documents</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              {stats.recent_activity && stats.recent_activity.length > 0 ? (
                <div className="space-y-3">
                  {stats.recent_activity.map((item, idx) => (
                    <div 
                      key={item.id || idx} 
                      className="flex items-center justify-between p-3 rounded-xl bg-slate-50 hover:bg-slate-100/70 transition-colors border border-slate-100 text-sm"
                    >
                      <div className="flex items-center space-x-3 truncate mr-3">
                        <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 flex items-center justify-center flex-shrink-0">
                          {item.type === 'upload' && <Upload className="w-4 h-4 text-emerald-600" />}
                          {item.type === 'delete' && <Clock className="w-4 h-4 text-rose-500" />}
                          {item.type === 'chat' && <MessageSquare className="w-4 h-4 text-teal-600" />}
                          {!['upload', 'delete', 'chat'].includes(item.type) && <Activity className="w-4 h-4 text-slate-500" />}
                        </div>
                        <div className="truncate">
                          <p className="font-medium text-slate-800 text-xs truncate">{item.title}</p>
                          {item.details && <p className="text-[11px] text-slate-500 truncate">{item.details}</p>}
                        </div>
                      </div>
                      <span className="text-[11px] text-slate-400 font-mono flex-shrink-0">
                        {formatActivityTime(item.timestamp)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-slate-400">
                  <FileText className="w-10 h-10 mx-auto text-slate-300 mb-2" />
                  <p className="text-sm font-medium">No activity yet</p>
                  <p className="text-xs text-slate-400 mt-1">Upload a document to get started</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

