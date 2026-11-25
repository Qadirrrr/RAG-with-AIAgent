import React from 'react';
import { Link } from 'react-router-dom';
import { Sparkles, Bot, FileText, MessageSquare, BarChart3, Plug, ShieldCheck, Check, ArrowRight } from 'lucide-react';
import { FALLBACK_PLANS } from '../services/api';

const features = [
  { icon: Bot, title: 'Multiple AI agents', text: 'Create a separate agent for support, sales, onboarding or internal knowledge, each with its own instructions and personality.' },
  { icon: FileText, title: 'RAG knowledge base', text: 'Upload PDF, DOCX and TXT files or add website URLs. Documents are chunked, embedded and stored in ChromaDB for accurate answers with sources.' },
  { icon: MessageSquare, title: 'Playground testing', text: 'Test every agent in a live chat playground before you publish it, and review real conversations from your customers.' },
  { icon: Plug, title: 'Website widget and API', text: 'Embed a chat widget on any website with one script tag, or call the REST API from your own app with a secure API key.' },
  { icon: BarChart3, title: 'Analytics and usage', text: 'Track messages, agents, documents and usage against your plan limits, and see which agents your visitors use most.' },
  { icon: ShieldCheck, title: 'Secure multi-tenant data', text: 'Every workspace has a separate knowledge base. Customers can only access their own agents, documents and conversations.' },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-600 text-white flex items-center justify-center"><Sparkles className="w-5 h-5" /></div>
            <span className="font-bold text-lg tracking-tight">RAG Agent</span>
            <span className="hidden sm:inline text-[11px] font-medium text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">SaaS Platform</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm font-semibold text-slate-600 hover:text-slate-900 px-3 py-2">Log in</Link>
            <Link to="/signup" className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-4 py-2 rounded-xl text-sm">Start free</Link>
          </div>
        </div>
      </header>

      <main>
        <section className="max-w-7xl mx-auto px-4 sm:px-8 py-16 sm:py-24 text-center">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100">
            Powered by LangChain, ChromaDB, OpenAI and Google Gemini
          </span>
          <h1 className="mt-6 text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 leading-tight">
            Build an AI agent that knows your business
          </h1>
          <p className="mt-5 text-base sm:text-lg text-slate-500 max-w-2xl mx-auto leading-relaxed">
            Sign up, upload your documents, and launch a smart support agent on your website in minutes. No programming knowledge needed.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to="/signup" className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-6 py-3 rounded-xl text-sm shadow-md">
              Create your first agent <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/login" className="inline-flex items-center gap-2 bg-white hover:bg-slate-50 text-slate-700 font-semibold px-6 py-3 rounded-xl text-sm border border-slate-200">
              Log in to dashboard
            </Link>
          </div>
        </section>

        <section className="max-w-7xl mx-auto px-4 sm:px-8 pb-16">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 text-center">Everything you need to launch</h2>
          <p className="text-sm text-slate-500 text-center mt-2">From knowledge upload to website widget, all in one dashboard.</p>
          <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((f) => {
              const Icon = f.icon;
              return (
                <div key={f.title} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
                  <div className="w-11 h-11 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4"><Icon className="w-5 h-5" /></div>
                  <h3 className="font-semibold text-slate-900">{f.title}</h3>
                  <p className="text-sm text-slate-500 mt-1.5 leading-relaxed">{f.text}</p>
                </div>
              );
            })}
          </div>
        </section>

        <section className="bg-white border-y border-slate-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-8 py-16">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 text-center">Simple pricing that grows with you</h2>
            <p className="text-sm text-slate-500 text-center mt-2">Start free. Upgrade when your agents get busy.</p>
            <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {FALLBACK_PLANS.map((plan) => (
                <div key={plan.id} className={`rounded-2xl border p-6 ${plan.id === 'pro' ? 'border-indigo-600 ring-2 ring-indigo-100 bg-indigo-50/40' : 'border-slate-200 bg-white'}`}>
                  <h3 className="font-bold text-slate-900">{plan.name}</h3>
                  <p className="mt-2"><span className="text-3xl font-extrabold text-slate-900">${plan.price}</span><span className="text-sm text-slate-500"> / month</span></p>
                  <ul className="mt-5 space-y-2.5">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-start gap-2 text-sm text-slate-600"><Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />{f}</li>
                    ))}
                  </ul>
                  <Link to="/signup" className={`mt-6 block text-center font-semibold px-4 py-2.5 rounded-xl text-sm ${plan.id === 'pro' ? 'bg-indigo-600 text-white hover:bg-indigo-700' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}>
                    Choose {plan.name}
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="max-w-7xl mx-auto px-4 sm:px-8 py-16 text-center">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900">Ready to answer your customers, day and night?</h2>
          <p className="text-sm text-slate-500 mt-2">Create a free account and publish your first agent today.</p>
          <Link to="/signup" className="mt-6 inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-6 py-3 rounded-xl text-sm">
            Start free <ArrowRight className="w-4 h-4" />
          </Link>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-8 py-6 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500">
          <span>RAG Agent SaaS Platform</span>
          <span>Secure multi-tenant AI agents with real RAG retrieval.</span>
        </div>
      </footer>
    </div>
  );
}
