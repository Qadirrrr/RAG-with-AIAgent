import React, { useState, useEffect, useCallback } from 'react';
import { CreditCard, Check, Loader2 } from 'lucide-react';
import apiService, { apiError, FALLBACK_PLANS } from '../services/api';
import { useWorkspace } from '../context/WorkspaceContext';
import { Spinner, ErrorBox, EmptyState } from '../components/ui';

export default function Billing() {
  const { selectedId, selected } = useWorkspace();
  const [plans, setPlans] = useState(FALLBACK_PLANS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [changing, setChanging] = useState(null);
  const [notice, setNotice] = useState(null);

  const currentPlanId = selected?.plan || selected?.subscription?.plan || selected?.plan_id || 'free';

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await apiService.getPlans();
      if (list && list.length > 0) setPlans(list);
    } catch (err) {
      setError(apiError(err, 'Could not load plans from the API. Showing standard plans.'));
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const changePlan = async (plan) => {
    if (!selectedId) { setError('Select a workspace first.'); return; }
    setChanging(plan.id || plan.name);
    setNotice(null);
    setError(null);
    try {
      await apiService.changeSubscription(selectedId, plan.id || plan.name);
      setNotice(`Plan changed to ${plan.name}. Your project is now on the ${plan.name} plan.`);
    } catch (err) {
      setError(apiError(err, 'Could not change plan.'));
    } finally { setChanging(null); }
  };

  if (loading) return <Spinner label="Loading plans..." />;
  if (!selectedId) return <EmptyState icon={CreditCard} title="No workspace selected" text="Select a workspace from the sidebar to manage its subscription." />;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-extrabold text-slate-900">Billing and plans</h2>
        <p className="text-sm text-slate-500 mt-1">Current plan for <span className="font-semibold text-slate-700">{selected?.name}</span>: <span className="font-semibold text-teal-700 capitalize">{currentPlanId}</span></p>
      </div>
      <ErrorBox message={error} onRetry={load} />
      {notice && <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-sm text-emerald-800">{notice}</div>}
      <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl text-sm text-amber-800">
        Payment checkout is manual for this MVP: changing a plan here records the new plan on the project. Online card checkout is not connected yet, and no fake Stripe checkout is shown.
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {plans.map((plan) => {
          const id = plan.id || plan.name?.toLowerCase();
          const isCurrent = String(currentPlanId).toLowerCase() === String(id).toLowerCase();
          const features = plan.features || [
            `${plan.agents_limit ?? '?'} AI agents`,
            `${plan.messages_limit ?? '?'} messages per month`,
            `${plan.documents_limit ?? '?'} documents`,
          ];
          return (
            <div key={id} className={`rounded-2xl border p-6 flex flex-col ${isCurrent ? 'border-teal-600 ring-2 ring-teal-100 bg-teal-50/40' : 'border-slate-200 bg-white'}`}>
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-slate-900">{plan.name}</h3>
                {isCurrent && <span className="text-[11px] font-bold bg-teal-700 text-white px-2 py-0.5 rounded-full">Current</span>}
              </div>
              <p className="mt-2"><span className="text-3xl font-extrabold text-slate-900">${plan.price ?? 0}</span><span className="text-sm text-slate-500"> / {plan.interval || 'month'}</span></p>
              <ul className="mt-5 space-y-2.5 flex-1">
                {features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-slate-600"><Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />{f}</li>
                ))}
              </ul>
              <button
                onClick={() => changePlan(plan)}
                disabled={isCurrent || changing === id}
                className={`mt-6 font-semibold px-4 py-2.5 rounded-xl text-sm ${isCurrent ? 'bg-slate-100 text-slate-400 cursor-default' : 'bg-teal-700 hover:bg-teal-800 text-white'}`}
              >
                {changing === id ? <span className="inline-flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Changing...</span> : isCurrent ? 'Current plan' : `Change to ${plan.name}`}
              </button>
            </div>
          );
        })}
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-800 mb-3">Usage limits by plan</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 border-b border-slate-100">
                <th className="py-2 pr-4 font-semibold">Plan</th>
                <th className="py-2 pr-4 font-semibold">Chatbots</th>
                <th className="py-2 pr-4 font-semibold">Messages / month</th>
                <th className="py-2 font-semibold">Documents</th>
              </tr>
            </thead>
            <tbody>
              {plans.map((p) => (
                <tr key={p.id || p.name} className="border-b border-slate-50">
                  <td className="py-2.5 pr-4 font-medium text-slate-800">{p.name}</td>
                  <td className="py-2.5 pr-4 text-slate-600">{p.agents_limit ?? 'n/a'}</td>
                  <td className="py-2.5 pr-4 text-slate-600">{p.messages_limit ?? 'n/a'}</td>
                  <td className="py-2.5 text-slate-600">{p.documents_limit ?? 'n/a'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
