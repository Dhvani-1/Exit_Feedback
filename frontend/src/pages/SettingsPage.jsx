import React, { useState, useEffect } from 'react';
import { Info, AlertCircle, Server } from 'lucide-react';
import api from '../services/api';

const SettingsPage = () => {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchSettings = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await api.get('/settings/email');
      setSettings(res.data);
    } catch (err) {
      setError(err.message || 'Failed to load system email settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-sky-500" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-white tracking-tight">System Email & Dispatch Settings</h1>
        <p className="text-xs text-slate-400 mt-1">Inspect actual email sender and system delivery provider configuration</p>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-2xl flex items-center gap-3 text-rose-400 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Configured Email Sender Card */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-5">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider text-slate-400 border-b border-slate-800 pb-3 flex items-center gap-2">
          <Server className="w-4 h-4 text-sky-400" />
          Configured Email Sender
        </h2>

        <div className="space-y-4">
          <div className="p-3.5 bg-slate-950/50 rounded-2xl border border-slate-800/80">
            <span className="text-[11px] font-semibold uppercase text-slate-500 block mb-1">Sender Name</span>
            <span className="text-sm font-bold text-white">{settings?.sender_name || 'Not Configured'}</span>
          </div>

          <div className="p-3.5 bg-slate-950/50 rounded-2xl border border-slate-800/80">
            <span className="text-[11px] font-semibold uppercase text-slate-500 block mb-1">Sender Email</span>
            <span className="text-sm font-mono font-bold text-sky-400">{settings?.sender_email || 'Not Configured'}</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-3.5 bg-slate-950/50 rounded-2xl border border-slate-800/80">
              <span className="text-[11px] font-semibold uppercase text-slate-500 block mb-1">Delivery Provider</span>
              <span className="text-sm font-semibold text-slate-200">{settings?.email_provider}</span>
            </div>

            <div className="p-3.5 bg-slate-950/50 rounded-2xl border border-slate-800/80">
              <span className="text-[11px] font-semibold uppercase text-slate-500 block mb-1">Email Mode</span>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border mt-0.5 ${
                settings?.email_mode === 'Production'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
              }`}>
                {settings?.email_mode}
              </span>
            </div>
          </div>

          <div className="p-3.5 bg-slate-950/50 rounded-2xl border border-slate-800/80 flex items-center justify-between">
            <div>
              <span className="text-[11px] font-semibold uppercase text-slate-500 block">SMTP Secrets / Credentials</span>
              <span className="text-xs text-slate-400">Passwords & API keys are strictly masked</span>
            </div>
            <span className={`px-2.5 py-1 rounded-xl text-xs font-bold border ${
              settings?.is_secret_configured
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                : 'bg-slate-500/10 text-slate-400 border-slate-500/20'
            }`}>
              {settings?.is_secret_configured ? 'Configured' : 'Not Configured'}
            </span>
          </div>

          <div className="p-3 bg-sky-950/30 border border-sky-800/40 rounded-xl text-xs text-slate-400 flex items-center gap-2">
            <Info className="w-4 h-4 text-sky-400 shrink-0" />
            <span>Sender settings managed securely via environment configuration.</span>
          </div>
        </div>
      </div>

      {/* Reset Test Data Banner */}
      <div className="bg-rose-950/20 border border-rose-500/30 rounded-3xl p-6 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <h3 className="text-sm font-bold text-rose-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400" />
            Testing Environment Reset
          </h3>
          <p className="text-xs text-slate-400">
            Clear all created employee records, email jobs, feedback records, and audit logs so you can reuse the same emails repeatedly for testing.
          </p>
        </div>
        <button
          onClick={async () => {
            if (window.confirm('Are you sure you want to clear all test data and logs? Admin users and settings will be preserved.')) {
              try {
                const res = await api.post('/settings/reset-test-data');
                alert(res.data.message);
              } catch (err) {
                alert(err.message || 'Failed to reset test data');
              }
            }
          }}
          className="px-4 py-2.5 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 hover:text-rose-200 text-xs font-bold rounded-xl border border-rose-500/40 transition shrink-0"
        >
          Reset All Test Data & Logs
        </button>
      </div>
    </div>
  );
};

export default SettingsPage;
