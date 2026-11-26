import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bot, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { apiError } from '../services/api';
import { inputCls, labelCls, btnPrimary } from '../components/ui';

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !email.trim() || password.length < 8) {
      setError('Please enter your name, a valid email and a password of at least 8 characters.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await signup(name.trim(), email.trim(), password);
      navigate('/');
    } catch (err) {
      setError(apiError(err, 'Signup failed. This email may already be registered.'));
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-[#F7F9FB] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-teal-700 text-white flex items-center justify-center mx-auto shadow-lg shadow-teal-200">
            <Bot className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 mt-4">Create your account</h1>
          <p className="text-sm text-slate-500 mt-1">Build your first chatbot in minutes, no code needed.</p>
        </div>
        <form onSubmit={submit} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-5">
          {error && <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-sm text-rose-800">{error}</div>}
          <div>
            <label className={labelCls}>Full name</label>
            <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" autoComplete="name" />
          </div>
          <div>
            <label className={labelCls}>Email</label>
            <input type="email" className={inputCls} value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" autoComplete="email" />
          </div>
          <div>
            <label className={labelCls}>Password</label>
            <input type="password" className={inputCls} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" autoComplete="new-password" />
          </div>
          <button type="submit" disabled={loading} className={btnPrimary + ' w-full'}>
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {loading ? 'Creating account...' : 'Create free account'}
          </button>
          <p className="text-center text-sm text-slate-500">
            Already have an account? <Link to="/login" className="font-semibold text-teal-600 hover:text-teal-700">Log in</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
