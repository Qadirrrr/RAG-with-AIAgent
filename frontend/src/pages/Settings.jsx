import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, ShieldCheck, Cpu, Database, Globe, RefreshCw, Key, CheckCircle2, AlertTriangle } from 'lucide-react';
import apiService from '../services/api';

export default function Settings() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchHealth();
  }, []);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getHealth();
      setHealth(data);
    } catch (err) {
      setError('Cannot connect to FastAPI backend server.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl animate-in fade-in duration-300">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-800 tracking-tight">
            Settings & Configuration
          </h2>
          <p className="text-slate-500 text-sm mt-1">
            System status, AI models, and vector database configuration.
          </p>
        </div>

        <button
          onClick={fetchHealth}
          disabled={loading}
          className="inline-flex items-center space-x-2 bg-white hover:bg-slate-50 text-slate-700 font-medium px-4 py-2 rounded-xl text-sm border border-slate-200 transition-colors shadow-xs"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-teal-600' : ''}`} />
          <span>Check Status</span>
        </button>
      </div>

      {/* Backend & Environment Card */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200/90 shadow-xs space-y-6">
        <h3 className="text-base font-semibold text-slate-800 flex items-center space-x-2.5">
          <Globe className="w-5 h-5 text-teal-600" />
          <span>Backend Connection</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
            <span className="text-xs text-slate-400 block mb-1">API Base URL</span>
            <span className="font-mono text-sm font-semibold text-slate-800">{apiBaseUrl}</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-between">
            <div>
              <span className="text-xs text-slate-400 block mb-1">FastAPI Server</span>
              <span className={`text-sm font-semibold ${health ? 'text-emerald-700' : 'text-rose-700'}`}>
                {health ? 'Online & Healthy' : 'Offline / Unreachable'}
              </span>
            </div>
            <span className={`w-3 h-3 rounded-full ${health ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
          </div>
        </div>
      </div>

      {/* AI Model Configuration Card */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200/90 shadow-xs space-y-6">
        <h3 className="text-base font-semibold text-slate-800 flex items-center space-x-2.5">
          <Cpu className="w-5 h-5 text-teal-600" />
          <span>AI Model Configuration</span>
        </h3>

        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-2xl bg-slate-50 border border-slate-100">
            <div>
              <p className="text-sm font-medium text-slate-800">Active AI Provider</p>
              <p className="text-xs text-slate-500 mt-0.5">Powers LLM reasoning and semantic vector embeddings</p>
            </div>
            <span className="font-mono text-xs font-bold uppercase text-teal-700 bg-teal-50 border border-teal-200/60 px-3 py-1.5 rounded-xl">
              {health?.provider === 'gemini' ? 'Google Gemini' : health?.provider === 'openai' ? 'OpenAI' : 'Not Configured'}
            </span>
          </div>

          <div className="flex items-center justify-between p-4 rounded-2xl bg-slate-50 border border-slate-100">
            <div>
              <p className="text-sm font-medium text-slate-800">Language Model (LLM)</p>
              <p className="text-xs text-slate-500 mt-0.5">Powers the LangChain AI Agent reasoner</p>
            </div>
            <span className="font-mono text-xs font-bold text-teal-700 bg-teal-50 border border-teal-200/60 px-3 py-1.5 rounded-xl">
              {health?.model || 'gemini-1.5-flash'}
            </span>
          </div>

          <div className="flex items-center justify-between p-4 rounded-2xl bg-slate-50 border border-slate-100">
            <div>
              <p className="text-sm font-medium text-slate-800">Embedding Model</p>
              <p className="text-xs text-slate-500 mt-0.5">Converts document chunks into ChromaDB vectors</p>
            </div>
            <span className="font-mono text-xs font-bold text-slate-700 bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-xl">
              {health?.embedding_model || 'models/text-embedding-004'}
            </span>
          </div>

          <div className="flex items-center justify-between p-4 rounded-2xl bg-slate-50 border border-slate-100">
            <div>
              <p className="text-sm font-medium text-slate-800">API Key Status</p>
              <p className="text-xs text-slate-500 mt-0.5">Configured in backend/.env (GEMINI_API_KEY or OPENAI_API_KEY)</p>
            </div>
            <div className="flex items-center space-x-2">
              {health?.api_configured ? (
                <span className="inline-flex items-center space-x-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Configured ({health.provider?.toUpperCase()})</span>
                </span>
              ) : (
                <span className="inline-flex items-center space-x-1.5 text-xs font-semibold text-amber-700 bg-amber-50 px-3 py-1.5 rounded-xl border border-amber-200">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Missing in backend/.env</span>
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Vector Store Configuration */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200/90 shadow-xs space-y-6">
        <h3 className="text-base font-semibold text-slate-800 flex items-center space-x-2.5">
          <Database className="w-5 h-5 text-teal-600" />
          <span>Vector Database</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
            <span className="text-xs text-slate-400 block mb-1">Engine</span>
            <span className="text-sm font-semibold text-slate-800">ChromaDB Persistent Store</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
            <span className="text-xs text-slate-400 block mb-1">Chroma Connection</span>
            <span className={`text-sm font-semibold ${health?.chroma_status === 'connected' ? 'text-emerald-700' : 'text-slate-600'}`}>
              {health?.chroma_status || 'Checking...'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

