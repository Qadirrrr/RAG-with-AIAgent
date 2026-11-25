import React, { useState, useEffect, useCallback } from 'react';
import { MessageSquare, Bot, FileText, BarChart3, TrendingUp } from 'lucide-react';
import apiService, { apiError } from '../services/api';
import { useWorkspace } from '../context/WorkspaceContext';
import StatCard from '../components/StatCard';
import { Spinner, ErrorBox, EmptyState } from '../components/ui';

export default function Analytics() {
  const { selectedId } = useWorkspace();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!selectedId) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try { setData(await apiService.getAnalytics(selectedId)); }
    catch (err) { setError(apiError(err, 'Could not load analytics. The backend analytics endpoint may not be ready yet.')); }
    finally { setLoading(false); }
  }, [selectedId]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Spinner label="Loading analytics..." />;
  if (!selectedId) return <EmptyState icon={BarChart3} title="No workspace selected" text="Select a workspace from the sidebar to view analytics." />;

  const totalMessages = data?.usage?.messages_used_this_month ?? data?.total_messages ?? 0;
  const totalAgents = data?.agents_count ?? 0;
  const totalDocs = data?.documents_count ?? 0;
  const totalConvs = data?.total_conversations ?? 0;
  const limit = data?.usage?.monthly_message_limit ?? 0;
  const usedPct = limit > 0 ? Math.min(100, Math.round((totalMessages / limit) * 100)) : 0;
  const daily = Array.isArray(data?.messages_per_day_last_14d) ? data.messages_per_day_last_14d : [];
  const perAgent = Array.isArray(data?.messages_per_agent) ? data.messages_per_agent : [];
  const maxDaily = daily.reduce((m, d) => Math.max(m, d.count ?? d.messages ?? 0), 0) || 1;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-extrabold text-slate-900">Analytics</h2>
        <p className="text-sm text-slate-500 mt-1">Usage and performance for this workspace.</p>
      </div>
      <ErrorBox message={error} onRetry={load} />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard title="Total Messages" value={totalMessages} icon={MessageSquare} description="Messages answered by agents" color="teal" />
        <StatCard title="Conversations" value={totalConvs} icon={TrendingUp} description="Chat sessions started" color="blue" />
        <StatCard title="Agents" value={totalAgents} icon={Bot} description="Active AI agents" color="emerald" />
        <StatCard title="Documents" value={totalDocs} icon={FileText} description="Indexed knowledge files" color="amber" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white rounded-2xl border border-slate-200 p-6">
          <h3 className="font-semibold text-slate-800 mb-1">Monthly usage</h3>
          <p className="text-xs text-slate-500 mb-4">{totalMessages} of {limit || 'unlimited'} messages used this month</p>
          <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
            <div className="bg-teal-700 h-3 rounded-full transition-all" style={{ width: `${usedPct}%` }} />
          </div>
          <p className="text-xs text-slate-500 mt-2">{usedPct}% of monthly limit used</p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200 p-6">
          <h3 className="font-semibold text-slate-800 mb-4">Messages per day</h3>
          {daily.length === 0 ? (
            <p className="text-sm text-slate-500">No daily breakdown returned by the API yet. Totals above are live from the analytics endpoint.</p>
          ) : (
            <div className="flex items-end gap-2 h-36">
              {daily.slice(-14).map((d, i) => {
                const count = d.count ?? d.messages ?? 0;
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1 min-w-0">
                    <span className="text-[10px] font-semibold text-slate-600">{count}</span>
                    <div className="w-full bg-teal-500 rounded-t-md" style={{ height: `${Math.max(4, (count / maxDaily) * 100)}px` }} title={`${d.date || d.day || ''}: ${count}`} />
                    <span className="text-[10px] text-slate-400 truncate w-full text-center">{(d.date || d.day || '').slice(5)}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100"><h3 className="font-semibold text-slate-800">Usage per agent</h3></div>
        {perAgent.length === 0 ? (
          <p className="p-6 text-sm text-slate-500">No per-agent breakdown returned by the API yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 border-b border-slate-100">
                <th className="px-6 py-3 font-semibold">Agent</th>
                <th className="px-6 py-3 font-semibold">Messages</th>
                <th className="px-6 py-3 font-semibold">Conversations</th>
                <th className="px-6 py-3 font-semibold">Documents</th>
              </tr>
            </thead>
            <tbody>
              {perAgent.map((a) => (
                <tr key={a.agent_id || a.agent_name} className="border-b border-slate-50">
                  <td className="px-6 py-3 font-medium text-slate-800">{a.agent_name || a.agent_id}</td>
                  <td className="px-6 py-3 text-slate-600">{a.messages ?? 0}</td>
                  <td className="px-6 py-3 text-slate-600">-</td>
                  <td className="px-6 py-3 text-slate-600">-</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
