import React, { useState, useEffect, useCallback } from 'react';
import { ShieldCheck, Users, Bot, CreditCard, MessageSquare } from 'lucide-react';
import apiService, { apiError } from '../services/api';
import StatCard from '../components/StatCard';
import { Spinner, ErrorBox, EmptyState } from '../components/ui';

export default function Admin() {
  const [overview, setOverview] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setForbidden(false);
    try {
      const [ov, us] = await Promise.allSettled([apiService.getAdminOverview(), apiService.getAdminUsers()]);
      if (ov.status === 'fulfilled') setOverview(ov.value);
      else if (ov.reason?.response?.status === 403) setForbidden(true);
      else setError(apiError(ov.reason, 'Could not load admin overview.'));
      if (us.status === 'fulfilled') setUsers(us.value);
      else if (us.reason?.response?.status === 403) setForbidden(true);
    } catch (err) {
      if (err?.response?.status === 403) setForbidden(true);
      else setError(apiError(err, 'Could not load admin data.'));
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Spinner label="Loading admin overview..." />;
  if (forbidden) {
    return (
      <EmptyState
        icon={ShieldCheck}
        title="Super-admin access required"
        text="This page is only available to super-admin accounts. Your account does not have that role."
      />
    );
  }

  const subs = Array.isArray(overview?.subscriptions) ? overview.subscriptions : [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-extrabold text-slate-900">Super-admin dashboard</h2>
        <p className="text-sm text-slate-500 mt-1">Manage customers, chatbots and subscriptions across all projects.</p>
      </div>
      <ErrorBox message={error} onRetry={load} />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard title="Total Users" value={overview?.total_users ?? users.length ?? 0} icon={Users} description="Registered customers" color="teal" />
        <StatCard title="Total Chatbots" value={overview?.total_agents ?? 0} icon={Bot} description="Chatbots across projects" color="emerald" />
        <StatCard title="Total Messages" value={overview?.total_messages ?? 0} icon={MessageSquare} description="Messages answered" color="blue" />
        <StatCard title="Active Subscriptions" value={overview?.active_subscriptions ?? subs.length ?? 0} icon={CreditCard} description="Paying projects" color="amber" />
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100"><h3 className="font-semibold text-slate-800">Customers ({users.length})</h3></div>
        {users.length === 0 ? (
          <p className="p-6 text-sm text-slate-500">No users returned by the admin endpoint yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b border-slate-100">
                  <th className="px-6 py-3 font-semibold">Name</th>
                  <th className="px-6 py-3 font-semibold">Email</th>
                  <th className="px-6 py-3 font-semibold">Plan</th>
                  <th className="px-6 py-3 font-semibold">Joined</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id || u.email} className="border-b border-slate-50">
                    <td className="px-6 py-3 font-medium text-slate-800">{u.name || 'n/a'}</td>
                    <td className="px-6 py-3 text-slate-600">{u.email}</td>
                    <td className="px-6 py-3"><span className="text-xs font-semibold bg-teal-50 text-teal-700 px-2 py-1 rounded-full capitalize">{u.plan || u.subscription || 'free'}</span></td>
                    <td className="px-6 py-3 text-slate-600">{u.created_at ? new Date(u.created_at).toLocaleDateString() : 'n/a'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {subs.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100"><h3 className="font-semibold text-slate-800">Subscriptions</h3></div>
          <ul className="divide-y divide-slate-100">
            {subs.map((s, i) => (
              <li key={s.id || i} className="px-6 py-3.5 flex items-center justify-between text-sm">
                <span className="font-medium text-slate-800">{s.workspace_name || s.workspace || s.user_email || 'Project'}</span>
                <span className="text-slate-500 capitalize">{s.plan || 'free'} {s.status ? `/ ${s.status}` : ''}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
