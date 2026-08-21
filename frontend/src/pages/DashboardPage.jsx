import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Users, CalendarCheck, Ban, Clock, ArrowRight, UserPlus, AlertCircle, Mail, Send, AlertTriangle, Download, RefreshCw, Loader2, CheckCircle2, Shield, BarChart3, ChevronRight } from 'lucide-react';
import api from '../services/api';
import StatusBadge from '../components/common/StatusBadge';

const DashboardPage = () => {
  // Date filter state
  const [dateFilter, setDateFilter] = useState('all_time');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [customError, setCustomError] = useState('');

  // Overdue threshold
  const [overdueDays, setOverdueDays] = useState(14);

  // Data states
  const [summary, setSummary] = useState(null);
  const [overdueData, setOverdueData] = useState(null);
  const [trendData, setTrendData] = useState(null);
  const [recentEmployees, setRecentEmployees] = useState([]);

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [exportingReport, setExportingReport] = useState(false);

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setCustomError('');

      // Build params
      const params = new URLSearchParams();
      if (dateFilter !== 'all_time') {
        params.append('date_filter', dateFilter);
      }
      if (dateFilter === 'custom') {
        if (!startDate || !endDate) {
          setCustomError('Both start and end dates are required for custom range.');
          setLoading(false);
          return;
        }
        if (new Date(endDate) < new Date(startDate)) {
          setCustomError('End date cannot be prior to start date.');
          setLoading(false);
          return;
        }
        params.append('start_date', startDate);
        params.append('end_date', endDate);
      }

      const [sumRes, overdueRes, trendRes, empRes] = await Promise.all([
        api.get(`/dashboard/summary?${params.toString()}`),
        api.get(`/dashboard/overdue?overdue_days=${overdueDays}`),
        api.get('/dashboard/trends?months=6'),
        api.get('/employees?page=1&page_size=5&sort_by=created_at&sort_order=desc'),
      ]);

      setSummary(sumRes.data);
      setOverdueData(overdueRes.data);
      setTrendData(trendRes.data);
      setRecentEmployees(empRes.data.items);
    } catch (err) {
      setError(err.message || 'Unable to load dashboard data. Please check server connection.');
    } finally {
      setLoading(false);
    }
  }, [dateFilter, startDate, endDate, overdueDays]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleExportReport = async (reportType) => {
    try {
      setExportingReport(true);
      const payload = {
        date_filter: dateFilter,
        start_date: startDate || null,
        end_date: endDate || null,
      };

      const response = await api.post(`/reports/${reportType}`, payload, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const todayStr = new Date().toISOString().split('T')[0];
      link.setAttribute('download', `${reportType}_report_${todayStr}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('Failed to export report file: ' + (err.message || 'Unknown error'));
    } finally {
      setExportingReport(false);
    }
  };

  if (loading && !summary) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <Loader2 className="w-10 h-10 text-sky-500 animate-spin" />
        <p className="text-xs text-slate-400 font-medium">Loading executive dashboard metrics...</p>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="p-6 bg-rose-500/10 border border-rose-500/30 rounded-3xl space-y-4 max-w-xl mx-auto my-12">
        <div className="flex items-center gap-3 text-rose-400">
          <AlertCircle className="w-6 h-6 shrink-0" />
          <div>
            <h3 className="font-bold text-sm">Unable to Load Dashboard Data</h3>
            <p className="text-xs text-rose-300/80 mt-0.5">{error}</p>
          </div>
        </div>
        <button
          onClick={fetchDashboardData}
          className="w-full py-2.5 bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold rounded-xl transition flex items-center justify-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Retry Loading Data
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Top Banner Header & Actions */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-white tracking-tight">HR Management Dashboard</h1>
          <p className="text-xs text-slate-400 mt-1">
            Executive oversight, response rate analytics, overdue tracking, and Excel reporting
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Export Report Actions */}
          <div className="relative group">
            <button
              disabled={exportingReport}
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-emerald-400 text-xs font-bold rounded-xl border border-slate-800 shadow-lg transition disabled:opacity-50"
            >
              {exportingReport ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              Export Excel Report
            </button>

            {/* Dropdown Menu */}
            <div className="absolute right-0 mt-2 w-56 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl py-2 hidden group-hover:block z-30">
              <button
                onClick={() => handleExportReport('employees')}
                className="w-full text-left px-4 py-2 text-xs text-slate-200 hover:bg-slate-800 hover:text-emerald-400 transition"
              >
                Employee Feedback Report
              </button>
              <button
                onClick={() => handleExportReport('feedback')}
                className="w-full text-left px-4 py-2 text-xs text-slate-200 hover:bg-slate-800 hover:text-emerald-400 transition"
              >
                Feedback Lifecycle Report
              </button>
              <button
                onClick={() => handleExportReport('email-jobs')}
                className="w-full text-left px-4 py-2 text-xs text-slate-200 hover:bg-slate-800 hover:text-emerald-400 transition"
              >
                Email Delivery Report
              </button>
            </div>
          </div>

          <Link
            to="/employees/new"
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-sky-600 to-cyan-600 hover:from-sky-500 hover:to-cyan-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-sky-900/30 transition shrink-0"
          >
            <UserPlus className="w-4 h-4" />
            Add Exiting Employee
          </Link>
        </div>
      </div>

      {/* Date Filter Bar */}
      <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-2xl shadow-lg space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
            <CalendarCheck className="w-4 h-4 text-sky-400" />
            <span>Feedback & Operations Date Range</span>
          </div>

          {/* Quick Select Buttons */}
          <div className="flex flex-wrap items-center gap-1.5 bg-slate-950/80 p-1 rounded-xl border border-slate-800 text-xs">
            {[
              { id: 'all_time', label: 'All Time' },
              { id: 'today', label: 'Today' },
              { id: 'last_7_days', label: 'Last 7 Days' },
              { id: 'last_30_days', label: 'Last 30 Days' },
              { id: 'this_month', label: 'This Month' },
              { id: 'prev_month', label: 'Prev Month' },
              { id: 'custom', label: 'Custom Range' },
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => setDateFilter(item.id)}
                className={`px-3 py-1.5 rounded-lg font-semibold transition ${
                  dateFilter === item.id
                    ? 'bg-sky-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* Custom Range Inputs */}
        {dateFilter === 'custom' && (
          <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-slate-800/80 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Start Date:</span>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-sky-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-400">End Date:</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-white focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>
        )}

        {customError && (
          <p className="text-xs text-rose-400 font-semibold">{customError}</p>
        )}
      </div>

      {/* KPI GRID 1: FEEDBACK METRICS & RESPONSE RATE */}
      <div>
        <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <CalendarCheck className="w-4 h-4 text-emerald-400" />
          Feedback Metrics & Response Rate
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="p-5 rounded-2xl bg-gradient-to-br from-indigo-900/30 to-blue-900/30 border border-indigo-500/30 backdrop-blur-xl">
            <div className="flex items-center justify-between text-xs font-semibold text-indigo-300 uppercase tracking-wider">
              <span>Feedback Response Rate</span>
              <BarChart3 className="w-4 h-4" />
            </div>
            <div className="mt-3 text-3xl font-extrabold text-white tracking-tight font-mono">
              {summary?.feedback?.response_rate || 0}%
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              {summary?.feedback?.eligible_cycles > 0
                ? `${summary?.feedback?.submitted} submitted of ${summary?.feedback?.eligible_cycles} eligible SENT cycles`
                : 'No eligible feedback cycles yet'}
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
            <div className="flex items-center justify-between text-xs font-semibold text-amber-400 uppercase tracking-wider">
              <span>Pending Feedback</span>
              <Clock className="w-4 h-4" />
            </div>
            <div className="mt-3 text-2xl font-extrabold text-white tracking-tight font-mono">
              {summary?.feedback?.pending || 0}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Active valid forms awaiting submission</p>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
            <div className="flex items-center justify-between text-xs font-semibold text-emerald-400 uppercase tracking-wider">
              <span>Submitted Responses</span>
              <CheckCircle2 className="w-4 h-4" />
            </div>
            <div className="mt-3 text-2xl font-extrabold text-white tracking-tight font-mono">
              {summary?.feedback?.submitted || 0}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Total completed feedback submissions</p>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider">
              <span>Expired Feedback</span>
              <Ban className="w-4 h-4" />
            </div>
            <div className="mt-3 text-2xl font-extrabold text-white tracking-tight font-mono">
              {summary?.feedback?.expired || 0}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Forms past expiration threshold</p>
          </div>
        </div>
      </div>

      {/* KPI GRID 2: EMPLOYEE, EMAIL & REMINDER METRICS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Employee Summary */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-5 shadow-xl space-y-3">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
            <Users className="w-4 h-4 text-sky-400" />
            Employee Metrics
          </h3>
          <div className="grid grid-cols-3 gap-2 text-center pt-1">
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-2xl">
              <div className="text-[11px] text-slate-400">Total</div>
              <div className="text-lg font-bold text-white font-mono mt-0.5">{summary?.employees?.total || 0}</div>
            </div>
            <div className="p-3 bg-emerald-950/30 border border-emerald-800/40 rounded-2xl">
              <div className="text-[11px] text-emerald-400">Scheduled</div>
              <div className="text-lg font-bold text-emerald-400 font-mono mt-0.5">{summary?.employees?.scheduled || 0}</div>
            </div>
            <div className="p-3 bg-rose-950/30 border border-rose-800/40 rounded-2xl">
              <div className="text-[11px] text-rose-400">Cancelled</div>
              <div className="text-lg font-bold text-rose-400 font-mono mt-0.5">{summary?.employees?.cancelled || 0}</div>
            </div>
          </div>
        </div>

        {/* Initial Email Dispatches */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-5 shadow-xl space-y-3">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
            <Mail className="w-4 h-4 text-sky-400" />
            Initial Email Dispatches
          </h3>
          <div className="grid grid-cols-3 gap-2 text-center pt-1">
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-2xl">
              <div className="text-[11px] text-slate-400">Scheduled</div>
              <div className="text-lg font-bold text-sky-400 font-mono mt-0.5">{summary?.emails?.scheduled || 0}</div>
            </div>
            <div className="p-3 bg-emerald-950/30 border border-emerald-800/40 rounded-2xl">
              <div className="text-[11px] text-emerald-400">Sent</div>
              <div className="text-lg font-bold text-emerald-400 font-mono mt-0.5">{summary?.emails?.sent || 0}</div>
            </div>
            <div className="p-3 bg-rose-950/30 border border-rose-800/40 rounded-2xl">
              <div className="text-[11px] text-rose-400">Failed</div>
              <div className="text-lg font-bold text-rose-400 font-mono mt-0.5">{summary?.emails?.failed || 0}</div>
            </div>
          </div>
        </div>

        {/* Reminder Stages */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-5 shadow-xl space-y-3">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
            <Send className="w-4 h-4 text-indigo-400" />
            Reminders Sent
          </h3>
          <div className="grid grid-cols-3 gap-2 text-center pt-1">
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-2xl">
              <div className="text-[11px] text-slate-400">Reminder 1</div>
              <div className="text-lg font-bold text-indigo-400 font-mono mt-0.5">{summary?.reminders?.reminder_1_sent || 0}</div>
            </div>
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-2xl">
              <div className="text-[11px] text-slate-400">Reminder 2</div>
              <div className="text-lg font-bold text-indigo-400 font-mono mt-0.5">{summary?.reminders?.reminder_2_sent || 0}</div>
            </div>
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-2xl">
              <div className="text-[11px] text-slate-400">Cancelled</div>
              <div className="text-lg font-bold text-slate-400 font-mono mt-0.5">{summary?.reminders?.reminder_cancelled || 0}</div>
            </div>
          </div>
        </div>
      </div>

      {/* MONTHLY TRENDS & STAGE CLASSIFICATION */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Monthly Trend Chart */}
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-sky-400" />
              Monthly Feedback Lifecycle Trend (Last 6 Months)
            </h3>
            <div className="flex items-center gap-4 text-[11px]">
              <span className="flex items-center gap-1 text-sky-400 font-semibold">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-400 inline-block" /> Due
              </span>
              <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 inline-block" /> Submitted
              </span>
            </div>
          </div>

          <div className="space-y-4 pt-2">
            {trendData?.series && trendData.series.length > 0 ? (
              trendData.series.map((item, idx) => {
                const maxVal = Math.max(...trendData.series.map((s) => Math.max(s.feedback_due, s.feedback_submitted)), 1);
                const duePct = Math.min(Math.round((item.feedback_due / maxVal) * 100), 100);
                const subPct = Math.min(Math.round((item.feedback_submitted / maxVal) * 100), 100);

                return (
                  <div key={idx} className="space-y-1.5 text-xs">
                    <div className="flex justify-between font-mono font-semibold text-slate-300">
                      <span>{item.month}</span>
                      <span className="text-[11px] text-slate-400">
                        Due: {item.feedback_due} | Submitted: {item.feedback_submitted}
                      </span>
                    </div>

                    <div className="space-y-1">
                      <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden flex">
                        <div className="bg-sky-500 h-full rounded-full transition-all duration-500" style={{ width: `${duePct}%` }} />
                      </div>
                      <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden flex">
                        <div className="bg-emerald-500 h-full rounded-full transition-all duration-500" style={{ width: `${subPct}%` }} />
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-xs text-slate-500 italic py-6 text-center">No trend data recorded for recent months.</p>
            )}
          </div>
        </div>

        {/* Submissions by Reminder Stage */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4 flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800 pb-3 flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-400" />
              Submissions by Reminder Stage
            </h3>
            <p className="text-[11px] text-slate-400 mt-2">
              Descriptive classification of feedback responses by the latest SENT reminder stage at submission time.
            </p>

            <div className="space-y-3 mt-4">
              <div className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-2xl flex items-center justify-between">
                <span className="text-xs text-slate-300 font-semibold">Submitted Before Reminder 1</span>
                <span className="text-sm font-bold text-sky-400 font-mono">
                  {summary?.reminders?.submissions_by_stage?.submitted_before_reminder_1 || 0}
                </span>
              </div>
              <div className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-2xl flex items-center justify-between">
                <span className="text-xs text-slate-300 font-semibold">Submitted After Reminder 1</span>
                <span className="text-sm font-bold text-indigo-400 font-mono">
                  {summary?.reminders?.submissions_by_stage?.submitted_after_reminder_1 || 0}
                </span>
              </div>
              <div className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-2xl flex items-center justify-between">
                <span className="text-xs text-slate-300 font-semibold">Submitted After Reminder 2</span>
                <span className="text-sm font-bold text-purple-400 font-mono">
                  {summary?.reminders?.submissions_by_stage?.submitted_after_reminder_2 || 0}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800/80 text-[10px] text-slate-500 italic">
            Note: Counts represent stage timing rather than direct causal attribution.
          </div>
        </div>
      </div>

      {/* OVERDUE FEEDBACK TABLE */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-3xl shadow-xl overflow-hidden space-y-4">
        <div className="p-6 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold text-white">Overdue Feedback Requests</h2>
              <span className="px-2.5 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-extrabold rounded-full font-mono">
                {overdueData?.overdue_count || 0} Requiring HR Attention
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Active PENDING feedback cycles where initial email was sent and threshold (&gt;{overdueDays} days) has passed
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400">Overdue Threshold:</span>
            <select
              value={overdueDays}
              onChange={(e) => setOverdueDays(Number(e.target.value))}
              className="px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-white font-semibold focus:outline-none focus:border-amber-500 cursor-pointer"
            >
              <option value={7}>7 Days</option>
              <option value={14}>14 Days (Default)</option>
              <option value={21}>21 Days</option>
              <option value={30}>30 Days</option>
            </select>
          </div>
        </div>

        {overdueData?.items && overdueData.items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-950/60 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
                  <th className="py-3.5 px-6">Full Name</th>
                  <th className="py-3.5 px-6">Personal Email</th>
                  <th className="py-3.5 px-6">Last Working Date</th>
                  <th className="py-3.5 px-6">Feedback Due Date</th>
                  <th className="py-3.5 px-6">Initial Email Sent At</th>
                  <th className="py-3.5 px-6">Days Pending</th>
                  <th className="py-3.5 px-6">Latest Reminder Status</th>
                  <th className="py-3.5 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {overdueData.items.map((item) => (
                  <tr key={item.employee_id} className="hover:bg-slate-800/40 transition">
                    <td className="py-4 px-6 font-semibold text-white">{item.full_name}</td>
                    <td className="py-4 px-6 text-slate-400 font-mono text-[11px]">{item.personal_email}</td>
                    <td className="py-4 px-6 font-medium text-slate-300">{item.last_working_date}</td>
                    <td className="py-4 px-6 font-semibold text-amber-300">{item.feedback_due_date}</td>
                    <td className="py-4 px-6 font-mono text-slate-400">{item.initial_email_sent_at || '—'}</td>
                    <td className="py-4 px-6 font-bold text-amber-400 font-mono">
                      {item.days_pending} Days
                    </td>
                    <td className="py-4 px-6">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                        {item.latest_reminder_status}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <Link
                        to={`/employees/${item.employee_id}`}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-sky-400 hover:text-sky-300 transition"
                      >
                        View Record
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500 text-sm italic">
            No overdue feedback requests currently pending past the {overdueDays}-day response threshold.
          </div>
        )}
      </div>
    </div>
  );
};

export default DashboardPage;
