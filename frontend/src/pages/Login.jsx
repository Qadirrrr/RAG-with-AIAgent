import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bot, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { apiError } from '../services/api';
import { inputCls, labelCls, btnPrimary } from '../components/ui';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) { setError('Please enter your email and password.'); return; }
    setLoading(true);
    setError(null);
    try {
      await login(email.trim(), password);
      navigate('/');
    } catch (err) {
      setError(apiError(err, 'Login failed. Please check your email and password.'));
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-[#F7F9FB] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-teal-700 text-white flex items-center justify-center mx-auto shadow-lg shadow-teal-200">
            <Bot className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 mt-4">Welcome back</h1>
          <p className="text-sm text-slate-500 mt-1">Log in to your AI Agent workspace.</p>
        </div>
        <form onSubmit={submit} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-5">
          {error && <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-sm text-rose-800">{error}</div>}
          <div>
            <label className={labelCls}>Email</label>
            <input type="email" className={inputCls} value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" autoComplete="email" />
          </div>
          <div>
            <label className={labelCls}>Password</label>
            <input type="password" className={inputCls} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Your password" autoComplete="current-password" />
          </div>
          <button type="submit" disabled={loading} className={btnPrimary + ' w-full'}>
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {loading ? 'Logging in...' : 'Log in'}
          </button>
          <p className="text-center text-sm text-slate-500">
            No account yet? <Link to="/signup" className="font-semibold text-teal-600 hover:text-teal-700">Create one free</Link>
          </p>
          <p className="text-center text-xs text-slate-400">
            <Link to="/landing" className="hover:text-slate-600">Back to home page</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
