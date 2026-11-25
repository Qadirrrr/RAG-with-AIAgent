import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Bot,
  FileText,
  HelpCircle,
  CreditCard,
  Plus,
  FlaskConical,
  Files,
  Plug,
  AlertCircle,
} from 'lucide-react';
import StatCard from '../components/StatCard';
import apiService from '../services/api';
import { useWorkspace } from '../context/WorkspaceContext';
import { useAuth } from '../context/AuthContext';

const EMPTY_STATS = {
  total_documents: 0,
  total_questions_asked: 0,
  agents_count: 0,
};

const STEPS = [
  { n: 1, title: 'Create a chatbot', text: 'Make a chatbot for your website and set its name, tone and instructions.' },
  { n: 2, title: 'Add your documents or website', text: 'Upload your files or add your website pages to its knowledge base.' },
  { n: 3, title: 'Add it to your website', text: 'Paste the widget code on your website and it answers only from your data.' },
];

export default function Dashboard() {
  const { selectedId, selected } = useWorkspace();
  const { user } = useAuth();
  const [stats, setStats] = useState(EMPTY_STATS);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, [selectedId]);

  const fetchDashboardData = async () => {
    if (!selectedId) {
      setStats(EMPTY_STATS);
      setAgents([]);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setStats(EMPTY_STATS);
      setAgents([]);
      const [statsData, agentsData] = await Promise.allSettled([
        apiService.getWorkspaceStats(selectedId),
        apiService.getAgents(selectedId),
      ]);

      if (statsData.status === 'fulfilled') {
        setStats({ ...EMPTY_STATS, ...statsData.value });
      }
      if (agentsData.status === 'fulfilled') {
        setAgents(agentsData.value || []);
      }
      setError(null);
    } catch (err) {
      setError('Could not load your dashboard. Check if backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const planId = selected?.plan || selected?.subscription?.plan || selected?.plan_id || 'free';
  const planLabel = String(planId).charAt(0).toUpperCase() + String(planId).slice(1);
  const firstName = (user?.name || '').split(' ')[0];

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header: greeting, current project, New Chatbot */}
      <div className="bg-[#0F2A3D] rounded-2xl p-6 sm:p-8 text-white shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-2xl">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              {firstName ? `Welcome back, ${firstName}` : 'Welcome back'}
            </h2>
            <p className="mt-2 text-slate-300 text-sm sm:text-base leading-relaxed">
              {selected?.name ? (
                <>Project: <span className="font-semibold text-white">{selected.name}</span>. </>
              ) : null}
              Create a chatbot for your website, add your own documents, and it answers only from your data.
            </p>
          </div>
          <Link
            to="/agents?new=1"
            className="inline-flex items-center space-x-2 bg-teal-700 hover:bg-teal-800 text-white font-semibold px-5 py-3 rounded-xl text-sm transition-colors shadow-sm shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span>New Chatbot</span>
          </Link>
        </div>
      </div>

      {/* Error alert if backend unreachable */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-center space-x-3 text-rose-800 text-sm">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Compact stats row for this project only */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          title="Chatbots"
          value={stats.agents_count}
          icon={Bot}
          description="In this project"
          color="teal"
        />
        <StatCard
          title="Documents"
          value={stats.total_documents}
          icon={FileText}
          description="In this project knowledge"
          color="emerald"
        />
        <StatCard
          title="Messages"
          value={stats.total_questions_asked}
          icon={HelpCircle}
          description="Questions answered"
          color="blue"
        />
        <StatCard
          title="Current Plan"
          value={planLabel}
          icon={CreditCard}
          description="For this project"
          color="amber"
        />
      </div>

      {/* How it works: 3 steps */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {STEPS.map((step) => (
          <div key={step.n} className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-xs">
            <div className="w-8 h-8 rounded-full bg-teal-700 text-white text-sm font-bold flex items-center justify-center">
              {step.n}
            </div>
            <h3 className="font-semibold text-slate-800 mt-3 text-sm">{step.title}</h3>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">{step.text}</p>
          </div>
        ))}
      </div>

      {/* His chatbots in this project */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold text-slate-800">Your chatbots</h3>
          <Link to="/agents" className="text-xs font-semibold text-teal-700 hover:text-teal-800">
            Manage all chatbots
          </Link>
        </div>

        {loading ? (
          <div className="bg-white rounded-2xl border border-slate-200/90 p-10 text-center text-sm text-slate-400">
            Loading your chatbots...
          </div>
        ) : agents.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200/90 p-10 text-center">
            <Bot className="w-10 h-10 mx-auto text-slate-300 mb-3" />
            <p className="text-sm font-semibold text-slate-800">Create your first chatbot</p>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
              Create a chatbot, add your documents or website to it, then paste its widget code on your website.
            </p>
            <Link
              to="/agents?new=1"
              className="inline-flex items-center space-x-2 bg-teal-700 hover:bg-teal-800 text-white font-semibold px-4 py-2.5 rounded-xl text-sm transition-colors shadow-sm mt-5"
            >
              <Plus className="w-4 h-4" />
              <span>New Chatbot</span>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {agents.map((agent) => (
              <div key={agent.id} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col">
                <div className="flex items-start justify-between gap-2">
                  <div className="w-11 h-11 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center">
                    <Bot className="w-5 h-5" />
                  </div>
                  <span className={`text-[11px] font-semibold px-2 py-1 rounded-full ${agent.is_active === false ? 'bg-slate-100 text-slate-500' : 'bg-emerald-50 text-emerald-700'}`}>
                    {agent.is_active === false ? 'Inactive' : 'Active'}
                  </span>
                </div>
                <h3 className="font-semibold text-slate-900 mt-4">{agent.name}</h3>
                <p className="text-xs text-slate-500 mt-1 line-clamp-2 min-h-[2rem]">{agent.description || agent.instructions || 'No description set.'}</p>
                <div className="flex flex-wrap gap-2 mt-4">
                  <span className="text-[11px] font-semibold bg-slate-100 text-slate-600 px-2 py-1 rounded-full">{agent.mode === 'agent' ? 'RAG + Agent' : 'Strict RAG'}</span>
                  <span className="text-[11px] font-semibold bg-slate-100 text-slate-600 px-2 py-1 rounded-full flex items-center gap-1">
                    <Files className="w-3 h-3" /> {agent.documents_count ?? agent.document_count ?? 0} docs
                  </span>
                </div>
                <div className="flex flex-col gap-2 mt-5 pt-4 border-t border-slate-100">
                  <div className="flex gap-2">
                    <Link to={`/agents/${agent.id}/knowledge`} className="flex-1 inline-flex items-center justify-center gap-1.5 bg-teal-700 hover:bg-teal-800 text-white font-semibold px-3 py-2 rounded-xl text-xs transition-colors">
                      <Files className="w-4 h-4" /> Add knowledge
                    </Link>
                    <Link to={`/agents/${agent.id}/playground`} className="flex-1 inline-flex items-center justify-center gap-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold px-3 py-2 rounded-xl text-xs transition-colors">
                      <FlaskConical className="w-4 h-4" /> Test chat
                    </Link>
                  </div>
                  <Link to="/integrations" className="inline-flex items-center justify-center gap-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold px-3 py-2 rounded-xl text-xs transition-colors">
                    <Plug className="w-4 h-4" /> Add to website
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
